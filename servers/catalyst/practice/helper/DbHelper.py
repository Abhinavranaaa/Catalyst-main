from roadmap.models import RoadmapQuestion,Roadmap, RoadmapJob
from ..models import Answer
import logging
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)

def fetchRoadmapQuestions(roadmap)->list:
    try:
        roadmap_questions = RoadmapQuestion.objects.filter(roadmap=roadmap).select_related("question")
        logger.info("Successfully fetched roadmap questions: %d", len(roadmap_questions))
        return roadmap_questions
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

def fetchRoadmapAttempts(roadmap)->list:
    try:
        roadmap_attempts = Answer.objects.filter(roadmap=roadmap).order_by("-answered_at")
        logger.info("Successfully fetched roadmap attempts: %d", len(roadmap_attempts))
        return roadmap_attempts
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

def fetchRoadmap(roadmap_id):
    try:
        roadmap = Roadmap.objects.filter(id=roadmap_id).first()
        logger.info("Successfully fetched roadmap")
        return roadmap
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

def fetchJob(job_id,user_id):
    try:
        job = RoadmapJob.objects.select_related("roadmap").get(
            id=job_id,
            user_id=user_id
        )
        logger.info("Successfully fetched roadmap job")
        return job
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

def fetchDailyQuota(user_id):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    used = RoadmapJob.objects.select_for_update().filter(
        user_id=user_id,
        created_at__gte=today_start
    ).exclude(status=RoadmapJob.Status.FAILED).count()
    return used



