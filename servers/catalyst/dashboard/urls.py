from django.urls import path

from dashboard.views import get_user_profileData

urlpatterns = [
    path("get/", get_user_profileData, name="user-profile"),
]