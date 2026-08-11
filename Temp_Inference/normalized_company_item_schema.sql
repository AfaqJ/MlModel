create extension if not exists pgcrypto;

-- Run this after the previous normalized tables have been backed up/exported
-- and dropped. It creates the production shape with companies and item catalog.

create table if not exists public.categories (
  categories_id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,

  constraint categories_code_not_blank check (length(trim(code)) > 0),
  constraint categories_name_not_blank check (length(trim(name)) > 0)
);

create table if not exists public.companies (
  company_id uuid primary key default gen_random_uuid(),

  rut text not null unique,
  company_name text not null,
  is_seller boolean not null default false,
  is_buyer boolean not null default false,

  giro text,
  address text,
  commune text,
  city text,

  constraint companies_rut_not_blank check (length(trim(rut)) > 0),
  constraint companies_name_not_blank check (length(trim(company_name)) > 0),
  constraint companies_has_role check (is_seller = true or is_buyer = true)
);

create table if not exists public.item_catalog (
  catalog_item_id uuid primary key default gen_random_uuid(),

  item_name text not null,
  description text not null default '',

  constraint item_catalog_name_description_unique unique (item_name, description),
  constraint item_catalog_item_name_not_blank check (length(trim(item_name)) > 0)
);

create table if not exists public.invoices (
  invoice_id uuid primary key default gen_random_uuid(),

  company_id uuid not null references public.companies(company_id),
  transaction_type text not null,

  invoice_folio text not null,
  document_type text not null,
  invoice_date date not null,
  invoice_period text generated always as (
    (extract(year from invoice_date)::int)::text
    || '-'
    || lpad((extract(month from invoice_date)::int)::text, 2, '0')
  ) stored,

  seller_rut text not null,
  seller_name text not null,
  seller_giro text,
  seller_address text,
  seller_commune text,
  seller_city text,

  buyer_rut text not null,
  buyer_name text not null,
  buyer_giro text,
  buyer_address text,
  buyer_commune text,
  buyer_city text,
  receiver_internal_code text,

  net_amount numeric,
  iva_amount numeric,
  exempt_amount numeric,
  total_amount numeric,
  due_date date,
  payment_form text,

  constraint invoices_business_key unique (seller_rut, document_type, invoice_folio),
  constraint invoices_transaction_type_allowed check (transaction_type in ('COMPRAS', 'VENTAS')),
  constraint invoices_folio_not_blank check (length(trim(invoice_folio)) > 0),
  constraint invoices_document_type_not_blank check (length(trim(document_type)) > 0),
  constraint invoices_seller_rut_not_blank check (length(trim(seller_rut)) > 0),
  constraint invoices_seller_name_not_blank check (length(trim(seller_name)) > 0),
  constraint invoices_buyer_rut_not_blank check (length(trim(buyer_rut)) > 0),
  constraint invoices_buyer_name_not_blank check (length(trim(buyer_name)) > 0)
);

create table if not exists public.invoice_items (
  item_id uuid primary key default gen_random_uuid(),

  invoice_id uuid not null references public.invoices(invoice_id),
  catalog_item_id uuid not null references public.item_catalog(catalog_item_id),
  invoice_line_number int not null,

  item_text text not null,
  description text,
  item_codes jsonb not null default '[]'::jsonb,
  meter_code text,

  quantity numeric,
  unit text,
  unit_price numeric,
  amount numeric,
  discount_pct numeric,
  discount_amount numeric,
  recargo_amount numeric,
  tax_exempt boolean not null default false,
  additional_tax_code text,

  model_version text not null,
  prediction_source text not null,

  predicted_categories_id uuid not null references public.categories(categories_id),
  predicted_code text not null,
  predicted_name text,

  top1_score numeric not null,
  margin numeric not null,
  entropy numeric not null,
  top3 jsonb not null default '[]'::jsonb,

  decision text not null,
  needs_review boolean generated always as (
    decision = 'review_required' and reviewed = false
  ) stored,
  reviewed boolean not null default false,

  final_categories_id uuid references public.categories(categories_id),
  final_code text,

  constraint invoice_items_invoice_line_unique unique (invoice_id, invoice_line_number),
  constraint invoice_items_line_number_positive check (invoice_line_number > 0),
  constraint invoice_items_item_text_not_blank check (length(trim(item_text)) > 0),
  constraint invoice_items_prediction_source_allowed check (
    prediction_source in ('model', 'product_lookup', 'meter_lookup')
  ),
  constraint invoice_items_decision_allowed check (
    decision in ('auto_accept', 'review_required')
  ),
  constraint invoice_items_top1_score_range check (
    top1_score >= 0 and top1_score <= 1
  ),
  constraint invoice_items_margin_range check (
    margin >= 0 and margin <= 1
  ),
  constraint invoice_items_entropy_nonnegative check (
    entropy >= 0
  ),
  constraint invoice_items_top3_is_array check (
    jsonb_typeof(top3) = 'array'
  ),
  constraint invoice_items_item_codes_is_array check (
    jsonb_typeof(item_codes) = 'array'
  )
);

create index if not exists companies_is_seller_idx
  on public.companies (is_seller)
  where is_seller = true;

create index if not exists companies_is_buyer_idx
  on public.companies (is_buyer)
  where is_buyer = true;

create index if not exists item_catalog_item_name_idx
  on public.item_catalog (item_name);

create index if not exists invoices_company_id_idx
  on public.invoices (company_id);

create index if not exists invoices_period_idx
  on public.invoices (invoice_period);

create index if not exists invoices_transaction_type_idx
  on public.invoices (transaction_type);

create index if not exists invoices_seller_rut_idx
  on public.invoices (seller_rut);

create index if not exists invoices_buyer_rut_idx
  on public.invoices (buyer_rut);

create index if not exists invoice_items_catalog_item_id_idx
  on public.invoice_items (catalog_item_id);

create index if not exists invoice_items_needs_review_idx
  on public.invoice_items (needs_review)
  where needs_review = true;

create index if not exists invoice_items_predicted_categories_id_idx
  on public.invoice_items (predicted_categories_id);

create index if not exists invoice_items_predicted_code_idx
  on public.invoice_items (predicted_code);

alter table public.categories enable row level security;
alter table public.companies enable row level security;
alter table public.item_catalog enable row level security;
alter table public.invoices enable row level security;
alter table public.invoice_items enable row level security;

grant select, insert, update, delete
on public.categories
to service_role;

grant select, insert, update, delete
on public.companies
to service_role;

grant select, insert, update, delete
on public.item_catalog
to service_role;

grant select, insert, update, delete
on public.invoices
to service_role;

grant select, insert, update, delete
on public.invoice_items
to service_role;
