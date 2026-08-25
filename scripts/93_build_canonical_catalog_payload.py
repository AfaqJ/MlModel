"""Build the approved canonical-catalog migration payload without writing Supabase.

The review proposal remains the line-by-line source of the grouping. This script
only applies Afaq's final 2026-08-25 decisions, reuses existing catalog UUIDs
where possible, and emits an inspectable, transactional SQL migration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import uuid
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = Path("/private/tmp/catalog_review_snapshot_20260825")
DEFAULT_PROPOSAL = Path(
    "/Users/afaq/Desktop/Mctech/catalog-review-demo/public/catalog-review.json"
)
DEFAULT_DECISIONS = Path(
    "/Users/afaq/Downloads/catalog-review-2026-08-25 (3).json"
)
DEFAULT_OUTPUT = ROOT / "reports/canonical_catalog_2026_08_25"

RAW_EVIDENCE_SHA256 = (
    "a92760613d88f160942986fd59902862dc57f160b025fda2247b999da14abfd4"
)
EXPECTED_CURRENT_CATALOG = 5_411
EXPECTED_FINAL_CATALOG = 4_029
EXPECTED_ITEMS = 11_746

GASOLINE_UNKNOWN_ID = "6dd1730b-25db-5feb-9313-91e58d88f46f"
TIRAFONDOS_ID = "33ee7055-383a-5d6b-ae34-0856c8df36a9"
TRACTOR_ID = "b743d34d-40e0-59d3-ae2c-bd62854f0605"
GASOLINE_93_ID = "a75e8162-863b-5f7e-b363-4cd33b2a1d72"
GASOLINE_95_ID = "1d7dc979-3112-5b73-89b8-339556a72089"
GASOLINE_97_ID = "61b0586a-cad0-5c63-8577-f510ca600293"
COPEC_COMPANY_ID = "9e9d047f-6858-441e-95da-4c1cda795eb5"

NAMESPACE = uuid.UUID("24a8c251-d3f1-432a-986d-686681b78624")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
    )


def normalized_label(value: str) -> str:
    """The same case/spacing normalization used by the database constraint."""
    return " ".join(value.strip().lower().split())


def search_label(value: str) -> str:
    """More permissive application-side lookup form documented for later use."""
    folded = unicodedata.normalize("NFKD", value)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.casefold()).strip()


def data_sha(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode()
        )
    return digest.hexdigest()


def raw_fields_sha(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: item["item_id"]):
        digest.update(row["item_id"].encode())
        digest.update(b"\x1f")
        digest.update(row["item_text"].encode())
        digest.update(b"\x1f")
        digest.update((row.get("description") or "").encode())
        digest.update(b"\n")
    return digest.hexdigest()


def sql_text(value: str | None) -> str:
    if value is None:
        return "null"
    return "'" + value.replace("'", "''") + "'"


def final_group_key(group: dict) -> tuple[str, str]:
    group_id = group["catalogItemId"]
    name = group["itemName"]
    if group_id == GASOLINE_UNKNOWN_ID:
        return group_id, "GASOLINA"
    if group_id == TIRAFONDOS_ID:
        return group_id, "Tirafondos"
    if group_id == TRACTOR_ID:
        return group_id, "Tractor de jardín John Deere S140"
    if name.startswith("Materiales · LIDIA ANGELICA SANHUEZA FUENTES"):
        return "manual:materiales", "Materiales"
    if name.startswith("Segun Ot ") and "MULTIMOTOS OSORNO SPA" in name:
        return "manual:segun_ot", "SEGUN OT"
    return group_id, name


def choose_catalog_ids(
    groups: list[dict], occurrences: list[dict], current_catalog: list[dict]
) -> dict[str, str]:
    current_by_id = {row["catalog_item_id"]: row for row in current_catalog}
    exact_ids: dict[str, list[str]] = defaultdict(list)
    for row in current_catalog:
        exact_ids[normalized_label(row["item_name"])].append(row["catalog_item_id"])

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in occurrences:
        counts[row["finalKey"]][row["currentCatalogItemId"]] += 1

    # Give exact-name groups first choice, then the largest groups. This keeps
    # IDs stable while preventing one old generic row from serving two outputs.
    ordered = sorted(
        groups,
        key=lambda group: (
            not bool(exact_ids.get(normalized_label(group["itemName"]))),
            -group["occurrenceCount"],
            group["itemName"],
        ),
    )
    used: set[str] = set()
    chosen: dict[str, str] = {}
    for group in ordered:
        key = group["finalKey"]
        candidates = []
        candidates.extend(sorted(exact_ids.get(normalized_label(group["itemName"]), [])))
        candidates.extend(
            catalog_id for catalog_id, _ in counts[key].most_common()
        )
        candidates.append(str(uuid.uuid5(NAMESPACE, f"catalog:{key}")))
        selected = next(candidate for candidate in candidates if candidate not in used)
        if selected in current_by_id or selected not in used:
            chosen[key] = selected
            used.add(selected)
    return chosen


def build_aliases(catalog_id_by_proposal: dict[str, str]) -> list[dict]:
    """Only semantic wording aliases; never months, dimensions, quantities or OT IDs."""
    specs = [
        (GASOLINE_93_ID, "93 S/P", None),
        (GASOLINE_93_ID, "Aramco Gasolina 93", None),
        (GASOLINE_93_ID, "G93", None),
        (GASOLINE_93_ID, "Gasolina 93 octanos sin plomo", None),
        (GASOLINE_95_ID, "G95", None),
        (GASOLINE_95_ID, "Gasolina 95 octanos sin plomo", None),
        (GASOLINE_97_ID, "V-POWER Gasolina 97 octanos sp", None),
        # The invoice item is DETALLE, so the meaningful reusable wording comes
        # from its description and is safe only for COPEC.
        (GASOLINE_UNKNOWN_ID, "GASOLINA NU 1203", COPEC_COMPANY_ID),
    ]
    rows = []
    for proposal_id, alias_name, company_id in specs:
        catalog_item_id = catalog_id_by_proposal[proposal_id]
        scope = company_id or "global"
        rows.append(
            {
                "alias_id": str(
                    uuid.uuid5(
                        NAMESPACE,
                        f"alias:{catalog_item_id}:{scope}:{search_label(alias_name)}",
                    )
                ),
                "catalog_item_id": catalog_item_id,
                "alias_name": alias_name,
                "normalized_alias": normalized_label(alias_name),
                "company_id": company_id,
            }
        )
    return sorted(rows, key=lambda row: (row["catalog_item_id"], row["alias_name"]))


def schema_sql() -> str:
    return """-- Review-only schema proposal. The apply SQL contains the same DDL in one transaction.
create or replace function public.catalog_normalize_label(value text)
returns text language sql immutable parallel safe as $$
  select lower(regexp_replace(btrim(coalesce(value, '')), '\\s+', ' ', 'g'))
$$;

create table if not exists public.item_aliases (
  alias_id uuid primary key default gen_random_uuid(),
  catalog_item_id uuid not null references public.item_catalog(catalog_item_id) on delete cascade,
  alias_name text not null,
  normalized_alias text generated always as (public.catalog_normalize_label(alias_name)) stored,
  company_id uuid references public.companies(company_id),
  created_at timestamptz not null default now(),
  constraint item_aliases_name_not_blank check (length(trim(alias_name)) > 0)
);

create unique index if not exists item_catalog_normalized_name_uidx
  on public.item_catalog (public.catalog_normalize_label(item_name));
create unique index if not exists item_aliases_global_normalized_uidx
  on public.item_aliases (normalized_alias) where company_id is null;
create unique index if not exists item_aliases_company_normalized_uidx
  on public.item_aliases (company_id, normalized_alias) where company_id is not null;
create index if not exists item_aliases_catalog_item_id_idx
  on public.item_aliases (catalog_item_id);

alter table public.item_aliases enable row level security;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    execute 'grant select, insert, update, delete on public.item_aliases to service_role';
  end if;
end $$;
"""


def apply_sql(
    catalog: list[dict], aliases: list[dict], mapping: list[dict], raw_hash: str
) -> str:
    catalog_values = ",\n".join(
        f"  ({sql_text(row['catalog_item_id'])}::uuid, {sql_text(row['item_name'])}, '')"
        for row in catalog
    )
    mapping_values = ",\n".join(
        "  ({}::uuid, {}::uuid, {}::uuid, {}, {})".format(
            sql_text(row["item_id"]),
            sql_text(row["current_catalog_item_id"]),
            sql_text(row["canonical_catalog_item_id"]),
            sql_text(row["item_text"]),
            sql_text(row["description"]),
        )
        for row in mapping
    )
    alias_values = ",\n".join(
        "  ({}::uuid, {}::uuid, {}, {})".format(
            sql_text(row["alias_id"]),
            sql_text(row["catalog_item_id"]),
            sql_text(row["alias_name"]),
            f"{sql_text(row['company_id'])}::uuid" if row["company_id"] else "null",
        )
        for row in aliases
    )
    ddl = schema_sql().replace(
        "-- Review-only schema proposal. The apply SQL contains the same DDL in one transaction.\n",
        "",
    )
    return f"""-- GENERATED, NOT APPLIED. Snapshot raw-evidence SHA-256: {raw_hash}
-- This file changes only catalog IDs/names and creates item_aliases.
begin;

create temp table desired_catalog (
  catalog_item_id uuid primary key,
  item_name text not null,
  description text not null
) on commit drop;
insert into desired_catalog values
{catalog_values};

create temp table item_catalog_mapping (
  item_id uuid primary key,
  old_catalog_item_id uuid not null,
  new_catalog_item_id uuid not null,
  original_item_text text not null,
  original_description text
) on commit drop;
insert into item_catalog_mapping values
{mapping_values};

do $$
begin
  if (select count(*) from public.invoice_items) <> {EXPECTED_ITEMS} then
    raise exception 'stale payload: production invoice_items count changed';
  end if;
  if exists (
    select 1 from public.invoice_items i
    full join item_catalog_mapping m using (item_id)
    where i.item_id is null or m.item_id is null
       or i.catalog_item_id <> m.old_catalog_item_id
       or i.item_text is distinct from m.original_item_text
       or i.description is distinct from m.original_description
  ) then
    raise exception 'stale payload: invoice evidence or existing catalog mapping changed';
  end if;
end $$;

-- Temporary names avoid collisions while old duplicate rows still exist.
update public.item_catalog c
set item_name = '__catalog_migration__' || c.catalog_item_id::text,
    description = ''
from desired_catalog d
where c.catalog_item_id = d.catalog_item_id;

insert into public.item_catalog (catalog_item_id, item_name, description)
select catalog_item_id, '__catalog_migration__' || catalog_item_id::text, ''
from desired_catalog
on conflict (catalog_item_id) do nothing;

update public.invoice_items i
set catalog_item_id = m.new_catalog_item_id
from item_catalog_mapping m
where i.item_id = m.item_id;

delete from public.item_catalog c
where not exists (
  select 1 from desired_catalog d where d.catalog_item_id = c.catalog_item_id
);

update public.item_catalog c
set item_name = d.item_name, description = d.description
from desired_catalog d
where c.catalog_item_id = d.catalog_item_id;

{ddl}
delete from public.item_aliases;
insert into public.item_aliases (alias_id, catalog_item_id, alias_name, company_id) values
{alias_values};

do $$
begin
  if (select count(*) from public.item_catalog) <> {EXPECTED_FINAL_CATALOG} then
    raise exception 'catalog count mismatch';
  end if;
  if (select count(*) from public.invoice_items) <> {EXPECTED_ITEMS} then
    raise exception 'invoice line count changed';
  end if;
  if (select count(*) from public.item_aliases) <> {len(aliases)} then
    raise exception 'alias count mismatch';
  end if;
  if exists (
    select 1 from public.invoice_items i
    join item_catalog_mapping m using (item_id)
    where i.catalog_item_id <> m.new_catalog_item_id
       or i.item_text is distinct from m.original_item_text
       or i.description is distinct from m.original_description
  ) then
    raise exception 'post-migration mapping or raw evidence mismatch';
  end if;
end $$;

commit;
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--proposal", type=Path, default=DEFAULT_PROPOSAL)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    proposal = read_json(args.proposal)
    decisions = read_json(args.decisions)
    current_catalog = read_jsonl(args.snapshot / "item_catalog.jsonl")
    current_items = read_jsonl(args.snapshot / "invoice_items.jsonl")

    assert decisions["rawEvidenceSha256"] == RAW_EVIDENCE_SHA256
    assert len(current_catalog) == EXPECTED_CURRENT_CATALOG
    assert len(current_items) == EXPECTED_ITEMS
    decision_counts = Counter(row["decision"] for row in decisions["decisions"])
    assert decision_counts == {"approved": 4_024, "pending": 4}
    assert not any(row["decision"] == "rejected" for row in decisions["decisions"])

    proposal_group = {group["catalogItemId"]: group for group in proposal["groups"]}
    grouped: dict[str, dict] = {}
    proposal_to_final_key: dict[str, str] = {}
    for group in proposal["groups"]:
        key, name = final_group_key(group)
        proposal_to_final_key[group["catalogItemId"]] = key
        target = grouped.setdefault(
            key,
            {
                "finalKey": key,
                "itemName": name,
                "sourceProposalIds": [],
                "occurrenceCount": 0,
            },
        )
        assert target["itemName"] == name
        target["sourceProposalIds"].append(group["catalogItemId"])
        target["occurrenceCount"] += group["occurrenceCount"]

    assert len(grouped) == EXPECTED_FINAL_CATALOG
    names = [normalized_label(group["itemName"]) for group in grouped.values()]
    assert len(names) == len(set(names)), "duplicate canonical name after case/spacing fold"

    transformed_occurrences = []
    for row in proposal["occurrences"]:
        out = dict(row)
        out["finalKey"] = proposal_to_final_key[row["catalogItemId"]]
        transformed_occurrences.append(out)
    assert len(transformed_occurrences) == EXPECTED_ITEMS

    chosen_ids = choose_catalog_ids(
        list(grouped.values()), transformed_occurrences, current_catalog
    )
    catalog = sorted(
        (
            {
                "catalog_item_id": chosen_ids[key],
                "item_name": group["itemName"],
                "description": "",
            }
            for key, group in grouped.items()
        ),
        key=lambda row: (normalized_label(row["item_name"]), row["catalog_item_id"]),
    )
    assert len({row["catalog_item_id"] for row in catalog}) == EXPECTED_FINAL_CATALOG

    catalog_id_by_proposal = {
        proposal_id: chosen_ids[final_key]
        for proposal_id, final_key in proposal_to_final_key.items()
    }
    aliases = build_aliases(catalog_id_by_proposal)

    current_item_by_id = {row["item_id"]: row for row in current_items}
    assert len(current_item_by_id) == EXPECTED_ITEMS
    mapping = []
    migrated_items = []
    for occurrence in transformed_occurrences:
        item = current_item_by_id[occurrence["itemId"]]
        assert item["catalog_item_id"] == occurrence["currentCatalogItemId"]
        canonical_id = chosen_ids[occurrence["finalKey"]]
        mapping.append(
            {
                "item_id": item["item_id"],
                "current_catalog_item_id": item["catalog_item_id"],
                "canonical_catalog_item_id": canonical_id,
                "canonical_name": grouped[occurrence["finalKey"]]["itemName"],
                "item_text": item["item_text"],
                "description": item.get("description"),
            }
        )
        migrated = dict(item)
        migrated["catalog_item_id"] = canonical_id
        migrated_items.append(migrated)
    mapping.sort(key=lambda row: row["item_id"])
    migrated_items.sort(key=lambda row: row["item_id"])

    before_raw_hash = raw_fields_sha(current_items)
    after_raw_hash = raw_fields_sha(migrated_items)
    assert before_raw_hash == after_raw_hash
    assert set(row["catalog_item_id"] for row in migrated_items) <= {
        row["catalog_item_id"] for row in catalog
    }

    args.output.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output / "item_catalog.jsonl", catalog)
    write_jsonl(args.output / "item_aliases.jsonl", aliases)
    write_jsonl(args.output / "invoice_item_catalog_mapping.jsonl", mapping)
    write_jsonl(args.output / "invoice_items.jsonl", migrated_items)
    (args.output / "001_item_aliases_schema.sql").write_text(
        schema_sql(), encoding="utf-8"
    )
    (args.output / "002_apply_canonical_catalog.sql").write_text(
        apply_sql(catalog, aliases, mapping, before_raw_hash), encoding="utf-8"
    )

    final_counts = Counter(row["canonical_name"] for row in mapping)
    examples = {
        name: final_counts[name]
        for name in (
            "Gasolina 93",
            "Gasolina 95",
            "GASOLINA",
            "Clavos",
            "Tirafondos",
            "Materiales",
            "SEGUN OT",
            "Tractor de jardín John Deere S140",
            "Aplicación de cal",
        )
    }
    manifest = {
        "status": "generated_not_applied",
        "source": {
            "snapshot": str(args.snapshot),
            "proposal": str(args.proposal),
            "decisions": str(args.decisions),
            "reviewRawEvidenceSha256": RAW_EVIDENCE_SHA256,
        },
        "counts": {
            "invoiceItems": len(migrated_items),
            "catalogBefore": len(current_catalog),
            "catalogAfter": len(catalog),
            "catalogReduction": len(current_catalog) - len(catalog),
            "aliases": len(aliases),
        },
        "invariants": {
            "rawItemTextAndDescriptionSha256Before": before_raw_hash,
            "rawItemTextAndDescriptionSha256After": after_raw_hash,
            "rawFieldsUnchanged": before_raw_hash == after_raw_hash,
            "uniqueCanonicalNamesAfterCaseSpacingFold": len(names) == len(set(names)),
            "everyInvoiceItemMapped": len(mapping) == EXPECTED_ITEMS,
        },
        "examples": examples,
        "payloadSha256": {
            "itemCatalog": data_sha(catalog),
            "itemAliases": data_sha(aliases),
            "invoiceItemCatalogMapping": data_sha(mapping),
            "invoiceItems": data_sha(migrated_items),
        },
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
