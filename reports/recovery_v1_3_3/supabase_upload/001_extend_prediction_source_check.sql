-- Required before import: the pipeline records more provenance than the
-- original three values. Keeping the distinction is what allows a later
-- question of 'was this row proven by the client or decided by the model?'
alter table public.invoice_items
  drop constraint if exists invoice_items_prediction_source_allowed;

alter table public.invoice_items
  add constraint invoice_items_prediction_source_allowed
  check (prediction_source in ('business_rule', 'client_evidence_backfill', 'manually_audited_near_identical_backfill', 'meter_lookup', 'model', 'product_lookup', 'silver_audit_backfill'));
