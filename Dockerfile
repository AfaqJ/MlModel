FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MODEL_DIR=/srv/artifacts/v1.4.1-int8
ENV TRANSFORMERS_VERBOSITY=error

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY artifacts/v1.4.1-int8/ artifacts/v1.4.1-int8/

# Shell form so Cloud Run's injected $PORT is honoured; 8080 is the local default.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
