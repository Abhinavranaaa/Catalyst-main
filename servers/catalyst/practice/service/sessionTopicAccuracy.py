import json
import logging
from django.db.models import Count, Sum, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
from catalyst.infra.redis import redis_client
from catalyst.constants import SUBJECT_TOPICS
from practice.models import SessionAttempt

logger = logging.getLogger(__name__)

_CACHE_TTL = 3600  # 1 hour


def _classify(accuracy: int, attempts: int) -> str:
    if attempts < 3:
        return "new"
    if accuracy >= 80 and attempts >= 5:
        return "mastered"
    if accuracy < 65:
        return "weakness"
    return "review"


# Weighted proficiency scoring — a skip is not a neutral non-event, it should
# still drag down mastery (just less than a wrong answer): correct=+3,
# skipped=0, wrong=-1. Normalized against the best-possible score (3 per
# attempt) so it stays comparable to the old 0-100 accuracy scale.
_CORRECT_POINTS = 3
_SKIPPED_POINTS = 0
_WRONG_POINTS = -1


def _compute_from_db(user_id: int, subject: str) -> list[dict]:
    topics = SUBJECT_TOPICS.get(subject, [])

    thirty_days_ago = timezone.now() - timedelta(days=30)

    rows = (
        SessionAttempt.objects
        .filter(
            user_id=user_id,
            session__subject=subject,
            created_at__gte=thirty_days_ago,
            topic_name__in=topics,
        )
        .values("topic_name")
        .annotate(
            total=Count("id"),
            score=Sum(
                Case(
                    When(skipped=True, then=_SKIPPED_POINTS),
                    When(is_correct=True, then=_CORRECT_POINTS),
                    default=_WRONG_POINTS,
                    output_field=IntegerField(),
                )
            ),
        )
    )

    attempted: dict[str, dict] = {}
    for row in rows:
        topic = row["topic_name"]
        total = row["total"]
        score = row["score"] or 0
        max_score = total * _CORRECT_POINTS
        accuracy = round(max(0, score) / max_score * 100) if max_score else 0
        attempted[topic] = {
            "topic": topic,
            "accuracy": accuracy,
            "attempts": total,
            "type": _classify(accuracy, total),
        }

    result = []
    for topic in topics:
        if topic in attempted:
            result.append(attempted[topic])
        else:
            result.append({"topic": topic, "accuracy": 0, "attempts": 0, "type": "new"})

    return result


def get_session_topic_accuracy(user_id: int, subject: str) -> list[dict]:
    key = f"session_accuracy:{user_id}:{subject}"

    cached = redis_client.get(key)
    if cached:
        logger.info("session_accuracy cache HIT user=%s subject=%s", user_id, subject)
        return json.loads(cached)

    logger.info("session_accuracy cache MISS user=%s subject=%s — querying DB", user_id, subject)
    result = _compute_from_db(user_id, subject)
    redis_client.setex(key, _CACHE_TTL, json.dumps(result))
    return result


def invalidate_session_topic_accuracy(user_id: int, subject: str) -> None:
    key = f"session_accuracy:{user_id}:{subject}"
    redis_client.delete(key)
    logger.info("Invalidated session_accuracy cache user=%s subject=%s", user_id, subject)
