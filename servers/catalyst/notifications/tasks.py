# notifications/tasks.py

from celery import shared_task
from users.models import UserProfile
from notifications.services.qloo_service import fetch_qloo_interests, deduplicate_interests
from notifications.models import Notification
from notifications.observer import EmailObserver, PushObserver, NotificationDistributor
import logging
import os
from dotenv import load_dotenv
from langchain import LLMChain
from langchain_cerebras import ChatCerebras
from langchain.prompts import PromptTemplate
from django.conf import settings
from catalyst.constants import NOTIFICATION_PROMPT_TEMPLATE, LLM_TEMP, MAX_TOKENS1, LLM_MODEL
import re
from collections import Counter
import nltk
from nltk.corpus import stopwords
import random
from nltk import pos_tag, word_tokenize, bigrams

logger = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))

if os.getenv("RENDER") != "true":
    load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

if not CEREBRAS_API_KEY:
    raise Exception("CEREBRAS_API_KEY is missing. Please set it as an environment variable.")

@shared_task
def process_user_interests_async(user_id, comments):
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        extracted = extract_keywords_from_comments(comments)
        qloo_interests = fetch_qloo_interests(extracted) 
        qloo_keywords = []
        for item in qloo_interests:
            keyword = item.get('name') or item.get('keyword') or item.get('tag')
            if keyword:
                qloo_keywords.append(keyword)

        combined = list(set(extracted + qloo_keywords)) 

        existing_list = profile.taste_keywords_list or []
        existing_embeds = profile.embedding_list or []

        deduped = deduplicate_interests(existing_list, existing_embeds, combined)
        if deduped:
            updated_list = existing_list + [item[0] for item in deduped]
            updated_embeds = existing_embeds + [item[1] for item in deduped]
            profile.taste_keywords_list = updated_list
            profile.embedding_list = updated_embeds
            profile.save()
    except Exception as e:
        logger.error(f"Processing of user interests failed for user {user_id}: {e}")
        pass


def extract_keywords_from_comments(comments, top_n=10):
    comments = comments.lower()
    tokens = re.findall(r'\b[a-z0-9]+\b', comments)
    
    stop_words = set(stopwords.words('english'))
    stop_words.update({'lover', 'lovers', 'love','like','want'}) 
    tagged = pos_tag(tokens)
    meaningful_words = [word for word, pos in tagged if pos in ('NN', 'NNS', 'NNP', 'NNPS') and word not in stop_words and len(word) > 3]
    bigram_list = [' '.join(bg) for bg in bigrams(meaningful_words)]
    combined = meaningful_words + bigram_list
    freq = Counter(combined)
    return [word for word, _ in freq.most_common(top_n)]

@shared_task(bind=True, max_retries=2, default_retry_delay=7200)
def send_daily_notifications(self):
    distributor = NotificationDistributor()
    distributor.register(EmailObserver())
    distributor.register(PushObserver())

    llm = ChatCerebras(
        model=LLM_MODEL,
        api_key=CEREBRAS_API_KEY,
        temperature=LLM_TEMP,
        max_tokens=MAX_TOKENS1
    )
    NOTIFICATION_PROMPT = NOTIFICATION_PROMPT_TEMPLATE
    prompt = PromptTemplate.from_template(NOTIFICATION_PROMPT)
    chain = LLMChain(llm=llm, prompt=prompt)

    profiles = UserProfile.objects.select_related('user').all()

    for profile in profiles:
        user = profile.user

        if not user.email:
            logger.info(f"Skipping user {user.id} due to missing email.")
            continue

        interests = profile.taste_keywords_list or []
        if not interests:
            message = "Keep up your learning journey! Explore new topics and stay curious."
            keyword_used = ""
            logger.debug(f"No interests for user {user.id}. Using fallback message.")
        else:
            last_notification = (
                Notification.objects.filter(user=user)
                .order_by('-created_at')
                .first()
            )
            
            last_keyword = None
            if last_notification and last_notification.keyword_used:
                last_keyword = last_notification.keyword_used.strip().lower()

            available_keywords = [kw for kw in interests if kw.lower() != last_keyword]

            if not available_keywords:
                chosen_keyword = random.choice(interests)
            else:
                chosen_keyword = random.choice(available_keywords)

            keyword_used = chosen_keyword

            try:
                output = chain.run(interests=keyword_used)
                message = output.strip()
                if not message or len(message) < 10:
                    raise ValueError("LLM returned empty or too short message.")
            except Exception as exc:
                logger.error(f"LLM generation failed for user {user.id}: {exc}")
                message = f"Based on your interest ({keyword_used}), we’ve curated new learning content for you!"

        Notification.objects.create(
            user=user,
            message=message,
            channel="email",
            keyword_used=keyword_used if keyword_used else ""
        )

        try:
            distributor.notify(user, message, keyword_used=keyword_used)
        except Exception as e:
            logger.error(f"Failed to send notification to user {user.id}: {e}")
            raise self.retry(exc=exc)

