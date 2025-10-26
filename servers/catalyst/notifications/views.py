from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import WebPushSubscription
from rest_framework.permissions import AllowAny
from django.conf import settings

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_push_subscription(request):
    data = request.data
    obj, _ = WebPushSubscription.objects.update_or_create(
        user=request.user,
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
