# Setup & Usage

## Requirements

- Python 3.12+
- Linux (primary target) or Windows 11 (development)

## First-time setup

**Linux / macOS:**
```bash
bash scripts/bootstrap.sh
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.\scripts\bootstrap.ps1
.\.venv\Scripts\Activate.ps1
```

This creates a virtual environment at `.venv/` and installs the project
in editable mode along with its dev dependencies (`pytest`,
`pytest-asyncio`, `ruff`).

## Running the test suite

**Linux / macOS:**
```bash
bash scripts/test.sh          # all tests
bash scripts/test.sh -v       # verbose
bash scripts/test.sh -k event_bus   # only event-bus tests
```

**Windows (PowerShell):**
```powershell
.\scripts\test.ps1
.\scripts\test.ps1 -v
.\scripts\test.ps1 -k event_bus
```

Equivalent directly on any platform: `pytest` from the repository root
(with the venv active).

## Running the application

```bash
python -m backend.app
```

Phase 0 boots the kernel with zero registered modules and waits. Stop it
with `Ctrl+C` (SIGINT) or `SIGTERM` on Linux/macOS — `Ctrl+C` or
`Ctrl+Break` on Windows. All of these trigger the kernel's graceful
shutdown sequence (see `docs/architecture/overview.md` and
`docs/architecture/decisions/0002-cross-platform-shutdown-signals.md`
for how this works cross-platform). You should see log lines for the
full startup and shutdown sequence, e.g.:

```
... | INFO | fenomen.kernel | Kernel starting (0 module(s) registered)
... | INFO | fenomen.kernel | Kernel running.
^C
... | INFO | fenomen.kernel | Kernel stopping.
... | INFO | fenomen.kernel | Kernel stopped.
```

## Linting

**Linux / macOS:** `bash scripts/lint.sh`
**Windows:** `.\scripts\lint.ps1`

## Configuration

Edit `config/default.yaml`. The `kernel:` section controls log level,
log format (`console` or `json`), and graceful-shutdown timeout. Each
module (starting Phase 1) will have its own top-level section, named
after that module.
