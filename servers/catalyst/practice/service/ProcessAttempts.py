from django.db import transaction
from django.utils import timezone
from ..models import Answer
from ..helper import fetchRoadmapAttempts, fetchRoadmapQuestions, fetchRoadmap
import logging
from ..StatsContext import StatsContext
from ..metrics import *
from users.models import User
from roadmap.models import Roadmap, RoadmapQuestion
from roadmap.service.generate import sync_roadmap_json_with_question_status



logger = logging.getLogger(__name__)

def processAttempts(
    user_id:str,
    roadmap_id:str,
    attempts: list[dict]
)->dict:
    roadmap = fetchRoadmap(roadmap_id=roadmap_id)
    roadmap_questions = fetchRoadmapQuestions(roadmap_id)
    question_map = {rq.question.id: rq.question for rq in roadmap_questions}
    submitted_attempts = insertAttempts(user_id,roadmap,attempts,question_map)
    updateRoadmapQuestions(roadmap_questions=roadmap_questions,submitted_attempts=submitted_attempts)
    roadmap_attempts = fetchRoadmapAttempts(roadmap_id)
    engine = FactoryEngine([
    AccuracyMetric(),
    MeanTimeMetric(),
    RoadmapCompletionMetric(),
    QuestionBreakdownMetric(),
    ])
    ctx = StatsContext(
    submitted_attempts=submitted_attempts,
    all_attempts=roadmap_attempts,
    question_lookup=question_map,
    )
    stats = engine.run(ctx)
    updateRoadmapJson(roadmap,stats.get('roadmap_completion_pct',0.0))
    return stats



def insertAttempts(
    user_id:str,
    roadmap,
    attempts: list[dict],
    question_map:dict
)->list:
    """
    Insert immutable attempt events in bulk.
    """
    
    user = User.objects.filter(id=user_id).first()
    now = timezone.now()
    answer_rows = []
    
    for attempt in attempts:
        question_id = attempt["question_id"]
        selected_index = attempt["selected_index"]
        answered_at = attempt.get("answered_at") or now
        time_taken = attempt.get("time_taken_seconds")
        question = question_map.get(question_id)
        if not question:
            logger.warning(
                "Invalid question attempt: roadmap_id=%s question_id=%s user_id=%s",
                roadmap.id,
                question_id,
                user_id,
            )

            continue

        is_correct = selected_index == question.correct_index

        answer_rows.append(
            Answer(
                user=user,
                roadmap=roadmap,
                question=question,
                selected_index=selected_index,
                is_correct=is_correct,
                answered_at=answered_at,
                time_taken_seconds=time_taken,
            )
        )

    with transaction.atomic():
        Answer.objects.bulk_create(answer_rows, batch_size=500)
    
    logging.info("Successfully bulk upserted submitted attemts")

    return answer_rows


def updateRoadmapQuestions(roadmap_questions: list, submitted_attempts: list):
    to_update = []
    question_map = {rq.question.id: rq for rq in roadmap_questions}
    for attempt in submitted_attempts:
        rq = question_map.get(attempt.question.id)
        if not rq:
            continue

        if rq.status == "unanswered" and attempt.is_correct:
            rq.status = "answered"
            to_update.append(rq)

    if to_update:
        RoadmapQuestion.objects.bulk_update(
            to_update,
            ["status"]
        )
    return to_update

    
def updateRoadmapJson(roadmap,completion_prcntg):
    updated_json = sync_roadmap_json_with_question_status(roadmap)
    roadmap.generated_json = updated_json
    roadmap.progress_percntg = completion_prcntg
    roadmap.save(update_fields=["generated_json","progress_percntg"])
