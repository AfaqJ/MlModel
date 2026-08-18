-- Read-only pre-flight. Safe to run at any time; changes nothing.
-- Equivalent to scripts/79_supabase_preflight.py, for the SQL editor.
-- Run BEFORE the loader. Every row of the result should read 'PASS'.

with expected(table_name, n) as (
  values ('categories', 71), ('companies', 460), ('item_catalog', 5579),
         ('invoices', 5157), ('invoice_items', 12071)
),
actual(table_name, n) as (
  select 'categories', count(*) from public.categories
  union all select 'companies', count(*) from public.companies
  union all select 'item_catalog', count(*) from public.item_catalog
  union all select 'invoices', count(*) from public.invoices
  union all select 'invoice_items', count(*) from public.invoice_items
)
select
  'live row counts' as check_name,
  a.table_name,
  a.n as found,
  e.n as expected,
  case when a.n = e.n then 'PASS' else 'FAIL - data changed since the payload was built' end as status
from actual a join expected e using (table_name)
order by a.table_name;

-- The payload carries real categories_id UUIDs baked in at build time. If the
-- taxonomy has been reloaded since, those FKs are stale and the payload must be
-- regenerated.
select
  'category codes' as check_name,
  count(*) as live_codes,
  71 as expected,
  case when count(*) = 71 then 'PASS' else 'FAIL' end as status
from public.categories;

-- Current review-state contract, for comparison after the import.
select
  'review state (before)' as check_name,
  count(*) filter (where final_code is not null) as final_code_set,
  count(*) filter (where needs_review) as needs_review_true,
  count(*) filter (where reviewed) as reviewed_true,
  count(*) filter (where final_code is null and final_categories_id is not null) as broken_pairs,
  case when count(*) filter (where final_code is null and final_categories_id is not null) = 0
       then 'PASS' else 'FAIL' end as status
from public.invoice_items;

-- predicted_categories_id must agree with predicted_code. Live is currently
-- clean; the import must keep it that way.
select
  'predicted_categories_id agrees with predicted_code' as check_name,
  count(*) as mismatched,
  case when count(*) = 0 then 'PASS' else 'FAIL' end as status
from public.invoice_items i
join public.categories c on c.categories_id = i.predicted_categories_id
where c.code is distinct from i.predicted_code;

-- Sales direction, the original incident. Should stay at zero.
select
  'direction safety' as check_name,
  count(*) filter (where v.transaction_type = 'VENTAS'
                     and i.decision = 'auto_accept'
                     and i.predicted_code not like 'ING-%') as ventas_on_expense_code,
  count(*) filter (where v.transaction_type = 'COMPRAS'
                     and i.decision = 'auto_accept'
                     and i.predicted_code like 'ING-%') as compras_on_income_code,
  case when count(*) filter (where (v.transaction_type = 'VENTAS'
                                      and i.decision = 'auto_accept'
                                      and i.predicted_code not like 'ING-%')
                                or (v.transaction_type = 'COMPRAS'
                                      and i.decision = 'auto_accept'
                                      and i.predicted_code like 'ING-%')) = 0
       then 'PASS' else 'FAIL' end as status
from public.invoice_items i
join public.invoices v on v.invoice_id = i.invoice_id;

-- Catalog rows nothing points at. 225 before the import; 0 after the prune.
select
  'orphan catalog rows' as check_name,
  count(*) as orphans
from public.item_catalog c
where not exists (
  select 1 from public.invoice_items i where i.catalog_item_id = c.catalog_item_id
);
