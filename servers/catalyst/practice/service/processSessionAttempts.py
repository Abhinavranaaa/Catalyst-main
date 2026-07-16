import logging
from django.db import transaction
from django.utils import timezone

from practice.models import Answer, SessionAttempt
from practice.service.sessionTopicAccuracy import (
    invalidate_session_topic_accuracy,
    get_session_topic_accuracy,
)
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

_MAX_TAP_MS = 120_000


# ── Custom exceptions (caught in the view) ────────────────────────────────────

class SessionNotFound(Exception):
    pass


class SessionForbidden(Exception):
    pass


class SessionAlreadySubmitted(Exception):
    pass


class UnknownQuestionId(Exception):
    def __init__(self, question_id: str):
        self.question_id = question_id
        super().__init__(f"question_id {question_id} not in session payload")


# ── Main entry point ──────────────────────────────────────────────────────────

def process_session_attempts(
    user_id: int,
    session_id: str,
    session_started_at,
    focus_area_attempts: list[dict],
) -> dict:
    """
    DS-009 submit pipeline:
    1  Validate session ownership
    2  Idempotency check
    3  Validate question IDs against payload
    4  Recompute correctness server-side
    5  Per-topic accuracy
    6  Bulk insert SessionAttempt + Answer rows, mark session complete
    7  Analytics
    8  Invalidate Redis cache, fetch fresh topic classifications
    9  Build topic results (updated_state matches next session's view)
    10 Build and return summary response
    """
    # Step 1 — ownership
    try:
        session = DailySession.objects.get(session_id=session_id)
    except DailySession.DoesNotExist:
        raise SessionNotFound()

    if str(session.user_id) != str(user_id):
        raise SessionForbidden()

    # Step 2 — idempotency
    if session.completed_at is not None:
        raise SessionAlreadySubmitted()

    # Step 3 — build valid question ID set from payload (no extra DB query)
    valid_question_ids: set[str] = set()
    for area in session.payload_json.get("focusAreas", []):
        for q in area.get("questions", []):
            valid_question_ids.add(str(q["id"]))

    # Flatten all attempts across focus areas; validate IDs
    flat: list[dict] = []
    for area in focus_area_attempts:
        for attempt in area["attempts"]:
            qid = str(attempt["question_id"])
            if qid not in valid_question_ids:
                raise UnknownQuestionId(qid)
            flat.append({**attempt, "topic_name": area["topic_name"], "topic_type": area["topic_type"]})

    # Step 4 — fetch correct_index from DB for server-side recomputation
    incoming_ids = [a["question_id"] for a in flat]
    db_questions: dict[str, Question] = {
        str(q.id): q
        for q in Question.objects.filter(id__in=incoming_ids).only("id", "correct_index")
    }

    # Step 5 — compute per-topic accuracy (answered only, skips excluded)
    topic_stats: dict[str, dict] = {}
    for area in focus_area_attempts:
        topic_stats[area["topic_name"]] = {
            "topic_type": area["topic_type"],
            "correct": 0,
            "answered": 0,
        }

    session_attempt_rows: list[SessionAttempt] = []
    answer_rows: list[Answer] = []

    for attempt in flat:
        qid = str(attempt["question_id"])
        q = db_questions.get(qid)
        selected = attempt.get("selected_index")
        skipped = selected is None

        # Server-side correctness
        is_correct = None if skipped else (selected == q.correct_index)

        # Clamp tap time
        tap_ms = attempt.get("time_to_first_tap_ms")
        if tap_ms is not None and tap_ms > _MAX_TAP_MS:
            tap_ms = _MAX_TAP_MS

        session_attempt_rows.append(SessionAttempt(
            session=session,
            user_id=user_id,
            question=q,
            topic_name=attempt["topic_name"],
            topic_type=attempt["topic_type"],
            selected_index=selected,
            is_correct=is_correct,
            time_to_first_tap_ms=tap_ms,
            answer_changed=attempt.get("answer_changed", False),
            bloom_level=attempt.get("bloom_level"),
            difficulty=attempt.get("difficulty"),
            sequence_position=attempt.get("sequence_position"),
            skipped=skipped,
        ))

        # Only non-skipped attempts go into the Answer table (selected_index is non-nullable there)
        # TODO: migrate analytics to SessionAttempt, then remove Answer write
        if not skipped:
            answer_rows.append(Answer(
                user_id=user_id,
                daily_session=session,
                question=q,
                selected_index=selected,
                is_correct=is_correct,
                time_taken_seconds=tap_ms // 1000 if tap_ms is not None else None,
            ))
            stats = topic_stats[attempt["topic_name"]]
            stats["answered"] += 1
            if is_correct:
                stats["correct"] += 1

    # Step 6 — bulk insert inside transaction (state transitions computed after DB commit)
    now = timezone.now()
    with transaction.atomic():
        SessionAttempt.objects.bulk_create(session_attempt_rows, batch_size=500)
        if answer_rows:
            Answer.objects.bulk_create(answer_rows, batch_size=500)

        # Mark session complete
        answered_total = sum(s["answered"] for s in topic_stats.values())
        correct_total = sum(s["correct"] for s in topic_stats.values())
        overall_accuracy = round(correct_total / answered_total * 100) if answered_total else 0

        session.status = "COMPLETED"
        session.is_completed = True
        session.completed_at = now
        session.session_started_at = session_started_at
        session.completion_accuracy = overall_accuracy
        session.completion_questions = answered_total
        session.save(update_fields=[
            "status", "is_completed", "completed_at", "session_started_at",
            "completion_accuracy", "completion_questions",
        ])

    # Analytics (streak + heatmap) — uses Answer rows for continuity
    if answer_rows:
        _analytics.process_attempt(user_id, answer_rows)

    # Update enrollment performance profile — incremental, constant cost regardless of history.
    # Returns analysis dict for the submit response (empty if no enrollment).
    analysis = {}
    if session.enrollment_id:
        from enrollments.service import update_profile_after_submission
        analysis = update_profile_after_submission(
            enrollment_id=session.enrollment_id,
            topic_stats=topic_stats,
            session_accuracy=overall_accuracy / 100.0,
        ) or {}

    # Step 8 — invalidate Redis cache, then fetch fresh classifications
    invalidate_session_topic_accuracy(user_id, session.subject)
    fresh_accuracy = get_session_topic_accuracy(user_id, session.subject)
    fresh_state_map = {t["topic"]: t["type"] for t in fresh_accuracy}

    # Step 9 — build topic results using the real post-submit classification
    topic_results = []
    for topic_name, stats in topic_stats.items():
        answered = stats["answered"]
        accuracy = (stats["correct"] / answered) if answered > 0 else 0.0
        topic_results.append({
            "topic_name": topic_name,
            "correct": stats["correct"],
            "total": answered,
            "accuracy": round(accuracy, 3),
            "previous_state": stats["topic_type"],
            "updated_state": fresh_state_map.get(topic_name, stats["topic_type"]),
        })

    # Step 10 — build response
    total_questions = len(flat)
    duration_seconds = int((now - session_started_at).total_seconds()) if session_started_at else None

    logger.info(
        "Session %s submitted: user=%s total=%d answered=%d correct=%d accuracy=%d%%",
        session_id, user_id, total_questions, answered_total, correct_total, overall_accuracy,
    )

    return {
        "status": "submitted",
        "session_id": str(session.session_id),
        "summary": {
            "total_questions": total_questions,
            "answered": answered_total,
            "correct": correct_total,
            "accuracy_rate": round(correct_total / answered_total, 3) if answered_total else 0,
            "session_duration_seconds": duration_seconds,
            "topics": topic_results,
        },
        "topic_breakdown": analysis.get("topic_breakdown"),
        "weekly_progress": analysis.get("weekly_progress"),
    }
