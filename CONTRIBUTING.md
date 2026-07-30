# Contributing to Fenomen 2

This is a long-term, single/small-team project. These conventions exist to
keep it that way as it grows.

## Rules (non-negotiable, per project agreement)

1. No quick hacks. Prefer scalable architecture over short code.
2. No placeholder code, no `TODO` implementations, no unfinished modules
   merged into `main`.
3. Every phase ends fully working, runnable, and tested before the next
   begins.
4. Significant architectural decisions get an ADR in
   `docs/architecture/decisions/` before implementation.
5. Every module gets a `README.md` per `docs/modules/README.md`'s template.

## Module Boundaries

- A module may import `backend.contracts` and the public interface of
  `backend.kernel`. It must never import another module's internals
  (`backend.modules.other_module.anything_internal`).
- Communication between modules happens through the event bus
  (`backend.contracts.events`), not direct calls.

## Before Opening a Change

- `bash scripts/lint.sh` and `bash scripts/test.sh` both pass.
- New behavior has tests. New modules have a `README.md`.
- If the change involves a non-obvious architectural choice, add or
  update an ADR.
