from django.shortcuts import render
from django.utils import timezone

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from roadmap.service.generate import generate_roadmap_json,fetchRoadmapJson,fetchRoadmapJob
from roadmap.service.dailySessionGenerator import generate_daily_session, claim_generation_slot
from roadmap.models import Roadmap, DailySession
from practice.service.processSessionAttempts import (
    process_session_attempts,
    SessionNotFound,
    SessionForbidden,
    SessionAlreadySubmitted,
    UnknownQuestionId,
)
from practice.serializers import SessionSubmitSerializer
from roadmap.serializers import GenerateRoadmapRequestSerializer, GetRoadmapRequestSerializer, GetJobRequestSerializer
import logging
from notifications.tasks import process_user_interests_async
from catalyst.constants import ADDITIONAL_COMMENTS, ROADMAP_ID
import jwt
from rest_framework.exceptions import AuthenticationFailed
import time
import concurrent.futures
from .search.validator import QueryValidator
from .search.parser import QueryParser
from .search.query_builder import QueryBuilder
from .search.sort import DynamicSortApplier
from .search.filter import DynamicFilterApplier
from .search.search import SearchDynamicQueries
from .serializers import RoadmapSerializer
from .service.jobService import RoadmapJobService
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from roadmap.models import RoadmapJob
from catalyst.rate_limit.RateLimitExceeded import RateLimitExceeded
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny



logger = logging.getLogger(__name__)

# Sync generation timeout — tune once p95 LLM latency is observable in logs.
_SYNC_GEN_TIMEOUT_SECONDS = 9

service = RoadmapJobService()
query_builder = QueryBuilder(dynamic_filter=DynamicFilterApplier(),sort=DynamicSortApplier(),search=SearchDynamicQueries())
validator = QueryValidator()
parser = QueryParser()

@api_view(['GET'])
def getRoadmapJson(request):
    serializer = GetRoadmapRequestSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        roadmapJson =fetchRoadmapJson(**serializer.validated_data)
        logger.info("successfully fetched the roadmap json and processing the response")
        return Response(
            {
                "message": "Roadmap generated successfully",
                "data": roadmapJson
            },
            status=status.HTTP_200_OK
        )
    except Exception:
        logger.exception("Internal server error during roadmap fetch")
        return Response(
            {
                "error": "An unexpected error occurred while fetching the roadmap. Please try again later."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['POST'])
def getListRoadmap(request):
    payload = request.data or {}
    try:
        validated_request = validator.validate(payload)
        parsed_request = parser.parse(validated_request)
        logger.info(f'request parsed into valid search sort filter limit and offset:{parsed_request.get("sort")},{parsed_request.get("filters")},{parsed_request.get("search")}')
    except ValueError as e:
        logger.warning("Query validation failed: %s", str(e))
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        qs = query_builder.build(request.user.id,parsed_request)
        serializer = RoadmapSerializer(qs, many=True)
        return Response({"response":serializer.data},status=status.HTTP_200_OK)
    except Exception:
        logger.exception("Internal server error during roadmap fetch")
        return Response(
            {
                "error": "An unexpected error occurred while fetching the roadmap. Please try again later."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )   


@api_view(['POST'])
def generate_roadmap_view(request):
    serializer = GenerateRoadmapRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        job = service.create(
            user_id=request.user.id,
            input_data=serializer.validated_data,
        )
        if job:
            return Response({
                "job_id": str(job.id),
                "status": job.status
            })
        else:
            return Response({
                "error_msg":"individual rate limit breached comeback next day"
            }, status = status.HTTP_403_FORBIDDEN)
        

        
    except Exception as e:
        return Response(
            {
                "error": f"An unexpected error occurred while fetching the roadmap. Please try again later.{e}"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@api_view(['POST'])
@csrf_exempt
@permission_classes([AllowAny])
def process_roadmap_task(request):
    data = json.loads(request.body)
    job_id = data["job_id"]
    try:
        with transaction.atomic():

            job = RoadmapJob.objects.select_for_update().get(id=job_id)
            if job.status == RoadmapJob.Status.COMPLETED:
                return JsonResponse({"status": "already_completed"})

            job.status = RoadmapJob.Status.PROCESSING
            job.save(update_fields=["status"])
    
        roadmap = generate_roadmap_json(job.user_id,**job.input_data)
        job.roadmap = roadmap
        job.status = RoadmapJob.Status.COMPLETED
        job.save(update_fields=["status","roadmap"])
        return JsonResponse({"status": "success"})
    
    except KeyError as e:
        logger.error("Roadmap response missing key: %s", e)
        raise e
    
    except RateLimitExceeded as e:
        job.status = RoadmapJob.Status.FAILED
        job.error_message = str(e)
        job.save(update_fields=["status", "error_message"])
        return JsonResponse({"status": "success"})

    except Exception as e:
        job.status = RoadmapJob.Status.FAILED
        job.error_message = str(e)
        job.save(update_fields=["status", "error_message"])
        raise e  


@api_view(['GET'])
def get_today_session(request):
    from enrollments.models import CourseEnrollment

    enrollment_id = request.query_params.get('enrollment_id')
    if not enrollment_id:
        return Response({'error': 'enrollment_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        enrollment = CourseEnrollment.objects.get(id=enrollment_id, user=request.user)
    except CourseEnrollment.DoesNotExist:
        return Response({'error': 'Enrollment not found'}, status=status.HTTP_404_NOT_FOUND)

    if enrollment.status != CourseEnrollment.Status.ACTIVE:
        return Response({'error': 'Enrollment is paused'}, status=status.HTTP_403_FORBIDDEN)

    # Fast path: existing READY session — no generation needed.
    ready = DailySession.objects.filter(
        enrollment=enrollment, status=DailySession.Status.READY
    ).first()
    if ready:
        return Response(_build_session_response(ready.payload_json, ready, request.user), status=status.HTTP_200_OK)

    # Already done today — don't regenerate, tell the frontend so it can
    # offer to review the completed session or upsell premium (multiple
    # sessions/day). Without this check the code below would try to
    # generate a second session and collide with the DB's one-per-day
    # constraint on (user, subject, date).
    today = timezone.now().date()
    completed_today = DailySession.objects.filter(
        enrollment=enrollment, date=today, status=DailySession.Status.COMPLETED,
    ).first()
    if completed_today:
        return Response(
            {
                "status": "already_completed",
                "message": "You've already completed today's session. Review it below, or go Premium to unlock multiple sessions a day.",
                "session": _build_session_response(completed_today.payload_json, completed_today, request.user),
                "canReview": True,
                "premiumUpsell": True,
            },
            status=status.HTTP_200_OK,
        )

    # Claim the right to generate today's session before spawning any work.
    # Without this, every poll that lands while generation is still running
    # (e.g. slow/degraded embedding service) would kick off its own redundant
    # LLM + embedding pipeline — piling up concurrent duplicate generations
    # that race on the same (user, subject, date) row.
    claimed = claim_generation_slot(enrollment, today)
    if claimed is None:
        # Someone else already claimed this date — either it just finished
        # (check again) or it's still in flight, in which case we just wait
        # for the next poll instead of starting another generation.
        ready = DailySession.objects.filter(
            enrollment=enrollment, status=DailySession.Status.READY, date=today,
        ).first()
        if ready:
            return Response(_build_session_response(ready.payload_json, ready, request.user), status=status.HTTP_200_OK)
        return Response({"status": "preparing"}, status=status.HTTP_202_ACCEPTED)

    # Slow path: generate synchronously inside a thread so we can time it out.
    # gthread Gunicorn workers handle requests in threads — signal.SIGALRM only
    # fires on the main thread, so we use ThreadPoolExecutor instead.
    #
    # Deliberately NOT a `with` block: ThreadPoolExecutor.__exit__ calls
    # shutdown(wait=True), which would block this request until the
    # generation thread finishes even after we've already decided to return
    # early on timeout — defeating the point of the timeout. shutdown(wait=False)
    # lets the thread keep running in the background (generate_daily_session
    # itself guarantees the claimed row ends up READY or gets cleaned up on
    # failure, and logs any exception that would otherwise go uncollected).
    t_start = time.perf_counter()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(generate_daily_session, enrollment=enrollment)
    try:
        raw_payload, session = future.result(timeout=_SYNC_GEN_TIMEOUT_SECONDS)
        elapsed_ms = int((time.perf_counter() - t_start) * 1000)
        logger.info(
            "sync_generation_success enrollment=%s duration_ms=%d",
            enrollment.id, elapsed_ms,
        )
        return Response(_build_session_response(raw_payload, session, request.user), status=status.HTTP_200_OK)

    except concurrent.futures.TimeoutError:
        elapsed_ms = int((time.perf_counter() - t_start) * 1000)
        logger.warning(
            "sync_generation_timeout enrollment=%s duration_ms=%d",
            enrollment.id, elapsed_ms,
        )
        return Response({"status": "preparing"}, status=status.HTTP_202_ACCEPTED)

    except Exception:
        logger.exception("Failed to generate daily session enrollment=%s", enrollment.id)
        return Response(
            {"error": "Failed to generate session. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    finally:
        executor.shutdown(wait=False)


@api_view(['GET'])
def get_session_questions(request, session_id):
    """
    Returns the full question list for a session, grouped by focus area.
    Called when the student taps "Begin session".

    Response: { "focusAreas": [{ "topicName", "type", "questions": [...] }] }
    """
    try:
        session = DailySession.objects.get(
            session_id=session_id, user_id=request.user.id
        )
    except DailySession.DoesNotExist:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    focus_areas = session.payload_json.get("focusAreas", [])
    return Response({
        "sessionId": str(session_id),
        "focusAreas": [
            {
                "topicName": area["topic"],
                "type": area["type"],
                "questions": area.get("questions", []),
            }
            for area in focus_areas
        ],
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def submit_session(request, session_id):
    """
    Submit all answers for a daily session (DS-009).

    Body: SessionSubmitSerializer shape — focus_area_attempts grouped by topic.
    """
    serializer = SessionSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    try:
        result = process_session_attempts(
            user_id=request.user.id,
            session_id=str(session_id),
            session_started_at=data["session_started_at"],
            focus_area_attempts=data["focus_area_attempts"],
        )
        return Response(result, status=status.HTTP_200_OK)
    except SessionNotFound:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)
    except SessionForbidden:
        return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
    except SessionAlreadySubmitted:
        return Response(
            {"status": "already_submitted", "session_id": str(session_id)},
            status=status.HTTP_409_CONFLICT,
        )
    except UnknownQuestionId as e:
        return Response(
            {"error": f"Unknown question_id: {e.question_id}"},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except Exception:
        logger.exception("Failed to submit session attempts")
        return Response(
            {"error": "Failed to submit session. Please try again later."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
def get_session_review(request, session_id):
    """
    Re-fetches a previously submitted session's results (DS-010).

    Returns the exact payload the /submit call returned at submission time —
    lets the frontend show a "review" screen later without re-submitting.
    """
    try:
        session = DailySession.objects.get(
            session_id=session_id, user_id=request.user.id
        )
    except DailySession.DoesNotExist:
        return Response({"error": "Session not found"}, status=status.HTTP_404_NOT_FOUND)

    if session.completed_at is None or session.results_json is None:
        return Response(
            {"error": "Session has not been submitted yet"},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(session.results_json, status=status.HTTP_200_OK)


def _build_session_response(raw: dict, session: DailySession, user) -> dict:
    """
    Transforms the generator's raw payload into the API response shape.

    Focus area questions are stripped — they live in DailySession.payload_json
    and are fetched separately when the student actually begins the session.
    The response shape matches the docx spec (Section 3.1) plus isCompleted
    and completion fields so the frontend can render the right state.
    """
    focus_areas = raw.get("focusAreas", [])
    top = focus_areas[0] if focus_areas else {}

    transformed_areas = [
        {
            "topicName": area["topic"],
            "questionCount": area["questionCount"],
            "type": area["type"],
            # accuracy only meaningful for weakness; null for new/review/advance
            "accuracy": area.get("accuracy") if area["type"] == "weakness" else None,
        }
        for area in focus_areas
    ]

    response = {
        "sessionId": raw["sessionId"],
        "subject": raw["subject"],
        "topicHeadline": top.get("topicHeadline", ""),
        "reason": top.get("reason", ""),
        "questionCount": raw["questionCount"],
        "estimatedMinutes": raw["estimatedMinutes"],
        "bloomsRange": raw["bloomsRange"],
        "weeklyProgress": {
            "completed": raw["weeklyProgress"],
            "target": 5,
        },
        "focusAreas": transformed_areas,
        "sessionStatus": session.status,
        "isCompleted": session.is_completed,
        "completionAccuracy": None,
        "completionQuestions": None,
        "completionStreak": None,
    }

    if session.is_completed:
        streak = 0
        try:
            from users.models import UserStats
            stats = UserStats.objects.get(user_id=user.id)
            streak = stats.current_streak
        except Exception:
            pass
        response["completionAccuracy"] = session.completion_accuracy
        response["completionQuestions"] = session.completion_questions
        response["completionStreak"] = streak

    return response


@api_view(['GET'])
def pollRoadmap(request):
    serializer = GetJobRequestSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        roadmapJob =fetchRoadmapJob(request.user.id,**serializer.validated_data)
        logger.info("successfully fetched the roadmap job and processing the response")
        return Response(
            roadmapJob,
            status=status.HTTP_200_OK
        )
    except RoadmapJob.DoesNotExist:
        return Response(
            {"error": "Job not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    
    

    

    


    
    

    




    


