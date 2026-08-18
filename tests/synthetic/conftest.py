"""
conftest.py for tests/synthetic/

Cleans up sys.modules pollution caused by module-level mocking in
synthetic test files.

These test files must mock sys.modules at module level (before importing
src.synthetic.*) because the source modules import from instana_client
and src.core.utils at import time.

The cleanup runs after all synthetic tests complete so that other test
modules can import the real modules.
"""

import sys

import pytest

# Keys that are mocked at module level by synthetic test files.
# We save the originals at conftest import time (before any test file is
# imported) and restore them after the synthetic test session finishes.
_MOCKED_KEYS = [
    "mcp",
    "mcp.types",
    "fastmcp",
    "instana_client",
    "instana_client.api",
    "instana_client.api.synthetic_catalog_api",
    "instana_client.api.synthetic_metrics_api",
    "instana_client.api.synthetic_settings_api",
    "instana_client.api.synthetic_test_playback_results_api",
    "instana_client.api_client",
    "instana_client.configuration",
    "instana_client.models",
    "instana_client.models.get_metrics_result",
    "instana_client.models.get_test_result",
    "instana_client.models.get_test_result_analytic",
    "instana_client.models.get_test_result_list",
    "instana_client.models.get_test_result_base",
    "instana_client.models.get_test_summary_result",
    "src.core",
    "src.core.utils",
]

# Save originals before any synthetic test module is imported
_originals = {k: sys.modules.get(k) for k in _MOCKED_KEYS}


@pytest.fixture(autouse=True, scope="session")
def restore_sys_modules_after_synthetic_tests():
    """Restore sys.modules after all synthetic tests complete."""
    yield
    # Restore each key to its original state
    for key, original in _originals.items():
        if original is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original
