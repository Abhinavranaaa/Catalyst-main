from django.urls import path

from . import views

urlpatterns = [
    path("", views.bookmark_list_create, name="bookmark-list-create"),
    path("<uuid:bookmark_id>/", views.bookmark_delete, name="bookmark-delete"),
]
