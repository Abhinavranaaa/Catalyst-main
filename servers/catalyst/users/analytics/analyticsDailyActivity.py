from django.db import transaction
from ..models import UserDailyActivity
from .analyticsUpdater import AnalyticsUpdater
from django.db import IntegrityError


class DailyStatsUpdater(AnalyticsUpdater):

    def update(self, user_id, attempts):

        if not attempts:
            return

        today = attempts[0].answered_at.date()
        attempted = len(attempts)
        correct = sum(1 for a in attempts if a.is_correct)
        time_spent = sum(
            a.time_taken_seconds for a in attempts
            if a.time_taken_seconds
        )
        try:
            obj, _ = UserDailyActivity.objects.select_for_update().get_or_create(
                user_id=user_id,
                date=today
            )
        except IntegrityError:
            obj = UserDailyActivity.objects.select_for_update().get(
                user_id=user_id,
                date=today
            )
        obj.total_attempted += attempted
        obj.total_correct += correct
        obj.time_spent_seconds += time_spent
        obj.save()