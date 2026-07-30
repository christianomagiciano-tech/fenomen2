"""
The Fenomen 2 microkernel.

The kernel provides the four services every module and interface can rely
on: the event bus, the module registry, the config manager, and structured
logging — plus the `Kernel` class that ties them together and orchestrates
startup/shutdown. The kernel must never import from `backend.modules` or
`backend.plugins`; it only knows about `backend.contracts`.
"""
