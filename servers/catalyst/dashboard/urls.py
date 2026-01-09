from django.urls import path

from dashboard.views import get_user_profileData
from notifications.views import save_push_subscription,get_vapid_public_key
urlpatterns = [
    path("get/", get_user_profileData, name="user-profile"),
    path('api/save-push-subscription', save_push_subscription),
    path('api/vapid-public-key', get_vapid_public_key, name='vapid_public_key'),
]