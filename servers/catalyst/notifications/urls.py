from django.urls import path
from notifications.views import triggerNotifications, process_notification_batch

urlpatterns = [
    path("trigger", triggerNotifications, name="generate-notifications"),
    path("process-batch", process_notification_batch)
]