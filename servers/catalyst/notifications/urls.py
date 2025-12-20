from django.urls import path
from notifications.views import triggerNotifications, save_push_subscription, get_vapid_public_key, process_notification_batch

urlpatterns = [
    path("trigger", triggerNotifications, name="generate-notifications"),
    path('api/save-push-subscription', save_push_subscription),
    path('api/vapid-public-key', get_vapid_public_key, name='vapid_public_key'),
    path("process-batch", process_notification_batch)
]