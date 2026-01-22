from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import WebPushSubscription
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .services import batchProcess
import json
import logging
from .tasks import process_daily_notifications_batch
from catalyst import authenticate
from users.models import User

logger = logging.getLogger(__name__)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_push_subscription(request):
    data = request.data
    obj, _ = WebPushSubscription.objects.update_or_create(
        user = User.objects.filter(id=authenticate(request)).first(),
        endpoint=data.get('endpoint'),
        defaults={
            'p256dh': data['keys']['p256dh'],
            'auth': data['keys']['auth'],
        }
    )
    return Response({'status': 'ok'})


@api_view(['GET'])
@permission_classes([AllowAny])
def get_vapid_public_key(request):
    return Response({"vapidPublicKey": settings.VAPID_PUBLIC_KEY})

@api_view(['GET'])
@csrf_exempt
def triggerNotifications(request):
    response = batchProcess(request)
    logger.info("batchProcess response: %s", response)
    return response


@csrf_exempt
@api_view(['POST'])
def process_notification_batch(request):
    
    try:
        payload = json.loads(request.body)
        user_ids = payload.get("user_ids", [])
    except Exception as e:
        return JsonResponse(
            {"error": "invalid_json", "detail": str(e)},
            status=400
        )

    if not user_ids:
        return JsonResponse({"status": "empty_batch"}, status=200)

    try:
        process_daily_notifications_batch(user_ids)
    except Exception:
        logger.exception("Batch processing failed")
        return JsonResponse(
            {"error": "batch_failed"},
            status=500
        )

    return JsonResponse(
        {
            "status": "batch_processed",
            "processed_count": len(user_ids),
        },
        status=200
    )



