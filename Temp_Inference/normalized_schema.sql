create extension if not exists pgcrypto;

create table if not exists public.taxonomy_categories (
  taxonomy_id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null
);

create table if not exists public.invoices (
  invoice_id uuid primary key default gen_random_uuid(),

  invoice_folio text not null,
  document_type text not null,
  transaction_type text not null,

  seller_rut text not null,
  buyer_rut text not null,
  seller_name text,
  buyer_name text,

  invoice_date date not null,
  invoice_period text generated always as (
    (extract(year from invoice_date)::int)::text
    || '-'
    || lpad((extract(month from invoice_date)::int)::text, 2, '0')
  ) stored,

  constraint invoices_business_key unique (seller_rut, document_type, invoice_folio),
  constraint invoices_transaction_type_allowed check (transaction_type in ('COMPRAS', 'VENTAS')),
  constraint invoices_folio_not_blank check (length(trim(invoice_folio)) > 0),
  constraint invoices_document_type_not_blank check (length(trim(document_type)) > 0),
  constraint invoices_seller_rut_not_blank check (length(trim(seller_rut)) > 0),
  constraint invoices_buyer_rut_not_blank check (length(trim(buyer_rut)) > 0)
);

create table if not exists public.invoice_items (
  item_id uuid primary key default gen_random_uuid(),

  invoice_id uuid not null references public.invoices(invoice_id),
  invoice_line_number int not null,

  item_text text not null,
  description text,
  meter_code text,
  amount numeric,

  model_version text not null,
  prediction_source text not null,

  predicted_taxonomy_id uuid not null references public.taxonomy_categories(taxonomy_id),
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

  final_taxonomy_id uuid references public.taxonomy_categories(taxonomy_id),
  final_code text,

  constraint invoice_items_invoice_line_unique unique (invoice_id, invoice_line_number),
  constraint invoice_items_line_number_positive check (invoice_line_number > 0),
  constraint invoice_items_item_text_not_blank check (length(trim(item_text)) > 0),
  constraint invoice_items_prediction_source_allowed check (
    prediction_source in ('model', 'product_lookup', 'meter_lookup', 'business_rule')
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
  )
);

create index if not exists invoices_period_idx
  on public.invoices (invoice_period);

create index if not exists invoices_transaction_type_idx
  on public.invoices (transaction_type);

create index if not exists invoices_seller_rut_idx
  on public.invoices (seller_rut);

create index if not exists invoices_buyer_rut_idx
  on public.invoices (buyer_rut);

create index if not exists invoice_items_needs_review_idx
  on public.invoice_items (needs_review)
  where needs_review = true;

create index if not exists invoice_items_predicted_taxonomy_id_idx
  on public.invoice_items (predicted_taxonomy_id);

create index if not exists invoice_items_predicted_code_idx
  on public.invoice_items (predicted_code);

alter table public.taxonomy_categories enable row level security;
alter table public.invoices enable row level security;
alter table public.invoice_items enable row level security;

grant select, insert, update, delete
on public.taxonomy_categories
to service_role;

grant select, insert, update, delete
on public.invoices
to service_role;

grant select, insert, update, delete
on public.invoice_items
to service_role;
