import json
import random
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from users.models import UserProfile 

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
