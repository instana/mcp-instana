"""
Unit tests for src/core/catalog_cache.py

Covers:
  - _cache_get / _cache_set  : store, hit, miss, expiry, sentinel identity
  - clear_cache               : full store wipe
  - ttl_cached decorator      : cache hit, cache miss, error not cached,
                                key isolation by base_url / method / key_args,
                                functools.wraps preservation, no-key_args path,
                                zero-TTL immediate expiry
"""

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.core.catalog_cache import (
    _CACHE_MISS,
    _CATALOG_CACHE,
    _cache_get,
    _cache_set,
    clear_cache,
    ttl_cached,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client(base_url: str = "https://tenant.instana.io"):
    """Return a minimal object that looks like a catalog client."""
    obj = MagicMock()
    obj.base_url = base_url
    return obj


async def _identity(self, *args, **kwargs):
    """Async function that returns whatever keyword arg 'result' is set to."""
    return kwargs.get("result", {"data": "fresh"})


# ---------------------------------------------------------------------------
# _cache_get / _cache_set
# ---------------------------------------------------------------------------

class TestCacheGetSet(unittest.TestCase):

    def setUp(self):
        clear_cache()

    # -- set then get --

    def test_set_and_get_returns_value(self):
        _cache_set("k1", {"metrics": ["cpu"]}, ttl=60)
        result = _cache_get("k1")
        self.assertEqual(result, {"metrics": ["cpu"]})

    def test_get_absent_key_returns_sentinel(self):
        result = _cache_get("does_not_exist")
        self.assertIs(result, _CACHE_MISS)

    def test_sentinel_is_not_none(self):
        """_CACHE_MISS must be distinguishable from None, {}, and []."""
        self.assertIsNot(_CACHE_MISS, None)
        self.assertIsNot(_CACHE_MISS, {})
        self.assertIsNot(_CACHE_MISS, [])

    # -- expiry --

    def test_expired_entry_returns_sentinel(self):
        _cache_set("k_exp", {"data": "old"}, ttl=0)
        # TTL=0 means expires_at = now; sleeping even 0.01 s guarantees expiry
        time.sleep(0.01)
        result = _cache_get("k_exp")
        self.assertIs(result, _CACHE_MISS)

    def test_expired_entry_is_deleted_from_store(self):
        _cache_set("k_del", {"data": "old"}, ttl=0)
        time.sleep(0.01)
        _cache_get("k_del")  # triggers deletion
        self.assertNotIn("k_del", _CATALOG_CACHE)

    def test_non_expired_entry_is_retained(self):
        _cache_set("k_live", {"data": "alive"}, ttl=60)
        _cache_get("k_live")
        self.assertIn("k_live", _CATALOG_CACHE)

    # -- overwrite --

    def test_set_overwrites_existing_entry(self):
        _cache_set("k_ow", "first", ttl=60)
        _cache_set("k_ow", "second", ttl=60)
        self.assertEqual(_cache_get("k_ow"), "second")

    # -- various value types --

    def test_caches_list(self):
        _cache_set("list_key", [1, 2, 3], ttl=60)
        self.assertEqual(_cache_get("list_key"), [1, 2, 3])

    def test_caches_none(self):
        _cache_set("none_key", None, ttl=60)
        result = _cache_get("none_key")
        # None is a valid cached value — should NOT return _CACHE_MISS
        self.assertIsNot(result, _CACHE_MISS)
        self.assertIsNone(result)

    def test_caches_empty_dict(self):
        _cache_set("empty_dict", {}, ttl=60)
        result = _cache_get("empty_dict")
        self.assertIsNot(result, _CACHE_MISS)
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

class TestClearCache(unittest.TestCase):

    def setUp(self):
        clear_cache()

    def test_clear_removes_all_entries(self):
        _cache_set("a", 1, ttl=60)
        _cache_set("b", 2, ttl=60)
        clear_cache()
        self.assertEqual(len(_CATALOG_CACHE), 0)

    def test_clear_on_empty_store_is_safe(self):
        clear_cache()  # already empty
        clear_cache()  # must not raise
        self.assertEqual(len(_CATALOG_CACHE), 0)

    def test_get_after_clear_returns_sentinel(self):
        _cache_set("k", "v", ttl=60)
        clear_cache()
        self.assertIs(_cache_get("k"), _CACHE_MISS)


# ---------------------------------------------------------------------------
# ttl_cached decorator
# ---------------------------------------------------------------------------

class TestTtlCached(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        clear_cache()

    # -- basic miss → set → hit --

    async def test_first_call_is_a_miss_and_calls_fn(self):
        call_count = 0

        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"data": "fresh"}

        client = _make_client()
        result = await method(client)
        self.assertEqual(result, {"data": "fresh"})
        self.assertEqual(call_count, 1)

    async def test_second_call_hits_cache_and_skips_fn(self):
        call_count = 0

        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"data": "fresh"}

        client = _make_client()
        await method(client)
        result = await method(client)
        self.assertEqual(result, {"data": "fresh"})
        self.assertEqual(call_count, 1)  # fn called only once

    # -- error responses never cached --

    async def test_error_response_is_not_cached(self):
        call_count = 0

        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"error": "something went wrong"}

        client = _make_client()
        await method(client)
        await method(client)
        self.assertEqual(call_count, 2)  # called both times — error not stored

    async def test_error_response_is_returned_to_caller(self):
        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            return {"error": "boom"}

        client = _make_client()
        result = await method(client)
        self.assertEqual(result, {"error": "boom"})

    async def test_non_error_dict_is_cached(self):
        """A dict without 'error' key must be cached normally."""
        call_count = 0

        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"metrics": ["cpu"]}

        client = _make_client()
        await method(client)
        await method(client)
        self.assertEqual(call_count, 1)

    # -- key isolation by base_url --

    async def test_different_base_urls_get_independent_cache_entries(self):
        call_count = 0

        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"data": self.base_url}

        client_a = _make_client("https://tenant-a.instana.io")
        client_b = _make_client("https://tenant-b.instana.io")

        result_a = await method(client_a)
        result_b = await method(client_b)

        self.assertEqual(result_a["data"], "https://tenant-a.instana.io")
        self.assertEqual(result_b["data"], "https://tenant-b.instana.io")
        self.assertEqual(call_count, 2)  # two separate API calls

    # -- key isolation by key_args --

    async def test_different_key_arg_values_get_independent_entries(self):
        call_count = 0

        @ttl_cached(ttl=60, key_args=("beacon_type", "use_case"))
        async def method(self, beacon_type="", use_case="", **kwargs):
            nonlocal call_count
            call_count += 1
            return {"bt": beacon_type, "uc": use_case}

        client = _make_client()
        r1 = await method(client, beacon_type="PAGELOAD", use_case="GROUPING")
        r2 = await method(client, beacon_type="ERROR",    use_case="GROUPING")
        r3 = await method(client, beacon_type="PAGELOAD", use_case="FILTERING")

        self.assertEqual(call_count, 3)
        self.assertEqual(r1, {"bt": "PAGELOAD", "uc": "GROUPING"})
        self.assertEqual(r2, {"bt": "ERROR",    "uc": "GROUPING"})
        self.assertEqual(r3, {"bt": "PAGELOAD", "uc": "FILTERING"})

    async def test_same_key_args_returns_cached_result(self):
        call_count = 0

        @ttl_cached(ttl=60, key_args=("plugin",))
        async def method(self, plugin="", **kwargs):
            nonlocal call_count
            call_count += 1
            return {"plugin": plugin}

        client = _make_client()
        await method(client, plugin="host")
        await method(client, plugin="host")
        self.assertEqual(call_count, 1)

    async def test_absent_key_arg_uses_empty_string(self):
        """If a key_arg is not in kwargs it should not raise; uses '' in key."""
        @ttl_cached(ttl=60, key_args=("missing_param",))
        async def method(self, **kwargs):
            return {"ok": True}

        client = _make_client()
        result = await method(client)
        self.assertEqual(result, {"ok": True})

    # -- TTL expiry via decorator --

    async def test_expired_cache_entry_triggers_fresh_call(self):
        call_count = 0

        @ttl_cached(ttl=0)  # expires immediately
        async def method(self, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"call": call_count}

        client = _make_client()
        await method(client)
        time.sleep(0.01)
        await method(client)
        self.assertEqual(call_count, 2)

    # -- no key_args (global per base_url) --

    async def test_no_key_args_shares_cache_across_param_variations(self):
        """With key_args=(), all calls for the same client share one cache slot."""
        call_count = 0

        @ttl_cached(ttl=60)  # key_args defaults to ()
        async def method(self, view="planner", **kwargs):
            nonlocal call_count
            call_count += 1
            return {"view": view}

        client = _make_client()
        await method(client, view="planner")
        await method(client, view="full")  # different param, same cache slot
        self.assertEqual(call_count, 1)

    # -- functools.wraps --

    async def test_decorator_preserves_function_name(self):
        @ttl_cached(ttl=60)
        async def my_catalog_method(self, **kwargs):
            """Original docstring."""
            return {}

        self.assertEqual(my_catalog_method.__name__, "my_catalog_method")

    async def test_decorator_preserves_docstring(self):
        @ttl_cached(ttl=60)
        async def my_catalog_method(self, **kwargs):
            """Original docstring."""
            return {}

        self.assertEqual(my_catalog_method.__doc__, "Original docstring.")

    # -- object without base_url --

    async def test_client_without_base_url_uses_empty_string(self):
        """getattr fallback to '' must not raise."""
        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            return {"ok": True}

        client = MagicMock(spec=[])  # no base_url attribute
        result = await method(client)
        self.assertEqual(result, {"ok": True})

    # -- cached value is the exact object returned --

    async def test_cached_value_is_identical_object(self):
        payload = {"metrics": ["cpu", "mem"]}

        @ttl_cached(ttl=60)
        async def method(self, **kwargs):
            return payload

        client = _make_client()
        first  = await method(client)
        second = await method(client)
        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
