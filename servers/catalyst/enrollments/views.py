import logging
from django.db import transaction, IntegrityError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from catalyst.constants import SUBJECT_TOPICS
from .models import CourseEnrollment

logger = logging.getLogger(__name__)

_FREE_TIER_CAP = 3


@api_view(['POST'])
def create_enrollment(request):
    course = request.data.get('course', '').strip()
    if not course:
        return Response({'error': 'course is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # select_for_update() locks the rows being counted so two concurrent
            # requests can't both see count=2 and both slip past the cap.
            active_count = (
                CourseEnrollment.objects
                .select_for_update()
                .filter(user=request.user, status=CourseEnrollment.Status.ACTIVE)
                .count()
            )
            if active_count >= _FREE_TIER_CAP:
                return Response(
                    {'error': 'upgrade_required', 'limit': _FREE_TIER_CAP},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )
            enrollment = CourseEnrollment.objects.create(
                user=request.user,
                course=course,
            )

        return Response(
            {
                'id': str(enrollment.id),
                'course': enrollment.course,
                'status': enrollment.status,
                'created_at': enrollment.created_at,
            },
            status=status.HTTP_201_CREATED,
        )

    except IntegrityError:
        return Response(
            {'error': 'already_enrolled', 'course': course},
            status=status.HTTP_409_CONFLICT,
        )

    except Exception:
        logger.exception("Unexpected error creating enrollment for user=%s", request.user.id)
        return Response(
            {'error': 'An unexpected error occurred. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def list_enrollments(request):
    enrollments = (
        CourseEnrollment.objects
        .filter(user=request.user)
        .order_by('created_at')
        .values('id', 'course', 'status', 'created_at')
    )
    return Response(list(enrollments))


@api_view(['GET'])
@permission_classes([AllowAny])
def list_available_courses(request):
    courses = [
        {'name': name, 'topics': topics}
        for name, topics in SUBJECT_TOPICS.items()
    ]
    return Response(courses)
