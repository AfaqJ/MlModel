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

Current: `mlmodel-00018-sll` (v1.4.1-int8, image `v1.4.1-names`, 100%, deployed
2026-09-16). Steps back: `mlmodel-00017-vg5` (the same v1.4.1 weights with the
stale name list), `mlmodel-00016-p8z` (v1.4.0), `mlmodel-00015-mjr` (v1.3.3),
and the v1.1.0 revisions.

**Check after:** hit `/artifact-check` on the service. It must report
`looks_like_lfs_pointer: false`, and `/model-info` must report the expected
`model_version`. Both v1.3.3-int8 and v1.4.0-int8 happen to be 278,181,947
bytes — same architecture, same quantisation — so size alone does **not**
identify the generation; read `model_version`.

## Roll back the database

`backups/supabase_20260812T070037Z/` is a full read-only export of all five
tables taken immediately before the v1.3.3 upload, via
`scripts/81_backup_supabase.py`. `backups/supabase_20260814T110447Z_pre_corrections/`
is the equivalent taken before the 2026-08-14 label corrections.
`backups/supabase_20260817T105217Z/` is the latest verified backup, taken before
the 2026-08-17 full payload re-load.

**There is no re-load path, by design.** The numbered uploaders were deleted on
2026-08-26 — each expected a database state that no longer exists. Recovery is a
restore from `backups/`; any forward fix is a scoped PostgREST write touching
only the rows it names, dry run first, and gated behind an explicit flag.

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
