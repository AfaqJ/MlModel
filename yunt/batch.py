"""Turning one received ZIP into a set of new documents, plus an honest account
of everything that did not make it.

SUPERSEDED, 2026-09-11. Ingestion lives in ../milk-company/src/lib/ingest/.
This module is the old Python reference; it is kept only because its tests still
run, and it has already diverged. Everything below about direction is WRONG as of
D-072: direction is read from the RUTs inside the document, and the folder is
only a fallback for a document naming Antillanca on neither side. Measured across
5,584 real DTEs, that case does not occur. Do not port logic out of this file and
do not treat it as the current design.

The direction (COMPRAS or VENTAS) comes from the folder, because it cannot be
recovered from the file: the same document type appears on both sides and the
classifier requires it. That is why the ZIP layout is part of the agreement with
Cristian rather than an implementation detail.

Nothing here writes anything. The result is a report.
"""

from __future__ import annotations

import io
import logging
import posixpath
import zipfile
from dataclasses import dataclass, field

from yunt import config, db, dte

log = logging.getLogger(__name__)

DIRECTIONS = ("COMPRAS", "VENTAS")


@dataclass
class Rejection:
    path: str
    reason: str
    detail: str = ""


@dataclass
class BatchResult:
    documents: list[dte.Document] = field(default_factory=list)   # new only
    duplicates: list[tuple[str, str, str]] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)
    files_seen: int = 0
    raw_detalle: int = 0
    lines: int = 0
    rescaled: int = 0
    unreconciled: int = 0

    @property
    def ok(self) -> bool:
        return bool(self.documents) and not self.rejected


def direction_of(path: str) -> str | None:
    """Which of COMPRAS / VENTAS this member sits under, at any depth."""
    parts = [p.upper() for p in posixpath.normpath(path).split("/")]
    for direction in DIRECTIONS:
        if direction in parts:
            return direction
    return None


def _safe_members(archive: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], list[Rejection]]:
    """Members we are willing to read, and why the rest were refused.

    The archive arrives by email from outside, so it is untrusted input: guard
    path traversal and the uncompressed size before reading anything.
    """
    members, rejected, total = [], [], 0
    for info in archive.infolist():
        if info.is_dir():
            continue
        name = info.filename
        if name.startswith("/") or ".." in posixpath.normpath(name).split("/"):
            rejected.append(Rejection(name, "unsafe_path"))
            continue
        if not name.lower().endswith(".xml"):
            rejected.append(Rejection(name, "not_xml"))
            continue
        if direction_of(name) is None:
            rejected.append(Rejection(name, "no_direction_folder",
                                      "must sit under COMPRAS/ or VENTAS/"))
            continue
        total += info.file_size
        if total > config.MAX_ZIP_BYTES:
            rejected.append(Rejection(name, "archive_too_large",
                                      f"uncompressed total over {config.MAX_ZIP_BYTES} bytes"))
            break
        members.append(info)
    return members, rejected


def existing_keys() -> set[tuple[str, str, str]]:
    """Every (issuer RUT, document type, folio) already held."""
    rows = db.select("invoices", "seller_rut,document_type,invoice_folio")
    return {(r["seller_rut"], str(r["document_type"]), str(r["invoice_folio"])) for r in rows}


def read_zip(data: bytes, known: set[tuple[str, str, str]] | None = None) -> BatchResult:
    """Parse every document in the archive and split it into new and duplicate.

    `known` is passed in rather than fetched here so this stays testable without
    a database, and so the caller decides how fresh that snapshot is.
    """
    result = BatchResult()
    known = known if known is not None else set()
    seen_in_batch: set[tuple[str, str, str]] = set()

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        result.rejected.append(Rejection("<archive>", "not_a_zip", str(exc)))
        return result

    members, result.rejected = _safe_members(archive)
    if len(members) > config.MAX_DOCUMENTS:
        result.rejected.append(Rejection("<archive>", "too_many_documents",
                                         f"{len(members)} files, limit {config.MAX_DOCUMENTS}"))
        return result

    for info in members:
        result.files_seen += 1
        try:
            documents = dte.parse(archive.read(info), direction_of(info.filename))
        except Exception as exc:  # noqa: BLE001 - one bad file must not stop the batch
            result.rejected.append(Rejection(info.filename, "unparseable", str(exc)[:200]))
            continue
        if not documents:
            result.rejected.append(Rejection(info.filename, "no_dte_found"))
            continue

        for doc in documents:
            if doc.key in known:
                result.duplicates.append(doc.key)
                continue
            if doc.key in seen_in_batch:
                # The same document twice inside one archive. Recorded, not stored
                # twice, and not counted as an already-held duplicate.
                result.duplicates.append(doc.key)
                continue
            seen_in_batch.add(doc.key)
            result.documents.append(doc)
            # Counted over NEW documents only, so it reconciles against `lines`.
            result.raw_detalle += doc.raw_detalle_count
            result.lines += len(doc.lines)
            result.rescaled += doc.rescaled_lines
            result.unreconciled += sum(1 for line in doc.lines if not line.reconciles)

    if result.lines > config.MAX_LINES:
        result.rejected.append(Rejection("<archive>", "too_many_lines",
                                         f"{result.lines} lines, limit {config.MAX_LINES}"))
        result.documents.clear()
    return result


def report(result: BatchResult) -> str:
    """The reception report, in Spanish, sent whether or not anything succeeded."""
    dropped = sum(len(d.dropped) for d in result.documents)
    out = [
        "Informe de recepcion",
        "",
        f"Archivos XML leidos:        {result.files_seen}",
        f"Documentos nuevos:          {len(result.documents)}",
        f"Documentos ya registrados:  {len(result.duplicates)}",
        f"Lineas extraidas:           {result.lines}",
    ]
    if result.rescaled:
        out.append(f"Lineas con escala corregida: {result.rescaled}")
    if result.unreconciled:
        out.append(f"Lineas que no cuadran (cantidad x precio): {result.unreconciled}")
    if dropped:
        out.append(f"Lineas descartadas con motivo: {dropped}")

    # The reconciliation, stated even when it is clean. A silent drop is what
    # left 357 lines unexplained in the original load.
    accounted = result.lines + dropped
    out += ["", f"Cuadratura: {result.raw_detalle} lineas en los archivos nuevos, "
                f"{accounted} contabilizadas."]

    if result.rejected:
        out += ["", f"Rechazados ({len(result.rejected)}):"]
        counts: dict[str, int] = {}
        for r in result.rejected:
            counts[r.reason] = counts.get(r.reason, 0) + 1
        out += [f"  {reason}: {n}" for reason, n in sorted(counts.items())]
        out += ["", "Ejemplos:"]
        out += [f"  {r.path} - {r.reason} {r.detail}".rstrip() for r in result.rejected[:10]]

    if not result.documents and not result.rejected:
        out += ["", "Nada nuevo que procesar: todo el contenido ya estaba registrado."]
    return "\n".join(out)
