import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class Bookmark(models.Model):
    REASON_CHOICES = [
        ("want_more_practice", "Want more practice like this"),
        ("new_concept", "New concept, want to revisit"),
        ("good_example", "Good example to reference later"),
        ("curious", "Just curious / interesting problem"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Plain UUIDField, not a hard FK — same reasoning as Subscription.user_id:
    # this is collect-only feedback data, not something that should fail to
    # write/read if a join ever goes sideways, and a question's lifecycle
    # (deletion/archival) shouldn't cascade into or be blocked by it.
    user_id = models.CharField(max_length=255)
    question_id = models.UUIDField()
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    reason_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "created_at"]),
        ]

    def __str__(self):
        return f"Bookmark({self.user_id}, {self.question_id})"


CATEGORY_CHOICES = [
    ("answer_or_explanation_wrong", "Answer or explanation seems wrong"),
    ("options_unclear_or_not_distinct", "Options don't make sense / aren't distinct"),
    ("missing_table_image_or_related_question", "Missing table, image, or related question"),
    ("confusing_wording", "Confusing or unclear wording"),
    ("something_else", "Something else"),
]


class FlagSubmission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=255)
    question_id = models.UUIDField()
    categories = ArrayField(
        models.CharField(max_length=50, choices=CATEGORY_CHOICES),
        default=list,
    )
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["question_id", "status"]),
        ]

    def __str__(self):
        return f"FlagSubmission({self.question_id}, {self.status})"
