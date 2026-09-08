"""Supabase over PostgREST.

Reads are free. Writes require `allow_writes=True` to be passed explicitly at
the call site, which is the convention this project already runs on: every
change to live data is a scoped write that names its rows, dry run first.

Two PostgREST facts that have each cost a session here:

  * an upsert is `INSERT ... ON CONFLICT`, so a partial-column payload fails the
    insert arm on every NOT NULL column it omits. Send whole rows, or PATCH.
  * `needs_review` on `invoice_items` is a GENERATED column. Including it in any
    write returns 400 and takes the whole batch down with it.
"""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

import certifi

from yunt import config

# The system trust store is not reliably present in a slim container, so the
# CA bundle is pinned the same way scripts/supabase_rest.py already does it.
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

log = logging.getLogger(__name__)

PAGE = 1000
RETRIES = 4

# Postgres derives this one; writing it is a 400 that fails the whole batch.
GENERATED_COLUMNS = {"needs_review"}


class WriteRefused(Exception):
    """A write was attempted without allow_writes."""


def _request(method: str, path: str, *, body=None, headers=None) -> tuple[int, bytes, dict]:
    if not config.SUPABASE_URL or not config.SUPABASE_SECRET_KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SECRET_KEY are not set")
    request = urllib.request.Request(
        f"{config.SUPABASE_URL}/rest/v1/{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        method=method,
        headers={
            "apikey": config.SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {config.SUPABASE_SECRET_KEY}",
            "Content-Type": "application/json",
            **(headers or {}),
        },
    )
    last = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
                return response.status, response.read(), dict(response.headers)
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise RuntimeError(f"{method} {path} -> {exc.code}: {exc.read()[:400]!r}") from exc
            last = exc
        except urllib.error.URLError as exc:
            last = exc
        time.sleep(2 ** attempt)
    raise RuntimeError(f"{method} {path} failed after {RETRIES} attempts: {last}")


def select(table: str, columns: str, query: str = "") -> list[dict]:
    """Read every matching row, paging until the server stops giving more."""
    rows: list[dict] = []
    while True:
        path = f"{table}?select={urllib.parse.quote(columns)}{query}"
        _, body, _ = _request(
            "GET", path,
            headers={"Range-Unit": "items", "Range": f"{len(rows)}-{len(rows) + PAGE - 1}"},
        )
        page = json.loads(body)
        rows.extend(page)
        if len(page) < PAGE:
            return rows


def insert(table: str, rows: list[dict], *, allow_writes: bool) -> list[dict]:
    """Insert rows and return them as stored, so generated ids come back."""
    if not allow_writes:
        raise WriteRefused(f"insert into {table} of {len(rows)} rows without allow_writes")
    for row in rows:
        bad = GENERATED_COLUMNS & row.keys()
        if bad:
            raise ValueError(f"{table}: {sorted(bad)} is generated and must not be written")
    stored: list[dict] = []
    for start in range(0, len(rows), PAGE):
        _, body, _ = _request(
            "POST", table, body=rows[start : start + PAGE],
            headers={"Prefer": "return=representation"},
        )
        stored.extend(json.loads(body))
    return stored
