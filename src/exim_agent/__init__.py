"""EXIM Agent package."""

from __future__ import annotations

import sys
from types import ModuleType


def _ensure_supabase_http_clients() -> None:
    """Shim missing supabase_auth.http_clients module when upstream omits it."""
    try:
        import supabase_auth  # type: ignore
    except Exception:
        return

    module_name = "supabase_auth.http_clients"
    if getattr(supabase_auth, "http_clients", None) or module_name in sys.modules:
        return

    try:
        import httpx  # type: ignore
    except Exception:
        return

    shim = ModuleType(module_name)
    shim.AsyncClient = httpx.AsyncClient  # type: ignore[attr-defined]
    shim.SyncClient = httpx.Client  # type: ignore[attr-defined]

    sys.modules[module_name] = shim
    setattr(supabase_auth, "http_clients", shim)


_ensure_supabase_http_clients()

__all__ = []
