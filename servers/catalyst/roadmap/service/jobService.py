# roadmap/services/job_service.py

from django.db import transaction
from roadmap.models import RoadmapJob
from .roadmapPublisher import RoadmapTaskPublisher


class RoadmapJobService:

    def __init__(self):
        self.publisher = RoadmapTaskPublisher()

    @transaction.atomic
    def create_and_enqueue(self, user_id, input_data) -> RoadmapJob:

        job = RoadmapJob.objects.create(
            user_id=user_id,
            input_data=input_data,
        )
        self.publisher.enqueue(str(job.id))
        return job