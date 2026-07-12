"""Request-scoped dependencies for the gateway API."""

from __future__ import annotations

from fastapi import Request

from api_gateway.adapters.downstream import Downstream


def get_downstream(request: Request) -> Downstream:
    """Return the shared downstream HTTP client (built in the app lifespan)."""
    downstream: Downstream = request.app.state.downstream
    return downstream
