"""Shared helper for every trace script.

`pycallgraph` is a *dynamic* tracer: it watches your code AS IT RUNS (via
sys.settrace) and records every function call, who called it, and how long it
took. Big catch: it only sees the ONE thread it started in.

FastAPI runs sync endpoints in a worker thread, so tracing through an HTTP
client shows nothing. Instead we call the real route functions and dependency
functions directly, in the main thread. To do that we hand them a tiny fake
`request` -- our dependencies only ever read `request.app.state`, so a stand-in
object with an `.app` attribute is enough. Same code path, one thread, fully
recorded.
"""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from pycallgraph import PyCallGraph, Config, GlobbingFilter
from pycallgraph.output import GraphvizOutput

from app.main import app  # this is create_app() already run -- boots empty (no model)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# The fake request. Route functions and dependencies only touch request.app.state,
# so this is all they need.
fake_request = SimpleNamespace(app=app)


def trace(name: str) -> PyCallGraph:
    config = Config()
    # Only draw OUR code (app.*). Without this the graph is a hairball of numpy /
    # onnxruntime / pydantic internals.
    config.trace_filter = GlobbingFilter(
        include=["app.*"],
        exclude=["pycallgraph.*"],
    )
    output = GraphvizOutput(
        output_file=str(OUTPUT_DIR / f"{name}.png"),
        output_type="png",
    )
    return PyCallGraph(output=output, config=config)
