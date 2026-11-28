"""
conftest.py for tests/application/

Cleans up sys.modules pollution caused by module-level mocking in
test_application_metrics.py and test_application_settings.py.

These test files must mock sys.modules at module level (before importing
src.application.*) because the source modules import from mcp, fastmcp,
instana_client, and src.prompts at import time.

The cleanup runs after all application tests complete so that other test
modules (tests/core/, tests/prompts/, etc.) can import the real modules.
"""

import sys

import pytest

# Keys that are mocked at module level by application test files.
# We save the originals at conftest import time (before any test file is
# imported) and restore them after the application test session finishes.
_MOCKED_KEYS = [
    "mcp",
    "mcp.types",
    "fastmcp",
    "fastmcp.server",
    "fastmcp.server.dependencies",
    "pydantic",
    "instana_client",
    "instana_client.api",
    "instana_client.api.application_metrics_api",
    "instana_client.api.application_settings_api",
    "instana_client.api_client",
    "instana_client.configuration",
    "instana_client.models",
    "instana_client.models.get_application_metrics",
    "instana_client.models.get_applications",
    "instana_client.models.get_endpoints",
    "instana_client.models.get_services",
    "instana_client.models.application_config",
    "instana_client.models.endpoint_config",
    "instana_client.models.manual_service_config",
    "instana_client.models.new_application_config",
    "instana_client.models.new_manual_service_config",
    "instana_client.models.service_config",
    "src.prompts",
    "src.core",
    "src.core.utils",
]

# Save originals before any application test module is imported
_originals = {k: sys.modules.get(k) for k in _MOCKED_KEYS}


@pytest.fixture(autouse=True, scope="session")
def restore_sys_modules_after_application_tests():
    """Restore sys.modules after all application tests complete."""
    yield
    # Restore each key to its original state
    for key, original in _originals.items():
        if original is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original


@pytest.fixture(autouse=True)
def no_request_base_url():
    """Keep link building independent of the mocked fastmcp.server.dependencies module."""
    from unittest.mock import patch

    ui_links = sys.modules.get("src.core.ui_links")
    if ui_links is None:
        yield
        return
    with patch.object(ui_links, "_request_base_url", return_value=None):
        yield
