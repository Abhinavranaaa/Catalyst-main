import json
import logging
from django.db.models import Count, Sum, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
from catalyst.infra.redis import redis_client
from catalyst.constants import SUBJECT_TOPICS
from practice.models import Answer

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


def _compute_from_db(user_id: int, subject: str) -> list[dict]:
    topics = SUBJECT_TOPICS.get(subject, [])

    thirty_days_ago = timezone.now() - timedelta(days=30)

    rows = (
        Answer.objects
        .filter(
            user_id=user_id,
            daily_session__isnull=False,
            daily_session__subject=subject,
            answered_at__gte=thirty_days_ago,
            question__topic__in=topics,
        )
        .values("question__topic")
        .annotate(
            total=Count("id"),
            correct=Sum(
                Case(
                    When(is_correct=True, then=1),
                    default=0,
                    output_field=IntegerField(),
                )
            ),
        )
    )

    attempted: dict[str, dict] = {}
    for row in rows:
        topic = row["question__topic"]
        total = row["total"]
        correct = row["correct"] or 0
        accuracy = round((correct / total) * 100) if total else 0
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
