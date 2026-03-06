from .analyticsUpdater import AnalyticsUpdater
from ..models import UserStats
from datetime import timedelta
import logging
from django.db import IntegrityError

logger = logging.getLogger(__name__)
class AnalyticsUpdaterUserStats(AnalyticsUpdater):
    def update(self, user_id, attempts):
        if not attempts:
            return
        try:
            stats = UserStats.objects.select_for_update().get(user_id=user_id)
        except UserStats.DoesNotExist:
            logger.info(f'init user stats for user{user_id}')
            try:
                stats = UserStats.objects.create(
                    user_id=user_id,
                    total_attempted=0,
                    total_time_spent_seconds=0,
                    current_streak=0,
                    max_streak=0,
                    easy_correct=0,
                    medium_correct=0,
                    hard_correct=0,
                )
            except IntegrityError:
                stats = UserStats.objects.select_for_update().get(user_id=user_id)

        for attempt in attempts:
            
            stats.total_attempted+=1
            if attempt.time_taken_seconds:
                stats.total_time_spent_seconds+=attempt.time_taken_seconds
            
            if attempt.is_correct:
                difficulty = attempt.question.difficulty.strip().lower()

                if difficulty == "easy":
                    stats.easy_correct += 1
                elif difficulty == "medium":
                    stats.medium_correct += 1
                elif difficulty == "hard":
                    stats.hard_correct += 1

        self._update_streak(stats, attempts[0]) 
        stats.save()

        return 
    

    
    def _update_streak(self, stats, attempt):
        today = attempt.answered_at.date()
        yesterday = today - timedelta(days=1)

        if stats.last_activity_date == today:
            return

        if stats.last_activity_date == yesterday:
            stats.current_streak += 1
        else:
            stats.current_streak = 1

        stats.max_streak = max(stats.max_streak, stats.current_streak)
        stats.last_activity_date = today