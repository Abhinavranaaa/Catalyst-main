from roadmap.models import RoadmapQuestion,Roadmap
from ..models import Answer
import logging

logger = logging.getLogger(__name__)

def fetchRoadmapQuestions(roadmap)->list:
    try:
        roadmap_questions = RoadmapQuestion.objects.filter(roadmap=roadmap).select_related("question")
        logging.info("Successfully fetched roadmap questions: %d", len(roadmap_questions))
        return roadmap_questions
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

def fetchRoadmapAttempts(roadmap)->list:
    try:
        roadmap_attempts = Answer.objects.filter(roadmap=roadmap).order_by("-answered_at")
        logging.info("Successfully fetched roadmap attempts: %d", len(roadmap_attempts))
        return roadmap_attempts
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

def fetchRoadmap(roadmap_id):
    try:
        roadmap = Roadmap.objects.filter(id=roadmap_id).first()
        logging.info("Successfully fetched roadmap")
        return roadmap
    except Exception as e:
        logger.exception("Exception e: %s, occured while fetching from db",e)
        raise

