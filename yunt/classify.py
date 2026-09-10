"""Calling the classifier service.

The classifier is a separate Cloud Run service (`mlmodel`) holding the ONNX
model. This service calls it over HTTP in batches rather than importing it,
which is what keeps the Yunt container free of torch, onnxruntime and a 278 MB
model file, and what lets the two deploy independently.

Authentication: `mlmodel` is public today. Once it is locked to a service
account, calls need a Google-signed identity token whose audience is the
classifier's URL. That token comes from the metadata server, which only exists
on Cloud Run — locally there is none, and the call simply goes out unsigned.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.parse
import urllib.request

import certifi

from yunt import config, dte

log = logging.getLogger(__name__)

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
BATCH_SIZE = 500           # the service refuses more; see MAX_BATCH_SIZE there
METADATA_TOKEN_URL = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/identity?audience="
)


def _identity_token(audience: str) -> str | None:
    """A Google-signed token for calling a private Cloud Run service.

    Returns None off Cloud Run (no metadata server), which is correct while the
    classifier is still public and makes local runs work unchanged.
    """
    request = urllib.request.Request(
        METADATA_TOKEN_URL + urllib.parse.quote(audience, safe=""),
        headers={"Metadata-Flavor": "Google"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8").strip()
    except Exception:
        return None


def to_request(document: dte.Document, line: dte.Line) -> dict:
    """One invoice line in the shape the classifier expects.

    `transaction_type` is required and is not optional politeness: it is part of
    the trained model input and of the deterministic routing before it, and it
    cannot be recovered from the document, which is why it comes from the folder.

    `meter_code` is the receiver's internal code. On a COMPRAS line from a known
    electricity meter it short-circuits the whole cascade to a fixed category.

    `transport_plate` is the DTE's Transporte/Patente value. Petrol needs it to
    distinguish farm jerrycans from vehicle travel without asking the model.
    """
    return {
        # Addresses the line uniquely inside this batch so results can be paired
        # back up even though the service may return them in any order.
        "input_id": f"{document.seller_rut}|{document.document_type}|"
                    f"{document.folio}|{line.line_number}",
        "item_text": (line.item_text or line.description or "SIN DETALLE")[:512],
        "description": (line.description or "")[:512],
        "provider": (document.seller_name or "")[:256],
        "meter_code": document.receiver_internal_code or None,
        "transport_plate": document.transport_plate or None,
        "transaction_type": document.transaction_type,
    }


def classify(documents: list[dte.Document], *, timeout: int = 300) -> dict[str, dict]:
    """Classify every line of every document. Returns results keyed by input_id.

    A batch that fails is raised rather than silently skipped: writing some lines
    with categories and others without, with nothing recording which, is the kind
    of half-success that is worse than an error.
    """
    if not config.CLASSIFIER_URL:
        raise RuntimeError("CLASSIFIER_URL is not set")

    items = [to_request(doc, line) for doc in documents for line in doc.lines]
    token = _identity_token(config.CLASSIFIER_URL)
    results: dict[str, dict] = {}

    for start in range(0, len(items), BATCH_SIZE):
        chunk = items[start : start + BATCH_SIZE]
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request = urllib.request.Request(
            f"{config.CLASSIFIER_URL}/predict-batch",
            data=json.dumps({"items": chunk, "top_k": 3}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"classifier returned {exc.code} for lines "
                f"{start}-{start + len(chunk)}: {exc.read()[:300]!r}"
            ) from exc

        for row in body.get("results", []):
            if "error" in row:
                # A row the service could not classify. Kept, so the line is
                # written to review rather than dropped or silently defaulted.
                results[row["input_id"]] = {"decision": "review_required",
                                            "source": None,
                                            "error": row["error"].get("message", "row_failed")}
                continue
            results[row["input_id"]] = row

        log.info("classified %d/%d lines", len(results), len(items))

    missing = {item["input_id"] for item in items} - results.keys()
    if missing:
        raise RuntimeError(f"{len(missing)} lines came back with no result at all")
    return results
