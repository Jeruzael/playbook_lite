import hmac
import hashlib
import json
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from core.models import WebhookEndpoint, OutboxEvent


DEFAULT_SIGNING_SECRET = getattr(settings, "WEBHOOK_SIGNING_SECRET", "")


def _sign(secret: str, body_bytes: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def enqueue_event(event_type: str, data: dict) -> int:
    """
    Create one OutboxEvent per matching active endpoint.
    Returns number of queued events.
    """
    endpoints = WebhookEndpoint.objects.filter(is_active=True)

    queued = 0
    for ep in endpoints:
        if ep.subscribed_events and event_type not in ep.subscribed_events:
            continue

        payload = {
            "id": None,  # filled by outbox event id if you want; leaving for simplicity
            "type": event_type,
            "created_at": timezone.now().isoformat(),
            "data": data,
        }

        OutboxEvent.objects.create(
            endpoint=ep,
            event_type=event_type,
            payload=payload,
            status=OutboxEvent.Status.PENDING,
            next_attempt_at=timezone.now(),
        )
        queued += 1

    return queued


def dispatch_one(event: OutboxEvent, timeout_seconds: int = 8) -> OutboxEvent:
    """
    Send one OutboxEvent to its endpoint with signature header.
    Handles retry scheduling.
    """
    ep = event.endpoint
    body = json.dumps(event.payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    secret = ep.signing_secret or DEFAULT_SIGNING_SECRET or ""
    headers = {
        "Content-Type": "application/json",
        "X-Event-Type": event.event_type,
        "X-Event-Id": str(event.id),
    }
    if secret:
        headers["X-Playbook-Signature"] = _sign(secret, body)

    try:
        resp = requests.post(ep.url, data=body, headers=headers, timeout=timeout_seconds)
        event.last_status_code = resp.status_code

        if 200 <= resp.status_code < 300:
            event.status = OutboxEvent.Status.DELIVERED
            event.delivered_at = timezone.now()
            event.last_error = ""
            event.save(update_fields=["status", "delivered_at", "last_error", "last_status_code", "updated_at"])
            return event

        # Non-2xx counts as failure -> retry
        raise RuntimeError(f"Non-2xx response: {resp.status_code} {resp.text[:300]}")

    except Exception as e:
        event.attempts += 1
        event.last_error = str(e)[:2000]

        # Exponential-ish backoff: 1m, 2m, 4m, 8m, 16m (cap at 60m)
        delay_minutes = min(2 ** max(event.attempts - 1, 0), 60)
        event.next_attempt_at = timezone.now() + timedelta(minutes=delay_minutes)

        if event.attempts >= 7:
            event.status = OutboxEvent.Status.FAILED
        else:
            event.status = OutboxEvent.Status.RETRY

        event.save(update_fields=[
            "status", "attempts", "next_attempt_at", "last_error", "last_status_code", "updated_at"
        ])
        return event
