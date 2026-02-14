from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from roadmap.service.generate import generate_roadmap,reshape_roadmap_for_response,save_roadmap_response,fetchRoadmapJson
from roadmap.serializers import GenerateRoadmapRequestSerializer, GetRoadmapRequestSerializer
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

logger = logging.getLogger(__name__)

@api_view(['POST'])
# @permission_classes([IsAuthenticated])
def generate_roadmap_view(request):

    user_id=authenticate(request)
    serializer = GenerateRoadmapRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        start=time.time()
        validated_data = serializer.validated_data
        response = generate_roadmap(user_id=user_id, **validated_data)
        roadmap_formatted = response["formatted"]
        roadmap = response["raw"]
        roadmap_instance = save_roadmap_response(user_id, raw_roadmap_data=roadmap_formatted, raw_roadmap=roadmap,subject=validated_data.get("subject"),topic=validated_data.get("topic"),)
        roadmap_formatted[ROADMAP_ID] = roadmap_instance.id
        # comments = serializer.validated_data.get(ADDITIONAL_COMMENTS, '')
        end=time.time()
        logger.info(f"Total E2E latency: {end - start:.3f} seconds")
        return Response(
            {
                "message": "Roadmap generated successfully",
                "data": roadmap_formatted
            },
            status=status.HTTP_201_CREATED
        )
        
    except KeyError as e:
        logger.error("Roadmap response missing key: %s", e)
        return Response(
            {"message": "Invalid roadmap response"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    except ValueError as ve:
        logger.warning(f"Business validation error: {ve}")
        return Response(
            {"error": str(ve)},
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        logger.exception("Internal server error during roadmap generation")
        return Response(
            {
                "error": "An unexpected error occurred while generating the roadmap. Please try again later."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
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


    
    

    

    


    
    

    




    


