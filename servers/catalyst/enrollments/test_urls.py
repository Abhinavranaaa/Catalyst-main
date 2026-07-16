from django.urls import path
from . import views
from roadmap import views as roadmap_views

urlpatterns = [
    path('api/enrollments/', views.create_enrollment, name='enrollment-create'),
    path('api/enrollments/list', views.list_enrollments, name='enrollment-list'),
    path('api/sessions/today', roadmap_views.get_today_session, name='session-today'),
]
