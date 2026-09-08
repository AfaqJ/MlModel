"""Checks for reading a received archive.

The archive arrives by email from outside the company, so the members are
untrusted input and the guards on them are part of the contract, not polish.
"""

from __future__ import annotations

import io
import zipfile

import pytest

from yunt import batch, dte
from tests.test_yunt_dte import wrap


def zipped(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buf.getvalue()


DETALLE = "<NmbItem>SAL</NmbItem><QtyItem>2</QtyItem><PrcItem>50</PrcItem><MontoItem>100</MontoItem>"


def test_direction_comes_from_the_folder_at_any_depth():
    assert batch.direction_of("COMPRAS/a.xml") == "COMPRAS"
    assert batch.direction_of("lote/ventas/2026/a.xml") == "VENTAS"
    assert batch.direction_of("otros/a.xml") is None


def test_a_document_is_read_with_the_direction_of_its_folder():
    result = batch.read_zip(zipped({"VENTAS/a.xml": wrap(DETALLE)}))
    assert len(result.documents) == 1
    assert result.documents[0].transaction_type == "VENTAS"
    assert result.lines == 1


def test_a_known_document_is_a_duplicate_not_a_new_one():
    data = zipped({"COMPRAS/a.xml": wrap(DETALLE)})
    key = batch.read_zip(data).documents[0].key
    again = batch.read_zip(data, {key})
    assert again.documents == [] and again.duplicates == [key]


def test_the_same_document_twice_in_one_archive_is_stored_once():
    data = zipped({"COMPRAS/a.xml": wrap(DETALLE), "COMPRAS/copia/a.xml": wrap(DETALLE)})
    result = batch.read_zip(data)
    assert len(result.documents) == 1 and len(result.duplicates) == 1


def test_a_file_outside_compras_or_ventas_is_rejected_with_a_reason():
    result = batch.read_zip(zipped({"otros/a.xml": wrap(DETALLE)}))
    assert result.documents == []
    assert result.rejected[0].reason == "no_direction_folder"


def test_path_traversal_is_refused():
    result = batch.read_zip(zipped({"../../COMPRAS/a.xml": wrap(DETALLE)}))
    assert [r.reason for r in result.rejected] == ["unsafe_path"]


def test_a_non_xml_member_is_rejected_without_stopping_the_batch():
    result = batch.read_zip(zipped({"COMPRAS/a.xml": wrap(DETALLE), "COMPRAS/notas.txt": b"hi"}))
    assert len(result.documents) == 1
    assert [r.reason for r in result.rejected] == ["not_xml"]


def test_an_unparseable_file_does_not_stop_the_batch():
    result = batch.read_zip(zipped({"COMPRAS/bad.xml": b"<not xml", "COMPRAS/a.xml": wrap(DETALLE)}))
    assert len(result.documents) == 1
    assert result.rejected[0].reason == "unparseable"


def test_something_that_is_not_a_zip_is_reported_not_raised():
    result = batch.read_zip(b"this is not a zip file")
    assert result.rejected[0].reason == "not_a_zip"


def test_the_archive_size_guard_fires(monkeypatch):
    monkeypatch.setattr(batch.config, "MAX_ZIP_BYTES", 10)
    result = batch.read_zip(zipped({"COMPRAS/a.xml": wrap(DETALLE)}))
    assert any(r.reason == "archive_too_large" for r in result.rejected)


def test_the_reconciliation_line_compares_the_same_population():
    """It counted raw lines from every document but accounted lines from the new
    ones only, so a clean re-send read '902 in, 0 accounted'."""
    data = zipped({"COMPRAS/a.xml": wrap(DETALLE)})
    key = batch.read_zip(data).documents[0].key
    result = batch.read_zip(data, {key})
    assert result.raw_detalle == 0 and result.lines == 0
    assert "0 lineas en los archivos nuevos, 0 contabilizadas" in batch.report(result)


def test_rut_is_normalised_to_the_shape_supabase_stores():
    assert dte.normalise_rut("11920610-3") == "119206103"
    assert dte.normalise_rut("13160971-k") == "13160971K"


def test_a_liquidacion_factura_type_43_is_read():
    xml = ("<DTE version=\"1.0\"><Liquidacion ID=\"x\"><Encabezado>"
           "<IdDoc><TipoDTE>43</TipoDTE><Folio>167065</Folio><FchEmis>2025-08-05</FchEmis></IdDoc>"
           "<Emisor><RUTEmisor>76360720-8</RUTEmisor><RznSoc>FERIA</RznSoc></Emisor>"
           "<Receptor><RUTRecep>96685810-9</RUTRecep></Receptor>"
           "<Totales><MntTotal>100</MntTotal></Totales></Encabezado>"
           f"<Detalle>{DETALLE}</Detalle></Liquidacion></DTE>").encode("latin-1")
    documents = dte.parse(xml, "COMPRAS")
    assert documents and documents[0].key == ("763607208", "43", "167065")
