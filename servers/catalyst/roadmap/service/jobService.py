# roadmap/services/job_service.py

from django.db import transaction
from roadmap.models import RoadmapJob
from .roadmapPublisher import RoadmapTaskPublisher
from practice.helper import fetchDailyQuota
from catalyst.constants import MAX_ROADMAPS_PER_WINDOW
import logging
from users.models import User

logger = logging.getLogger(__name__)
class RoadmapJobService:

    def __init__(self):
        self.publisher = RoadmapTaskPublisher()

    @transaction.atomic
    def create(self, user_id, input_data) -> RoadmapJob:
        # lock user
        User.objects.select_for_update().get(id=user_id)

        count = fetchDailyQuota(user_id=user_id)
        if(count>=MAX_ROADMAPS_PER_WINDOW):
            logger.info(f"individual roadmap limit hit for user_id{user_id}")
            return None
        job = RoadmapJob.objects.create(
            user_id=user_id,
            input_data=input_data,
        )
        transaction.on_commit(
            lambda: self.enqueue(job.id)
        )
        return job
    
    def enqueue(self,job_id):
        logger.info(f"enqueuing task for job_id{job_id}")
        self.publisher.enqueue(str(job_id))