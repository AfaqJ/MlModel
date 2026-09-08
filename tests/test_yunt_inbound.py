"""Checks for the two gates on the inbound path, and for the send allowlist.

These are the security boundary of the service, so they get a real signature
produced by the same library Resend signs with, not a stubbed verifier.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

SECRET = "whsec_" + base64.b64encode(b"a-test-signing-secret-32-bytes!!").decode()
ALLOWED = "cristian@antillanca.cl"
STRANGER = "someone@example.com"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("YUNT_ALLOWED_ADDRESSES", f" {ALLOWED.upper()} , afaq@mctechstudio.com ")
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", SECRET)
    monkeypatch.setenv("RESEND_API_KEY", "")          # deliberately unconfigured
    from yunt import config, inbound, mail, main
    for module in (config, inbound, mail, main):
        importlib.reload(module)
    return TestClient(main.app), config, mail


def signed(body: dict) -> tuple[bytes, dict]:
    """Sign a payload the way Svix does: HMAC-SHA256 over `id.timestamp.body`."""
    raw = json.dumps(body).encode("utf-8")
    msg_id, ts = "msg_test", str(int(time.time()))
    key = base64.b64decode(SECRET.removeprefix("whsec_"))
    sig = base64.b64encode(
        hmac.new(key, f"{msg_id}.{ts}.".encode() + raw, hashlib.sha256).digest()
    ).decode()
    return raw, {"svix-id": msg_id, "svix-timestamp": ts, "svix-signature": f"v1,{sig}"}


def event(sender: str) -> dict:
    return {
        "type": "email.received",
        "data": {
            "email_id": "e_1", "from": sender, "to": ["facturas@yunt.example"],
            "subject": "Facturas agosto", "message_id": "<abc@mail>",
            "attachments": [{"filename": "agosto.zip", "content_type": "application/zip", "size": 900}],
        },
    }


def post(client, raw, headers):
    return client.post("/inbound/resend", content=raw, headers=headers)


def test_allowlist_is_case_and_whitespace_insensitive(client):
    _, config, _ = client
    assert config.is_allowed(ALLOWED)
    assert config.is_allowed(f"Cristian <{ALLOWED.upper()}>")
    assert not config.is_allowed(STRANGER)


def test_allowlist_fails_closed_when_unset(monkeypatch):
    monkeypatch.delenv("YUNT_ALLOWED_ADDRESSES", raising=False)
    from yunt import config
    importlib.reload(config)
    assert config.ALLOWED_ADDRESSES == ()
    assert not config.is_allowed(ALLOWED)          # nobody, not everybody


def test_send_refuses_a_recipient_off_the_list(client):
    _, _, mail = client
    result = mail.send(STRANGER, subject="x", text="y")
    assert not result.sent and result.refused_reason == "recipient_not_allowed"


def test_an_unsigned_request_is_rejected(client):
    api, _, _ = client
    raw = json.dumps(event(ALLOWED)).encode()
    assert post(api, raw, {}).status_code == 400


def test_a_tampered_body_is_rejected(client):
    api, _, _ = client
    raw, headers = signed(event(ALLOWED))
    assert post(api, raw + b" ", headers).status_code == 400


def test_a_signed_request_from_a_stranger_is_accepted_and_ignored(client):
    api, _, _ = client
    raw, headers = signed(event(STRANGER))
    response = post(api, raw, headers)
    # 200 so Resend stops retrying, but nothing is acted on and no bounce is sent.
    assert response.status_code == 200 and response.text == "ignored"


def test_a_signed_request_from_an_allowed_sender_is_accepted(client):
    api, _, _ = client
    raw, headers = signed(event(ALLOWED))
    response = post(api, raw, headers)
    assert response.status_code == 200 and response.text == "ok"


def test_zip_attachments_are_recognised_by_name_or_type():
    from yunt.inbound import parse_event
    email = parse_event(event(ALLOWED))
    assert len(email.zip_attachments) == 1
    assert email.sender == ALLOWED
