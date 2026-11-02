import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from conftest import capture, headers
from cryptography.hazmat.primitives.asymmetric import rsa
from dealwaggle.config import Settings, get_settings
from dealwaggle_db.models import Job, Organisation, Subscription
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_production_refuses_demo_and_missing_auth():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", demo_mode=True)
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            database_url="postgresql+psycopg://localhost/db",
        )


def test_demo_header_cannot_authenticate_when_demo_disabled(context, monkeypatch):
    client, _, _, _ = context
    monkeypatch.setenv("DEALWAGGLE_DEMO_MODE", "false")
    get_settings.cache_clear()
    assert client.get("/api/me", headers=headers("alice")).status_code == 401


def test_jwt_checks_expiry_issuer_audience_and_signature(context, monkeypatch):
    client, _, _, _ = context
    monkeypatch.setenv("DEALWAGGLE_DEMO_MODE", "false")
    monkeypatch.setenv("DEALWAGGLE_JWT_ISSUER", "https://identity.example.test")
    monkeypatch.setenv("DEALWAGGLE_JWT_JWKS_URL", "https://identity.example.test/jwks")
    get_settings.cache_clear()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    fake_jwks = Mock()
    fake_jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=private.public_key())
    monkeypatch.setattr("dealwaggle.auth.jwks_client", lambda _: fake_jwks)
    claims = {
        "sub": "demo:alice",
        "iss": "https://identity.example.test",
        "aud": "dealwaggle",
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(minutes=5),
    }

    def request(overrides):
        token = jwt.encode({**claims, **overrides}, private, algorithm="RS256")
        return client.get("/api/me", headers={"authorization": "Bearer " + token})

    assert request({}).status_code == 200
    assert request({"aud": "other"}).status_code == 401
    assert request({"iss": "https://attacker.example.test"}).status_code == 401
    assert request({"exp": datetime.now(UTC) - timedelta(minutes=5)}).status_code == 401
    assert request({"sub": "not-provisioned"}).status_code == 403


def test_billing_owner_only_and_fail_closed(context):
    client, _, _, org = context
    assert client.get(f"/api/billing/{org}", headers=headers("outsider")).status_code == 403
    assert (
        client.post(
            "/api/billing/checkout", json={"organisation_id": org}, headers=headers("ben")
        ).status_code
        == 403
    )
    assert client.post("/api/billing/checkout", json={"organisation_id": org}).status_code == 503
    person = capture(client, org, kind="person")
    assert (
        client.post(
            f"/api/entities/{person['entity_id']}/enrich",
            json={"organisation_id": org, "linkedin_url": "https://www.linkedin.com/in/person"},
        ).status_code
        == 402
    )


def test_stripe_signature_replay_and_no_entitlement_from_browser_redirect(context, monkeypatch):
    client, engine, _, org = context
    monkeypatch.setenv("DEALWAGGLE_STRIPE_WEBHOOK_SECRET", "stripe-test")
    get_settings.cache_clear()
    payload = json.dumps(
        {
            "id": "evt_test",
            "object": "event",
            "type": "customer.subscription.updated",
            "data": {"object": {"customer": "cus_test"}},
        }
    )
    timestamp = int(time.time())
    signature = hmac.new(
        b"stripe-test", f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    headers = {"stripe-signature": f"t={timestamp},v1={signature}"}
    assert client.post("/webhooks/stripe", content=payload).status_code == 401
    assert client.post("/webhooks/stripe", content=payload, headers=headers).status_code == 200
    assert client.post("/webhooks/stripe", content=payload, headers=headers).status_code == 200
    assert not client.get(f"/api/billing/{org}?billing=success").json()["premium"]
    with Session(engine) as session:
        assert len(session.scalars(select(Job).where(Job.kind == "webhook:stripe")).all()) == 1


def test_subscription_uses_current_provider_state_not_stale_event(context, monkeypatch):
    _, engine, _, org = context
    from dealwaggle.billing import sync_subscription

    monkeypatch.setenv("DEALWAGGLE_STRIPE_PRICE_ID", "price_team")
    get_settings.cache_clear()

    class StripeObject(dict):
        def __getattr__(self, key):
            return self[key]

    active = StripeObject(
        id="sub_current",
        status="active",
        created=5,
        items=SimpleNamespace(data=[SimpleNamespace(price=SimpleNamespace(id="price_team"))]),
    )
    fake = Mock()
    fake.v1.subscriptions.list.return_value.auto_paging_iter.return_value = iter([active])
    monkeypatch.setattr("dealwaggle.billing.client", lambda: fake)
    with Session(engine) as session:
        session.get(Organisation, org).stripe_customer_id = "cus_team"
        session.commit()
        sync_subscription(
            session, {"data": {"object": {"customer": "cus_team", "status": "canceled"}}}
        )
        session.commit()
        subscription = session.scalar(
            select(Subscription).where(Subscription.organisation_id == org)
        )
        assert subscription.status == "active"
        assert subscription.stripe_subscription_id == "sub_current"


def test_checkout_reuses_open_session_and_checks_subscription_before_webhook(context, monkeypatch):
    client, engine, _, org = context
    for name, value in {
        "STRIPE_SECRET_KEY": "test",
        "STRIPE_PRICE_ID": "price_team",
        "STRIPE_WEBHOOK_SECRET": "test",
    }.items():
        monkeypatch.setenv("DEALWAGGLE_" + name, value)
    get_settings.cache_clear()
    with Session(engine) as session:
        session.get(Organisation, org).stripe_customer_id = "cus_team"
        session.commit()
    fake = Mock()
    fake.v1.subscriptions.list.return_value.auto_paging_iter.return_value = iter([])
    fake.v1.checkout.sessions.list.return_value.data = [
        SimpleNamespace(url="https://checkout.stripe.com/example")
    ]
    monkeypatch.setattr("dealwaggle.billing.client", lambda: fake)
    response = client.post("/api/billing/checkout", json={"organisation_id": org})
    assert response.json()["url"] == "https://checkout.stripe.com/example"
    fake.v1.checkout.sessions.create.assert_not_called()
    fake.v1.subscriptions.list.return_value.auto_paging_iter.return_value = iter(
        [SimpleNamespace(status="active")]
    )
    assert client.post("/api/billing/checkout", json={"organisation_id": org}).status_code == 409
    fake.v1.checkout.sessions.create.assert_not_called()
