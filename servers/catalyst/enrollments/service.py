import logging
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# (min_attempts, min_accuracy_ratio, label) — checked in order; first match wins.
_MASTERY_THRESHOLDS = [
    (5, 0.80, "mastered"),
    (3, 0.50, "proficient"),
    (3, 0.00, "developing"),
]


def compute_mastery(correct: int, attempted: int) -> str:
    if attempted < 3:
        return "new"
    accuracy = correct / attempted
    for min_att, min_acc, label in _MASTERY_THRESHOLDS:
        if attempted >= min_att and accuracy >= min_acc:
            return label
    return "developing"


def update_profile_after_submission(
    enrollment_id,
    topic_stats: dict,
    session_accuracy: float,
) -> dict:
    """
    Incrementally update UserCourseProfile after a session submission.

    topic_stats: {topic_name: {"correct": int, "answered": int, ...}}
    session_accuracy: 0.0–1.0 float

    Query cost is O(1) with respect to historical depth — only the topics
    in this session are touched; the rest of topic_accuracy is not iterated.

    Returns analysis dict for inclusion in the submit response:
        {topic_breakdown, weekly_progress}
    Returns {} if no profile exists (pre-MC-01 sessions).
    """
    from enrollments.models import UserCourseProfile

    try:
        with transaction.atomic():
            profile = UserCourseProfile.objects.select_for_update().get(
                enrollment_id=enrollment_id
            )

            # Snapshot per-topic mastery BEFORE update so we can detect changes.
            pre_mastery = {
                topic: profile.topic_accuracy.get(topic, {}).get("mastery", "new")
                for topic in topic_stats
            }

            # prev_week_accuracy starts as whatever was stored from the last reset.
            # The reset branch overwrites it with this week's final value before clearing.
            prev_week_accuracy = profile.previous_week_accuracy

            now = timezone.now()
            if profile.weekly_sessions_completed > 0:
                if profile.last_updated.isocalendar()[:2] != now.isocalendar()[:2]:
                    logger.info(
                        "Weekly reset for enrollment=%s prev_week=%s",
                        enrollment_id, profile.last_updated.isocalendar()[:2],
                    )
                    # Preserve this week's final average before clearing it.
                    prev_week_accuracy = profile.weekly_accuracy
                    profile.previous_week_accuracy = profile.weekly_accuracy
                    profile.weekly_sessions_completed = 0
                    profile.weekly_accuracy = None

            # Incremental topic update — only the topics in this session.
            for topic_name, result in topic_stats.items():
                existing = profile.topic_accuracy.get(
                    topic_name, {"correct": 0, "attempted": 0}
                )
                existing["correct"] += result["correct"]
                existing["attempted"] += result["answered"]
                existing["mastery"] = compute_mastery(
                    existing["correct"], existing["attempted"]
                )
                profile.topic_accuracy[topic_name] = existing

            # Running simple average for weekly accuracy.
            if profile.weekly_accuracy is not None:
                profile.weekly_accuracy = (
                    (profile.weekly_accuracy * profile.weekly_sessions_completed + session_accuracy)
                    / (profile.weekly_sessions_completed + 1)
                )
            else:
                profile.weekly_accuracy = session_accuracy

            profile.weekly_sessions_completed += 1
            profile.save(update_fields=[
                "topic_accuracy",
                "weekly_accuracy",
                "weekly_sessions_completed",
                "previous_week_accuracy",
                "last_updated",
            ])

        # ── Build analysis ──────────────────────────────────────────────────
        topic_breakdown = []
        for topic_name, result in topic_stats.items():
            updated = profile.topic_accuracy[topic_name]
            old_mastery = pre_mastery[topic_name]
            new_mastery = updated["mastery"]
            topic_breakdown.append({
                "topic": topic_name,
                "correct": result["correct"],
                "attempted": result["answered"],
                "mastery": new_mastery,
                "mastery_changed": old_mastery != new_mastery,
                "previous_mastery": old_mastery,
            })

        if prev_week_accuracy is not None and profile.weekly_accuracy is not None:
            delta = round(profile.weekly_accuracy - prev_week_accuracy, 4)
        else:
            delta = None

        return {
            "topic_breakdown": topic_breakdown,
            "weekly_progress": {
                "sessions_completed": profile.weekly_sessions_completed,
                "weekly_accuracy": round(profile.weekly_accuracy, 4) if profile.weekly_accuracy is not None else None,
                "accuracy_delta_vs_last_week": delta,
            },
        }

    except UserCourseProfile.DoesNotExist:
        logger.warning(
            "No UserCourseProfile for enrollment=%s — skipping profile update",
            enrollment_id,
        )
        return {}
