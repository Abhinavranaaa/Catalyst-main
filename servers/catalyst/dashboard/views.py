import jwt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import logging
from .fetchUserData import fetch_user_profile_with_top_roadmaps
from rest_framework.exceptions import AuthenticationFailed
from catalyst import authenticate

logger = logging.getLogger(__name__)

@api_view(['GET'])
def get_user_profileData(request):
    user_id = authenticate(request)
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


