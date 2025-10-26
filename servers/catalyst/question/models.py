import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    difficulty = models.CharField(max_length=50, blank=True,
                                  null=True)  # Instead of TextField, since difficulty is likely a short string like 'easy', 'medium'
    source = models.TextField(blank=True, null=True)
    options = ArrayField(models.TextField(), blank=False,
                         null=False)  # Ideal if you want to store a list of options cleanly
    correct_index = models.IntegerField()
    text = models.TextField()

    def __str__(self):
        return self.text[:80]  # show a snippet of the question

    class Meta:
        db_table = 'questions'
        verbose_name = "Question"
        verbose_name_plural = "Questions"







