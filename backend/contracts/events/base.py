"""
Base type for every event that travels across the Fenomen 2 event bus.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Event(BaseModel):
    """
    Base class for all events.

    Concrete events (e.g. `KernelStartedEvent`) subclass this and add
    whatever payload fields they need. The event bus dispatches purely on
    the Python type of the event instance, so two events with identical
    field shapes but different classes are treated as different event
    types — this is intentional and mirrors how the event vocabulary is
    meant to grow (one explicit class per meaning, not stringly-typed
    "kind" fields).

    Instances are immutable once created (`frozen=True`) — an event is a
    fact about something that already happened, and facts don't change
    after the fact.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=_utc_now)
    source: str = Field(
        description="Name of the module or kernel component that published this event."
    )
