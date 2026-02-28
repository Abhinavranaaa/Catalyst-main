from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from roadmap.service.generate import generate_roadmap_json,fetchRoadmapJson,fetchRoadmapJob
from roadmap.serializers import GenerateRoadmapRequestSerializer, GetRoadmapRequestSerializer, GetJobRequestSerializer
import logging
from notifications.tasks import process_user_interests_async
from catalyst.constants import ADDITIONAL_COMMENTS, ROADMAP_ID
import jwt
from rest_framework.exceptions import AuthenticationFailed
import time
from catalyst import authenticate
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


logger = logging.getLogger(__name__)

@api_view(['GET'])
def getRoadmapJson(request):
    user_id=authenticate(request)
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
    user_id=authenticate(request)
    payload = request.data or {}
    try:
        validator = QueryValidator()
        parser = QueryParser()
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
        query_builder = QueryBuilder(dynamic_filter=DynamicFilterApplier(),sort=DynamicSortApplier(),search=SearchDynamicQueries())
        qs = query_builder.build(user_id,parsed_request)
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

    user_id=authenticate(request)
    serializer = GenerateRoadmapRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        service = RoadmapJobService()
        job = service.create(
            user_id=user_id,
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
def pollRoadmap(request):
    user_id=authenticate(request)
    serializer = GetJobRequestSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        roadmapJob =fetchRoadmapJob(user_id,**serializer.validated_data)
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

    
    

    

    


    
    

    




    


