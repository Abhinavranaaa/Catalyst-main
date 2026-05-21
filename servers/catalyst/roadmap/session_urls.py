from django.urls import path
from roadmap.views import get_today_session, get_session_questions, submit_session

urlpatterns = [
    path("today", get_today_session, name="session-today"),
    path("<uuid:session_id>/questions", get_session_questions, name="session-questions"),
    path("<uuid:session_id>/submit", submit_session, name="session-submit"),
]
