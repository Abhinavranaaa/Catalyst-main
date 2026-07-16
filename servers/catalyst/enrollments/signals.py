from django.db.models.signals import post_save
from django.dispatch import receiver

from enrollments.models import CourseEnrollment, UserCourseProfile


@receiver(post_save, sender=CourseEnrollment)
def create_profile_for_enrollment(sender, instance, created, **kwargs):
    if created:
        UserCourseProfile.objects.create(enrollment=instance)
