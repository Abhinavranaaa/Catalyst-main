from rest_framework import serializers

from .models import CATEGORY_CHOICES, Bookmark, FlagSubmission


class BookmarkCreateSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    reason = serializers.ChoiceField(choices=Bookmark.REASON_CHOICES)
    reason_text = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class BookmarkReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ["id", "question_id", "reason", "reason_text", "created_at"]


class FlagSubmissionCreateSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    categories = serializers.ListField(
        child=serializers.ChoiceField(choices=CATEGORY_CHOICES),
        required=False,
        default=list,
        allow_empty=True,
    )
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class FlagSubmissionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlagSubmission
        fields = ["id", "question_id", "categories", "description", "status", "created_at"]
