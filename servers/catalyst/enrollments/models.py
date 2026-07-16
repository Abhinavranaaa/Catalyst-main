import uuid
from django.db import models
from users.models import User


class UserCourseProfile(models.Model):
    """
    Durable per-enrollment performance snapshot — updated incrementally on
    every session submit so reads (login, session generation) never scan
    the full attempt history.
    """
    enrollment = models.OneToOneField(
        'enrollments.CourseEnrollment',
        on_delete=models.CASCADE,
        related_name='profile',
    )
    # {"processes": {"correct": 12, "attempted": 15, "mastery": "proficient"}, ...}
    topic_accuracy = models.JSONField(default=dict)
    weekly_sessions_completed = models.IntegerField(default=0)
    weekly_accuracy = models.FloatField(null=True, blank=True)
    previous_week_accuracy = models.FloatField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_course_profiles'

    def __str__(self):
        return f"Profile({self.enrollment_id})"


class CourseEnrollment(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    # Plain CharField — not constrained to a fixed choices list so new courses
    # can be added without a migration.
    course = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_enrollments'
        # One enrollment row per user+course — re-activation updates status, not a new row.
        unique_together = [('user', 'course')]
        indexes = [
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.course} ({self.status})"
