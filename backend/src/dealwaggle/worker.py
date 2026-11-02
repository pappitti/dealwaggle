"""PostgreSQL queue; hold a row lock through one bounded job transaction.

No separate queue publish can be lost after the webhook is acknowledged. A worker
crash rolls back its transaction and releases the lock for the next worker.
"""

import argparse
import logging
import time
from datetime import timedelta
from email.utils import parseaddr
from urllib.parse import quote

import httpx
from dealwaggle_db.models import ChannelIdentity, Job, Membership, Source, User, WebhookEvent, now
from sqlalchemy import select
from sqlalchemy.orm import Session

from dealwaggle.config import get_settings
from dealwaggle.db import get_engine
from dealwaggle.providers import NeedsReview, ProviderNotConfigured, UnconfiguredProvider

logger = logging.getLogger(__name__)


def identity_for(session, channel, address):
    identity = session.scalar(
        select(ChannelIdentity).where(
            ChannelIdentity.channel == channel, ChannelIdentity.address == address
        )
    )
    if (
        not identity
        or not identity.verified_at
        or not session.get(Membership, (identity.owner_id, identity.organisation_id))
    ):
        raise NeedsReview("unlinked_sender")
    return identity


def accept_source(session, identity, channel, key, body):
    if session.scalar(select(Source.id).where(Source.provider_key == key)):
        return
    if not isinstance(body, str) or not body.strip():
        raise NeedsReview("empty_message")
    if len(body) > 50000:
        raise NeedsReview("message_exceeds_review_limit")
    user = session.get(User, identity.owner_id)
    source = Source(
        owner_id=identity.owner_id,
        organisation_id=identity.organisation_id,
        channel=channel,
        attribution=user.name,
        body=body,
        provider_key=key,
    )
    session.add(source)
    session.flush()
    session.add(
        Job(kind="extract", dedupe_key=f"extract:{source.id}", payload={"source_id": source.id})
    )


def ingest_whatsapp(session, payload):
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if (
                value.get("metadata", {}).get("phone_number_id")
                != get_settings().whatsapp_phone_number_id
            ):
                continue
            for message in value.get("messages", []):
                message_id = message.get("id")
                if not message_id:
                    raise NeedsReview("missing_message_id")
                dedupe_key = "whatsapp_message:" + message_id
                if not session.scalar(select(Job.id).where(Job.dedupe_key == dedupe_key)):
                    session.add(
                        Job(kind="whatsapp_message", dedupe_key=dedupe_key, payload=message)
                    )


def ingest_resend(session, payload):
    data = payload.get("data", {})
    # Unique forwarding addresses are provisioned after account verification.
    recipients = {parseaddr(address)[1].lower() for address in data.get("to", [])}
    identities = session.scalars(
        select(ChannelIdentity).where(
            ChannelIdentity.channel == "email", ChannelIdentity.address.in_(recipients)
        )
    ).all()
    if not identities:
        raise NeedsReview("unlinked_recipient")
    key = get_settings().resend_api_key
    if not key:
        raise ProviderNotConfigured("resend")
    email_id = data.get("email_id")
    if not email_id or not isinstance(email_id, str):
        raise NeedsReview("missing_email_id")
    with httpx.Client(timeout=20) as api:
        response = api.get(
            "https://api.resend.com/emails/receiving/" + quote(email_id, safe=""),
            headers={"Authorization": f"Bearer {key}"},
        )
        response.raise_for_status()
        content = response.json()
    if not content.get("text"):
        raise NeedsReview("email_needs_text_or_attachment_processing")
    for identity in identities:
        identity_for(session, "email", identity.address)
        accept_source(
            session, identity, "email", f"resend:{email_id}:{identity.id}", content["text"]
        )


def dispatch(session, job):
    if job.kind.startswith("webhook:"):
        event = session.get(WebhookEvent, job.payload["event_id"])
        if job.kind == "webhook:whatsapp":
            ingest_whatsapp(session, event.payload)
        elif job.kind == "webhook:resend":
            ingest_resend(session, event.payload)
        elif job.kind == "webhook:stripe":
            from dealwaggle.billing import sync_subscription

            sync_subscription(session, event.payload)
    elif job.kind == "whatsapp_message":
        message = job.payload
        identity = identity_for(session, "whatsapp", message.get("from", ""))
        if message.get("type") != "text":
            raise NeedsReview("unsupported_whatsapp_media")
        accept_source(
            session,
            identity,
            "whatsapp",
            "whatsapp:" + message["id"],
            message.get("text", {}).get("body", ""),
        )
    elif job.kind == "extract":
        source = session.get(Source, job.payload["source_id"])
        if source.status == "reviewed":
            return
        UnconfiguredProvider().extract(source.body)
    elif job.kind == "enrich_person":
        UnconfiguredProvider().enrich_person(job.payload["url"])
    else:
        raise NeedsReview("unknown_job_kind")


def run_once(engine=None):
    with Session(engine or get_engine()) as session, session.begin():
        job = session.scalar(
            select(Job)
            .where(Job.status == "queued", Job.available_at <= now())
            .order_by(Job.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return False
        job.attempts += 1
        try:
            with session.begin_nested():
                dispatch(session, job)
            job.status = "completed"
            job.last_error = None
        except (ProviderNotConfigured, NeedsReview) as error:
            job.status = "blocked"
            job.last_error = str(error)[:200]
            if job.kind == "extract":
                source = session.get(Source, job.payload["source_id"])
                if source.status != "reviewed":
                    source.status = "needs_review"
        except Exception as error:
            job.status = "failed" if job.attempts >= 5 else "queued"
            job.available_at = now() + timedelta(seconds=min(300, 2**job.attempts))
            # Exception messages can contain credentials, message bodies or URLs.
            job.last_error = type(error).__name__
            logger.warning("Job %s attempt %s: %s", job.id, job.attempts, job.last_error)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--retry", help="Explicitly requeue a blocked/failed job after resolving its cause"
    )
    args = parser.parse_args()
    if args.retry:
        with Session(get_engine()) as session:
            job = session.get(Job, args.retry)
            if not job or job.status not in ("blocked", "failed"):
                parser.error("Job must exist and be blocked or failed")
            job.status, job.attempts, job.available_at = "queued", 0, now()
            session.commit()
        return
    logging.basicConfig(level=logging.INFO)
    while True:
        worked = run_once()
        if args.once:
            return
        if not worked:
            time.sleep(2)


if __name__ == "__main__":
    main()
