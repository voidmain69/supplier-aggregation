"""Event specification: the metadata that ties a payload model to its transport.

Hand-written (not generated). ``registry.py`` — which *is* generated — builds an
``EVENT_REGISTRY`` of these, one per event schema, so producers and consumers can look
up the model class, Kafka topic and dataschema URI for a given event ``type``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EventSpec(BaseModel):
    """Binds an event ``type`` to its payload model and transport coordinates."""

    model_config = ConfigDict(frozen=True)

    event_type: str
    """Event type, e.g. ``supplier.offer.price-changed``."""

    model: type[BaseModel]
    """Pydantic model validating the CloudEvent ``data`` payload."""

    topic: str
    """Kafka topic the event is published to, e.g. ``sa.supplier.offer``."""

    dataschema: str
    """URI of the JSON Schema (``$id``) the payload validates against."""
