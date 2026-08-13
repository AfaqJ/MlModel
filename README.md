# MCT-37 — invoice line-item classifier

FastAPI + ONNX service that classifies Spanish invoice line items into
accounting categories for Antillanca.

**Start at [`CLAUDE.md`](CLAUDE.md)** — it is the front door for this repo, for
humans and agents alike. Current state and recent work live in
[`docs/STATE.md`](docs/STATE.md).

## What is in this repo

- `app/` — FastAPI application and the inference cascade
- `training/` — SetFit training and ONNX export (needs `.venv-train`)
- `scripts/` — the offline labeling and Supabase upload pipeline
- `Data/` — raw XML through to gold training data
- `docs/` — project context; all of it current, nothing archived
- `tests/` — 98 tests, all must pass

## What is not in this repo

Trained artifacts are gitignored — `model.onnx` is 278 MB, too large for normal
git, and shipping it through git is what once turned it into an LFS pointer.
They are fully reproducible from `training/export_recovery_onnx.py`.

The deployed package is `artifacts/v1.3.3-int8/`. `app/core/config.py` points at
it. Build it before building the Docker image.

## Run locally

```bash
python3.11 -m venv .venv-backend
```

```bash
.venv-backend/bin/pip install -r requirements.txt pytest httpx
```

```bash
.venv-backend/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check — note the model loads lazily, so `model_loaded` is `false` until
the first prediction:

```bash
curl http://127.0.0.1:8000/health
```

`.venv-train` has PyTorch; `.venv-backend` deliberately does not. PyTorch must
never reach the production container.
