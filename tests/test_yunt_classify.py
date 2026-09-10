"""Checks for the classifier call. No network: the transport is stubbed so the
mapping and the failure handling are what get tested."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from yunt import classify, dte
from tests.test_yunt_dte import wrap


def documents(n_lines: int = 2):
    detalle = "".join(
        f"<NmbItem>ITEM {i}</NmbItem><QtyItem>1</QtyItem>"
        f"<PrcItem>10</PrcItem><MontoItem>10</MontoItem>"
        for i in range(1)
    )
    return dte.parse(wrap(detalle), "COMPRAS")


def test_the_request_carries_everything_the_cascade_needs():
    doc = documents()[0]
    payload = classify.to_request(doc, doc.lines[0])
    # transaction_type is required by the service and cannot be recovered from
    # the file, which is the whole reason the ZIP has direction folders.
    assert payload["transaction_type"] == "COMPRAS"
    assert payload["provider"] == "PRUEBA"
    assert payload["item_text"] == "ITEM 0"
    # extra="forbid" on the service side: an unexpected key is a 422.
    assert set(payload) == {"input_id", "item_text", "description",
                            "provider", "meter_code", "transport_plate", "transaction_type"}


def test_input_id_is_unique_per_line_across_documents():
    doc = documents()[0]
    ids = {classify.to_request(doc, line)["input_id"] for line in doc.lines}
    assert len(ids) == len(doc.lines)
    assert doc.folio in next(iter(ids))


def test_a_line_with_no_name_falls_back_to_its_description():
    xml = wrap("<NmbItem></NmbItem><DscItem>SOLO DESCRIPCION</DscItem><MontoItem>5</MontoItem>")
    doc = dte.parse(xml, "COMPRAS")[0]
    assert classify.to_request(doc, doc.lines[0])["item_text"] == "SOLO DESCRIPCION"


class FakeResponse:
    def __init__(self, payload): self._payload = json.dumps(payload).encode()
    def read(self): return self._payload
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_a_row_the_service_could_not_classify_goes_to_review_not_missing(monkeypatch):
    monkeypatch.setattr(classify.config, "CLASSIFIER_URL", "https://example.invalid")
    docs = documents()
    ids = [classify.to_request(docs[0], line)["input_id"] for line in docs[0].lines]
    payload = {"results": [{"input_id": ids[0], "error": {"message": "boom"}}]}

    with patch.object(classify, "_identity_token", return_value=None), \
         patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
        results = classify.classify(docs)

    # Kept and marked for review, never dropped and never silently defaulted to
    # a category.
    assert results[ids[0]]["decision"] == "review_required"
    assert results[ids[0]]["source"] is None


def test_a_line_that_comes_back_with_no_result_at_all_is_an_error(monkeypatch):
    """Writing some lines classified and others not, with nothing recording
    which, is a half-success that is worse than a failure."""
    monkeypatch.setattr(classify.config, "CLASSIFIER_URL", "https://example.invalid")
    with patch.object(classify, "_identity_token", return_value=None), \
         patch("urllib.request.urlopen", return_value=FakeResponse({"results": []})):
        with pytest.raises(RuntimeError, match="no result at all"):
            classify.classify(documents())


def test_it_refuses_to_run_without_a_classifier_url(monkeypatch):
    monkeypatch.setattr(classify.config, "CLASSIFIER_URL", "")
    with pytest.raises(RuntimeError, match="CLASSIFIER_URL"):
        classify.classify(documents())
