# ADR 0001: Microkernel + Event Bus as the Core Architectural Pattern

- **Status**: Accepted
- **Date**: Phase 0

## Context

Fenomen 2 is a platform, not a fixed-feature application: voice
recognition, text-to-speech, memory, reasoning, a command system, a
plugin system, a web dashboard, multiple AI agents, and multi-node
support are all expected to be added over time, by independent effort,
without destabilizing what already exists.

Three patterns were considered:

1. **Layered monolith** (`services/`, `controllers/`, `models/`) — the
   default shape for most backend applications.
2. **Full microservices** (one process/container per capability) from
   day one.
3. **Microkernel with a central event bus**, where the kernel provides
   only cross-cutting infrastructure (event bus, module registry,
   config, lifecycle) and every capability is an independent module
   that talks to the rest of the system only through published events.

## Decision

Adopt the **microkernel + event bus** pattern.

- The kernel (`backend/kernel/`) knows nothing about any specific
  module. It only knows about `backend/contracts/` — the shared
  vocabulary (event schemas, the `Module` base class, error types).
- Modules never import each other's internals. A module that needs
  something from another module publishes/subscribes to events, or
  (in later phases) depends on a service interface declared in
  `contracts/` — never on `modules/other_module/...` directly.
- The event bus starts as a simple in-process `asyncio` publish/
  subscribe implementation (see ADR consequences below) but is used
  through a fixed interface (`subscribe` / `unsubscribe` / `publish`)
  everywhere in the codebase.

## Consequences

**Positive**

- New capabilities are added by writing a new module against a fixed
  contract, not by modifying existing code — directly serves the
  "every component independent" and "easy future expansion" goals.
- Multi-node support (a distant but explicit goal) becomes a
  *localized* change: swap the event bus's implementation for a
  networked one (e.g. Redis Pub/Sub, NATS) behind the same interface.
  No module code changes, because no module ever held a reference to
  "the in-process bus" — only to "something implementing
  subscribe/unsubscribe/publish."
- Multiple AI agents are simply multiple instances of the same module
  contract, coordinated by the bus rather than by direct calls to one
  another — no special-casing required.
- Modules are independently unit-testable: a module's `initialize()`
  can be called with a hand-constructed `ModuleContext` in a test,
  with no other module or kernel machinery involved.

**Negative / accepted trade-offs**

- Indirection: tracing "what happens when X occurs" requires knowing
  what's subscribed to the relevant event, rather than reading a
  direct function call chain. Mitigated by keeping event names/types
  explicit and documented per module (see `docs/modules/README.md`
  for the required documentation shape once modules exist).
- The in-process bus does not provide delivery guarantees (no
  persistence, no retry, no at-least-once semantics) — acceptable for
  Phase 0–7 (single process, single machine), and explicitly scoped
  to be revisited when a networked bus implementation is introduced in
  the multi-node phase.
- Slightly more upfront ceremony than direct function calls for a
  single, small feature. Accepted deliberately per project rule:
  "prefer scalable architecture over short code."

## Alternatives Rejected

- **Layered monolith**: resists "modules added independently over
  time" — features accumulate as edits to shared layers, and nothing
  stops modules from reaching into each other's internals over time.
- **Full microservices from day one**: pays deployment, service-
  discovery, and network-reliability costs before there is any real
  need for a distributed system. Revisit if/when the multi-node phase
  is actually reached.
