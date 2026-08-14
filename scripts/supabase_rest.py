"""Minimal PostgREST client shared by the pre-flight and the loader.

Kept separate so the read-only pre-flight cannot accidentally gain write
ability: `get`/`count` are safe, and every mutating helper takes an explicit
`allow_writes` flag that the caller must have obtained from a human.
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

import certifi

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "Temp_Inference/.env.loader"
PAGE = 1000
RETRIES = 4


def load_env(path: Path = ENV_FILE) -> tuple[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    url = values.get("SUPABASE_URL", "").rstrip("/")
    key = values.get("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        raise SystemExit(f"SUPABASE_URL / SUPABASE_SECRET_KEY missing from {path}")
    return url, key


class Rest:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.context = ssl.create_default_context(cafile=certifi.where())
        self.writes = 0

    def _request(self, method: str, path: str, *, body: Any = None, headers: dict | None = None):
        payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.url}/rest/v1/{path}", data=payload, method=method,
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                **(headers or {}),
            },
        )
        last: Exception | None = None
        for attempt in range(RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=120, context=self.context) as response:
                    return response.headers, response.read()
            except urllib.error.HTTPError as error:
                detail = error.read().decode(errors="replace")[:400]
                # 4xx is our mistake: the payload or the query is wrong, and
                # retrying sends the same bad request again.
                if error.code < 500:
                    raise RuntimeError(f"{method} {path} -> {error.code}: {detail}") from error
                last = RuntimeError(f"{method} {path} -> {error.code}: {detail}")
            except urllib.error.URLError as error:
                last = RuntimeError(f"{method} {path} -> {error}")
            time.sleep(2 ** attempt)
        raise last or RuntimeError(f"{method} {path} failed")

    # ---- read -----------------------------------------------------------
    def get(self, table: str, select: str, query: str = "") -> list[dict]:
        rows: list[dict] = []
        start = 0
        while True:
            suffix = f"&{query}" if query else ""
            headers, body = self._request(
                "GET", f"{table}?select={select}{suffix}",
                headers={"Range": f"{start}-{start + PAGE - 1}"},
            )
            page = json.loads(body)
            rows.extend(page)
            if len(page) < PAGE:
                return rows
            start += PAGE

    def count(self, table: str, query: str = "") -> int:
        suffix = f"&{query}" if query else ""
        headers, _ = self._request(
            "GET", f"{table}?select=*{suffix}",
            headers={"Prefer": "count=exact", "Range": "0-0"},
        )
        return int(headers.get("Content-Range", "*/0").split("/")[-1])

    # ---- write ----------------------------------------------------------
    def upsert(self, table: str, rows: list[dict], on_conflict: str, *, allow_writes: bool) -> int:
        if not allow_writes:
            raise RuntimeError("refusing to write: allow_writes is False")
        for batch in chunks(rows, 500):
            self._request(
                "POST", f"{table}?on_conflict={urllib.parse.quote(on_conflict)}",
                body=batch,
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            self.writes += len(batch)
        return len(rows)

    def patch(self, table: str, query: str, values: dict, *, allow_writes: bool) -> None:
        """Update only the given columns on rows matching `query`.

        Use this, not upsert(), when every target row already exists: PostgREST
        upsert is INSERT ... ON CONFLICT, so any NOT NULL column missing from
        the payload fails the insert arm even though the row is really an
        update.
        """
        if not allow_writes:
            raise RuntimeError("refusing to write: allow_writes is False")
        self._request("PATCH", f"{table}?{query}", body=values,
                      headers={"Prefer": "return=minimal"})
        self.writes += 1

    def delete(self, table: str, query: str, *, allow_writes: bool) -> None:
        if not allow_writes:
            raise RuntimeError("refusing to write: allow_writes is False")
        self._request("DELETE", f"{table}?{query}", headers={"Prefer": "return=minimal"})
        self.writes += 1


def chunks(items: list[Any], size: int) -> Iterator[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def quote_in(values) -> str:
    """Render a PostgREST `in.(...)` list, quoting so commas survive."""
    escaped = ['"' + str(v).replace('"', '""') + '"' for v in values]
    return "(" + ",".join(escaped) + ")"
