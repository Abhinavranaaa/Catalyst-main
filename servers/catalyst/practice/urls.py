from django.urls import path
from .views import postUserAttempt

urlpatterns = [
    path("saveAttempts", postUserAttempt, name="post-attempt"),
]