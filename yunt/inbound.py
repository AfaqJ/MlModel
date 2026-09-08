"""Receiving mail from Resend.

Resend does not hold a mailbox for us. When a message arrives at our receiving
domain it POSTs an `email.received` event to this service. That event carries
the sender, subject and attachment *metadata* — not the body and not the file
bytes — so acting on a message takes a second call back to Resend.

Two gates, in this order, before anything else happens:

  1. the Svix signature over the RAW request body, which proves the request
     really came from Resend and not from anyone who found the URL;
  2. the sender allowlist.

A request failing (1) is rejected with 400. A message failing (2) is recorded
and answered with silence — never a bounce, which would tell a stranger the
address is live.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from yunt import config

log = logging.getLogger(__name__)

RESEND_API = "https://api.resend.com"


class SignatureError(Exception):
    """The request did not carry a valid Resend signature."""


@dataclass(frozen=True)
class InboundEmail:
    email_id: str
    sender: str
    recipients: tuple[str, ...]
    subject: str
    message_id: str | None
    attachments: tuple[dict, ...] = field(default_factory=tuple)

    @property
    def zip_attachments(self) -> tuple[dict, ...]:
        return tuple(
            a for a in self.attachments
            if (a.get("filename") or "").lower().endswith(".zip")
            or (a.get("content_type") or "") in {"application/zip", "application/x-zip-compressed"}
        )


def verify(raw_body: bytes, headers: dict) -> dict:
    """Verify the Svix signature and return the decoded event.

    The signature covers the raw bytes. Parsing to JSON and re-serialising
    changes them (key order, whitespace) and the check then fails for a
    perfectly genuine request, which is the classic way to lose an afternoon.
    """
    if not config.RESEND_WEBHOOK_SECRET:
        raise SignatureError("RESEND_WEBHOOK_SECRET is not set")

    from svix.webhooks import Webhook, WebhookVerificationError

    try:
        payload = Webhook(config.RESEND_WEBHOOK_SECRET).verify(raw_body, headers)
    except WebhookVerificationError as exc:
        raise SignatureError(str(exc)) from exc
    return payload


def parse_event(event: dict) -> InboundEmail | None:
    """Pull the fields we care about out of an `email.received` event."""
    if event.get("type") != "email.received":
        return None
    data = event.get("data") or {}
    to = data.get("to") or []
    if isinstance(to, str):
        to = [to]
    return InboundEmail(
        email_id=str(data.get("email_id") or data.get("id") or ""),
        sender=str(data.get("from") or ""),
        recipients=tuple(str(x) for x in to),
        subject=str(data.get("subject") or ""),
        message_id=data.get("message_id"),
        attachments=tuple(data.get("attachments") or ()),
    )


def _get(path: str) -> dict:
    request = urllib.request.Request(
        f"{RESEND_API}{path}",
        headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_attachments(email_id: str) -> list[dict]:
    """List the attachments Resend holds for a received message.

    The webhook may already carry this; this call is the fallback, and the
    authority when it does not.
    """
    body = _get(f"/emails/{email_id}/attachments")
    return list(body.get("data") or body.get("attachments") or [])


def download_attachment(attachment: dict, email_id: str, *, max_bytes: int) -> bytes:
    """Fetch one attachment's bytes, refusing anything over max_bytes.

    The size is checked twice: against the metadata before the request, and
    against what actually arrives. A declared size is a claim, not a fact.
    """
    declared = int(attachment.get("size") or 0)
    if declared and declared > max_bytes:
        raise ValueError(f"attachment is {declared} bytes, limit is {max_bytes}")

    url = attachment.get("download_url")
    if not url:
        attachment_id = attachment.get("id")
        if not attachment_id:
            raise ValueError("attachment has neither a download_url nor an id")
        url = _get(f"/emails/{email_id}/attachments/{attachment_id}").get("download_url")
    if not url:
        raise ValueError("no download_url for attachment")

    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError(f"attachment exceeds the {max_bytes} byte limit")
    return data
