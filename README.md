# MlModel Backend

FastAPI backend for the MCT-37 invoice line-item classifier.

## What is in this repo

- `app/` - FastAPI application code
- `requirements.txt` - production Python dependencies
- `Dockerfile` - container recipe
- `tests/` - backend smoke tests

## What is not in this repo

The trained model package is not committed because `model.onnx` is too large for normal GitHub.

Before building the Docker image, place the model package at:

```text
artifacts/v1.0.0/
```

## Run locally

```bash
python3.11 -m venv .venv-backend
.venv-backend/bin/pip install -r requirements.txt pytest httpx
.venv-backend/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```
