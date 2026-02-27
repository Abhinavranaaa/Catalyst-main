import uuid
from django.db import models
from question.models import Question
from users.models import User
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from decimal import Decimal

class Roadmap(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    topics = ArrayField(models.TextField(), blank=True,null=True) 
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    progress_percntg = models.DecimalField(
        default=Decimal('0.00'), 
        max_digits=6, 
        decimal_places=2
    )
    modified_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    avg_difficulty = models.CharField(
        max_length=20,
        default="Medium",
        choices=[
            ("medium", "Medium"),
            ("easy", "Easy"),
            ("hard", "Hard"),
        ]
    )
    generated_json = models.JSONField(blank=True, null=True)
    search_vector_en = SearchVectorField(null=True)
    search_vector_smpl = SearchVectorField(null=True)


    class Meta:
        db_table = 'roadmaps'
        verbose_name = "Roadmap"
        verbose_name_plural = "Roadmaps"
        indexes = [
            GinIndex(fields=["search_vector_en"]),
            GinIndex(fields=["search_vector_smpl"]),
        ]

    def __str__(self):
        return self.title


class RoadmapQuestion(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=50,
        default="unanswered",
        choices=[
            ("answered", "Answered"),
            ("unanswered", "Unanswered"),
        ]
    )
    
    class Meta:
        db_table = 'roadmap_question'
        unique_together = (('roadmap', 'question'),) 
        managed = True


class RoadmapJob(models.Model):

    class Status(models.TextChoices):
        QUEUED = "queued"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    input_data = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED
    )
    error_message = models.TextField(null=True, blank=True)
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE,null=True,blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
        ]
