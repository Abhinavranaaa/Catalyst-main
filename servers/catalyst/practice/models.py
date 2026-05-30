
import uuid
from django.db import models
from users.models import User
from roadmap.models import Roadmap, DailySession
from question.models import Question


class TopicType(models.TextChoices):
    WEAKNESS = "weakness", "Weakness"
    NEW = "new", "New"
    REVIEW = "review", "Review"


class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.DO_NOTHING, blank=True, null=True)
    daily_session = models.ForeignKey(DailySession, on_delete=models.DO_NOTHING, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING, blank=True, null=True)
    selected_index = models.IntegerField()
    is_correct = models.BooleanField(blank=True, null=True)
    answered_at = models.DateTimeField(auto_now_add=True)
    time_taken_seconds = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'answers'
        # unique_together = (('user', 'roadmap', 'question'),)
        verbose_name = "Answer"
        verbose_name_plural = "Answers"

    def __str__(self):
        return f"{self.user} - {self.question}"


# class QuestionAttempt(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True)
#     question = models.ForeignKey(Question, on_delete=models.DO_NOTHING, blank=True, null=True)
#     attempt_count = models.IntegerField(default=1, blank=True, null=True)
#     correct_attempts = models.IntegerField(default=0, blank=True, null=True)
#     incorrect_attempts = models.IntegerField(default=0, blank=True, null=True)
#     last_attempted_at = models.DateTimeField(auto_now=True, blank=True, null=True)
#     total_time_spent_seconds = models.IntegerField(default=0, blank=True, null=True)

#     class Meta:
#         db_table = 'question_attempts'
#         verbose_name = "Question Attempt"
#         verbose_name_plural = "Question Attempts"

#     def __str__(self):
#         return f"{self.user} - {self.question}"

class SessionAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(DailySession, on_delete=models.CASCADE, related_name="session_attempts")
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING)
    topic_name = models.CharField(max_length=255)
    topic_type = models.CharField(max_length=20, choices=TopicType.choices)
    selected_index = models.IntegerField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    time_to_first_tap_ms = models.IntegerField(null=True, blank=True)
    answer_changed = models.BooleanField(default=False)
    bloom_level = models.PositiveSmallIntegerField(null=True, blank=True)
    difficulty = models.CharField(max_length=20, null=True, blank=True)
    sequence_position = models.PositiveSmallIntegerField(null=True, blank=True)
    skipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "session_attempts"
        verbose_name = "Session Attempt"
        verbose_name_plural = "Session Attempts"

    def __str__(self):
        return f"[{self.topic_name}] Q:{self.question_id} skipped={self.skipped}"
