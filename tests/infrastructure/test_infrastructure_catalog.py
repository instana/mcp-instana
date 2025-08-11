"""
Unit tests for the InfrastructureCatalogMCPTools class
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
app_logger = logging.getLogger('src.infrastructure.infrastructure_catalog')
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
            kwargs['api_client'] = self.catalog_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_catalog_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_catalog_api = MagicMock()

# Add __name__ attribute to mock classes
mock_catalog_api.__name__ = "InfrastructureCatalogApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_catalog_api'].InfrastructureCatalogApi = mock_catalog_api

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.infrastructure.infrastructure_catalog import InfrastructureCatalogMCPTools

class TestInfrastructureCatalogMCPTools(unittest.TestCase):
    """Test the InfrastructureCatalogMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_catalog_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.catalog_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = InfrastructureCatalogMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.catalog_api = self.catalog_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_infrastructure_catalog_metrics_success(self):
        """Test get_infrastructure_catalog_metrics with successful response"""
        # Set up the mock response
        mock_result = ["cpu.usage", "memory.used", "disk.io"]
        self.catalog_api.get_infrastructure_catalog_metrics.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        # Check that the API was called with correct parameters
        self.catalog_api.get_infrastructure_catalog_metrics.assert_called_once_with(
            plugin="host", filter=None
        )

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_infrastructure_catalog_metrics_error(self):
        """Test get_infrastructure_catalog_metrics error handling"""
        # Set up the mock to raise an exception
        self.catalog_api.get_infrastructure_catalog_metrics.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        # Check that the result contains an error message (returns as a list with error string)
        self.assertIsInstance(result, list)
        self.assertIn("Error:", result[0])

    def test_get_infrastructure_catalog_plugins_success(self):
        """Test get_infrastructure_catalog_plugins with successful response"""
        # Set up the mock response that gets transformed
        mock_result = [
            {"name": "host", "description": "Host monitoring"},
            {"name": "docker", "description": "Docker monitoring"}
        ]
        self.catalog_api.get_infrastructure_catalog_plugins.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_infrastructure_catalog_plugins())

        # Check that the API was called
        self.catalog_api.get_infrastructure_catalog_plugins.assert_called_once()

        # Check that the result has been transformed (the method processes the response)
        self.assertIn("message", result)
        self.assertIn("plugins", result)

    def test_get_infrastructure_catalog_plugins_error(self):
        """Test get_infrastructure_catalog_plugins error handling"""
        # Set up the mock to raise an exception
        self.catalog_api.get_infrastructure_catalog_plugins.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_infrastructure_catalog_plugins())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get plugin catalog", result["error"])

    def test_get_tag_catalog_success(self):
        """Test get_tag_catalog with successful response"""
        # Set up the mock response
        mock_result = {
            "tags": [
                {"name": "environment", "values": ["production", "staging"]},
                {"name": "region", "values": ["us-east-1", "us-west-2"]}
            ]
        }
        self.catalog_api.get_tag_catalog.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        # Check that the API was called with the correct arguments
        self.catalog_api.get_tag_catalog.assert_called_once_with(plugin="host")

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_tag_catalog_error(self):
        """Test get_tag_catalog error handling"""
        # Set up the mock to raise an exception
        self.catalog_api.get_tag_catalog.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get tag catalog", result["error"])


if __name__ == '__main__':
    unittest.main()
