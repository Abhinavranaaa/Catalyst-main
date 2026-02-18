from django.shortcuts import render
from rest_framework.views import APIView
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
from catalyst.constants import CATALYST_EMAIL
from notifications.observer import EmailObserver
from .serializers import SerializeUserInfo
import logging
from users.signals.createProfile import saveAndProcessUser
from catalyst import authenticate


logger = logging.getLogger(__name__)

# Create your views here.
class RegisterView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class LoginView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        user = User.objects.filter(email = email).first()

        if user is None:
            raise AuthenticationFailed("User Not Found")

        if not user.check_password(password):
            raise AuthenticationFailed("Incorrect Password")

        payload = {
            "id" : user.id,
            "exp" : datetime.datetime.utcnow() + datetime.timedelta(minutes = 60),
            "iat" : datetime.datetime.utcnow()
        }

        token = jwt.encode(payload, "secret" , algorithm = "HS256")

        response = Response()

        response.set_cookie(key = "jwt" , value = token, httponly = True , secure=True,samesite='None',path='/')
        response.data = {
            "jwt": token
        }

        return response

class UserView(APIView):
    def get(self,request):
        user = BaseAuthenticatedView().get_user_from_token(request)

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
    user_id = authenticate(request)
    serializer = SerializeUserInfo(data=request.data)
    serializer.is_valid(raise_exception=False)
    response = saveAndProcessUser(user_id,**serializer.validated_data)
    logger.info("save user info response: %s", response)
    return Response({"message": "Onboarded successfully"}, status=status.HTTP_201_CREATED)


