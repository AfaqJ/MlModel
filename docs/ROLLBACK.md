# ROLLBACK — how to undo each step

Production now holds real state in two places: the Cloud Run service and the
Supabase database. Both need a written way back.

## Ground truth that cannot be lost

If everything else burns, the project is recoverable from these. No script in
normal operation modifies them:

```
Data/Raw_Data/                              raw XML, read-only
Data/candidates/recovery_v1_3_2/            the gold v1.3.3 trained on
backups/supabase_20260812T070037Z/          pre-upload export, all 5 tables
backups/supabase_20260814T110447Z_pre_corrections/  pre-correction export, all 5 tables
backups/supabase_20260817T105217Z/          pre-2026-08-17 full re-load, all 5 tables
```

## Roll back the deployed model

Cloud Run keeps every revision. Traffic-shifting is instant and needs no
rebuild:

```bash
gcloud run revisions list --service mlmodel --region europe-west1
```

```bash
gcloud run services update-traffic mlmodel --region europe-west1 --to-revisions <REVISION>=100
```

Current: `mlmodel-00014-lrp` (v1.3.3-int8, 100%). The v1.1.0 revisions are still
present, so a rollback to the pre-recovery generation is available.

**Check after:** hit `/artifact-check` on the service. It must report
`model.onnx = 278,181,947 bytes` and `looks_like_lfs_pointer: false` for
v1.3.3-int8. A different size means a different generation is live.

## Roll back the database

`backups/supabase_20260812T070037Z/` is a full read-only export of all five
tables taken immediately before the v1.3.3 upload, via
`scripts/81_backup_supabase.py`. `backups/supabase_20260814T110447Z_pre_corrections/`
is the equivalent taken before the 2026-08-14 label corrections.
`backups/supabase_20260817T105217Z/` is the latest verified backup, taken before
the 2026-08-17 full payload re-load.

**To re-load after the first upload has landed,** use
`scripts/82_apply_label_corrections.py`, not script 80. Script 80 is the
first-load path and its pre-flight refuses once v1.3.3 is live — correctly, since
it expects pre-upload row counts. Script 82 pushes whole rows and deletes live
rows the payload no longer contains. Dry run by default; writing needs both
`--execute` and `--i-have-backed-up-the-database`.

**There was no transaction around the upload,** and there cannot be — PostgREST
cannot wrap five tables in one. Restoring means re-loading from the backup, not
rolling back. Take a fresh backup first, or you lose any client review work done
since.

Three things compensate for the missing transaction, and they are why a failed
upload leaves a valid database rather than a corrupt one:

1. **Ordering** — dependencies land before dependants, so a failure leaves the
   database merely partially updated.
2. **Abort on first mismatch** — every stage verifies its own count.
3. **Idempotence** — every write is an upsert on a business key, or a delete of
   an already-identified row.

Stage 7 (the catalog prune) re-queries live rather than trusting the pre-flight,
because it is the only destructive step whose safety depends on stage 6 having
completed.

**The backup is a logical row export, not a `pg_dump`.** It restores data — not
schema, indexes, or policies. The widened `prediction_source` CHECK constraint
would *not* come back from it. That constraint must allow: `model`,
`product_lookup`, `meter_lookup`, `business_rule`, `client_evidence_backfill`,
`silver_audit_backfill`, `manually_audited_near_identical_backfill`.

## Roll back an artifact

Artifacts are gitignored and fully reproducible from the exporter, so there is
nothing to restore — rebuild:

```bash
.venv-train/bin/python training/export_recovery_onnx.py --gold Data/candidates/recovery_v1_3_2/master_gold.csv --split Data/candidates/recovery_v1_3_2/split_seed42.csv
```

`artifacts/v1.0.0/` and `artifacts/v1.1.0/` are protected paths — never
overwritten, so no rollback is needed for them.

## Roll back a training run

Training writes to a new `models/<name>/` directory. Nothing is overwritten, so
rolling back means pointing `app/core/config.py` at the previous artifact and
redeploying. `models/setfit_base/` (the base encoder) is a protected path in the
trainer and is never touched.
