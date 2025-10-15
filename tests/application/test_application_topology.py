"""
Unit tests for the ApplicationTopologyMCPTools class
"""

import asyncio
import logging
import sys
import unittest
from datetime import datetime
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.application.application_topology')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False  # Prevent logs from propagating to parent loggers

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    # Skip printing exceptions from the mock side_effect
    if isinstance(value, Exception) and (str(value) == "API Error" or str(value) == "Initialization Error"):
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
    # Just do nothing - this will suppress all traceback printing from print_exc
    pass

traceback.print_exception = custom_print_exception
traceback.print_exc = custom_print_exc


# No need for with_header_auth mock since the method doesn't use it

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.application_topology_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_topology_api = MagicMock()

# Add __name__ attribute to mock classes
mock_topology_api.__name__ = "ApplicationTopologyApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_topology_api'].ApplicationTopologyApi = mock_topology_api

# Patch the with_header_auth decorator
# Import the class to test
from src.application.application_topology import ApplicationTopologyMCPTools


class TestApplicationTopologyMCPTools(unittest.TestCase):
    """Test cases for ApplicationTopologyMCPTools class."""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_topology_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.topology_api = mock_topology_api

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.topology_api = mock_topology_api

    def test_get_application_topology(self):
        """Test get_application_topology method."""
        # Mock response data - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response_data = {
            "nodes": [
                {
                    "id": "service-1",
                    "name": "frontend-service",
                    "type": "web"
                },
                {
                    "id": "service-2",
                    "name": "backend-service",
                    "type": "api"
                }
            ],
            "edges": [
                {
                    "source": "service-1",
                    "target": "service-2",
                    "calls": 150
                }
            ]
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')

        # Configure the mock
        self.client.topology_api.get_services_map_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method
        result = asyncio.run(self.client.get_application_topology(
            window_size=3600000,
            to_timestamp=int(datetime.now().timestamp() * 1000),
            application_id="app-123",
            application_boundary_scope="INBOUND"
        ))

        # Verify the API was called with correct parameters
        self.client.topology_api.get_services_map_without_preload_content.assert_called_once()
        call_args = self.client.topology_api.get_services_map_without_preload_content.call_args[1]
        self.assertEqual(call_args["window_size"], 3600000)
        self.assertEqual(call_args["application_id"], "app-123")
        self.assertEqual(call_args["application_boundary_scope"], "INBOUND")

        # Verify the result
        self.assertIn("nodes", result)
        self.assertIn("edges", result)
        self.assertEqual(len(result["nodes"]), 2)
        self.assertEqual(len(result["edges"]), 1)
        self.assertEqual(result["nodes"][0]["name"], "frontend-service")
        self.assertEqual(result["edges"][0]["calls"], 150)

    def test_get_application_topology_with_defaults(self):
        """Test get_application_topology method with default parameters."""
        # Mock response data
        mock_response = MagicMock()
        mock_response_data = {"nodes": [], "edges": []}
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')

        # Configure the mock
        self.client.topology_api.get_services_map_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_application_topology())

        # Verify the API was called
        self.client.topology_api.get_services_map_without_preload_content.assert_called_once()

        # Verify default values were used
        call_args = self.client.topology_api.get_services_map_without_preload_content.call_args[1]
        self.assertEqual(call_args["window_size"], 3600000)  # Default 1 hour

        # Verify the result structure
        self.assertIn("nodes", result)
        self.assertIn("edges", result)

    def test_get_application_topology_error_handling(self):
        """Test error handling in get_application_topology method."""
        # Configure the mock to raise an exception
        self.client.topology_api.get_services_map_without_preload_content = MagicMock(side_effect=Exception("API Error"))

        # Call the method
        result = asyncio.run(self.client.get_application_topology())

        # Verify error handling
        self.assertIn("error", result)
        self.assertIn("Failed to get application topology", result["error"])

    def test_get_application_topology_dict_result(self):
        """Test get_application_topology with a result that's already a dict."""
        # Mock response data as a response object with data attribute
        mock_response = MagicMock()
        mock_result = {"nodes": [], "edges": []}
        import json
        mock_response.data = json.dumps(mock_result).encode('utf-8')

        # Configure the mock
        self.client.topology_api.get_services_map_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method
        result = asyncio.run(self.client.get_application_topology())

        # Verify the result is passed through unchanged
        self.assertEqual(result, mock_result)
    def test_initialization_error_handling(self):
        """Test error handling during initialization."""
        # Configure the ApplicationTopologyApi constructor to raise an exception
        with patch('src.application.application_topology.ApplicationTopologyApi',
                  side_effect=Exception("Initialization Error")):

            # Attempt to create the client, which should raise the exception
            with self.assertRaises(Exception) as context:
                ApplicationTopologyMCPTools(read_token="test_token", base_url="https://test.instana.io")

            # Verify the exception was raised and properly handled
            self.assertIn("Initialization Error", str(context.exception))


if __name__ == "__main__":
    unittest.main()



