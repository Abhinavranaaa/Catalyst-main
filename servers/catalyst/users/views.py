from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.decorators import api_view,permission_classes
from .serializers import UserSerializer , UserLoginSerializer
from rest_framework.response import Response
from rest_framework.exceptions import AuthenticationFailed
from users.models import User, UserProfile, Subscriber
import jwt, datetime
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from .serializers import (
    UserProfileSerializer,
    UserWithProfileSerializer,
    ProfileUpdateSerializer,
    ChangePasswordSerializer
)
from rest_framework.decorators import api_view
from catalyst.constants import CATALYST_EMAIL,WINDOW
from notifications.observer import EmailObserver
from .serializers import SerializeUserInfo
import logging
from users.signals.createProfile import saveAndProcessUser
from .service.dashboardRead import DashBoardReadService,DashBoardCacheService,DashboardBuilder
from rest_framework.permissions import AllowAny
from google_auth_oauthlib.flow import Flow
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import redirect
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from datetime import timedelta
from django.db import DatabaseError
import os

# initialisation
logger = logging.getLogger(__name__)
cache_service = DashBoardCacheService(WINDOW)
builder = DashboardBuilder()
dashboard_service = DashBoardReadService(cache_service, builder)

# Create your views here.


def create_jwt(user_id):
    payload = {
        "id": user_id,
        "exp": datetime.datetime.utcnow() + timedelta(minutes = 60),
        "iat" : datetime.datetime.utcnow()
    }

    return jwt.encode(payload, "secret", algorithm="HS256")

class RegisterView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = User.objects.filter(email = email).first()
        if user.auth_provider == "GOOGLE":
            raise AuthenticationFailed("Login using your previous method: google")

        if user is None:
            raise AuthenticationFailed("User Not Found")

        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect Password try other login options")

        token = create_jwt(user.id)
        response = Response()
        response.set_cookie(key = "jwt" , value = token, httponly = True , secure=True,samesite='None',path='/')
        response.data = {
            "jwt": token
        }

        return response

class UserView(APIView):
    def get(self,request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)

class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie("jwt")
        response.data = {
            "message" : "success"
        }
        return response



class BaseAuthenticatedView(APIView):
    """Base class that handles JWT cookie authentication"""

    def get_user_from_token(self, request):
        """Extract and validate user from JWT cookie"""
        token = request.COOKIES.get("jwt")

        if not token:
            raise AuthenticationFailed("Unauthenticated")

        try:
            payload = jwt.decode(token, "secret", algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token")

        user = User.objects.filter(id=payload["id"]).first()
        if not user:
            raise AuthenticationFailed("User not found")

        return user


class ProfileView(BaseAuthenticatedView):
    """Get user profile"""

    def get(self, request):
        user = self.get_user_from_token(request)

        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)

        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)


class ProfileUpdateView(BaseAuthenticatedView):
    """Update user profile"""

    def put(self, request):
        return self._update_profile(request, partial=False)

    def patch(self, request):
        return self._update_profile(request, partial=True)

    def _update_profile(self, request, partial=False):
        user = self.get_user_from_token(request)

        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(user=user)

        serializer = ProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            serializer.save()
            # Return full profile data
            response_serializer = UserProfileSerializer(profile)
            return Response(response_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserWithProfileView(BaseAuthenticatedView):
    """Get user data with profile - extends your existing UserView"""

    def get(self, request):
        user = self.get_user_from_token(request)

        # Ensure profile exists
        profile, created = UserProfile.objects.get_or_create(user=user)

        serializer = UserWithProfileSerializer(user)
        return Response(serializer.data)


class ChangePasswordView(BaseAuthenticatedView):
    """Change user password"""

    def post(self, request):
        user = self.get_user_from_token(request)

        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {'error': 'Old password is incorrect'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()

            return Response({'message': 'Password changed successfully'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileImageUploadView(BaseAuthenticatedView):
    """Upload profile image"""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = self.get_user_from_token(request)

        # Get or create profile
        profile, created = UserProfile.objects.get_or_create(user=user)

        if 'profile_image' not in request.FILES:
            return Response(
                {'error': 'No image file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file type
        file = request.FILES['profile_image']
        if not file.content_type.startswith('image/'):
            return Response(
                {'error': 'File must be an image'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            return Response(
                {'error': 'Image file too large (max 5MB)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        profile.profile_image = file
        profile.save()

        serializer = UserProfileSerializer(profile)
        return Response({
            'message': 'Profile image uploaded successfully',
            'profile': serializer.data
        })

    def delete(self, request):
        """Remove profile image"""
        user = self.get_user_from_token(request)

        try:
            profile = user.profile
            if profile.profile_image and profile.profile_image.name != 'profile_images/default.jpg':
                profile.profile_image.delete()
                profile.profile_image = 'profile_images/default.jpg'
                profile.save()

                return Response({'message': 'Profile image removed successfully'})
            else:
                return Response(
                    {'error': 'No profile image to remove'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class ProfileStatsView(BaseAuthenticatedView):
    """Get profile statistics and completion status"""

    def get(self, request):
        user = self.get_user_from_token(request)

        try:
            profile = user.profile

            # Calculate profile completion
            fields_to_check = ['bio', 'phone', 'location', 'birth_date']
            completed_fields = sum(1 for field in fields_to_check if getattr(profile, field))

            has_image = (profile.profile_image and
                        profile.profile_image.name != 'profile_images/default.jpg')

            completion_percentage = ((completed_fields + (1 if has_image else 0)) /
                                   (len(fields_to_check) + 1)) * 100

            stats = {
                'profile_completion': round(completion_percentage),
                'has_profile_image': has_image,
                'completed_fields': completed_fields,
                'total_fields': len(fields_to_check) + 1,
                'missing_fields': [field for field in fields_to_check
                                 if not getattr(profile, field)],
                'last_updated': profile.updated_at,
                'member_since': profile.created_at,
            }

            return Response(stats)

        except UserProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)

        


class SubscribeView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"message": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        if Subscriber.objects.filter(email=email).exists():
            return Response({"message": "Email already subscribed"}, status=status.HTTP_409_CONFLICT)

        subscriber = Subscriber.objects.create(email=email)

        email_observer = EmailObserver()
        domain_url = 'https://catalyst-main-1036749949194.us-central1.run.app' 

        email_observer.send(
            user=subscriber,  
            message="Thank you for subscribing to our notifications!",
            domain_url=domain_url
        )

        return Response({"message": "Subscribed successfully"}, status=status.HTTP_201_CREATED)
    
@api_view(['POST'])
def triggerOnboarding(request):
    serializer = SerializeUserInfo(data=request.data)
    serializer.is_valid(raise_exception=False)
    response = saveAndProcessUser(request.user.id,**serializer.validated_data)
    logger.info("save user info response: %s", response)
    return Response({"message": "Onboarded successfully"}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def getDashboard(request):
    try:
        response = dashboard_service.render(request.user.id)
        return Response({"message": "rendered successfully","result":response}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {
                "error": f"An unexpected error occurred while fetching the dashboard. Please try again later.{e}"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(["GET"])
@permission_classes([AllowAny])
def google_login(request):

    flow = Flow.from_client_config(
        settings.GOOGLE_OAUTH_CONFIG,
        scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    auth_url, state = flow.authorization_url()
    print(auth_url)
    request.session["google_oauth_state"] = state
    request.session["code_verifier"] = flow.code_verifier

    return redirect(auth_url)

@permission_classes([AllowAny])
def google_callback(request):

    try:
        error = request.GET.get("error")
        if error:
            logger.warning(f"Google OAuth denied: {error}")
            return redirect(settings.FRONTEND_LOGIN_FAILED)

        state = request.session.get("google_oauth_state")
        if not state:
            logger.error("Missing OAuth state in session")
            return redirect(settings.FRONTEND_LOGIN_FAILED)
        
        # os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        flow = Flow.from_client_config(
            settings.GOOGLE_OAUTH_CONFIG,
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            state=state,
            code_verifier=request.session["code_verifier"],
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )

        try:
            flow.fetch_token(
                authorization_response=request.build_absolute_uri()
            )
        except Exception:
            logger.exception("Token exchange failed")
            return redirect(settings.FRONTEND_LOGIN_FAILED)

        credentials = flow.credentials

        try:
            idinfo = id_token.verify_oauth2_token(
                credentials.id_token,
                grequests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
        except Exception:
            logger.exception("ID token verification failed")
            return redirect(settings.FRONTEND_LOGIN_FAILED)

        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email:
            logger.error("Email missing in Google profile")
            return redirect(settings.FRONTEND_LOGIN_FAILED)

        try:
            user_id = user_init(email, name)
        except DatabaseError:
            logger.exception("User creation failed")
            return redirect(settings.FRONTEND_LOGIN_FAILED)

        try:
            token = create_jwt(user_id)
            print(token)
        except Exception:
            logger.exception("JWT generation failed")
            return redirect(settings.FRONTEND_LOGIN_FAILED)

       
        response = redirect(settings.FRONTEND_HOME)

        response.set_cookie(
            "jwt",
            token,
            httponly=True,
            secure=True,
            samesite=None,
            max_age=settings.JWT_EXP_SECONDS
        )

        return response

    except Exception:
        logger.exception("Unexpected OAuth failure")
        return redirect(settings.FRONTEND_LOGIN_FAILED)

def user_init(email:str,name:str):
    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create(
            email=email,
            name=name,
            auth_provider="GOOGLE"
        )
    return user.id

@api_view(['GET'])
@permission_classes([AllowAny])
def me(request):
    return Response({
        "user_id": request.user.id
    })
    