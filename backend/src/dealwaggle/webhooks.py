"""Authenticate the original bytes and atomically persist event + work before ACK."""

import hashlib
import hmac
import json

import stripe
from dealwaggle_db.models import Job, WebhookEvent
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from svix.webhooks import Webhook, WebhookVerificationError

from dealwaggle.config import get_settings
from dealwaggle.db import get_session

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


async def body_bytes(request):
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > get_settings().max_webhook_bytes:
            raise HTTPException(413, "Webhook payload too large")
    return bytes(content)


def persist(session: Session, provider: str, external_id: str, payload: dict):
    if not external_id or len(external_id) > 255:
        raise HTTPException(400, "Missing or invalid event identifier")
    try:
        event = WebhookEvent(provider=provider, external_id=external_id, payload=payload)
        session.add(event)
        session.flush()
        session.add(
            Job(
                kind=f"webhook:{provider}",
                dedupe_key=f"{provider}:{external_id}",
                payload={"event_id": event.id},
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        if not session.scalar(
            select(WebhookEvent.id).where(
                WebhookEvent.provider == provider, WebhookEvent.external_id == external_id
            )
        ):
            raise
    return {"received": True}


@router.get("/whatsapp", response_class=PlainTextResponse)
def whatsapp_challenge(request: Request):
    settings = get_settings()
    if not settings.whatsapp_verify_token:
        raise HTTPException(503, "WhatsApp is not configured")
    query = request.query_params
    if query.get("hub.mode") != "subscribe" or not hmac.compare_digest(
        query.get("hub.verify_token", ""), settings.whatsapp_verify_token
    ):
        raise HTTPException(403, "Verification failed")
    return query.get("hub.challenge", "")


@router.post("/whatsapp")
async def whatsapp(request: Request, session: Session = Depends(get_session)):
    settings = get_settings()
    if not settings.whatsapp_app_secret or not settings.whatsapp_phone_number_id:
        raise HTTPException(503, "WhatsApp is not configured")
    body = await body_bytes(request)
    expected = (
        "sha256="
        + hmac.new(settings.whatsapp_app_secret.encode(), body, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), expected):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise HTTPException(400, "Invalid JSON") from None
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        raise HTTPException(400, "Invalid WhatsApp event")
    return persist(session, "whatsapp", hashlib.sha256(body).hexdigest(), payload)


@router.post("/resend")
async def resend(request: Request, session: Session = Depends(get_session)):
    secret = get_settings().resend_webhook_secret
    if not secret:
        raise HTTPException(503, "Resend is not configured")
    body = await body_bytes(request)
    try:
        payload = Webhook(secret).verify(body, dict(request.headers))
    except (WebhookVerificationError, ValueError):
        raise HTTPException(401, "Invalid webhook signature") from None
    if not isinstance(payload, dict):
        raise HTTPException(400, "Invalid event")
    if payload.get("type") != "email.received":
        return {"received": True}
    return persist(session, "resend", request.headers.get("svix-id", ""), payload)


@router.post("/stripe")
async def stripe_webhook(request: Request, session: Session = Depends(get_session)):
    secret = get_settings().stripe_webhook_secret
    if not secret:
        raise HTTPException(503, "Stripe is not configured")
    body = await body_bytes(request)
    try:
        stripe.Webhook.construct_event(body, request.headers.get("stripe-signature", ""), secret)
    except (ValueError, stripe.SignatureVerificationError):
        raise HTTPException(401, "Invalid webhook signature") from None
    payload = json.loads(body)
    if not (
        payload.get("type", "").startswith("customer.subscription.")
        or payload.get("type") == "checkout.session.completed"
    ):
        return {"received": True}
    return persist(session, "stripe", payload["id"], payload)
