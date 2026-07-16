FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MODEL_DIR=/srv/artifacts/v1.1.0
ENV TRANSFORMERS_VERBOSITY=error

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY artifacts/v1.1.0/ artifacts/v1.1.0/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
