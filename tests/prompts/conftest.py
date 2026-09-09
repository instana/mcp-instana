"""Pytest configuration for all prompt tests."""
import sys
from unittest.mock import MagicMock


def pytest_configure(config):
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
