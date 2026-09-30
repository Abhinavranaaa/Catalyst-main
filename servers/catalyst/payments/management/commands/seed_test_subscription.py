from django.core.management.base import BaseCommand, CommandError

from payments.models import Plan, Subscription


class Command(BaseCommand):
    help = (
        "Seed a placeholder Plan (razorpay_plan_id=test_plan_placeholder) and an "
        "active test Subscription for the given user_id, for exercising "
        "has_entitlement() before Razorpay integration exists."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "user_id",
            type=str,
            help="user_id to attach the test Subscription to",
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        if not user_id:
            raise CommandError("user_id is required")

        plan, plan_created = Plan.objects.get_or_create(
            razorpay_plan_id="test_plan_placeholder",
            defaults={"name": "Test Plan", "price": 0},
        )

        subscription, sub_created = Subscription.objects.get_or_create(
            user_id=str(user_id),
            plan=plan,
            defaults={"status": "active"},
        )
        if not sub_created and subscription.status != "active":
            subscription.status = "active"
            subscription.save(update_fields=["status"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Plan {'created' if plan_created else 'reused'}: {plan.id} "
                f"({plan.razorpay_plan_id})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Subscription {'created' if sub_created else 'reused'}: "
                f"{subscription.id} (user_id={subscription.user_id}, status={subscription.status})"
            )
        )
