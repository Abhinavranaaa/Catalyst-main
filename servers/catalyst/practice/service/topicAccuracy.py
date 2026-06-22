import json
import logging
from django.db.models import Count, Sum, Case, When, IntegerField
from django.utils import timezone
from datetime import timedelta
from catalyst.infra.redis import redis_client
from practice.models import Answer
from roadmap.models import Roadmap

logger = logging.getLogger(__name__)


def _classify(accuracy: int, attempts: int) -> str:
    """
    Classification applied in priority order as specified.
    attempts < 3 is checked first — not enough data to judge accuracy.
    """
    if attempts < 3:
        return "new"
    if accuracy >= 80 and attempts >= 5:
        return "mastered"
    if accuracy < 65:
        return "weakness"
    return "review"


def _compute_from_db(user_id: int, roadmap_id: str) -> list[dict]:
    """
    Two queries total:
      1. Fetch roadmap.topics (only that column).
      2. Single aggregation JOIN on answers + questions filtered to those topics.
    No loops touch the DB — zero N+1 risk.
    """
    roadmap = Roadmap.objects.only("topics").get(id=roadmap_id)
    topics = roadmap.topics or []

    if not topics:
        return []

    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Single query: JOIN answers → questions, GROUP BY topic
    rows = (
        Answer.objects
        .filter(
            user_id=user_id,
            roadmap_id=roadmap_id,
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

    # Topics in the roadmap but with no answers at all → "new"
    result = []
    for topic in topics:
        if topic in attempted:
            result.append(attempted[topic])
        else:
            result.append({"topic": topic, "accuracy": 0, "attempts": 0, "type": "new"})

    return result


def get_topic_accuracy(user_id: int, roadmap_id: str) -> list[dict]:
    key = f"accuracy:{user_id}:{roadmap_id}"

    cached = redis_client.get(key)
    if cached:
        logger.info("topic_accuracy cache HIT user=%s roadmap=%s", user_id, roadmap_id)
        return json.loads(cached)

    logger.info("topic_accuracy cache MISS user=%s roadmap=%s — querying DB", user_id, roadmap_id)
    result = _compute_from_db(user_id, roadmap_id)
    redis_client.set(key, json.dumps(result))
    return result


def invalidate_topic_accuracy(user_id, roadmap_id) -> None:
    """
    Call this after every answer submission.
    bulk_create does not fire post_save signals, so this must be called
    explicitly from processAttempts rather than via a Django signal.
    """
    key = f"accuracy:{user_id}:{roadmap_id}"
    redis_client.delete(key)
    logger.info("Invalidated topic_accuracy cache user=%s roadmap=%s", user_id, roadmap_id)
