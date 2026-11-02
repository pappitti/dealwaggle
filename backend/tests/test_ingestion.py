import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from unittest.mock import Mock

from dealwaggle.config import get_settings
from dealwaggle.worker import run_once
from dealwaggle_db.models import ChannelIdentity, Job, Source, WebhookEvent, now
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from svix.webhooks import Webhook


def configure(monkeypatch, **values):
    for key, value in values.items():
        monkeypatch.setenv("DEALWAGGLE_" + key.upper(), value)
    get_settings.cache_clear()


def whatsapp_body(messages=None, phone="business-phone"):
    return json.dumps(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": phone},
                                "messages": messages
                                or [
                                    {
                                        "id": "wamid.one",
                                        "from": "44123456789",
                                        "type": "text",
                                        "text": {"body": "Company is raising"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ],
        }
    ).encode()


def signed_whatsapp(client, body):
    signature = "sha256=" + hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    return client.post(
        "/webhooks/whatsapp", content=body, headers={"x-hub-signature-256": signature}
    )


def test_whatsapp_signature_challenge_and_replay(context, monkeypatch):
    client, engine, _, _ = context
    configure(
        monkeypatch,
        whatsapp_app_secret="app-secret",
        whatsapp_phone_number_id="business-phone",
        whatsapp_verify_token="verify-me",
    )
    assert (
        client.get(
            "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=123"
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=verify-me&hub.challenge=123"
        ).text
        == "123"
    )
    body = whatsapp_body()
    assert client.post("/webhooks/whatsapp", content=body).status_code == 401
    assert signed_whatsapp(client, body).status_code == 200
    assert signed_whatsapp(client, body).status_code == 200
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(WebhookEvent)) == 1
        assert session.scalar(select(func.count()).select_from(Job)) == 1


def test_worker_routes_verified_sender_defaults_team_and_blocks_missing_llm(context, monkeypatch):
    client, engine, users, org = context
    configure(
        monkeypatch, whatsapp_app_secret="app-secret", whatsapp_phone_number_id="business-phone"
    )
    with Session(engine) as session:
        session.add(
            ChannelIdentity(
                owner_id=users["alice"],
                organisation_id=org,
                channel="whatsapp",
                address="44123456789",
                verified_at=now(),
            )
        )
        session.commit()
    signed_whatsapp(client, whatsapp_body())
    assert run_once(engine)  # fan out individual messages
    assert run_once(engine)  # route sender
    assert run_once(engine)  # missing extraction provider
    assert not run_once(engine)
    with Session(engine) as session:
        source = session.scalar(select(Source).where(Source.provider_key == "whatsapp:wamid.one"))
        assert source.organisation_id == org
        assert source.status == "needs_review"
        job = session.scalar(select(Job).where(Job.kind == "extract"))
        assert job.status == "blocked" and job.last_error == "extraction"
    assert client.get("/api/inbox", headers={"x-demo-user": "ben"}).json() == []


def test_unknown_sender_does_not_block_known_sender_in_same_batch(context, monkeypatch):
    client, engine, users, org = context
    configure(
        monkeypatch, whatsapp_app_secret="app-secret", whatsapp_phone_number_id="business-phone"
    )
    with Session(engine) as session:
        session.add(
            ChannelIdentity(
                owner_id=users["alice"],
                organisation_id=org,
                channel="whatsapp",
                address="known",
                verified_at=now(),
            )
        )
        session.commit()
    signed_whatsapp(
        client,
        whatsapp_body(
            [
                {"id": "one", "from": "unknown", "type": "text", "text": {"body": "private"}},
                {"id": "two", "from": "known", "type": "text", "text": {"body": "valid"}},
            ]
        ),
    )
    for _ in range(4):
        run_once(engine)
    with Session(engine) as session:
        assert session.scalar(select(Source).where(Source.provider_key == "whatsapp:two"))
        assert not session.scalar(select(Source).where(Source.provider_key == "whatsapp:one"))
        assert (
            session.scalar(select(Job).where(Job.dedupe_key == "whatsapp_message:one")).status
            == "blocked"
        )


def test_resend_requires_signature_and_rejects_stale_signature(context, monkeypatch):
    client, engine, _, _ = context
    secret = "whsec_" + base64.b64encode(b"test-signing-secret").decode()
    configure(monkeypatch, resend_webhook_secret=secret)
    payload = json.dumps(
        {"type": "email.received", "data": {"email_id": "email-1", "to": ["alias@example.test"]}}
    )
    timestamp = datetime.now(UTC)
    signature = Webhook(secret).sign("event-1", timestamp, payload)
    headers = {
        "svix-id": "event-1",
        "svix-timestamp": str(int(timestamp.timestamp())),
        "svix-signature": signature,
    }
    assert client.post("/webhooks/resend", content=payload).status_code == 401
    assert client.post("/webhooks/resend", content=payload, headers=headers).status_code == 200
    assert client.post("/webhooks/resend", content=payload, headers=headers).status_code == 200
    old = datetime.fromtimestamp(time.time() - 600, UTC)
    headers.update(
        {
            "svix-timestamp": str(int(old.timestamp())),
            "svix-signature": Webhook(secret).sign("event-1", old, payload),
        }
    )
    assert client.post("/webhooks/resend", content=payload, headers=headers).status_code == 401
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(WebhookEvent)) == 1


def test_resend_fetches_body_from_fixed_provider_endpoint(context, monkeypatch):
    _, engine, users, org = context
    from dealwaggle.worker import ingest_resend

    configure(monkeypatch, resend_api_key="test-key")
    with Session(engine) as session:
        identity = ChannelIdentity(
            owner_id=users["alice"],
            organisation_id=org,
            channel="email",
            address="unguessable@example.test",
            verified_at=now(),
        )
        session.add(identity)
        session.commit()
    response = Mock()
    response.json.return_value = {"text": "Fetched email body"}
    http = Mock()
    http.__enter__ = Mock(return_value=http)
    http.__exit__ = Mock(return_value=False)
    http.get.return_value = response
    monkeypatch.setattr("dealwaggle.worker.httpx.Client", Mock(return_value=http))
    with Session(engine) as session:
        ingest_resend(
            session, {"data": {"email_id": "email-id", "to": ["unguessable@example.test"]}}
        )
        session.commit()
        assert session.scalar(select(Source).where(Source.body == "Fetched email body"))
    assert http.get.call_args.args[0] == "https://api.resend.com/emails/receiving/email-id"


def test_worker_failure_rolls_back_partial_writes_and_bounds_retries(context, monkeypatch):
    _, engine, users, org = context
    with Session(engine) as session:
        job = Job(kind="test", dedupe_key="test-job", payload={})
        session.add(job)
        session.commit()
        job_id = job.id

    def fail(session, job):
        session.add(
            Source(
                owner_id=users["alice"],
                organisation_id=org,
                channel="manual",
                attribution="test",
                body="must roll back",
            )
        )
        session.flush()
        raise RuntimeError("secret should never be stored in errors")

    monkeypatch.setattr("dealwaggle.worker.dispatch", fail)
    for attempt in range(5):
        assert run_once(engine)
        with Session(engine) as session:
            job = session.get(Job, job_id)
            assert job.attempts == attempt + 1
            assert job.last_error == "RuntimeError"
            assert not session.scalar(select(Source).where(Source.body == "must roll back"))
            job.available_at = now()
            session.commit()
    with Session(engine) as session:
        assert session.get(Job, job_id).status == "failed"
    assert not run_once(engine)


def test_webhook_body_limit(context, monkeypatch):
    client, _, _, _ = context
    configure(
        monkeypatch,
        whatsapp_app_secret="app-secret",
        whatsapp_phone_number_id="business-phone",
        max_webhook_bytes="20",
    )
    assert signed_whatsapp(client, whatsapp_body()).status_code == 413


def test_postgres_skips_locked_job(context, monkeypatch):
    import pytest

    _, engine, _, _ = context
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires PostgreSQL row locks; runs in CI")
    with Session(engine) as session:
        first = Job(kind="test", dedupe_key="first", payload={})
        second = Job(kind="test", dedupe_key="second", payload={})
        session.add_all([first, second])
        session.commit()
        first_id, second_id = first.id, second.id
    monkeypatch.setattr("dealwaggle.worker.dispatch", lambda session, job: None)
    with Session(engine) as holder, holder.begin():
        holder.scalar(select(Job).where(Job.id == first_id).with_for_update())
        assert run_once(engine)
        with Session(engine) as check:
            assert check.get(Job, second_id).status == "completed"
            assert check.get(Job, first_id).status == "queued"
    assert run_once(engine)


def test_oversized_source_is_not_silently_truncated(context):
    import pytest
    from dealwaggle.providers import NeedsReview
    from dealwaggle.worker import accept_source

    _, engine, users, org = context
    identity = ChannelIdentity(owner_id=users["alice"], organisation_id=org)
    with Session(engine) as session:
        with pytest.raises(NeedsReview, match="message_exceeds_review_limit"):
            accept_source(session, identity, "email", "long-email", "x" * 50001)
        assert not session.scalar(select(Source).where(Source.provider_key == "long-email"))
