from django.http import HttpResponseForbidden
from django.conf import settings
from decouple import config

class CloudflareShieldMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        expected_secret = config("CLOUDFLARE_SHIELD_SECRET")
        incoming_secret = request.META.get('HTTP_X_APP_SEC')

        if incoming_secret != expected_secret:
            return HttpResponseForbidden("Direct access is not allowed.")

        return self.get_response(request)