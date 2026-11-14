from django.urls import path

from . import views

urlpatterns = [
    path('api/bookmarks/', views.bookmark_list_create, name='bookmark-list-create'),
    path('api/bookmarks/<uuid:bookmark_id>/', views.bookmark_delete, name='bookmark-delete'),
    path('api/flags/', views.flag_create, name='flag-create'),
]
