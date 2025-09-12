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
from catalyst.constants import LLM_MODEL, MAX_TOKENS1, LLM_TEMP1

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

llm = ChatCerebras(
        model=LLM_MODEL, 
        api_key=CEREBRAS_API_KEY,
        temperature=LLM_TEMP1,
        max_tokens=MAX_TOKENS1
    )

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
        profile = UserProfile.objects.get(user_id=user_id)

        user_data = {
            "learning_streak": profile.learning_streak or 0,
            "strong_topics": ", ".join(profile.strong_topics) if profile.strong_topics else "None",
            "weak_topics": ", ".join(profile.weak_topics) if profile.weak_topics else "None",
            "average_accuracy": round(profile.average_accuracy or 0.0, 2),
            "avg_difficulty": profile.avg_difficulty or "medium",
            "average_time_per_question": round(profile.average_time_per_question or 0.0, 1),
            "taste_keywords_list": profile.taste_keywords_list or []
        }

        template = """
        You are an expert AI learning coach. Analyze the following weekly metrics and generate a clear, 3-part summary:

        === USER PERFORMANCE DATA ===
        - Learning Streak: {learning_streak} days
        - Strong Topics: {strong_topics}
        - Weak Topics: {weak_topics}
        - Average Accuracy: {average_accuracy}%
        - Average Difficulty Attempted: {avg_difficulty}
        - Average Time per Question: {average_time_per_question} seconds
        - Taste Keywords List: {taste_keywords_list}

        === TASK ===
        1. Write a short paragraph summarizing the user's current learning behavior and style (e.g., cautious, fast-paced, high-achiever, etc.).
        2. Suggest how curriculum blocks should be adapted to this learner (e.g., start simple, mix topics, reinforce weaknesses first, etc.).
        3. Give 2-3 roadmap-specific tips that could help improve performance or motivation.

        Keep it concise, grounded in the data, and easy for an LLM or a human coach to reuse in a personalized roadmap.
        """
        prompt = PromptTemplate.from_template(template)
        chain = LLMChain(llm=llm, prompt=prompt)

        summary = chain.run(user_data).strip()

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
