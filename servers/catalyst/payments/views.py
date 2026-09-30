import hashlib
import json
import logging
from datetime import datetime, timezone as dt_timezone

import razorpay
from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from payments.models import Plan, ProcessedWebhookEvent, Subscription
from payments.razorpay_client import get_razorpay_client

logger = logging.getLogger(__name__)

_STATUS_BY_EVENT = {
    "subscription.activated": "active",
    "subscription.charged": "active",
    "subscription.cancelled": "cancelled",
    "subscription.paused": "paused",
}


def _parse_timestamp(unix_ts):
    return datetime.fromtimestamp(unix_ts, tz=dt_timezone.utc)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    plan_id = request.data.get("plan_id")
    if not plan_id:
        return Response({"error": "plan_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    plan = get_object_or_404(Plan, id=plan_id, is_active=True)

    razorpay_client = get_razorpay_client()
    try:
        rp_subscription = razorpay_client.subscription.create({
            "plan_id": plan.razorpay_plan_id,
            "customer_notify": 1,
            "total_count": 12,
        })
    except razorpay.errors.BadRequestError as exc:
        logger.warning("Razorpay rejected subscription creation for plan %s: %s", plan.id, exc)
        return Response({"error": "razorpay_error"}, status=status.HTTP_502_BAD_GATEWAY)

    subscription = Subscription.objects.create(
        user_id=str(request.user.id),
        razorpay_subscription_id=rp_subscription["id"],
        plan=plan,
        status="created",
    )

    return Response({"razorpay_subscription_id": subscription.razorpay_subscription_id})


@api_view(["POST"])
@permission_classes([AllowAny])
def razorpay_webhook(request):
    signature = request.headers.get("X-Razorpay-Signature")
    body = request.body

    if not signature:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    razorpay_client = get_razorpay_client()
    try:
        razorpay_client.utility.verify_webhook_signature(
            body.decode(), signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
    except razorpay.errors.SignatureVerificationError:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    event = json.loads(body)

    # Razorpay's webhook JSON body carries no event id of its own — the
    # documented dedup key is the `x-razorpay-event-id` header, unique per
    # delivery and stable across retries. Fall back to a body hash only if a
    # delivery is somehow missing it, so a validly-signed event is never
    # dropped for lack of a dedup key.
    event_id = request.headers.get("X-Razorpay-Event-Id")
    if not event_id:
        event_id = hashlib.sha256(body).hexdigest()
        logger.warning("Razorpay webhook missing X-Razorpay-Event-Id header; using body hash for dedup")

    if ProcessedWebhookEvent.objects.filter(event_id=event_id).exists():
        return Response(status=status.HTTP_200_OK)

    event_type = event.get("event")
    new_status = _STATUS_BY_EVENT.get(event_type)

    try:
        with transaction.atomic():
            if new_status:
                payload = event["payload"]["subscription"]["entity"]
                rp_subscription_id = payload["id"]

                subscription = Subscription.objects.filter(
                    razorpay_subscription_id=rp_subscription_id
                ).first()

                if subscription:
                    subscription.status = new_status
                    if event_type == "subscription.charged":
                        subscription.current_period_end = _parse_timestamp(payload["current_end"])
                    subscription.save()

            ProcessedWebhookEvent.objects.create(event_id=event_id)
    except IntegrityError:
        # Lost a race with a concurrent delivery of the same event — the
        # unique constraint on event_id is the real dedup guard; the
        # .exists() check above is just a fast path to skip re-processing
        # in the common (non-racing) case. The whole block above rolled
        # back, so this delivery made no partial state change.
        logger.info("Razorpay webhook event %s already processed by a concurrent request", event_id)

    return Response(status=status.HTTP_200_OK)
