from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from roadmap.service.generate import generate_roadmap,reshape_roadmap_for_response,save_roadmap_response
from roadmap.serializers import GenerateRoadmapRequestSerializer
import logging
from notifications.tasks import process_user_interests_async
from catalyst.constants import ADDITIONAL_COMMENTS, ROADMAP_ID
import jwt
from rest_framework.exceptions import AuthenticationFailed
import time
from catalyst import authenticate

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
        roadmap = generate_roadmap(user_id=user_id, **serializer.validated_data)
        roadmap_formatted = reshape_roadmap_for_response(roadmap)
        roadmap_instance = save_roadmap_response(user_id, raw_roadmap_data=roadmap_formatted)
        roadmap_formatted[ROADMAP_ID] = roadmap_instance.id
        comments = serializer.validated_data.get(ADDITIONAL_COMMENTS, '')
        end=time.time()
        logger.info(f"Total E2E latency: {end - start:.3f} seconds")
        return Response(
            {
                "message": "Roadmap generated successfully",
                "data": roadmap_formatted
            },
            status=status.HTTP_201_CREATED
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