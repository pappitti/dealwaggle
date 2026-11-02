import stripe
from dealwaggle_db.models import Organisation, Subscription, now
from fastapi import HTTPException
from sqlalchemy import select

from dealwaggle.config import get_settings
from dealwaggle.providers import ProviderNotConfigured


def client():
    settings = get_settings()
    if not settings.stripe_secret_key:
        raise ProviderNotConfigured("stripe")
    return stripe.StripeClient(
        settings.stripe_secret_key,
        max_network_retries=1,
        http_client=stripe.RequestsClient(timeout=20),
    )


def checkout_url(session, organisation_id):
    settings = get_settings()
    if (
        not settings.stripe_secret_key
        or not settings.stripe_price_id
        or not settings.stripe_webhook_secret
    ):
        raise HTTPException(503, "Billing is not configured")
    org = session.scalar(
        select(Organisation).where(Organisation.id == organisation_id).with_for_update()
    )
    api = client()
    if not org.stripe_customer_id:
        customer = api.v1.customers.create(
            {"name": org.name, "metadata": {"organisation_id": org.id}},
            options={"idempotency_key": f"organisation:{org.id}"},
        )
        org.stripe_customer_id = customer.id
        session.commit()
    # Reacquire after customer persistence. Serialize checkout creation per org.
    org = session.scalar(
        select(Organisation).where(Organisation.id == organisation_id).with_for_update()
    )
    subscriptions = api.v1.subscriptions.list(
        {"customer": org.stripe_customer_id, "status": "all", "limit": 100}
    )
    if any(
        sub.status not in ("canceled", "incomplete_expired")
        for sub in subscriptions.auto_paging_iter()
    ):
        raise HTTPException(409, "Manage your existing subscription in the billing portal")
    # A retry after an ambiguous provider response reuses the open checkout.
    existing = api.v1.checkout.sessions.list(
        {"customer": org.stripe_customer_id, "status": "open", "limit": 1}
    )
    if existing.data:
        url = existing.data[0].url
        session.commit()
        return url
    checkout = api.v1.checkout.sessions.create(
        {
            "mode": "subscription",
            "customer": org.stripe_customer_id,
            "line_items": [{"price": settings.stripe_price_id, "quantity": 1}],
            "success_url": settings.app_url + "/?billing=success",
            "cancel_url": settings.app_url + "/?billing=cancelled",
            "client_reference_id": org.id,
        }
    )
    session.commit()
    return checkout.url


def portal_url(session, organisation_id):
    org = session.get(Organisation, organisation_id)
    if not org.stripe_customer_id or not get_settings().stripe_secret_key:
        raise HTTPException(503, "Billing is not configured")
    return (
        client()
        .v1.billing_portal.sessions.create(
            {"customer": org.stripe_customer_id, "return_url": get_settings().app_url}
        )
        .url
    )


def sync_subscription(session, payload):
    """Fetch current Stripe state, so delayed webhook events cannot regress access."""
    customer_id = payload.get("data", {}).get("object", {}).get("customer")
    org = (
        session.scalar(
            select(Organisation)
            .where(Organisation.stripe_customer_id == customer_id)
            .with_for_update()
        )
        if customer_id
        else None
    )
    if not org:
        return
    subscriptions = client().v1.subscriptions.list(
        {"customer": customer_id, "status": "all", "limit": 100}
    )
    price_id = get_settings().stripe_price_id
    matches = [
        sub
        for sub in subscriptions.auto_paging_iter()
        if any(item.price.id == price_id for item in sub["items"].data)
    ]
    matches.sort(key=lambda sub: (sub.status in ("active", "trialing"), sub.created), reverse=True)
    current = matches[0] if matches else None
    record = session.scalar(select(Subscription).where(Subscription.organisation_id == org.id))
    if not record:
        record = Subscription(organisation_id=org.id)
        session.add(record)
    record.stripe_subscription_id = current.id if current else None
    record.status = current.status if current else "inactive"
    record.price_id = price_id if current else None
    record.updated_at = now()
