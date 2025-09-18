from django.shortcuts import render
import jwt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging
from dashboard.fetchUserData import fetch_user_profile_with_top_roadmaps

logger = logging.getLogger(__name__)

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_user_profileData(request):
    token = request.COOKIES.get("jwt")
    #user_id = request.headers.get('X-User-ID')
    if not token:
        raise AuthenticationFailed("Unauthenticated")
    try:
        payload = jwt.decode(token, "secret", algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Unauthenticated")

    user_id = payload["id"]

    if not user_id:
        return Response(
            {"error": "Missing User ID in headers"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        values=fetch_user_profile_with_top_roadmaps(user_id)
        return Response(
            {
                "message": "User Profile Data",
                "data": values
            },
            status=status.HTTP_200_OK
        )
    except ValueError as ve:
        logger.warning(f"Business validation error: {ve}")
        return Response(
            {"error": str(ve)},
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:
        logger.exception("Internal server error during fetching User Profile")
        return Response(
            {
                "error": "An unexpected error occurred while fetching user fields. Please try again later."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


