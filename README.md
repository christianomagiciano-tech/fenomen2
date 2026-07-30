# Fenomen 2

A modular AI platform, built to grow over a long timeline rather than
ship as a fixed-feature product. See
[`docs/architecture/overview.md`](docs/architecture/overview.md) for the
full architecture, and
[`docs/architecture/decisions/`](docs/architecture/decisions/) for the
reasoning behind major design choices.

## Current Status: Phase 0 — Foundations ✅ Complete

The kernel is implemented and fully verified on both Linux and Windows
11: event bus, module registry, config manager, structured logging, and
lifecycle orchestration (ordered startup, graceful shutdown — including
cross-platform signal handling, see
[ADR 0002](docs/architecture/decisions/0002-cross-platform-shutdown-signals.md)
— and health reporting). 46/46 tests passing. Zero product modules exist
yet — see the roadmap below. Full results:
[`docs/phase-summaries/phase-0.md`](docs/phase-summaries/phase-0.md).

## Quick Start

**Linux / macOS:**
```bash
bash scripts/bootstrap.sh
source .venv/bin/activate
bash scripts/test.sh
python -m backend.app   # Ctrl+C to stop gracefully
```

**Windows (PowerShell):**
```powershell
.\scripts\bootstrap.ps1
.\.venv\Scripts\Activate.ps1
.\scripts\test.ps1
python -m backend.app   # Ctrl+C to stop gracefully
```

Full instructions: [`docs/setup.md`](docs/setup.md).

## Technology Stack

- Python 3.12 (backend)
- Angular (frontend — from Phase 4)
- Linux (primary deployment target), Windows 11 supported for development

## Project Rules

1. No quick hacks — scalable architecture over short code.
2. Every important design decision is explained (see `docs/architecture/decisions/`).
3. Clean code, kept organized.
4. Every phase ends fully working, runnable, and tested — no placeholders, no unfinished modules.

## Roadmap

| Phase | Deliverable |
|---|---|
| 0 | Kernel foundations (this phase) |
| 1 | Command system + CLI interface |
| 2 | Memory module |
| 3 | AI reasoning module |
| 4 | Local server (FastAPI) + Angular web dashboard |
| 5 | Voice recognition + text-to-speech |
| 6 | Generalized plugin system (dynamic discovery) |
| 7 | Multiple AI agents |
| 8 | Multi-node support |

## Repository Layout

See [`docs/architecture/overview.md`](docs/architecture/overview.md#repository-layout).
