"""Runtime configuration, read once from the environment.

Plain os.environ rather than pydantic-settings: this service has a handful of
settings and no need for a second dependency to read them.

The one rule that matters here is that ALLOWED_ADDRESSES fails closed. An unset
or empty list means the service will not send mail to anyone, which is the safe
state for a service that is deployed before its recipients are agreed.
"""

from __future__ import annotations

import os


def _csv(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name, "")
    return tuple(sorted({part.strip().lower() for part in raw.split(",") if part.strip()}))


# Who may send us mail, and who we may send mail to. One list, both directions.
ALLOWED_ADDRESSES: tuple[str, ...] = _csv("YUNT_ALLOWED_ADDRESSES")

# Resend
RESEND_API_KEY: str = os.environ.get("RESEND_API_KEY", "")
RESEND_WEBHOOK_SECRET: str = os.environ.get("RESEND_WEBHOOK_SECRET", "")
MAIL_FROM: str = os.environ.get("YUNT_MAIL_FROM", "")

# The classifier service. Private, called with an OIDC token for this audience.
CLASSIFIER_URL: str = os.environ.get("CLASSIFIER_URL", "").rstrip("/")

# Supabase, over PostgREST.
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY: str = os.environ.get("SUPABASE_SECRET_KEY", "")

SERVICE_VERSION: str = os.environ.get("YUNT_VERSION", "0.1.0")
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# A batch is refused rather than truncated above these. Measured against the
# real corpus: a month is 300-460 documents and 2.5-4.0 MB of XML, so these are
# roughly a year of headroom and still bound the work a single email can cause.
MAX_ZIP_BYTES = int(os.environ.get("YUNT_MAX_ZIP_BYTES", 60 * 1024 * 1024))
MAX_DOCUMENTS = int(os.environ.get("YUNT_MAX_DOCUMENTS", 8000))
MAX_LINES = int(os.environ.get("YUNT_MAX_LINES", 60000))


def is_allowed(address: str) -> bool:
    """True only if the address is explicitly on the list.

    Fails closed on an empty list by construction: `x in ()` is always False.
    """
    return _mailbox(address) in ALLOWED_ADDRESSES


def _mailbox(address: str) -> str:
    """Reduce 'Cristian <a@b.cl>' or ' A@B.CL ' to 'a@b.cl'."""
    value = (address or "").strip()
    if "<" in value and ">" in value:
        value = value[value.rindex("<") + 1 : value.rindex(">")]
    return value.strip().strip("<>").lower()
