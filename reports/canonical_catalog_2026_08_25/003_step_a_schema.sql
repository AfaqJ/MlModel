-- STEP A — paste this into the Supabase SQL editor and run it.
-- Schema only. It moves no data and deletes nothing.
--
-- Split out of 002_apply_canonical_catalog.sql, which is 2.6 MB and cannot be
-- pasted. Step B (the data) then runs over PostgREST; step C re-adds uniqueness.
--
-- Deliberately OMITTED here: item_catalog_normalized_name_uidx. That unique
-- index must be created AFTER the data migration, not before — until the 1,398
-- duplicate rows are gone it would reject the very renames that remove them.
-- It is step C, and its success is the proof the migration completed.

begin;

-- 1. Normalizer used by the alias generated column and by both unique indexes.
create or replace function public.catalog_normalize_label(value text)
returns text language sql immutable parallel safe as $$
  select lower(regexp_replace(btrim(coalesce(value, '')), '\s+', ' ', 'g'))
$$;

-- 2. The alias table (D-044). Empty until step B fills it with the 8 approved
--    alternate wordings.
create table if not exists public.item_aliases (
  alias_id uuid primary key default gen_random_uuid(),
  catalog_item_id uuid not null references public.item_catalog(catalog_item_id) on delete cascade,
  alias_name text not null,
  normalized_alias text generated always as (public.catalog_normalize_label(alias_name)) stored,
  company_id uuid references public.companies(company_id),
  created_at timestamptz not null default now(),
  constraint item_aliases_name_not_blank check (length(trim(alias_name)) > 0)
);

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

-- 3. Drop whatever unique constraint currently covers item_catalog
--    (item_name, description).
--
--    Why: step B renames 3,366 surviving rows to their canonical names while
--    1,398 duplicates are still present. Over PostgREST there is no single
--    transaction and no deferrable constraint, so those renames would collide.
--    Step C replaces this with a STRICTER rule — unique on the NORMALIZED name,
--    which is what D-044 actually wants. The table is never left unconstrained
--    for longer than the migration itself.
--
--    Written as a discovery loop because the constraint's generated name is not
--    recorded anywhere in the repo. It reports what it dropped; if it finds
--    nothing it says so and changes nothing.
do $$
declare
  r record;
  dropped int := 0;
begin
  for r in
    select c.conname
    from pg_constraint c
    join pg_class t on t.oid = c.conrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'item_catalog'
      and c.contype = 'u'
      and (
        select array_agg(a.attname::text order by a.attname)
        from unnest(c.conkey) k
        join pg_attribute a on a.attrelid = c.conrelid and a.attnum = k
      ) = array['description', 'item_name']
  loop
    execute format('alter table public.item_catalog drop constraint %I', r.conname);
    raise notice 'dropped unique constraint %', r.conname;
    dropped := dropped + 1;
  end loop;

  for r in
    select i.indexrelid::regclass::text as idxname
    from pg_index i
    join pg_class t on t.oid = i.indrelid
    join pg_namespace n on n.oid = t.relnamespace
    where n.nspname = 'public'
      and t.relname = 'item_catalog'
      and i.indisunique
      and not i.indisprimary
      and (
        select array_agg(a.attname::text order by a.attname)
        from unnest(i.indkey) k
        join pg_attribute a on a.attrelid = i.indrelid and a.attnum = k
      ) = array['description', 'item_name']
  loop
    execute format('drop index public.%I', split_part(r.idxname, '.', -1));
    raise notice 'dropped unique index %', r.idxname;
    dropped := dropped + 1;
  end loop;

  if dropped = 0 then
    raise notice 'no (item_name, description) unique constraint found — nothing dropped';
  end if;
end $$;

commit;

-- Expect: item_aliases exists and is empty; item_catalog still has all 5,411
-- rows and all 11,746 invoice lines still resolve. Nothing has moved yet.
select
  (select count(*) from public.item_catalog)   as catalog_rows_expect_5411,
  (select count(*) from public.invoice_items)  as invoice_lines_expect_11746,
  (select count(*) from public.item_aliases)   as aliases_expect_0;
