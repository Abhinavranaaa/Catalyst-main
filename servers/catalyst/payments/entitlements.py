from payments.models import Subscription


def has_entitlement(user_id: str, entitlement_key: str) -> bool:
    """The only function anything else in the codebase should call to check paid access."""
    return Subscription.objects.filter(
        user_id=str(user_id),
        status="active",
        plan__entitlements__entitlement_key=entitlement_key,
    ).exists()
