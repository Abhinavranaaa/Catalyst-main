import logging
from django.db import transaction
from django.utils import timezone

from practice.models import Answer
from practice.service.sessionTopicAccuracy import invalidate_session_topic_accuracy
from question.models import Question
from roadmap.models import DailySession
from users.analytics.analyticsOrchestrator import AnalyticsCoordinator
from users.analytics.analyticsUserStats import AnalyticsUpdaterUserStats
from users.analytics.analyticsDailyActivity import DailyStatsUpdater
from users.service.dashboarCacheService import DashBoardCacheService
from catalyst.constants import WINDOW

logger = logging.getLogger(__name__)

_analytics = AnalyticsCoordinator(
    [AnalyticsUpdaterUserStats(), DailyStatsUpdater()],
    DashBoardCacheService(WINDOW),
)


def process_session_attempts(user_id: int, session_id: str, attempts: list[dict]) -> dict:
    """
    Validates and stores answers for a daily session, updates analytics
    (streak + heatmap), marks the session complete, and invalidates the
    session topic accuracy cache.

    Returns {"accuracy": int, "questionsAnswered": int}.
    """
    session = DailySession.objects.get(session_id=session_id, user_id=user_id)

    # Build a set of question IDs that belong to this session from the payload
    valid_question_ids: set[str] = set()
    for area in session.payload_json.get("focusAreas", []):
        for q in area.get("questions", []):
            valid_question_ids.add(str(q["id"]))

    incoming_ids = [str(a["question_id"]) for a in attempts]
    db_questions = {
        str(q.id): q
        for q in Question.objects.filter(id__in=incoming_ids)
        .only("id", "correct_index", "difficulty", "bloom_level")
    }

    answer_rows: list[Answer] = []
    for attempt in attempts:
        qid = str(attempt["question_id"])
        if qid not in valid_question_ids:
            logger.warning(
                "question_id %s not in session %s — skipped", qid, session_id
            )
            continue
        q = db_questions.get(qid)
        if not q:
            logger.warning("question_id %s not found in DB — skipped", qid)
            continue

        answer_rows.append(
            Answer(
                user_id=user_id,
                daily_session=session,
                question=q,
                selected_index=attempt["selected_index"],
                is_correct=attempt["selected_index"] == q.correct_index,
                time_taken_seconds=attempt.get("time_taken_seconds"),
            )
        )

    with transaction.atomic():
        Answer.objects.bulk_create(answer_rows, batch_size=500)

    # Update streak + heatmap via the same analytics pipeline used by roadmaps
    if answer_rows:
        _analytics.process_attempt(user_id, answer_rows)

    total = len(answer_rows)
    correct = sum(1 for a in answer_rows if a.is_correct)
    accuracy = round(correct / total * 100) if total else 0

    session.is_completed = True
    session.completed_at = timezone.now()
    session.completion_accuracy = accuracy
    session.completion_questions = total
    session.save(update_fields=[
        "is_completed", "completed_at", "completion_accuracy", "completion_questions"
    ])

    invalidate_session_topic_accuracy(user_id, session.subject)

    logger.info(
        "Session %s submitted: user=%s total=%d correct=%d accuracy=%d%%",
        session_id, user_id, total, correct, accuracy,
    )
    return {"accuracy": accuracy, "questionsAnswered": total}
