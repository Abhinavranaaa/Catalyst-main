from django.shortcuts import render
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
import jwt
from .serializers import PostUsrAttemptSerializer
from .service import processAttempts
import time
from catalyst import authenticate

# Create your views here.
# remember how the importing work in django and the order of imports
# and the use of http handlers via google cloud
# make sure to read it
logger = logging.getLogger(__name__)

@api_view(['POST'])
def postUserAttempt(request):
    user_id=authenticate(request)
    serializer = PostUsrAttemptSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    try:
        start=time.time()
        report = processAttempts(user_id=user_id, **serializer.validated_data)
        end=time.time()
        logger.info(f"Total E2E latency: {end - start:.3f} seconds")
        return Response(
            {
                "message": "Report for the posted attempts",
                "data": report
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
        logger.exception("Internal server error during submitting roadmap, %s", str(e))
        return Response(
            {
                "error": "An unexpected error occurred while updating attempts. Please try again later."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
     



    







