-- Required before script 82 uploads the 2026-08-18 hardware dispersal.
-- `manual_recategorisation` is a row we moved on our own reasoning about what
-- the object is -- a brucellosis test is not building maintenance -- as opposed
-- to `business_rule`, which means the client's own convention decided it. Every
-- such row stays `review_required`; the distinction is what keeps "the client
-- proved this" separable from "we reasoned about it".
alter table public.invoice_items
  drop constraint if exists invoice_items_prediction_source_allowed;

alter table public.invoice_items
  add constraint invoice_items_prediction_source_allowed
  check (prediction_source in ('business_rule', 'client_evidence_backfill',
    'manually_audited_near_identical_backfill', 'manual_recategorisation',
    'meter_lookup', 'model', 'product_lookup', 'silver_audit_backfill'));
