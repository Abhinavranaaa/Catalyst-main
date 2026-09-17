import logging
from datetime import date as date_cls

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def generate_next_daily_session_task(enrollment_id, date_iso: str) -> None:
    """
    Eagerly generates the DailySession for `date_iso` right after the
    session before it was submitted, so the next login already has a
    READY session instead of waiting on synchronous generation.

    Best-effort: any failure here just leaves that date to be generated
    lazily by get_today_session, same as before this task existed.
    """
    from enrollments.models import CourseEnrollment
    from roadmap.service.dailySessionGenerator import generate_daily_session

    try:
        enrollment = CourseEnrollment.objects.get(id=enrollment_id)
    except CourseEnrollment.DoesNotExist:
        logger.warning("Eager session generation skipped — enrollment=%s not found", enrollment_id)
        return

    if enrollment.status != CourseEnrollment.Status.ACTIVE:
        logger.info(
            "Eager session generation skipped — enrollment=%s is not active", enrollment_id,
        )
        return

    target_date = date_cls.fromisoformat(date_iso)
    try:
        generate_daily_session(enrollment, date=target_date)
    except Exception:
        logger.exception(
            "Eager next-day session generation failed enrollment=%s date=%s",
            enrollment_id, date_iso,
        )
