"""
conftest.py for tests/website/

Cleans up sys.modules pollution caused by module-level mocking in
test_website_analyze.py and test_website_catalog.py.

These test files must mock sys.modules at module level (before importing
src.website.*) because the source modules import from mcp, instana_client,
and src.core.utils at import time.

The cleanup runs after all website tests complete so that other test
modules can import the real modules.
"""

import sys

import pytest

# Keys that are mocked at module level by website test files.
# We save the originals at conftest import time (before any test file is
# imported) and restore them after the website test session finishes.
_MOCKED_KEYS = [
    "mcp",
    "mcp.types",
    "instana_client",
    "instana_client.api",
    "instana_client.api.website_analyze_api",
    "instana_client.api.website_catalog_api",
    "instana_client.api_client",
    "instana_client.configuration",
    "instana_client.models",
    "instana_client.models.get_website_beacon_groups",
    "instana_client.models.tag_filter_expression_element",
    "instana_client.models.cursor_pagination",
    "instana_client.models.get_website_beacons",
    "instana_client.models.deprecated_tag_filter",
    "src.core",
    "src.core.utils",
]

# Save originals before any website test module is imported
_originals = {k: sys.modules.get(k) for k in _MOCKED_KEYS}


@pytest.fixture(autouse=True, scope="session")
def restore_sys_modules_after_website_tests():
    """Restore sys.modules after all website tests complete."""
    yield
    # Restore each key to its original state
    for key, original in _originals.items():
        if original is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original
