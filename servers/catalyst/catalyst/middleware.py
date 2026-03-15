from django.http import HttpResponseForbidden
from django.conf import settings
from decouple import config
import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from users.models import User

class CloudflareShieldMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        expected_secret = config("CLOUDFLARE_SHIELD_SECRET")
        incoming_secret = request.META.get('HTTP_X_APP_SEC')

        if incoming_secret != expected_secret:
            return HttpResponseForbidden("Direct access is not allowed.")

        return self.get_response(request)


class CookieJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):

        token = request.COOKIES.get("jwt")

        if not token:
            return None   

        try:
            payload = jwt.decode(
                token,
                "secret",
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            # treat as anonymous 
            return None
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token")

        user = User.objects.filter(id=payload["id"]).first()

        if not user:
            raise AuthenticationFailed("User not found")

        return (user, None)