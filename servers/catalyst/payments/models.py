import uuid

from django.db import models


class Plan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razorpay_plan_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PlanEntitlement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="entitlements")
    entitlement_key = models.CharField(max_length=100)

    class Meta:
        unique_together = ("plan", "entitlement_key")

    def __str__(self):
        return f"{self.plan_id}:{self.entitlement_key}"


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("paused", "Paused"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Plain string, not a hard FK — same pattern as TelemetryEvent. An entitlement
    # check must degrade to "no active subscription" instead of throwing on a
    # broken join, since it runs on essentially every gated request.
    user_id = models.CharField(max_length=255)
    razorpay_subscription_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    # PROTECT — a Plan being retired must never cascade-delete active subscriber
    # records. Retire a plan via is_active=False instead.
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "status"]),
        ]

    def __str__(self):
        return f"Subscription({self.user_id}, {self.status})"


class ProcessedWebhookEvent(models.Model):
    # Razorpay's webhook JSON body has no unique event id field of its own —
    # the dedup key is the `x-razorpay-event-id` header, stable across retries.
    event_id = models.CharField(max_length=255, unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id
