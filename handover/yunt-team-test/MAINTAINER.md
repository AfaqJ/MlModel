# Handover controls

The original 23-table row snapshot, sample identifiers, source XML hashes and
current detached/restored status are local under
`backups/yunt_team_handover_20260913/`. Never share these whole-table backups as
the team attachment. Share only QUICK_START.html, the original invoice ZIP and
REFERENCE.md (and use TEAMS_MESSAGE.md as the accompanying text).

**2026-09-15: live was restored to baseline.** The five sample invoices / twelve
lines are back and the 09-14 repeat-purchase test rows were removed (backup and
script: `backups/pre_baseline_restore_20260915/`). The `restore` command below
will now refuse — there is nothing left to restore. The ZIP is no longer unseen;
a new team test needs a fresh detach.

Baseline: 5,195 invoices / 11,746 lines. Handover: 5,190 / 11,734. All other
tracked rows are identical to the new full snapshot. Removing five complete
documents is required: removing only their lines would still deduplicate the
invoice headers. Catalog identities and remaining precedent lines are preserved.

The new snapshot's five core tables also match the older independent backup
`backups/supabase_20260911T074329Z/` field for field: zero added, removed or
changed rows. Exact restore was executed and verified, followed by final detach.
The actual TypeScript XML parser read the shared ZIP and confirmed all five
identities, twelve line numbers and stored amounts without a model call.

Before anyone tests, exact restoration is:

    .venv-backend/bin/python scripts/91_yunt_team_sample.py restore
    .venv-backend/bin/python scripts/91_yunt_team_sample.py restore --apply

This fails closed if any tracked data changed. Once the team starts, inspect
the new batch and request/order identities and plan cleanup from those exact
records. Do not run `90_yunt_live_test_undo.py --apply`: its broad historical
anchors assumed that every Yunt purchase was a test. Do not overwrite either
saved baseline. Ingestion creates new invoice/line IDs and predictions, so
matching counts alone after reimport does not prove original values restored.

The team email permission is additive: `YUNT_ADDITIONAL_ALLOWED_ADDRESSES`
contains `cristian.anguita@gmail.com,@mctechstudio.com` in Vercel Preview.
`YUNT_ALLOWED_ADDRESSES` is preserved. Both gates use their combined entries.
Exact-domain matching excludes subdomains, lookalike suffixes and unrelated Gmail
users. A signed Resend webhook proves webhook origin; this task does not add
DMARC-based sender identity enforcement or dashboard accounts.

Preview commit `a16fc51` is Ready on
`https://milk-company-git-yunt-mountain-creative.vercel.app`; the enabled Resend
webhook points at that alias's `/api/yunt/inbound`. No fresh live email from the
newly allowed senders was sent during preparation. The HTML guide's local links
were verified; visual browser QA was blocked by browser URL policy.

The ZIP is one shared ingestion exercise. Coordinate one sender; do not spend
paid model turns repeatedly resending it expecting new findings. No paid model
call is needed to prepare this handover.
