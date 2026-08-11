# call_graphs — visualize every endpoint's real flow

These scripts fire a real request at each endpoint and let `pycallgraph` record
the actual chain of function calls, then draw it as a PNG. This is *dynamic*
analysis: only code that actually runs shows up, so the graphs are the truth,
not a guess.

## One-time setup

```bash
brew install graphviz                              # the 'dot' drawing engine
.venv-backend/bin/pip install python-call-graph    # the tracer (imports as 'pycallgraph')
```

## Generate all graphs

```bash
# from the repo root
.venv-backend/bin/python call_graphs/run_all.py
```

PNGs land in `call_graphs/output/`. Open them to see, for each endpoint, who
calls whom and how long each function took.

## Run just one flow

```bash
cd call_graphs
../.venv-backend/bin/python trace_predict.py
```

## What each script shows

| Script | Endpoint | What the graph reveals |
|---|---|---|
| `trace_health.py` | GET /health | tiniest flow, model never loads |
| `trace_artifact_check.py` | GET /artifact-check | reads model files on disk via the settings dependency |
| `trace_model_info.py` | GET /model-info | the one-time model BUILD chain (encoder + head + lookup) |
| `trace_predict.py` | POST /predict | the full predict pipeline (lookup -> embed -> classify -> decide) |
| `trace_predict_batch.py` | POST /predict-batch | the batch loop calling predict once per item |

`predict` and `predict_batch` warm the model up *before* tracing, so their
graphs show the prediction path only, not the load. `model_info` is where you go
to see the load itself.
