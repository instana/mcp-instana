"""Pytest configuration for all prompt tests."""
import importlib.util
import sys
from unittest.mock import MagicMock


def _fastmcp_available() -> bool:
    try:
        return importlib.util.find_spec("fastmcp") is not None
    except (ValueError, ImportError):
        # A mock fastmcp is already registered in sys.modules (no __spec__)
        return False


def pytest_configure(config):
    # Only mock fastmcp when it is not installed. Replacing an installed package in
    # sys.modules at configure time breaks every other test module collected afterwards.
    if _fastmcp_available():
        return

    mock_mcp_instance = MagicMock()

    def mock_prompt_decorator():
        def decorator(func):
            return func
        return decorator

    mock_mcp_instance.prompt = mock_prompt_decorator
    mock_fastmcp = MagicMock()
    mock_fastmcp.FastMCP.return_value = mock_mcp_instance
    if "fastmcp" not in sys.modules:
        sys.modules["fastmcp"] = mock_fastmcp
