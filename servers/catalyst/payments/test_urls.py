from django.urls import path

from . import views

urlpatterns = [
    path('api/payments/subscriptions', views.create_subscription, name='payments-create-subscription'),
    path('api/payments/subscriptions/status', views.subscription_status, name='payments-subscription-status'),
    path('api/payments/webhook', views.razorpay_webhook, name='payments-webhook'),
]