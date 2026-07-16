from django.urls import path
from . import views

urlpatterns = [
    path('', views.create_enrollment, name='enrollment-create'),
    path('list', views.list_enrollments, name='enrollment-list'),
]
