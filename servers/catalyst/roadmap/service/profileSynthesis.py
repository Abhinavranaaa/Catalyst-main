import logging
from typing import Dict
from django.core.exceptions import ObjectDoesNotExist
from users.models import UserProfile
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_cerebras import ChatCerebras
from django.conf import settings
import os
from dotenv import load_dotenv
from catalyst.constants import LLM_MODEL_PROFILE, MAX_TOKENS1, LLM_TEMP1, PROFILE_TEMPLATE_2
from catalyst.utils import remove_think_blocks 
import time
from upstash_redis import Redis

redis = Redis.from_env()
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..','..'))
if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

llm = ChatCerebras(
        model=LLM_MODEL_PROFILE, 
        api_key=CEREBRAS_API_KEY,
        temperature=LLM_TEMP1,
        max_tokens=MAX_TOKENS1
    )

def fetchUsrProfile(user_id: str) -> str:
    key= f"user_profile:{user_id}"
    cached=redis.get(key)
    if cached:
        return cached
    profile = buildUserProfile(user_id)
    redis.set(key,profile['summary'],ex=86400)
    return profile['summary']


def buildUserProfile(user_id: str) -> Dict[str, str]:
    """
    Generate a rich but concise user learning profile summary using precomputed and cached data.
    
    Args:
        user_id: Unique identifier for the learner.
    
    Returns:
        Dict containing:
            - 'user_id': The ID
            - 'summary': AI-generated learning snapshot
            - 'raw': Raw structured data sent to the LLM
    """
    try:
        start=time.time()
        profile = UserProfile.objects.get(user_id=user_id)
        end=time.time()
        logger.info(f"Supabase latency for user profile: {end - start:.3f} seconds")

        user_data = {
            "learning_streak": profile.learning_streak or 0,
            "strong_topics": ", ".join(profile.strong_topics) if profile.strong_topics else "None",
            "weak_topics": ", ".join(profile.weak_topics) if profile.weak_topics else "None",
            "average_accuracy": round(profile.average_accuracy or 0.0, 2),
            "avg_difficulty": profile.avg_difficulty or "medium",
            "average_time_per_question": round(profile.average_time_per_question or 0.0, 1),
            "taste_keywords_list": profile.taste_keywords_list or []
        }

        template = PROFILE_TEMPLATE_2
        prompt = PromptTemplate.from_template(template)
        chain = LLMChain(llm=llm, prompt=prompt)
        start = time.time()
        summary = remove_think_blocks(chain.run(user_data))
        # logger.info("LLM summary generated: %s", summary)
        end = time.time()
        logger.info(f"Cerebras LLM profile latency: {end - start:.3f} seconds")

        return {
            "user_id": user_id,
            "summary": summary,
            "raw": user_data
        }

    except ObjectDoesNotExist:
        logger.warning(f"UserProfile not found for user {user_id}. Returning fallback profile.")
        return _fallback_user_profile(user_id)

    except Exception as e:
        logger.error(f"Error generating user profile for {user_id}: {e}", exc_info=True)
        return _fallback_user_profile(user_id)
    

def _fallback_user_profile(user_id: str) -> Dict[str, str]:
    """Return a generic fallback profile if user-specific generation fails."""
    return {
        "user_id": user_id,
        "raw": {},
        "summary": (
            "New learner with minimal performance data. Default roadmap should start with basics, "
            "gradually increase difficulty, and assess topic strengths through early feedback blocks."
        )
    }
