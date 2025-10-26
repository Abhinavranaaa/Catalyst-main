import uuid
from django.db import models
from question.models import Question
from users.models import User

class Roadmap(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    # New JSONField to store full generated roadmap JSON
    generated_json = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'roadmaps'
        verbose_name = "Roadmap"
        verbose_name_plural = "Roadmaps"
        unique_together = ('user', 'title')

    def __str__(self):
        return self.title


class RoadmapQuestion(models.Model):
    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    class Meta:
        db_table = 'roadmap_question'
        unique_together = (('roadmap', 'question'),) 
        managed = True
