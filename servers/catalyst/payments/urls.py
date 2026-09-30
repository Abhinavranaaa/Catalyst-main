from django.urls import path

from . import views

urlpatterns = [
    path("subscriptions", views.create_subscription, name="payments-create-subscription"),
    path("webhook", views.razorpay_webhook, name="payments-webhook"),
]