from __future__ import annotations

import logging
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.runtime import init_runtime_state


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app = FastAPI(title="MCT-37 Invoice Classifier", version=settings.service_version)
    app.state.settings = settings
    init_runtime_state(app)
    app.include_router(router)
    return app


app = create_app()
