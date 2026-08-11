"""Flow: GET /health  --  the lightweight 'are you alive?' check.

Smallest graph: it never touches the model. It only reads app.state.settings
and checks whether the model has been loaded yet.
"""
from __future__ import annotations

from _common import trace, fake_request
from app.api import routes

with trace("health"):
    result = routes.health(fake_request)

print("health ->", result)
