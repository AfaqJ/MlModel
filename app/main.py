from __future__ import annotations

import logging
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.model_loader import ModelBundle
from app.inference.predictor import Predictor


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(title="MCT-37 Invoice Classifier", version=settings.service_version)
    app.state.settings = settings
    app.state.bundle = ModelBundle(settings.model_dir, settings.product_lookup_path)
    app.state.predictor = Predictor(app.state.bundle, shadow_mode=settings.shadow_mode)
    app.include_router(router)
    return app


app = create_app()
