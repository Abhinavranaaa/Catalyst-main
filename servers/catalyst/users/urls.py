from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="register"),
    path("login" , views.LoginView.as_view(), name = "login"),
    path("user", views.UserView.as_view(), name="user"),  # Basic user info
    path("logout", views.LogoutView.as_view(), name="logout"),
    path("subscribe", views.SubscribeView.as_view(), name="subscribe"),

    # New profile endpoints
    path("user/profile", views.UserWithProfileView.as_view(), name="user-with-profile"),
    path("profile", views.ProfileView.as_view(), name="profile"),
    path("profile/update", views.ProfileUpdateView.as_view(), name="profile-update"),
    path("profile/image", views.ProfileImageUploadView.as_view(), name="profile-image"),
    path("profile/stats", views.ProfileStatsView.as_view(), name="profile-stats"),
    path("user/change-password", views.ChangePasswordView.as_view(), name="change-password"),
    path("iOSUser" , views.IOSUserView.as_view(), name="iOSUser")
]

