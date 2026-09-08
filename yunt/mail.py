"""The only place in this service that can send mail.

Two things are deliberate:

  * Every send goes through `send()`, and `send()` refuses any recipient that is
    not on YUNT_ALLOWED_ADDRESSES. There is no second path and no override
    argument, which is what makes "the Yunt cannot contact a supplier" a
    property of the code rather than a promise.

  * It fails closed. No API key, no allowlist, or a recipient off the list all
    return a Refused result instead of raising, because the callers are report
    paths that must still record what happened.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

from yunt import config

log = logging.getLogger(__name__)

RESEND_SEND_URL = "https://api.resend.com/emails"


@dataclass(frozen=True)
class SendResult:
    sent: bool
    message_id: str | None = None
    refused_reason: str | None = None


def send(
    to: str,
    subject: str,
    text: str,
    *,
    reply_to_message_id: str | None = None,
    attachments: list[dict] | None = None,
) -> SendResult:
    """Send one message. The recipient must be on the allowlist."""
    if not config.is_allowed(to):
        # Not an error: an inbound message from a stranger reaches here, and the
        # correct behaviour is to record it and stay silent.
        log.warning("refusing to send to an address that is not on the allowlist")
        return SendResult(False, refused_reason="recipient_not_allowed")

    if not config.RESEND_API_KEY or not config.MAIL_FROM:
        log.error("mail is not configured (RESEND_API_KEY / YUNT_MAIL_FROM)")
        return SendResult(False, refused_reason="mail_not_configured")

    payload: dict = {
        "from": config.MAIL_FROM,
        "to": [config._mailbox(to)],
        "subject": subject,
        "text": text,
    }
    if attachments:
        payload["attachments"] = attachments
    if reply_to_message_id:
        # Keeps the exchange as one thread in Cristian's mail client rather than
        # a pile of unrelated messages.
        payload["headers"] = {
            "In-Reply-To": reply_to_message_id,
            "References": reply_to_message_id,
        }

    request = urllib.request.Request(
        RESEND_SEND_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return SendResult(True, message_id=body.get("id"))
    except urllib.error.HTTPError as exc:
        # Never log the body of a failed send at error level with the key in it;
        # the key is a header, but the body can carry recipient data.
        log.error("resend rejected the send: HTTP %s", exc.code)
        return SendResult(False, refused_reason=f"resend_http_{exc.code}")
    except Exception as exc:  # noqa: BLE001 - a send failure must never crash a report path
        log.error("send failed: %s", type(exc).__name__)
        return SendResult(False, refused_reason="send_failed")
