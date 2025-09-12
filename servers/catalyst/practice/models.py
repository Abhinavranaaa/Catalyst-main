
import uuid
from django.db import models
from users.models import User
from roadmap.models import Roadmap
from question.models import Question


class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.DO_NOTHING, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING, blank=True, null=True)
    selected_index = models.IntegerField()
    is_correct = models.BooleanField(blank=True, null=True)
    answered_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    time_taken_seconds = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'answers'
        unique_together = (('user', 'roadmap', 'question'),)
        verbose_name = "Answer"
        verbose_name_plural = "Answers"

    def __str__(self):
        return f"{self.user} - {self.question}"


class QuestionAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, blank=True, null=True)
    question = models.ForeignKey(Question, on_delete=models.DO_NOTHING, blank=True, null=True)
    attempt_count = models.IntegerField(default=1, blank=True, null=True)
    correct_attempts = models.IntegerField(default=0, blank=True, null=True)
    incorrect_attempts = models.IntegerField(default=0, blank=True, null=True)
    last_attempted_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    total_time_spent_seconds = models.IntegerField(default=0, blank=True, null=True)

    class Meta:
        db_table = 'question_attempts'
        verbose_name = "Question Attempt"
        verbose_name_plural = "Question Attempts"

    def __str__(self):
        return f"{self.user} - {self.question}"

# Create your models here.
