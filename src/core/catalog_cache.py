"""
Catalog TTL Cache

Lightweight process-level cache for Instana catalog API responses (metrics,
tags, plugins).  Catalog data is stable within a tenant — it changes only when
new integrations are deployed — so caching eliminates repeated round-trips that
happen on every LLM analyze workflow.

Cache store structure:
    { cache_key: (expires_at_monotonic, value) }

Cache keys always include ``base_url`` so different Instana tenants are fully
isolated from one another in a multi-tenant process.

Default TTL: 1800 s (30 minutes) for all catalog types.

Configuration
-------------
**stdio mode** (local / .bob/mcp.json):
    Cache settings are read from environment variables once at process startup.
    To change them, update the env block in .bob/mcp.json and let Bob restart
    the server — no hot-reload is needed since the server always reboots anyway.

    INSTANA_CACHE_ENABLED  — "false" / "0" / "no"  to disable (default: "true")
    INSTANA_CACHE_TTL      — integer seconds         (default: 1800)

**streamable-http mode** (internal / production):
    The same env vars set the process-level defaults at startup.  In addition,
    every individual request can override them via HTTP headers — consistent
    with how instana-base-url / instana-api-token already work:

    instana-cache-enabled  — "false" / "0" / "no"  to disable for this request
    instana-cache-ttl      — integer seconds for this request

    Per-request headers take precedence over the process defaults, so you can
    flip caching on or off on the very next request without any restart.
"""

import functools
import logging
import os
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults & process-level config (set once at startup from env vars)
# ---------------------------------------------------------------------------

DEFAULT_CATALOG_TTL: int = 1800  # 30 minutes

# Process-level defaults — read from env vars at import time.
# In stdio mode these are the only values used.
# In http mode they serve as fallback when no per-request header is supplied.
def _parse_enabled(raw: str) -> bool:
    return raw.strip().lower() not in ("false", "0", "no")


def _parse_ttl(raw: str, fallback: int) -> int:
    try:
        return max(0, int(raw.strip()))
    except (ValueError, TypeError):
        logger.warning(
            "Invalid TTL value '%s' — using %ds", raw, fallback
        )
        return fallback


_process_cache_enabled: bool = _parse_enabled(
    os.getenv("INSTANA_CACHE_ENABLED", "true")
)
_process_cache_ttl: int = _parse_ttl(
    os.getenv("INSTANA_CACHE_TTL", ""),
    DEFAULT_CATALOG_TTL,
) if os.getenv("INSTANA_CACHE_TTL", "").strip() else DEFAULT_CATALOG_TTL

logger.debug(
    "Catalog cache process defaults: enabled=%s, ttl=%ds",
    _process_cache_enabled, _process_cache_ttl,
)


# ---------------------------------------------------------------------------
# Per-request header resolution (http mode only)
# ---------------------------------------------------------------------------

def _resolve_request_overrides() -> Tuple[bool, int]:
    """Read instana-cache-* headers from the current HTTP request, if any.

    Returns:
        (enabled, ttl) — the per-request values when running in streamable-http
        mode, or the process-level defaults when headers are absent / in stdio mode.
    """
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers()
    except (ImportError, AttributeError, RuntimeError):
        # Not in an HTTP request context (stdio mode or called outside a request)
        return _process_cache_enabled, _process_cache_ttl

    enabled = _process_cache_enabled
    ttl = _process_cache_ttl

    raw_enabled = headers.get("instana-cache-enabled", "").strip()
    if raw_enabled:
        enabled = _parse_enabled(raw_enabled)
        logger.debug(
            "Cache config: instana-cache-enabled header='%s' → enabled=%s",
            raw_enabled, enabled,
        )

    raw_ttl = headers.get("instana-cache-ttl", "").strip()
    if raw_ttl:
        ttl = _parse_ttl(raw_ttl, _process_cache_ttl)
        logger.debug(
            "Cache config: instana-cache-ttl header='%s' → ttl=%ds",
            raw_ttl, ttl,
        )

    return enabled, ttl


# ---------------------------------------------------------------------------
# Internal store
# ---------------------------------------------------------------------------

_CATALOG_CACHE: Dict[str, Tuple[float, Any]] = {}
_CACHE_MISS = object()  # sentinel — distinguishable from None / {} / []


def _cache_get(key: str) -> Any:
    """Return the cached value for *key*, or ``_CACHE_MISS`` if absent/expired."""
    entry = _CATALOG_CACHE.get(key)
    if entry is None:
        return _CACHE_MISS
    expires_at, value = entry
    if time.monotonic() > expires_at:
        del _CATALOG_CACHE[key]
        return _CACHE_MISS
    return value


def _cache_set(key: str, value: Any, ttl: int) -> None:
    """Store *value* under *key* with a TTL of *ttl* seconds."""
    _CATALOG_CACHE[key] = (time.monotonic() + ttl, value)


def clear_cache() -> None:
    """Remove all entries from the catalog cache.

    Intended for use in tests to prevent cross-test cache pollution.
    """
    _CATALOG_CACHE.clear()


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------

def ttl_cached(ttl: Optional[int] = None, key_args: Tuple[str, ...] = ()):
    """Cache the return value of a catalog method.

    Must be applied **outside** ``@with_header_auth`` so the cache check runs
    before any auth/SDK setup.  Error responses (dicts containing an
    ``"error"`` key) are never cached so a transient network failure cannot
    poison the store.

    On every call the decorator:
      1. Resolves the effective ``enabled`` and ``ttl`` for this call:
           - In **http mode**: checks ``instana-cache-enabled`` /
             ``instana-cache-ttl`` request headers; falls back to process defaults.
           - In **stdio mode**: uses the process-level env-var defaults directly.
      2. Logs at DEBUG the current cache state (enabled/disabled, effective TTL).
      3. Returns the cached value on a HIT, calls through on a MISS or BYPASS.

    Args:
        ttl:      Seconds to keep the cached result.  ``None`` (default) defers
                  to the process-level default (1800 s) or the per-request header,
                  both resolved at call time.  Pass an explicit value only when a
                  specific method needs a different TTL regardless of config.
        key_args: Names of keyword arguments — beyond ``self.base_url`` — that
                  make cache entries distinct for the same method.
                  Example: ``("beacon_type", "use_case")`` for tag-catalog calls.

    Example::

        @ttl_cached(key_args=("plugin",))
        @with_header_auth(InfrastructureCatalogApi)
        async def get_infrastructure_catalog_metrics(self, plugin, ...):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            # Step 1 — resolve enabled + ttl for this call
            cache_enabled, effective_ttl = _resolve_request_overrides()

            # Explicit ttl= on the decorator always wins over dynamic config
            if ttl is not None:
                effective_ttl = ttl

            # Step 2 — debug log: current state for this call
            logger.debug(
                "ttl_cached [%s] caching=%s ttl=%ds",
                fn.__name__,
                "ENABLED" if cache_enabled else "DISABLED",
                effective_ttl,
            )

            # Step 3 — bypass entirely when caching is disabled
            if not cache_enabled:
                logger.debug(
                    "ttl_cached BYPASS (caching disabled) fn=%s", fn.__name__
                )
                return await fn(self, *args, **kwargs)

            # Step 4 — build cache key
            base_url = getattr(self, "base_url", "")
            key_parts = [base_url, fn.__name__]
            for arg_name in key_args:
                key_parts.append(str(kwargs.get(arg_name, "")))
            cache_key = "|".join(key_parts)

            # Step 5 — check store
            cached = _cache_get(cache_key)
            if cached is not _CACHE_MISS:
                logger.debug("ttl_cached HIT  key=%s", cache_key)
                return cached

            logger.debug("ttl_cached MISS key=%s", cache_key)
            result = await fn(self, *args, **kwargs)

            # Never cache error responses — transient failures must not persist
            if not (isinstance(result, dict) and "error" in result):
                _cache_set(cache_key, result, effective_ttl)

            return result
        return wrapper
    return decorator
