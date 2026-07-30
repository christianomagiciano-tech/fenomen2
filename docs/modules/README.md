# Module Documentation Convention

No product modules exist yet (Phase 0 ships zero — see
`docs/architecture/overview.md`). Starting Phase 1, every module added
under `backend/modules/<module_name>/` must include a `README.md` in that
same folder, following this template:

```markdown
# <Module Name>

## Purpose
One paragraph: what this module does and why it exists.

## Events Published
- `EventClassName` — when it's published, and what the payload means.

## Events Subscribed
- `EventClassName` — what the module does in response.

## Configuration
The module's config schema (from `config_schema.py`), and what each field
controls. Reference, don't duplicate — link to the schema file.

## Dependencies
Anything this module depends on beyond `backend.contracts` and the kernel
(e.g. an external service, a Python package not already in `pyproject.toml`).

## Design Notes
Anything non-obvious about how the module is built, and why — mirrors the
"explain important design decisions" project rule at module scope.
```

This keeps every module's event contract discoverable without reading its
implementation, which matters once several modules are reacting to the
same event stream.
