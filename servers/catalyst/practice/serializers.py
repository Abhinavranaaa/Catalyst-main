from rest_framework import serializers

_MAX_TAP_MS = 120_000


class AttemptSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_index = serializers.IntegerField()
    time_taken_seconds = serializers.IntegerField(required=False, allow_null=True)


class PostUsrAttemptSerializer(serializers.Serializer):
    roadmap_id = serializers.UUIDField()
    attempts = AttemptSerializer(many=True)


# ── DS-009 ────────────────────────────────────────────────────────────────────

class SessionAttemptInputSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_index = serializers.IntegerField(allow_null=True)
    # is_correct from client is ignored — server always recomputes
    is_correct = serializers.BooleanField(allow_null=True, required=False)
    time_to_first_tap_ms = serializers.IntegerField(allow_null=True, required=False)
    answer_changed = serializers.BooleanField(default=False)
    bloom_level = serializers.IntegerField(allow_null=True, required=False)
    difficulty = serializers.CharField(allow_null=True, required=False)
    sequence_position = serializers.IntegerField(required=False, allow_null=True)

    def validate_time_to_first_tap_ms(self, value):
        if value is not None and value > _MAX_TAP_MS:
            return _MAX_TAP_MS
        return value


class FocusAreaAttemptsSerializer(serializers.Serializer):
    topic_name = serializers.CharField()
    topic_type = serializers.ChoiceField(choices=["weakness", "new", "review", "advance"])
    attempts = SessionAttemptInputSerializer(many=True)


class SessionSubmitSerializer(serializers.Serializer):
    session_started_at = serializers.DateTimeField()
    device_timezone_offset_minutes = serializers.IntegerField(required=False, allow_null=True)
    focus_area_attempts = FocusAreaAttemptsSerializer(many=True)
