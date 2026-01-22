from django.db import transaction
from django.utils import timezone
from ..models import Answer
from ..helper import fetchRoadmapAttempts
from ..helper import fetchRoadmapQuestions
import logging
from ..StatsContext import StatsContext
from ..metrics import *
from users.models import User
from roadmap.models import Roadmap



logger = logging.getLogger(__name__)

def processAttempts(
    user_id:str,
    roadmap_id:str,
    attempts: list[dict]
)->dict:  
    roadmap_questions = fetchRoadmapQuestions(roadmap_id)
    submitted_attempts = insertAttempts(user_id,roadmap_id,attempts,roadmap_questions)
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
    roadmap_questions=roadmap_questions,
    )
    stats = engine.run(ctx)
    return stats






def insertAttempts(
    user_id:str,
    roadmap_id:str,
    attempts: list[dict],
    roadmap_questions:list
)->list:
    """
    Insert immutable attempt events in bulk.
    """
    
    question_map = {rq.question.id: rq.question for rq in roadmap_questions}
    user = User.objects.filter(id=user_id).first()
    roadmap = Roadmap.objects.filter(id=roadmap_id).first()
    now = timezone.now()
    answer_rows = []
    
    for attempt in attempts:
        question_id = attempt["question_id"]
        selected_index = attempt["selected_index"]
        answered_at = attempt.get("answered_at") or now
        time_taken = attempt.get("time_taken_seconds")
        question = question_map.get(question_id)
        if not question:
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


