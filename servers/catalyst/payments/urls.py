from django.urls import path

from . import views

urlpatterns = [
    path("subscriptions", views.create_subscription, name="payments-create-subscription"),
    path("subscriptions/status", views.subscription_status, name="payments-subscription-status"),
    path("webhook", views.razorpay_webhook, name="payments-webhook"),
]