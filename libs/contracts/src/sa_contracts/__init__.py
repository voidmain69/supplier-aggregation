"""sa_contracts — the platform's typed event contracts.

The JSON Schemas in ``contracts/events/*.json`` are the source of truth; the payload
models here are generated from them by ``tools/gen_contracts.py`` (``make contracts``).
:data:`EVENT_REGISTRY` binds each event ``type`` to its model, Kafka topic and
dataschema URI so producers and consumers share one lookup.
"""

from __future__ import annotations

from sa_contracts.registry import EVENT_REGISTRY
from sa_contracts.spec import EventSpec


def spec_for(event_type: str) -> EventSpec:
    """Return the :class:`EventSpec` for an event ``type``.

    Raises :class:`KeyError` if the type is not registered — callers should treat an
    unknown type as a contract violation, not silently ignore it.
    """
    return EVENT_REGISTRY[event_type]


__all__ = ["EVENT_REGISTRY", "EventSpec", "spec_for"]
