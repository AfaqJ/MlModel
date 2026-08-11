# Beginner Backend Codebase Guide

This backend is a small FastAPI service. Its job is simple:

1. Receive invoice line item text.
2. Check if a client-known product rule matches.
3. If not, ask the ML model.
4. Return top category choices plus `auto_accept` or `review_required`.

## File Structure

```text
app/
  main.py
  api/
    routes.py
    schemas.py
  core/
    config.py
    model_loader.py
  inference/
    predictor.py
    onnx_encoder.py
    classifier.py
    confidence.py
    product_lookup.py
    normalize.py
  data/
    product_lookup.csv
```

## What Each File Does

- `app/main.py`: starts FastAPI, loads settings, loads the model once, connects routes.
- `app/api/schemas.py`: defines the JSON shape for requests and responses.
- `app/api/routes.py`: defines `/health`, `/model-info`, `/predict`, and `/predict-batch`.
- `app/core/config.py`: reads settings like `MODEL_DIR` and `MAX_BATCH_SIZE`.
- `app/core/model_loader.py`: loads model files, labels, thresholds, and lookup rules.
- `app/inference/onnx_encoder.py`: turns text into embeddings using ONNX Runtime.
- `app/inference/classifier.py`: loads the LogisticRegression head and returns probabilities.
- `app/inference/predictor.py`: connects lookup, encoder, classifier, and decision logic.
- `app/inference/confidence.py`: decides auto-accept vs review.
- `app/inference/product_lookup.py`: checks exact client-known product/service rules.
- `app/inference/normalize.py`: makes lookup text comparable by uppercasing, removing accents, and cleaning punctuation.

## The Prediction Flow

1. `routes.py` receives JSON from `/predict`.
2. `schemas.py` checks that fields like `item_text` are valid.
3. `predictor.py` asks `product_lookup.py` if the line is already known.
4. `predictor.py` builds text like `item_text | description | provider`.
5. `onnx_encoder.py` converts that text into an embedding.
6. `classifier.py` turns the embedding into category scores.
7. `confidence.py` decides whether to auto-accept or send to review.
8. `routes.py` sends the JSON response back.

## Beginner Glossary

- API: the backend's menu of actions.
- Endpoint: one API URL, like `/predict`.
- Request: the data sent into the backend.
- Response: the answer sent back.
- Schema: the expected shape of the data.
- Model: the trained ML files used for prediction.
- Stateless: the backend does not store invoice history; Supabase/frontend will store state.

## Why Stateless Is Good

The ML service should not be the system of record. It should answer one request at a time. If it restarts, it reloads the model and keeps working. This makes deployment, rollback, and scaling much simpler.

## Why Product Lookup Comes First

Some products are already defined by the client. If an exact known rule exists, we trust that rule before the model. The model still helps when there is no exact match.

## Why Weak Classes Go To Review

Some categories have very few training examples. Even if the model sounds confident, we should not trust those automatically yet. More human feedback can improve this later.
