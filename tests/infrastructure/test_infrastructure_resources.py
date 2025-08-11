"""
Unit tests for the InfrastructureResourcesMCPTools class
"""

import asyncio
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.infrastructure.infrastructure_resources')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False  # Prevent logs from propagating to parent loggers

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    # Skip printing exceptions from the mock side_effect
    if isinstance(value, Exception) and str(value) == "Test error":
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
    # Just do nothing - this will suppress all traceback printing from print_exc
    pass

traceback.print_exception = custom_print_exception
traceback.print_exc = custom_print_exc

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.resources_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_resources_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_resources_api = MagicMock()

# Add __name__ attribute to mock classes
mock_resources_api.__name__ = "InfrastructureResourcesApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_resources_api'].InfrastructureResourcesApi = mock_resources_api

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.infrastructure.infrastructure_resources import (
        InfrastructureResourcesMCPTools,
    )

class TestInfrastructureResourcesMCPTools(unittest.TestCase):
    """Test the InfrastructureResourcesMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_resources_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.resources_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = InfrastructureResourcesMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.resources_api = self.resources_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_monitoring_state_success(self):
        """Test get_monitoring_state with successful response"""
        # Set up the mock response
        mock_result = {
            "state": "healthy",
            "agents": 10,
            "entities": 250
        }
        self.resources_api.get_monitoring_state.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_monitoring_state())

        # Check that the API was called
        self.resources_api.get_monitoring_state.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_monitoring_state_error(self):
        """Test get_monitoring_state error handling"""
        # Set up the mock to raise an exception
        self.resources_api.get_monitoring_state.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_monitoring_state())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get monitoring state", result["error"])

    def test_get_snapshot_success(self):
        """Test get_snapshot with successful response"""
        # Set up the mock response
        mock_result = {
            "id": "snap1",
            "timestamp": 1625184000000,
            "data": {"cpu.usage": 50.5}
        }
        self.resources_api.get_snapshot.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_snapshot_error(self):
        """Test get_snapshot error handling"""
        # Set up the mock to raise an exception
        self.resources_api.get_snapshot.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get snapshot", result["error"])

    def test_get_snapshots_success(self):
        """Test get_snapshots with successful response"""
        # Set up the mock response
        mock_result = [
            {"id": "snap1", "timestamp": 1625184000000},
            {"id": "snap2", "timestamp": 1625184060000}
        ]
        self.resources_api.get_snapshots.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_snapshots(
            plugin="host",
            query="entity.tag=production"
        ))

        # Check that the API was called
        self.resources_api.get_snapshots.assert_called_once()

        # Check that the result is processed correctly (the method transforms empty results)
        # When no snapshots are found, it returns a summary message
        self.assertIn("message", result)

    def test_get_snapshots_error(self):
        """Test get_snapshots error handling"""
        # Set up the mock to raise an exception
        self.resources_api.get_snapshots.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_snapshots(
            plugin="host",
            query="entity.tag=production"
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get snapshots", result["error"])


if __name__ == '__main__':
    unittest.main()
