import hashlib
import hmac
import json
import threading
import uuid
from datetime import datetime
from unittest import mock

from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from payments.entitlements import has_entitlement
from payments.models import Plan, PlanEntitlement, ProcessedWebhookEvent, Subscription
from users.models import User

# Same trick enrollments/tests.py uses: strip CloudflareShieldMiddleware (no
# shield secret needed in tests) and point at a local urlconf so the system
# check doesn't drag in notifications' heavy deps (torch/numpy).
_TEST_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
_TEST_URLS = 'payments.test_urls'
_WEBHOOK_SECRET = 'test-webhook-secret'


def _make_user(suffix=''):
    return User.objects.create(
        email=f"pay_{suffix or uuid.uuid4().hex[:8]}@example.com",
        name="Test User",
    )


def _sign(body: bytes, secret: str = _WEBHOOK_SECRET) -> str:
    return hmac.new(key=secret.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()


def _subscription_event(event_type, rp_subscription_id, **entity_overrides):
    entity = {
        "id": rp_subscription_id,
        "entity": "subscription",
        "status": "active",
        "current_end": 1572892200,
    }
    entity.update(entity_overrides)
    return {
        "entity": "event",
        "event": event_type,
        "contains": ["subscription"],
        "payload": {"subscription": {"entity": entity}},
        "created_at": 1567690383,
    }


class HasEntitlementTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            razorpay_plan_id="test_plan_placeholder",
            name="Test Plan",
            price=0,
        )

    def test_no_subscription_returns_false(self):
        self.assertFalse(has_entitlement("user-without-subscription", "extra_courses"))

    def test_active_subscription_with_entitlement_returns_true(self):
        PlanEntitlement.objects.create(plan=self.plan, entitlement_key="extra_courses")
        Subscription.objects.create(user_id="user-1", plan=self.plan, status="active")

        self.assertTrue(has_entitlement("user-1", "extra_courses"))

    def test_cancelled_subscription_returns_false(self):
        PlanEntitlement.objects.create(plan=self.plan, entitlement_key="extra_courses")
        Subscription.objects.create(user_id="user-2", plan=self.plan, status="cancelled")

        self.assertFalse(has_entitlement("user-2", "extra_courses"))


@override_settings(
    MIDDLEWARE=_TEST_MIDDLEWARE,
    ROOT_URLCONF=_TEST_URLS,
    RAZORPAY_WEBHOOK_SECRET=_WEBHOOK_SECRET,
)
class CreateSubscriptionViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)
        self.plan = Plan.objects.create(
            razorpay_plan_id="plan_test123", name="Pro", price=499
        )

    @mock.patch("payments.views.get_razorpay_client")
    def test_returns_razorpay_subscription_id_for_valid_plan(self, mock_get_client):
        mock_client = mock.Mock()
        mock_client.subscription.create.return_value = {"id": "sub_test123"}
        mock_get_client.return_value = mock_client

        resp = self.client.post("/api/payments/subscriptions", {"plan_id": str(self.plan.id)})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["razorpay_subscription_id"], "sub_test123")
        self.assertTrue(
            Subscription.objects.filter(
                razorpay_subscription_id="sub_test123",
                plan=self.plan,
                user_id=str(self.user.id),
                status="created",
            ).exists()
        )
        mock_client.subscription.create.assert_called_once_with({
            "plan_id": "plan_test123",
            "customer_notify": 1,
            "total_count": 12,
        })

    def test_unknown_plan_returns_404(self):
        resp = self.client.post("/api/payments/subscriptions", {"plan_id": str(uuid.uuid4())})
        self.assertEqual(resp.status_code, 404)

    def test_inactive_plan_returns_404(self):
        self.plan.is_active = False
        self.plan.save()
        resp = self.client.post("/api/payments/subscriptions", {"plan_id": str(self.plan.id)})
        self.assertEqual(resp.status_code, 404)

    def test_requires_authentication(self):
        # CookieJWTAuthentication doesn't declare authenticate_header, so DRF's
        # IsAuthenticated denial falls back to 403 rather than 401 — same
        # behavior every other authenticated endpoint in this codebase has.
        self.client.force_authenticate(user=None)
        resp = self.client.post("/api/payments/subscriptions", {"plan_id": str(self.plan.id)})
        self.assertEqual(resp.status_code, 403)


@override_settings(
    MIDDLEWARE=_TEST_MIDDLEWARE,
    ROOT_URLCONF=_TEST_URLS,
    RAZORPAY_WEBHOOK_SECRET=_WEBHOOK_SECRET,
)
class SubscriptionStatusViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = _make_user()
        self.client.force_authenticate(user=self.user)
        self.plan = Plan.objects.create(razorpay_plan_id="plan_test123", name="Pro", price=499)

    def test_no_subscription_returns_inactive_cleanly(self):
        resp = self.client.get("/api/payments/subscriptions/status")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {
            "has_active_subscription": False,
            "status": None,
            "plan_name": None,
            "current_period_end": None,
        })

    def test_active_subscriber_returns_correct_data(self):
        period_end = timezone.now().replace(microsecond=0)
        Subscription.objects.create(
            user_id=str(self.user.id),
            plan=self.plan,
            razorpay_subscription_id="sub_test123",
            status="active",
            current_period_end=period_end,
        )

        resp = self.client.get("/api/payments/subscriptions/status")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["has_active_subscription"])
        self.assertEqual(body["status"], "active")
        self.assertEqual(body["plan_name"], "Pro")
        self.assertEqual(
            datetime.fromisoformat(body["current_period_end"].replace("Z", "+00:00")),
            period_end,
        )

    def test_reads_through_the_same_subscription_model_pay02_writes_to(self):
        # No separate read-model / cache — this endpoint must reflect whatever
        # razorpay_webhook (PAY-02) last wrote to Subscription, directly.
        subscription = Subscription.objects.create(
            user_id=str(self.user.id),
            plan=self.plan,
            razorpay_subscription_id="sub_test123",
            status="created",
        )

        resp = self.client.get("/api/payments/subscriptions/status")
        self.assertFalse(resp.json()["has_active_subscription"])

        # Simulate what razorpay_webhook does on subscription.activated.
        subscription.status = "active"
        subscription.save()

        resp = self.client.get("/api/payments/subscriptions/status")
        self.assertTrue(resp.json()["has_active_subscription"])
        self.assertEqual(resp.json()["status"], "active")

    def test_cancelled_only_subscriber_reports_inactive_with_last_known_status(self):
        Subscription.objects.create(
            user_id=str(self.user.id),
            plan=self.plan,
            razorpay_subscription_id="sub_test123",
            status="cancelled",
        )

        resp = self.client.get("/api/payments/subscriptions/status")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["has_active_subscription"])
        self.assertEqual(body["status"], "cancelled")
        self.assertEqual(body["plan_name"], "Pro")

    def test_active_row_preferred_over_older_cancelled_row(self):
        Subscription.objects.create(
            user_id=str(self.user.id),
            plan=self.plan,
            razorpay_subscription_id="sub_old",
            status="cancelled",
        )
        Subscription.objects.create(
            user_id=str(self.user.id),
            plan=self.plan,
            razorpay_subscription_id="sub_new",
            status="active",
        )

        resp = self.client.get("/api/payments/subscriptions/status")

        body = resp.json()
        self.assertTrue(body["has_active_subscription"])
        self.assertEqual(body["status"], "active")

    def test_does_not_leak_other_users_subscriptions(self):
        Subscription.objects.create(
            user_id="some-other-user",
            plan=self.plan,
            razorpay_subscription_id="sub_other",
            status="active",
        )

        resp = self.client.get("/api/payments/subscriptions/status")

        self.assertFalse(resp.json()["has_active_subscription"])
        self.assertIsNone(resp.json()["status"])

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get("/api/payments/subscriptions/status")
        self.assertEqual(resp.status_code, 403)


@override_settings(
    MIDDLEWARE=_TEST_MIDDLEWARE,
    ROOT_URLCONF=_TEST_URLS,
    RAZORPAY_WEBHOOK_SECRET=_WEBHOOK_SECRET,
)
class RazorpayWebhookTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = Plan.objects.create(razorpay_plan_id="plan_test123", name="Pro", price=499)
        self.subscription = Subscription.objects.create(
            user_id="webhook-user",
            plan=self.plan,
            razorpay_subscription_id="sub_test123",
            status="created",
        )

    def _post_webhook(self, event, event_id="evt_1", signature=None):
        body = json.dumps(event).encode()
        sig = signature if signature is not None else _sign(body)
        headers = {"HTTP_X_RAZORPAY_SIGNATURE": sig}
        if event_id is not None:
            headers["HTTP_X_RAZORPAY_EVENT_ID"] = event_id
        return self.client.generic(
            "POST", "/api/payments/webhook", data=body,
            content_type="application/json", **headers,
        )

    def test_missing_signature_returns_400(self):
        event = _subscription_event("subscription.activated", "sub_test123")
        body = json.dumps(event).encode()
        resp = self.client.generic(
            "POST", "/api/payments/webhook", data=body, content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "created")

    def test_forged_signature_returns_400_and_does_not_mutate_subscription(self):
        event = _subscription_event("subscription.activated", "sub_test123")
        resp = self._post_webhook(event, signature="0" * 64)

        self.assertEqual(resp.status_code, 400)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "created")
        self.assertFalse(ProcessedWebhookEvent.objects.exists())

    def test_activated_event_sets_status_active(self):
        event = _subscription_event("subscription.activated", "sub_test123")
        resp = self._post_webhook(event, event_id="evt_activated")

        self.assertEqual(resp.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "active")
        self.assertTrue(ProcessedWebhookEvent.objects.filter(event_id="evt_activated").exists())

    def test_charged_event_sets_active_and_current_period_end(self):
        event = _subscription_event("subscription.charged", "sub_test123", current_end=1572892200)
        resp = self._post_webhook(event, event_id="evt_charged")

        self.assertEqual(resp.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "active")
        self.assertIsNotNone(self.subscription.current_period_end)
        self.assertEqual(self.subscription.current_period_end.timestamp(), 1572892200)

    def test_cancelled_event_sets_status_cancelled(self):
        self.subscription.status = "active"
        self.subscription.save()
        event = _subscription_event("subscription.cancelled", "sub_test123")
        resp = self._post_webhook(event, event_id="evt_cancelled")

        self.assertEqual(resp.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "cancelled")

    def test_paused_event_sets_status_paused(self):
        self.subscription.status = "active"
        self.subscription.save()
        event = _subscription_event("subscription.paused", "sub_test123")
        resp = self._post_webhook(event, event_id="evt_paused")

        self.assertEqual(resp.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "paused")

    def test_duplicate_event_id_is_processed_only_once(self):
        event = _subscription_event("subscription.activated", "sub_test123")

        first = self._post_webhook(event, event_id="evt_dup")
        self.assertEqual(first.status_code, 200)
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "active")

        # Flip it back to simulate "no reprocessing happened" being observable.
        self.subscription.status = "paused"
        self.subscription.save()

        second = self._post_webhook(event, event_id="evt_dup")
        self.assertEqual(second.status_code, 200)

        self.subscription.refresh_from_db()
        self.assertEqual(
            self.subscription.status, "paused",
            "replayed event must not reprocess and flip status back to active",
        )
        self.assertEqual(
            ProcessedWebhookEvent.objects.filter(event_id="evt_dup").count(), 1
        )

    def test_unknown_razorpay_subscription_id_is_acknowledged_without_error(self):
        event = _subscription_event("subscription.activated", "sub_does_not_exist")
        resp = self._post_webhook(event, event_id="evt_unknown_sub")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ProcessedWebhookEvent.objects.filter(event_id="evt_unknown_sub").exists())


@override_settings(
    MIDDLEWARE=_TEST_MIDDLEWARE,
    ROOT_URLCONF=_TEST_URLS,
    RAZORPAY_WEBHOOK_SECRET=_WEBHOOK_SECRET,
)
class RazorpayWebhookConcurrencyTests(TransactionTestCase):
    """
    Two near-simultaneous deliveries of the identical webhook event both pass
    the ProcessedWebhookEvent existence check before either has inserted its
    row (the TOCTOU window between the .exists() guard and the .create()
    call). The DB's unique constraint on event_id is what actually has to
    stop double-processing here — this test forces that window open with a
    barrier instead of hoping a race shows up under normal timing.
    """

    def setUp(self):
        self.plan = Plan.objects.create(razorpay_plan_id="plan_test123", name="Pro", price=499)
        self.subscription = Subscription.objects.create(
            user_id="race-user",
            plan=self.plan,
            razorpay_subscription_id="sub_test123",
            status="created",
        )

    def test_concurrent_identical_webhook_deliveries_apply_state_change_once(self):
        event = _subscription_event("subscription.activated", "sub_test123")
        body = json.dumps(event).encode()
        sig = _sign(body)
        event_id = "evt_race"

        barrier = threading.Barrier(2, timeout=10)
        real_exists = QuerySet.exists

        def synced_exists(qs_self):
            # Only the ProcessedWebhookEvent dedup lookup needs to be forced
            # into lockstep; letting every other .exists() call through
            # unsynchronized keeps this from deadlocking on unrelated queries.
            if qs_self.model is ProcessedWebhookEvent:
                barrier.wait()
            return real_exists(qs_self)

        outcomes = {}

        def send_request(key):
            client = APIClient()
            try:
                resp = client.generic(
                    "POST", "/api/payments/webhook", data=body,
                    content_type="application/json",
                    HTTP_X_RAZORPAY_SIGNATURE=sig,
                    HTTP_X_RAZORPAY_EVENT_ID=event_id,
                )
                outcomes[key] = resp.status_code
            except Exception as exc:  # noqa: BLE001 - must not vanish in the thread
                outcomes[key] = exc

        with mock.patch.object(QuerySet, "exists", synced_exists):
            t1 = threading.Thread(target=send_request, args=("a",))
            t2 = threading.Thread(target=send_request, args=("b",))
            t1.start()
            t2.start()
            t1.join(timeout=15)
            t2.join(timeout=15)

        for key, outcome in outcomes.items():
            self.assertNotIsInstance(
                outcome, Exception,
                f"request {key} raised instead of handling the race cleanly: {outcome!r}",
            )
        self.assertEqual(
            outcomes, {"a": 200, "b": 200},
            "both concurrent deliveries of the same event must be acknowledged with 200",
        )

        self.assertEqual(
            ProcessedWebhookEvent.objects.filter(event_id=event_id).count(), 1,
            "unique constraint should have let only one delivery record the event",
        )
        self.subscription.refresh_from_db()
        self.assertEqual(self.subscription.status, "active")
