"""Flow: GET /artifact-check  --  inspects the model files on disk.

Still no model load. settings_dependency hands the route the Settings object,
then it stats each artifact file to confirm it exists and isn't a broken
Git-LFS pointer.
"""
from __future__ import annotations

from _common import trace, fake_request
from app.api import routes
from app.core import runtime

with trace("artifact_check"):
    settings = runtime.settings_dependency(fake_request)
    result = routes.artifact_check(settings=settings)

print("artifact_check -> model_dir:", result["model_dir"])
