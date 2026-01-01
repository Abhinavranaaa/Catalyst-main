import json
import random
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from users.models import UserProfile 
from typing import Optional, List
import logging

logger=logging.getLogger(__name__)
User = get_user_model()

with open(settings.BASE_DIR / 'mock_data' / 'user_profiles.json') as f:
    MOCKED_PROFILES = json.load(f)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        random_profile = random.choice(MOCKED_PROFILES)
        UserProfile.objects.create(
            user=instance,
            learning_streak=random_profile.get('learning_streak'),
            strong_topics=random_profile.get('strong_topics', []),
            weak_topics=random_profile.get('weak_topics', []),
            average_accuracy=random_profile.get('average_accuracy'),
            avg_difficulty=random_profile.get('avg_difficulty'),
            average_time_per_question=random_profile.get('average_time_per_question'),
            taste_keywords_list=random_profile.get('taste_keywords_list')
        )

def saveAndProcessUser(
    user_id: str,
    primary_goal: str,
    daily_target_time: Optional[int] = None,
    interests: Optional[List[str]] = None
):
    """
    Saves onboarding data and updates taste keywords safely.
    """
    try:
        profile = UserProfile.objects.get(user_id=user_id)
        profile.primary_goal_onboarding = primary_goal
        if daily_target_time is not None:
            profile.daily_target_time = daily_target_time

        if interests:
            existing_keywords = profile.taste_keywords_list or []
            merged_keywords = list(dict.fromkeys(existing_keywords + interests))
            profile.taste_keywords_list = merged_keywords

        profile.save()
        return profile

    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile not found for user_id={user_id}")
        return None

    except Exception as e:
        logger.exception(
            f"Failed to save onboarding data for user_id={user_id}: {e}"
        )
        return None

    
