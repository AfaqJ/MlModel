#!/usr/bin/env python3
"""Build the manually audited, transaction-aware v1.3.1 gold candidate.

The input is the already validated recovery_v1_2_0 candidate. This script:

1. Gives every gold row an explicit COMPRAS/VENTAS direction.
2. Records whether that direction came from the raw XML-derived table, an
   existing explicit field, or the taxonomy's income-vs-expense family.
3. Promotes only raw rows that were manually inspected in invoice context.
4. Writes every inspected starving-category candidate, including rejections
   and needs-client decisions, to an auditable CSV.

It does not modify the prior candidate, baseline gold, or deployed artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.inference.model_input import build_model_text, clean_description


BASE = ROOT / "Data/candidates/recovery_v1_2_0/master_gold.csv"
RAW = ROOT / "Data/processed/line_items.csv"
TAXONOMY = ROOT / "Data/current_context_2026_06_30/taxonomy_from_plan.csv"
OUTPUT = ROOT / "Data/candidates/recovery_v1_3_1"
OUTPUT_FIELDS = [
    "gold_id", "category_code", "leaf", "source", "item_text",
    "description", "provider", "farm", "audit_reason", "verify_flag",
    "direction", "direction_evidence", "raw_row_id",
]
AUDIT_FIELDS = [
    "audit_id", "category_code", "leaf", "raw_row_id", "source", "period",
    "source_file", "folio", "nro_lin_det", "item_text", "description",
    "provider", "candidate_basis", "verdict", "audit_reason",
    "promoted_gold_id",
]
EXPECTED_FOLDER_INVENTORY_SHA256 = "81a36a424c8d8496d320d5fc4483ff10af3200ad268e99962dc3c9d4e888a69e"
FOLDER_AUDIT_FIELDS = [
    "gold_id", "old_category_code", "new_category_code", "leaf", "source",
    "item_text", "description", "provider", "disposition", "authority",
    "audit_reason",
]
BASE_QUARANTINE = {
    # The old keyword audit treated "RIEGO CAL" as irrigation expense, but the
    # full item/description says 30 tonnes of lime with application and loading.
    "SA-00400": ("EXP-9.2", "RIEGO CAL PRADERAS 30 TON"),
    # These coverage lines share their XML invoices with the explicit client-
    # confirmed collective worker policy 12799. Earlier silver review assigned
    # them to generic "other insurance" without using the sibling line.
    "SA-00909": ("ADM-2.3", "Periodo de Cobertura junio 2025"),
    "SA-00920": ("ADM-2.3", "Periodo de Cobertura julio 2025"),
    "SA-00933": ("ADM-2.3", "Periodo de Cobertura agosto 2025"),
    "SA-00985": ("ADM-2.3", "Periodo de Cobertura enero 2026"),
    "SA-00990": ("ADM-2.3", "Periodo de Cobertura febrero 2026"),
}

# These rows are preserved in the audit ledger but excluded from model
# training. Folder placement alone cannot resolve them safely, or the row is an
# invoice template/header rather than a bought item. This is deliberately a
# quarantine, not a deletion from the original client/raw data.
FOLDER_QUARANTINE = {
    "SA-00405": "Mipro Pastoreo Skyline has contradictory prior category labels and needs client resolution.",
    "SA-00414": "Generic manual spray bottle has no row-level evidence proving an animal-health use.",
    # Animal-marking spray is plainly not a mastitis medicine, but no stronger
    # row-level client label establishes the replacement category.
    "SA-00425": "Folder label conflicts with the item; replacement category is not established by stronger row-level evidence.",
    "SA-00426": "Folder label conflicts with the item; replacement category is not established by stronger row-level evidence.",
    # Folder and prior silver audits disagree about this washing-machine
    # installation; 'sala de ordeña' could mean dairy-room or building repair.
    "SA-00239": "Conflicting prior audits (EXP-10.1 versus EXP-14.4); needs client resolution.",
    "SA-00591": "Conflicting prior audits (EXP-10.1 versus EXP-14.4); needs client resolution.",
    # Generic colour/tint line has no item identity.
    "SA-00590": "Generic colour-only line cannot support a category label.",
    # Printed invoice separators, column headings, software placeholders and
    # reminders are not purchased vehicle-maintenance items.
    "SA-00607": "Invoice separator/header, not a bought item.",
    "SA-00608": "Printed invoice column header, not a bought item.",
    "SA-00609": "Invoice software placeholder, not a bought item.",
    "SA-00610": "Workshop heading, not a bought item.",
    "SA-00611": "Service reminder, not a bought item.",
    # Food on a supermarket invoice could be administration refreshments or
    # employee benefits. Folder placement does not resolve that distinction.
    "SA-00672": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00652": "COPEC gasoline is not proven to be administration fuel by the provider-specific client example for Paola Uslar.",
    "SA-00675": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00676": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00677": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00678": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00679": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00681": "Food line is ambiguous between administration refreshments and staff benefit.",
    "SA-00707": "Abbreviated generic hardware line is insufficient to prove irrigation use.",
    "SA-00708": "Generic metal clamps are insufficient to prove irrigation use.",
    "SA-00754": "Water refill at a farm is ambiguous without a recipient/purpose.",
    "SA-00706": "Bale transport line does not identify silo versus hay and cannot safely choose EXP-4.2 or EXP-4.3.",
    # Folder-only HR examples describe food, bags, imprints and book titles but
    # their row text does not prove an employee benefit/gift purpose.
    **{gold_id: "Folder-only HR context does not prove this item was an employee benefit or gift." for gold_id in (
        "RG-01026", "RG-01099", "RG-01100", "RG-01101", "RG-01102", "RG-01103", "RG-01104", "RG-01105",
        "RG-01106", "RG-01107", "RG-01108", "RG-01109", "RG-01110", "RG-01111", "RG-01112", "RG-01113",
        "RG-01114", "RG-01115", "RG-01116", "RG-01117", "RG-01118", "RG-01119", "RG-01120", "RG-01121",
        "RG-01122",
    )},
    # The item text below is generic across electricity sites. Site category is
    # determined by the invoice meter ID, which is handled by the authoritative
    # meter lookup and is absent from model text. Training these rows causes the
    # model to learn a false site/category relationship from provider wording.
    **{gold_id: "Generic electricity charge requires the invoice meter ID; folder label must not train the text model." for gold_id in (
        "SA-00710", "SA-00711", "SA-00722", "SA-00723", "SA-00724", "SA-00725", "SA-00726", "SA-00727", "SA-00728",
        "SA-00729", "SA-00730", "SA-00731", "SA-00732", "SA-00733", "SA-00734", "SA-00736", "SA-00737", "SA-00738",
        "SA-00739", "SA-00740", "SA-00741", "SA-00742", "SA-00743", "SA-00744", "SA-00745", "SA-00746", "SA-00747",
        "SA-00749", "SA-00750", "SA-00751", "RG-01027", "RG-01028", "RG-01029", "RG-01030", "RG-01031", "RG-01032",
        "RG-01033", "RG-01034", "RG-01035", "RG-01075",
    )},
}

ADDITIONAL_QUARANTINE = {
    # These silver rows use language shared by both purchased bales and a
    # contractor making bales on the client's farm. There is not enough invoice
    # context to choose safely.
    "SA-00939": "Maxxifardos does not establish whether bales were purchased or made by a contractor.",
    "SA-00940": "Maxxifardos does not establish whether bales were purchased or made by a contractor.",
}
BASE_CORRECTIONS = {
    # Invoice-folder placement is not a row-level label. The client's product
    # rules classify the same Shoof nitrile-glove family (L/M/S) as work
    # clothing/EPP, and the user explicitly resolved XL in favour of that
    # row-level product authority.
    "SA-00416": {
        "old_code": "EXP-2.6",
        "new_code": "EXP-16.1",
        "expected_item": "GUANTE LARGO NITRILO XL SHOOF 204630",
        "source": "client_product_family_resolution",
        "reason": "Row-level client product labels override category-folder placement; Shoof nitrile gloves are EPP.",
    },
    "SA-00410": {"old_code": "EXP-2.6", "new_code": "EXP-16.1", "expected_item": "TRAJE DESECHABLE TYVEK DUPONT M", "source": "client_product_family_resolution", "reason": "Tyvek size variants follow the row-level client product family label for work clothing/EPP."},
    "SA-00411": {"old_code": "EXP-2.6", "new_code": "EXP-16.1", "expected_item": "TRAJE DESECHABLE TYVEK DUPONT L", "source": "client_product_family_resolution", "reason": "Tyvek size variants follow the row-level client product family label for work clothing/EPP."},
    "SA-00412": {"old_code": "EXP-2.6", "new_code": "EXP-16.1", "expected_item": "TRAJE DESECHABLE TYVEK DUPONT XXL", "source": "client_product_family_resolution", "reason": "Tyvek size variants follow the row-level client product family label for work clothing/EPP."},
    "SA-00432": {"old_code": "EXP-2.5", "new_code": "EXP-2.6", "expected_item": "AGUJAS DESECHABLES # 18 X 1 1/2!", "source": "client_product_family_resolution", "reason": "Client row-level needle rules classify disposable needles as animal-health supplies, not medicine."},
    "SA-00439": {"old_code": "EXP-2.5", "new_code": "EXP-2.6", "expected_item": "AGUJA DESECHABLE 16 X 1/2", "source": "client_product_family_resolution", "reason": "Client row-level needle rules classify disposable needles as animal-health supplies, not medicine."},
    "SA-00433": {"old_code": "EXP-2.5", "new_code": "EXP-2.6", "expected_item": "JERINGA DESECHABLE 20CC-C/AGUJA(L.L.)", "source": "client_product_family_resolution", "reason": "Client row-level syringe rules classify disposable syringes as animal-health supplies, not medicine."},
    "SA-00440": {"old_code": "EXP-2.5", "new_code": "EXP-2.6", "expected_item": "JERINGA DESECHABLE 10CC C/AGUJA (L.L.)", "source": "client_product_family_resolution", "reason": "Client row-level syringe rules classify disposable syringes as animal-health supplies, not medicine."},
    "SA-00626": {"old_code": "EXP-13.1", "new_code": "EXP-2.6", "expected_item": "PINTURA CELO TELL TAIL AZUL", "source": "client_product_family_resolution", "reason": "Client row-level Tell Tail animal-marking paint rules override the unrelated invoice folder."},
    "SA-00627": {"old_code": "EXP-13.1", "new_code": "EXP-2.6", "expected_item": "PINTURA CELO TELL TAIL ROJO", "source": "client_product_family_resolution", "reason": "Client row-level Tell Tail animal-marking paint rules override the unrelated invoice folder."},
    "SA-00628": {"old_code": "EXP-13.1", "new_code": "EXP-2.6", "expected_item": "PINTURA CELO TELL TAIL VERDE", "source": "client_product_family_resolution", "reason": "Client row-level Tell Tail animal-marking paint rules override the unrelated invoice folder."},
    "SA-00481": {"old_code": "EXP-5.3", "new_code": "EXP-2.6", "expected_item": "TOALLA PAPEL INTERFOLIADA", "source": "client_product_family_resolution", "reason": "Client row-level paper-towel product rule overrides the unrelated feed-category invoice folder."},
    "CF-00001": {"old_code": "EXP-10.1", "new_code": "EXP-16.1", "expected_item": "MANGAS PARA ORDEA MECANICA", "source": "client_product_family_resolution", "reason": "Client row-level milking-sleeve product rule labels this protective garment as work clothing/EPP."},
    "SA-00287": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 09/10/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00288": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 10/03/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00289": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 06/02/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00290": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 10/07/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00291": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 10/11/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00292": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 06/03/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00293": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 11/12/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00294": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 08/05/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00295": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 10/06/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00296": {"old_code": "ADM-2.3", "new_code": "ADM-2.1", "expected_item": "POLIZA 6615118, FECHA DE PAGO 08/08/2025", "source": "direct_client_family_resolution", "reason": "Direct client examples identify policy 6615118 as vehicle insurance; they override keyword silver."},
    "SA-00959": {"old_code": "EXP-12.1", "new_code": "EXP-12.2", "expected_item": "PLANILLA NUMERO 73697 - ANALISIS : COOP-FECAS-SEDIMENTACION", "source": "direct_client_family_resolution", "reason": "Fecal parasite/sedimentation analysis is animal analysis; client row examples override Ollama/silver."},
    "SA-00960": {"old_code": "EXP-12.1", "new_code": "EXP-12.2", "expected_item": "PLANILLA NUMERO 73698 - ANALISIS : COOP-FECAS-PARASITOS PUL", "source": "direct_client_family_resolution", "reason": "Fecal parasite/sedimentation analysis is animal analysis; client row examples override Ollama/silver."},
    "SA-00993": {"old_code": "EXP-12.1", "new_code": "EXP-12.2", "expected_item": "PLANILLA NUMERO 76449 - ANALISIS : COOP-FECAS-SEDIMENTACION", "source": "direct_client_family_resolution", "reason": "Fecal parasite/sedimentation analysis is animal analysis; client row examples override Ollama/silver."},
    "SA-00994": {"old_code": "EXP-12.1", "new_code": "EXP-12.2", "expected_item": "PLANILLA NUMERO 76450 - ANALISIS : COOP-FECAS-SEDIMENTACION", "source": "direct_client_family_resolution", "reason": "Fecal parasite/sedimentation analysis is animal analysis; client row examples override Ollama/silver."},
    "SA-00802": {"old_code": "EXP-15.3", "new_code": "EXP-4.2", "expected_item": "Traslado de bolos de silo", "source": "direct_client_family_resolution", "reason": "Direct client examples include bale transport in Bolos Silo; they override silver/Ollama freight labeling."},
    "RG-00603": {"old_code": "EXP-2.5", "new_code": "EXP-3.1", "expected_item": "CONCEPTAL_FACTOR LIBERA.HORMONAL * 50 ml", "source": "client_product_family_resolution", "reason": "Exact client product rule for Conceptal reproductive hormone overrides the conflicting direct example."},
    "SA-00399": {"old_code": "EXP-9.2", "new_code": "EXP-15.5", "expected_item": "RIEGO PURINES EN PRADERAS", "source": "manual_taxonomy_resolution", "reason": "Purine application is explicitly an agricultural service in the client taxonomy; two folder rows independently agree."},
    "SA-00413": {"old_code": "EXP-2.6", "new_code": "EXP-14.2", "expected_item": "ALAMBRE PUAS MOTTO 500 MTR.", "source": "client_product_family_resolution", "reason": "Client product rule for the same MOTTO barbed-wire family overrides the unrelated invoice folder."},
    "SA-00417": {"old_code": "EXP-2.6", "new_code": "EXP-16.2", "expected_item": "DESODORANTE PINOS - CEREZA", "source": "client_product_family_resolution", "reason": "Client product family places PINOS deodorizer variants under other operational expenses, not animal health."},
    "SA-00422": {"old_code": "EXP-2.2", "new_code": "EXP-2.5", "expected_item": "PENCIVET X CAJA -____", "source": "client_product_family_resolution", "reason": "Exact client PENCIVET product examples override the mastitis-folder placement."},
    "SA-00423": {"old_code": "EXP-2.2", "new_code": "EXP-2.4", "expected_item": "DIGESTIVO BILIFAR 120 GRS. -____", "source": "client_product_family_resolution", "reason": "Exact client BILIFAR product examples override the mastitis-folder placement."},
    "SA-00427": {"old_code": "EXP-2.2", "new_code": "EXP-16.1", "expected_item": "GUANTES SHOOF LARGO (L) NITRI.AZUL CAJA 100 UN -____", "source": "client_product_family_resolution", "reason": "Row-level client Shoof glove family labels override the mastitis-folder placement."},
    "SA-00463": {"old_code": "EXP-10.4", "new_code": "EXP-10.1", "expected_item": "FILTRO LECHE 75 MM * 800 SE - 200 UN", "source": "manual_taxonomy_resolution", "reason": "Milk filters are explicitly listed in the client definition of dairy-room maintenance and match audited milk-filter siblings."},
    "SA-00472": {"old_code": "EXP-10.3", "new_code": "EXP-10.1", "expected_item": "PIOLA PERLON RETIRADOR (NEGRA)/ MT", "source": "manual_taxonomy_resolution", "reason": "A remover cord is milking equipment/maintenance, not a detergent or hygiene chemical."},
    "SA-00494": {"old_code": "EXP-8.3", "new_code": "EXP-8.1", "expected_item": "SEMILLA BALLICA DAIRY PRIME DES X", "source": "manual_taxonomy_resolution", "reason": "The same Dairy Prime perennial ryegrass family appears repeatedly as EXP-8.1; folder placement alone had assigned reseeding."},
    "SA-00501": {"old_code": "EXP-4.2", "new_code": "EXP-15.5", "expected_item": "Aplicacin de lodo", "source": "manual_taxonomy_resolution", "reason": "Sludge application is an agricultural application service, not purchase/transport of silage bales."},
    "SA-00520": {"old_code": "EXP-4.3", "new_code": "EXP-6.3", "expected_item": "Aplicacin de cal", "source": "manual_taxonomy_resolution", "reason": "The item explicitly says lime application; the client taxonomy places lime product and application in EXP-6.3."},
    "SA-00550": {"old_code": "EXP-16.1", "new_code": "EXP-13.1", "expected_item": "A. GADUS S2 V220 2 X", "source": "client_product_family_resolution", "reason": "Client product rule for the same Gadus grease family overrides the work-clothing folder."},
    "SA-00551": {"old_code": "EXP-16.1", "new_code": "EXP-8.1", "expected_item": "SEMILLA BALLICA NUI IMPORT X", "source": "manual_taxonomy_resolution", "reason": "NUI is perennial ryegrass seed; it cannot be work clothing or tools."},
    "SA-00553": {"old_code": "EXP-16.1", "new_code": "EXP-8.1", "expected_item": "SEMILLA BALLICA NUI IMPORT X 25 KG", "source": "manual_taxonomy_resolution", "reason": "NUI is perennial ryegrass seed; it cannot be work clothing or tools."},
    "SA-00578": {"old_code": "EXP-14.2", "new_code": "EXP-13.1", "expected_item": "A. SPIRAX S4 TXM JC X 20 L (968314)", "source": "client_product_family_resolution", "reason": "Client product rule for the same Spirax transmission-oil family overrides the fencing folder."},
    "SA-00625": {"old_code": "EXP-13.1", "new_code": "EXP-2.6", "expected_item": "FORMALINA X", "source": "client_product_family_resolution", "reason": "Client FORMALINA product examples override the machinery-maintenance folder."},
    "SA-00629": {"old_code": "EXP-13.1", "new_code": "EXP-2.6", "expected_item": "TACO DE MADERA X", "source": "client_product_family_resolution", "reason": "Client wooden hoof-block product example overrides the machinery-maintenance folder."},
    "SA-00759": {"old_code": "EXP-5.4", "new_code": "EXP-4.2", "expected_item": "BOLOS MAITEN 2DA VUELTA", "source": "manual_taxonomy_resolution", "reason": "Per-hectare contractor work making silage bales belongs to on-farm bale production, not purchased feed."},
    "SA-00763": {"old_code": "EXP-5.4", "new_code": "EXP-4.2", "expected_item": "MOVIMIENTOS DE BOLOS", "source": "direct_client_family_resolution", "reason": "Direct client evidence places movement/transport of silage bales with on-farm silage-bale costs."},
    "SA-00764": {"old_code": "EXP-5.4", "new_code": "EXP-4.2", "expected_item": "MALLA PARA BOLO TOTAL COVER 1,25 X 3000 MT", "source": "manual_taxonomy_resolution", "reason": "The client taxonomy explicitly includes silage plastics/wrapping materials in on-farm silage production."},
    "SA-00766": {"old_code": "EXP-5.4", "new_code": "EXP-4.2", "expected_item": "BOLOS MAITEN", "source": "manual_taxonomy_resolution", "reason": "Per-hectare contractor work making silage bales belongs to on-farm bale production, not purchased feed."},
    "SA-00767": {"old_code": "EXP-5.4", "new_code": "EXP-4.2", "expected_item": "BOLOS FUTRONO", "source": "manual_taxonomy_resolution", "reason": "Contractor bale-production line belongs to on-farm silage-bale costs, not purchased feed."},
    "SA-00517": {"old_code": "EXP-4.3", "new_code": "EXP-4.2", "expected_item": "BOLOS SILO CHAPILCAHUIN", "source": "manual_taxonomy_resolution", "reason": "The row explicitly says silage bales, so the more specific Bolos Silo category overrides the hay folder."},
    "SA-00571": {"old_code": "EXP-14.1", "new_code": "EXP-15.4", "expected_item": "ARRIENDO CAMION", "source": "manual_taxonomy_resolution", "reason": "The item explicitly says truck rental; machinery/vehicle rental is EXP-15.4, not road maintenance."},
    "SA-00572": {"old_code": "EXP-14.1", "new_code": "EXP-15.4", "expected_item": "ARRIENDO EXCAVADORA", "source": "manual_taxonomy_resolution", "reason": "The item explicitly says excavator rental; machinery/vehicle rental is EXP-15.4, not road maintenance."},
    "SA-00573": {"old_code": "EXP-14.1", "new_code": "EXP-15.4", "expected_item": "ARRIENDO MAQUINARIA", "source": "manual_taxonomy_resolution", "reason": "The item explicitly says machinery rental; machinery/vehicle rental is EXP-15.4, not road maintenance."},
    "SA-00704": {"old_code": "EXP-15.3", "new_code": "EXP-4.2", "expected_item": "Flete", "source": "direct_client_family_resolution", "reason": "Description explicitly says transport of silage bales; client evidence and taxonomy put incidental bale transport in EXP-4.2."},
}


@dataclass(frozen=True)
class Decision:
    category_code: str
    verdict: str
    candidate_basis: str
    audit_reason: str


DECISIONS: dict[int, Decision] = {}


def register(
    code: str,
    verdict: str,
    row_ids: list[int],
    basis: str,
    reason: str,
) -> None:
    for row_id in row_ids:
        if row_id in DECISIONS:
            raise RuntimeError(f"duplicate manual audit row id: {row_id}")
        DECISIONS[row_id] = Decision(code, verdict, basis, reason)


# ADM-1.3: ADDVISE is the client-confirmed office-rent provider. Each raw row
# names a different billing month; October 2025 was already present in gold.
register("ADM-1.3", "promote", [83, 803, 1520, 2139, 3043, 3939, 4618, 5873, 6767, 8641, 9606, 10594, 11312],
         "provider_and_recurring_invoice_sequence",
         "ADDVISE office-rent provider is client-confirmed; item explicitly says Arriendo plus month.")
register("ADM-1.3", "already_gold", [7672], "provider_and_recurring_invoice_sequence",
         "October 2025 ADDVISE rent is already represented by a client-confirmed gold row.")

# ADM-1.9: the single legal representation line is real but already in gold.
register("ADM-1.9", "already_gold", [1465], "legal_provider_giro_and_item",
         "Legal representation from a provider whose XML giro is legal advisory; already in gold.")

# EXP-10.2: products are dip chemicals; applicators are dairy equipment and are
# deliberately not treated as Diping.
register("EXP-10.2", "already_gold", [117], "explicit_dip_product", "FULLDIP with GEA is already client-confirmed gold.")
register("EXP-10.2", "promote", [2143, 2144, 9635], "explicit_dip_product",
         "COW GUARD/FULLDIP explicitly identify teat-dip products; descriptions/providers create new valid inputs.")
register("EXP-10.2", "reject", [5443, 5544], "keyword_candidate",
         "Dipping applicators are equipment, not teat-dip chemical; likely dairy-shed expense, not EXP-10.2.")

# EXP-15.1: all monthly Aichele rows collapse to the already present exact input.
register("EXP-15.1", "already_gold", [26], "client_confirmed_provider_and_item",
         "Aichele agronomic advisory exact input is already present from the client folder.")

# EXP-15.2: only actual podology services belong in veterinary consultancy.
register("EXP-15.2", "already_gold", [2965, 11908], "explicit_bovine_podology_service",
         "These bovine podology services already exist as audited gold examples.")
register("EXP-15.2", "promote", [2966, 2968], "explicit_bovine_podology_service",
         "Distinct clinical/corrective bovine podology service descriptions from a veterinary-service provider.")
register("EXP-15.2", "needs_client", [2967, 2969, 11909], "same_invoice_ancillary_charge",
         "Travel allowance is on a veterinary invoice but could be veterinary service or administration mobilization.")
register("EXP-15.2", "reject", [3105, 5934, 6281], "provider_giro_keyword_false_positive",
         "Physical product/medicine from a veterinary provider, not veterinary consultancy.")
register("EXP-15.2", "reject", [5025, 5026, 5027, 5028, 5029, 5030, 5031, 5032, 6014, 6017],
         "provider_giro_keyword_false_positive", "Hardware matched only because the seller's broad giro mentions veterinary sales.")
register("EXP-15.2", "reject", [5311, 5312, 5329, 8181, 10126], "item_keyword_false_positive",
         "Veterinary coveralls are work clothing, not veterinary consultancy.")
register("EXP-15.2", "reject", [5880, 5881, 5882, 5883, 5884, 5885, 5886, 5887, 5888, 5889, 7680, 7681, 7682],
         "provider_giro_keyword_false_positive", "Laboratory tests belong to animal analysis, not veterinary consultancy.")
register("EXP-15.2", "reject", [7175], "provider_giro_keyword_false_positive",
         "Disposable needle is an animal-health supply, not veterinary consultancy.")

# EXP-6.3: explicit agricultural lime/application is safe. GEA "CAL" service
# abbreviations and hardware-store PintaCal are not agricultural lime.
register("EXP-6.3", "already_gold", [1147, 1525], "explicit_agricultural_lime", "Exact agricultural-lime input is already gold.")
register("EXP-6.3", "promote", [1490, 2999, 3409, 7328, 7600, 7601, 7604, 7609],
         "explicit_agricultural_lime",
         "Item/description explicitly identifies agricultural lime product or lime application on pasture/fund.")
register("EXP-6.3", "reject", [1550, 2172], "ambiguous_cal_abbreviation",
         "GEA technical/emergency 'CAL' is a service-call abbreviation, not agricultural lime.")
register("EXP-6.3", "reject", [3984, 4086], "hardware_lime_or_paint",
         "PintaCal from hardware retailers is building/paint material, not a farm soil amendment.")

# EXP-6.4: the raw chicken-manure product is explicit and adds the real XML
# provider form; Tebbe application is already represented.
register("EXP-6.4", "promote", [583], "explicit_chicken_manure", "Item explicitly says GUANO DE GALLINA; client product mapping confirms the category.")
register("EXP-6.4", "already_gold", [804], "explicit_manure_application", "Tebbe manure application exact input is already gold.")

# EXP-5.5: EUROLAC is client-confirmed and its real raw-provider form was absent.
register("EXP-5.5", "already_gold", [4282, 8286], "client_confirmed_milk_replacer", "Exact raw input is already represented in gold.")
register("EXP-5.5", "promote", [5297], "client_confirmed_milk_replacer", "EUROLAC is a client-confirmed milk replacer; raw provider form is a new valid input.")

# ADM-2.2: each period line is tied, in the same XML invoice, to collective
# worker policy 12799. October was already audited from the client folder.
register("ADM-2.2", "promote", [327, 1062, 1702, 2383, 3321, 4162, 5131, 6127, 8951, 9944, 10894, 11511],
         "same_invoice_collective_policy_12799",
         "Coverage-period line shares an invoice with client-confirmed collective worker policy 12799.")
register("ADM-2.2", "already_gold", [8037], "same_invoice_collective_policy_12799", "October coverage-period line is already audited gold.")

# EXP-5.1: the raw siblings were previously assigned to incompatible feed/mineral
# categories. Do not manufacture certainty from the item name alone.
register("EXP-5.1", "already_gold", [93], "previous_audited_example", "Maiten Mipro Pastoreo row is already audited gold.")
register("EXP-5.1", "needs_client", [94], "contradictory_prior_audits",
         "Same product invoice was previously labeled across cow/calf/other-animal feed; farm name is not enough.")
register("EXP-5.1", "needs_client", [8648], "contradictory_prior_audits",
         "Skyline row conflicts between mineral salts and other-animal feed in prior ledgers; do not promote.")

# Completion of the raw search for the remaining weak categories. Promotions
# are limited to rows whose own item/description states the category; model
# confidence is never used as label authority.
register("ADM-1.2", "promote", [434, 435, 436, 5275], "explicit_television_service",
         "DIRECTV programming/decoder charges explicitly identify a communications service.")
register("ADM-1.2", "promote", [81, 799, 1517, 3040, 3937, 4615, 5869, 7666], "explicit_internet_service",
         "Item explicitly says internet service and includes the recurring billing month.")
register("ADM-1.4", "promote", [11200, 11840, 9198, 7197], "explicit_gasoline_description",
         "Description explicitly identifies gasoline and litres; client examples place administration gasoline in mobilization.")
register("ADM-1.4", "promote", [723], "explicit_airfare_tax",
         "Airfare taxes are part of administration travel/mobilization.")
register("ADM-1.5", "promote", [8622, 3899, 7587, 1460, 8620], "explicit_meal",
         "Item explicitly identifies an administration meal.")
register("ADM-1.5", "promote", [7803, 7805, 6760], "explicit_lodging",
         "Item explicitly identifies hotel lodging or a lodging ancillary charge.")
register("ADM-1.8", "promote", [137, 138, 3077, 3078, 3952, 3953], "audisoft_accounting_system",
         "AUDISOFT electronic invoicing/accounting-system service matches the client taxonomy's named provider family.")
register("EXP-15.4", "promote", [9451], "explicit_machine_lease",
         "Item explicitly says excavator rental.")
register("EXP-2.1", "promote", [2565], "explicit_dry_cow_therapy",
         "ORBENIN E.D.C. explicitly identifies dry-cow therapy.")
register("EXP-4.1", "promote", [9572, 9573], "explicit_pile_silage",
         "Item explicitly says SILO PARVA and identifies the farm.")
register("EXP-4.1", "promote", [8369, 10118], "explicit_silage_additive",
         "SILOSOLVE is explicitly a silage additive, consistent with the client category definition.")
register("EXP-5.2", "promote", [2728, 9311], "explicit_calf_concentrate",
         "SURALIM inicial/crecimiento explicitly identifies calf starter/grower concentrate.")
register("EXP-6.1", "promote", [11676, 1353, 1350], "explicit_phosphorus_fertilizer",
         "Trefos, monoammonium phosphate and triple superphosphate are explicitly named phosphorus fertilizers.")
register("EXP-6.1", "promote", [2070], "explicit_map_fertilization",
         "MAP fertilization explicitly identifies monoammonium-phosphate use.")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", (value or "").lower())
    value = value.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def base_fields_key(item: str, description: str, provider: str) -> str:
    return normalize(" | ".join(part for part in (clean(item), clean_description(description), clean(provider)) if part))


def direction_for(code: str) -> str:
    return "VENTAS" if code.startswith("ING-") else "COMPRAS"


def model_key(row: dict[str, str]) -> str:
    return normalize(build_model_text(row["item_text"], row["description"], row["provider"], row["direction"]))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_csv(rows: list[dict[str, str]], fields: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def build(base_rows: list[dict[str, str]], raw_rows: list[dict[str, str]], taxonomy: list[dict[str, str]]):
    names = {row["new_code"].strip(): row["leaf"].strip() for row in taxonomy}
    base_ids = {row["gold_id"] for row in base_rows}
    folder_inventory = "\n".join(sorted(
        "|".join((row["gold_id"], row["category_code"], normalize(row["item_text"])))
        for row in base_rows if row.get("source", "").startswith("file_audit")
    )) + "\n"
    if hashlib.sha256(folder_inventory.encode()).hexdigest() != EXPECTED_FOLDER_INVENTORY_SHA256:
        raise RuntimeError("folder inventory changed; every new/changed row requires a new explicit manual audit")
    all_quarantine_ids = set(BASE_QUARANTINE) | set(FOLDER_QUARANTINE) | set(ADDITIONAL_QUARANTINE)
    if missing_quarantine := sorted(all_quarantine_ids - base_ids):
        raise RuntimeError(f"quarantine references missing gold IDs: {missing_quarantine}")
    if missing_corrections := sorted(set(BASE_CORRECTIONS) - base_ids):
        raise RuntimeError(f"corrections reference missing gold IDs: {missing_corrections}")
    if overlap := sorted(all_quarantine_ids & set(BASE_CORRECTIONS)):
        raise RuntimeError(f"rows cannot be both corrected and quarantined: {overlap}")
    raw_by_id = {int(row["row_id"]): row for row in raw_rows}
    missing = sorted(set(DECISIONS) - set(raw_by_id))
    if missing:
        raise RuntimeError(f"manual audit references missing raw row ids: {missing}")

    raw_directions: defaultdict[str, set[str]] = defaultdict(set)
    for raw in raw_rows:
        raw_directions[base_fields_key(raw["nmb_item"], raw["dsc_item"], raw["rzn_soc_emisor"])].add(raw["source"])

    output: list[dict[str, str]] = []
    quarantined: list[dict[str, str]] = []
    corrected: list[dict[str, str]] = []
    folder_audits: list[dict[str, str]] = []
    for original in base_rows:
        is_folder_row = original.get("source", "").startswith("file_audit")
        correction = BASE_CORRECTIONS.get(original["gold_id"])
        quarantine_reason = (
            FOLDER_QUARANTINE.get(original["gold_id"])
            or ADDITIONAL_QUARANTINE.get(original["gold_id"])
        )
        if is_folder_row:
            if correction:
                disposition = "correct"
                new_code = correction["new_code"]
                authority = correction["source"]
                reason = correction["reason"]
            elif quarantine_reason:
                disposition = "quarantine"
                new_code = ""
                authority = "locked_399_row_manual_review"
                reason = quarantine_reason
            else:
                disposition = "keep"
                new_code = original["category_code"]
                authority = "locked_399_row_manual_review"
                reason = "Kept after review of the locked 399-row folder inventory; row semantics are consistent and no stronger contradictory evidence was found."
            folder_audits.append({
                "gold_id": original["gold_id"],
                "old_category_code": original["category_code"],
                "new_category_code": new_code,
                "leaf": names.get(new_code, ""),
                "source": original["source"],
                "item_text": clean(original.get("item_text")),
                "description": clean(original.get("description")),
                "provider": clean(original.get("provider")),
                "disposition": disposition,
                "authority": authority,
                "audit_reason": reason,
            })
        if original["gold_id"] in BASE_QUARANTINE:
            expected_code, expected_item = BASE_QUARANTINE[original["gold_id"]]
            if original["category_code"] != expected_code or normalize(original["item_text"]) != normalize(expected_item):
                raise RuntimeError(f"base quarantine guard failed: {original['gold_id']}")
            quarantined.append(original)
            continue
        if quarantine_reason:
            quarantined.append(original)
            continue
        row = {field: clean(original.get(field, "")) for field in OUTPUT_FIELDS}
        if correction:
            if (
                row["category_code"] != correction["old_code"]
                or normalize(row["item_text"]) != normalize(correction["expected_item"])
            ):
                raise RuntimeError(f"base correction guard failed: {row['gold_id']}")
            row["category_code"] = correction["new_code"]
            row["leaf"] = names[correction["new_code"]]
            row["source"] = correction["source"]
            row["audit_reason"] = correction["reason"]
            row["verify_flag"] = ""
            corrected.append(row)
        expected = direction_for(row["category_code"])
        explicit = row["direction"].upper()
        if explicit and explicit != expected:
            raise RuntimeError(f"gold direction contradicts category family: {row['gold_id']}")
        raw_match = raw_directions.get(base_fields_key(row["item_text"], row["description"], row["provider"]), set())
        if explicit:
            row["direction"] = explicit
            row["direction_evidence"] = "existing_explicit"
        elif raw_match == {expected}:
            row["direction"] = expected
            row["direction_evidence"] = "raw_exact_model_fields"
        else:
            row["direction"] = expected
            row["direction_evidence"] = "taxonomy_income_vs_expense_family"
        output.append(row)

    established: dict[str, str] = {}
    for row in output:
        key = model_key(row)
        prior = established.setdefault(key, row["category_code"])
        if prior != row["category_code"]:
            raise RuntimeError(f"base cross-label model-input contradiction: {prior} vs {row['category_code']}")

    audits: list[dict[str, str]] = []
    promoted = []
    for sequence, row_id in enumerate(sorted(DECISIONS), start=1):
        decision = DECISIONS[row_id]
        raw = raw_by_id[row_id]
        expected_direction = direction_for(decision.category_code)
        if raw["source"] != expected_direction:
            raise RuntimeError(f"audit row {row_id} direction {raw['source']} disagrees with {decision.category_code}")
        promoted_id = ""
        if decision.verdict == "promote":
            candidate = {
                "gold_id": f"MA-{row_id:05d}",
                "category_code": decision.category_code,
                "leaf": names[decision.category_code],
                "source": "manual_raw_starving_audit",
                "item_text": clean(raw["nmb_item"]),
                "description": clean(raw["dsc_item"]),
                "provider": clean(raw["rzn_soc_emisor"]),
                "farm": clean(raw["farm"]),
                "audit_reason": decision.audit_reason,
                "verify_flag": "",
                "direction": raw["source"],
                "direction_evidence": "raw_xml_source",
                "raw_row_id": str(row_id),
            }
            key = model_key(candidate)
            prior = established.get(key)
            if prior and prior != decision.category_code:
                raise RuntimeError(f"promotion {row_id} contradicts established label {prior}")
            if prior is None:
                established[key] = decision.category_code
                output.append(candidate)
                promoted.append(candidate)
                promoted_id = candidate["gold_id"]
        audits.append({
            "audit_id": f"WA-{sequence:03d}",
            "category_code": decision.category_code,
            "leaf": names[decision.category_code],
            "raw_row_id": str(row_id),
            "source": raw["source"],
            "period": raw["period"],
            "source_file": raw["source_file"],
            "folio": raw["folio"],
            "nro_lin_det": raw["nro_lin_det"],
            "item_text": clean(raw["nmb_item"]),
            "description": clean(raw["dsc_item"]),
            "provider": clean(raw["rzn_soc_emisor"]),
            "candidate_basis": decision.candidate_basis,
            "verdict": decision.verdict,
            "audit_reason": decision.audit_reason,
            "promoted_gold_id": promoted_id,
        })

    labels_by_key: defaultdict[str, set[str]] = defaultdict(set)
    for row in output:
        labels_by_key[model_key(row)].add(row["category_code"])
    contradictions = {key: values for key, values in labels_by_key.items() if len(values) > 1}
    if contradictions:
        raise RuntimeError(f"final cross-label contradictions: {list(contradictions.items())[:5]}")
    expected_folder_rows = sum(row.get("source", "").startswith("file_audit") for row in base_rows)
    if len(folder_audits) != expected_folder_rows:
        raise RuntimeError(f"folder audit ledger incomplete: {len(folder_audits)} of {expected_folder_rows}")
    return output, audits, promoted, quarantined, corrected, folder_audits


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--raw", type=Path, default=RAW)
    parser.add_argument("--taxonomy", type=Path, default=TAXONOMY)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.output_dir.exists() and not args.overwrite:
        raise SystemExit(f"refusing to overwrite {args.output_dir}; pass --overwrite")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    master, audits, promoted, quarantined, corrected, folder_audits = build(
        read_csv(args.base), read_csv(args.raw), read_csv(args.taxonomy)
    )

    master_path = args.output_dir / "master_gold.csv"
    audit_path = args.output_dir / "starving_category_manual_audit.csv"
    promoted_path = args.output_dir / "promoted_raw_rows.csv"
    quarantine_path = args.output_dir / "quarantined_wrong_labels.csv"
    folder_audit_path = args.output_dir / "folder_line_audit.csv"
    master_path.write_text(render_csv(master, OUTPUT_FIELDS), encoding="utf-8")
    audit_path.write_text(render_csv(audits, AUDIT_FIELDS), encoding="utf-8")
    promoted_path.write_text(render_csv(promoted, OUTPUT_FIELDS), encoding="utf-8")
    quarantine_fields = list(read_csv(args.base)[0])
    quarantine_path.write_text(render_csv(quarantined, quarantine_fields), encoding="utf-8")
    folder_audit_path.write_text(render_csv(folder_audits, FOLDER_AUDIT_FIELDS), encoding="utf-8")

    distinct_counts = Counter()
    for row in {model_key(row): row for row in master}.values():
        distinct_counts[row["category_code"]] += 1
    taxonomy_codes = {row["new_code"] for row in read_csv(args.taxonomy)}
    trained_classes = {code for code, count in distinct_counts.items() if count >= 2}
    manifest = {
        "candidate": "recovery_v1_3_1_transaction_aware_authority_corrected",
        "policy": "validated v1.2 recovery + strict manual raw audit; transaction direction in every model input; no synthetic data",
        "inputs": {
            str(args.base.relative_to(ROOT)): sha256(args.base),
            str(args.raw.relative_to(ROOT)): sha256(args.raw),
            str(args.taxonomy.relative_to(ROOT)): sha256(args.taxonomy),
        },
        "counts": {
            "base_rows": len(read_csv(args.base)),
            "quarantined_wrong_labels": len(quarantined),
            "corrected_authority_conflicts": len(corrected),
            "folder_rows_audited": len(folder_audits),
            "folder_rows_kept": sum(row["disposition"] == "keep" for row in folder_audits),
            "folder_rows_corrected": sum(row["disposition"] == "correct" for row in folder_audits),
            "folder_rows_quarantined": sum(row["disposition"] == "quarantine" for row in folder_audits),
            "manual_candidates_inspected": len(audits),
            "manual_rows_promoted": len(promoted),
            "final_rows": len(master),
            "normalized_distinct_transaction_aware_inputs": len({model_key(row) for row in master}),
            "synthetic_rows": 0,
            "cross_label_contradictions": 0,
        },
        "audit_verdicts": dict(sorted(Counter(row["verdict"] for row in audits).items())),
        "promotions_by_category": dict(sorted(Counter(row["category_code"] for row in promoted).items())),
        "authority_corrections": {
            row["gold_id"]: {
                "category_code": row["category_code"],
                "source": row["source"],
                "audit_reason": row["audit_reason"],
            }
            for row in corrected
        },
        "direction_evidence": dict(sorted(Counter(row["direction_evidence"] for row in master).items())),
        "direction_counts": dict(sorted(Counter(row["direction"] for row in master).items())),
        "active_taxonomy_categories": len(taxonomy_codes),
        "model_eligible_categories_ge2_distinct": len(trained_classes),
        "active_not_model_eligible": sorted(taxonomy_codes - trained_classes),
        "no_valid_raw_sales_examples": ["ING-0.5", "ING-0.6"],
        "starving_audit_notes": {
            "EXP-8.3": "No raw line explicitly says repoblamiento/reseeding; generic seed/siembra rows are ambiguous among pasture categories.",
            "ING-0.5": "No verified VENTAS row for other-animal sales; three old silver candidates were COMPRAS and remain rejected.",
            "ING-0.6": "No verified VENTAS firewood row; all raw leña matches are COMPRAS or unrelated provider giro text.",
            "EXP-11.2": "Generic electricity text cannot distinguish buildings; the client meter lookup remains the authoritative discriminator.",
            "EXP-5.1": "Mipro rows have contradictory prior labels and were not promoted without client confirmation.",
        },
        "outputs": {},
    }
    for path in (master_path, audit_path, promoted_path, quarantine_path, folder_audit_path):
        manifest["outputs"][path.name] = sha256(path)
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
