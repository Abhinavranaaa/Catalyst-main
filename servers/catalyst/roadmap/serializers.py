from rest_framework import serializers
from roadmap.models import Roadmap
import random

class GenerateRoadmapRequestSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=255)
    topic = serializers.CharField(max_length=255)
    additional_comments = serializers.CharField(allow_blank=True, required=False)

class GetRoadmapRequestSerializer(serializers.Serializer):
    roadmap_id = serializers.CharField(max_length=255)

class GetJobRequestSerializer(serializers.Serializer):
    job_id = serializers.CharField(max_length=255)
# roadmap/api/serializers.py

class RoadmapSerializer(serializers.ModelSerializer):

    preview_topics = serializers.SerializerMethodField()

    class Meta:
        model = Roadmap
        fields = [
            "id",
            "title",
            "description",
            "preview_topics",
            "avg_difficulty",
            "progress_percntg",
            "modified_at",
        ]

    def get_preview_topics(self, obj):
        topics = obj.topics or []

        if len(topics) <= 2:
            return topics

        return random.sample(topics, 2)
    
