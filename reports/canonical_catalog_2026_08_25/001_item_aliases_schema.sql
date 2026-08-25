-- Review-only schema proposal. The apply SQL contains the same DDL in one transaction.
create or replace function public.catalog_normalize_label(value text)
returns text language sql immutable parallel safe as $$
  select lower(regexp_replace(btrim(coalesce(value, '')), '\s+', ' ', 'g'))
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
