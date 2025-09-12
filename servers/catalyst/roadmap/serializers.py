from rest_framework import serializers

class GenerateRoadmapRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    topic = serializers.CharField(max_length=255)
    additional_comments = serializers.CharField(allow_blank=True, required=False)