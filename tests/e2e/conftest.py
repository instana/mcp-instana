"""
Shared fixtures for E2E tests
"""

import os
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import your application modules
from src.core.server import create_app
from src.core.utils import BaseInstanaClient


@pytest.fixture(scope="session")
def instana_credentials() -> Dict[str, str]:
    """Provide Instana API credentials for tests."""
    return {
        "base_url": os.environ.get("INSTANA_BASE_URL", "https://test.instana.io"),
        "api_token": os.environ.get("INSTANA_API_TOKEN", "test_token")
    }


@pytest.fixture(scope="session")
def test_environment() -> Dict[str, Any]:
    """Provide test environment configuration."""
    return {
        "enabled_tools": os.environ.get("INSTANA_ENABLED_TOOLS", "all"),
        "timeout": int(os.environ.get("TEST_TIMEOUT", "30")),
        "retry_attempts": int(os.environ.get("TEST_RETRY_ATTEMPTS", "3"))
    }


@pytest.fixture(scope="session")
async def mcp_server(instana_credentials, test_environment):
    """Create and configure the MCP server for testing."""
    try:
        app, _ = create_app(
            instana_credentials["api_token"],
            instana_credentials["base_url"],
            enabled_tools=test_environment["enabled_tools"]
        )
        yield app
    except Exception as e:
        pytest.fail(f"Failed to create MCP server: {e}")


@pytest.fixture(scope="session")
async def client_session():
    """Create a shared aiohttp client session for tests."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            yield session
    except ImportError:
        # Fallback if aiohttp is not available
        yield None


@pytest.fixture
def mock_instana_response():
    """Provide mock Instana API responses for testing."""
    return {
        "applications": {
            "applications": [
                {
                    "id": "test-app-1",
                    "name": "Test Application 1",
                    "type": "java",
                    "services": ["service-1", "service-2"]
                },
                {
                    "id": "test-app-2",
                    "name": "Test Application 2",
                    "type": "python",
                    "services": ["service-3"]
                }
            ]
        },
        "services": {
            "services": [
                {
                    "id": "service-1",
                    "name": "Test Service 1",
                    "type": "java"
                }
            ]
        },
        "metrics": {
            "metrics": [
                {
                    "id": "cpu_usage",
                    "name": "CPU Usage",
                    "unit": "percent"
                }
            ]
        }
    }


@pytest.fixture
def mock_base_client(instana_credentials):
    """Create a mock base client for testing."""
    client = MagicMock(spec=BaseInstanaClient)
    client.read_token = instana_credentials["api_token"]
    client.base_url = instana_credentials["base_url"]
    client.make_request = AsyncMock()
    return client


# Helper function to check if we should run real API tests
def should_run_real_api_tests():
    """Check if we should run tests against real Instana API."""
    return (
        os.environ.get("INSTANA_API_TOKEN") and
        os.environ.get("INSTANA_BASE_URL") and
        os.environ.get("RUN_REAL_API_TESTS", "false").lower() == "true"
    )


# Markers for different test types


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "real_api: mark test as requiring real API access"
    )
    config.addinivalue_line(
        "markers", "mocked: mark test as using mocked responses"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
