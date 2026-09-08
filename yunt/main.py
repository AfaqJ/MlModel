"""The Yunt service.

Deployed separately from the classifier (`mlmodel`). This one is public because
Resend's webhook arrives from the internet with no Google identity — its gate is
the Svix signature plus the sender allowlist, not IAM. The classifier is the
opposite: private, called by this service with an OIDC token.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, Response

from yunt import config, inbound, mail

logging.basicConfig(level=config.LOG_LEVEL)
log = logging.getLogger("yunt")

app = FastAPI(title="Yunt", version=config.SERVICE_VERSION)


@app.get("/health")
def health() -> dict:
    """Liveness, plus enough configuration state to diagnose a silent service.

    It reports whether each secret is *present*, never its value.
    """
    return {
        "status": "ok",
        "version": config.SERVICE_VERSION,
        "allowlist_size": len(config.ALLOWED_ADDRESSES),
        "mail_configured": bool(config.RESEND_API_KEY and config.MAIL_FROM),
        "webhook_configured": bool(config.RESEND_WEBHOOK_SECRET),
    }


@app.post("/inbound/resend")
async def inbound_resend(request: Request) -> Response:
    raw = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    try:
        event = inbound.verify(raw, headers)
    except inbound.SignatureError as exc:
        log.warning("rejected an unsigned or badly signed webhook: %s", exc)
        return Response(status_code=400, content="invalid signature")

    email = inbound.parse_event(event)
    if email is None:
        # Another event type we do not handle. 200 so Resend stops retrying.
        return Response(status_code=200, content="ignored")

    if not config.is_allowed(email.sender):
        # Recorded, and answered with silence. A bounce would confirm to a
        # stranger that the address is live.
        log.warning("inbound from an address that is not on the allowlist; ignoring")
        return Response(status_code=200, content="ignored")

    log.info(
        "inbound accepted: %s attachment(s), %s zip(s)",
        len(email.attachments), len(email.zip_attachments),
    )

    # ponytail: acknowledgement is sent inline. Fine while nothing here is slow;
    # ingestion moves to a background task (and Cloud Run CPU-always-on) in the
    # phase that unzips and classifies, because Resend retries a slow webhook.
    zips = len(email.zip_attachments)
    body = (
        f"Recibido: {email.subject or '(sin asunto)'}\n\n"
        f"Adjuntos: {len(email.attachments)}"
        + (f", de los cuales {zips} ZIP.\n" if zips else ".\n")
        + "\nEste es el acuse de recibo. El informe de lectura llega a continuacion."
    )
    result = mail.send(
        email.sender,
        subject=f"Re: {email.subject}" if email.subject else "Recibido",
        text=body,
        reply_to_message_id=email.message_id,
    )
    if not result.sent:
        log.error("acknowledgement not sent: %s", result.refused_reason)

    return Response(status_code=200, content="ok")
