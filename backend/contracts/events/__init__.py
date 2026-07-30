"""
Typed event definitions.

Every event that can travel across the event bus is a Pydantic model
defined here (or, for module-specific events, in that module's own
`events.py` — see `docs/modules/README.md` once modules exist). Events are
looked up by their Python *class*, not by a string topic name, so
`from backend.contracts.events.kernel import KernelStartedEvent` is how a
module discovers what it can subscribe to — no magic strings.
"""
