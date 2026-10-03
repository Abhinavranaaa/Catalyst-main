from django.urls import path

from . import views

urlpatterns = [
    path("", views.flag_create, name="flag-create"),
]
