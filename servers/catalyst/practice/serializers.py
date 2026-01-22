from rest_framework import serializers

class AttemptSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_index = serializers.IntegerField()
    answered_at = serializers.DateTimeField(required=False,allow_null=True)
    time_taken_seconds = serializers.IntegerField(required=False, allow_null=True)


class PostUsrAttemptSerializer(serializers.Serializer):
    roadmap_id = serializers.UUIDField()
    # submitted_at = serializers.DateTimeField()
    attempts = AttemptSerializer(many=True)


