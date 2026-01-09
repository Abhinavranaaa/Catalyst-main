from django.urls import path
from notifications.views import triggerNotifications, save_push_subscription, get_vapid_public_key, process_notification_batch

urlpatterns = [
    path("trigger", triggerNotifications, name="generate-notifications"),
    path("process-batch", process_notification_batch)
]