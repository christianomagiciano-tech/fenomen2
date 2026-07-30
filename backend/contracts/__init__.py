"""
Shared contracts (interfaces, DTOs, and errors) that every module and the
kernel depend on.

This package must never import from `backend.kernel`, `backend.modules`, or
`backend.plugins`. It defines the *vocabulary* the rest of the system speaks,
not any behaviour. Keeping it dependency-free in that direction is what lets
modules depend only on contracts (never on each other) and lets the kernel
depend only on contracts (never on any specific module).
"""
