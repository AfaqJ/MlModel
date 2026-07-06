from __future__ import annotations

from threading import RLock
from fastapi import FastAPI

from app.core.model_loader import ModelBundle
from app.inference.predictor import Predictor


def init_runtime_state(app: FastAPI) -> None:
    app.state.bundle = None
    app.state.predictor = None
    app.state.model_lock = RLock()


def get_bundle(app: FastAPI) -> ModelBundle:
    if app.state.bundle is None:
        with app.state.model_lock:
            if app.state.bundle is None:
                settings = app.state.settings
                app.state.bundle = ModelBundle(settings.model_dir, settings.product_lookup_path)
    return app.state.bundle


def get_predictor(app: FastAPI) -> Predictor:
    if app.state.predictor is None:
        with app.state.model_lock:
            if app.state.predictor is None:
                bundle = get_bundle(app)
                app.state.predictor = Predictor(bundle, shadow_mode=app.state.settings.shadow_mode)
    return app.state.predictor
