"""
Unit tests for the ApplicationCatalogMCPTools class
"""

import asyncio
import logging
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
app_logger = logging.getLogger('src.application.application_catalog')
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
import os

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
sys.modules['instana_client.api.application_catalog_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_app_catalog_api = MagicMock()

# Add __name__ attribute to mock classes
mock_app_catalog_api.__name__ = "ApplicationCatalogApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_catalog_api'].ApplicationCatalogApi = mock_app_catalog_api

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.application.application_catalog import ApplicationCatalogMCPTools

class TestApplicationCatalogMCPTools(unittest.TestCase):
    """Test the ApplicationCatalogMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_app_catalog_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.catalog_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationCatalogMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.catalog_api = self.catalog_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    @patch('src.application.application_catalog.datetime')
    def test_get_application_tag_catalog_with_defaults(self, mock_datetime):
        """Test get_application_tag_catalog with default parameters"""
        # Set up the mock datetime
        from datetime import datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Set up the mock response
        mock_response = MagicMock()
        mock_response.data = b'[{"tagTree": [{"name": "level1", "children": [{"name": "child1"}, {"name": "child2"}, {"name": "child3"}, {"name": "child4"}]}, {"name": "level2", "children": []}, {"name": "level3", "children": []}, {"name": "level4"}]}]'

        self.client.catalog_api.get_application_tag_catalog_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_application_tag_catalog())

        # Check that the mock was called with the correct arguments
        self.client.catalog_api.get_application_tag_catalog_without_preload_content.assert_called_once()

        # Check that the result contains the expected trimmed data
        self.assertIn("tags", result)
        self.assertEqual(len(result["tags"]), 1)
        self.assertEqual(len(result["tags"][0]["tagTree"]), 3)  # Should be trimmed to 3 levels
        self.assertEqual(len(result["tags"][0]["tagTree"][0]["children"]), 3)  # Should be trimmed to 3 children

    def test_get_application_tag_catalog_with_params(self):
        """Test get_application_tag_catalog with specific parameters"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.data = b'{"tagTree": []}'

        self.client.catalog_api.get_application_tag_catalog_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method with specific parameters
        use_case = "GROUPING"
        data_source = "CALLS"
        var_from = 1625097600000  # Example timestamp

        result = asyncio.run(self.client.get_application_tag_catalog(
            use_case=use_case,
            data_source=data_source,
            var_from=var_from
        ))

        # Check that the mock was called with the correct arguments
        self.client.catalog_api.get_application_tag_catalog_without_preload_content.assert_called_once_with(
            use_case=use_case,
            data_source=data_source,
            var_from=var_from
        )

        # Check that the result is correct - the implementation wraps the dict in another dict
        self.assertEqual(result, {"tagTree": []})

    def test_get_application_tag_catalog_error(self):
        """Test get_application_tag_catalog error handling"""
        # Set up the mock to raise an exception
        self.client.catalog_api.get_application_tag_catalog_without_preload_content = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_application_tag_catalog())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application catalog", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_application_tag_catalog_unexpected_format(self):
        """Test get_application_tag_catalog with unexpected response format"""
        # Set up the mock response with an unexpected format
        mock_response = MagicMock()
        mock_response.data = b"not a valid json"

        self.client.catalog_api.get_application_tag_catalog_without_preload_content = MagicMock(return_value=mock_response)

        # Call the method
        result = asyncio.run(self.client.get_application_tag_catalog())

        # Check that the result contains an error message
        self.assertIn("error", result)

    def test_get_application_metric_catalog_success(self):
        """Test get_application_metric_catalog with a successful response"""
        # Set up the mock response
        mock_metric1_dict = {
            "id": "metric1",
            "name": "Metric 1",
            "unit": "count"
        }
        mock_metric2_dict = {
            "id": "metric2",
            "name": "Metric 2",
            "unit": "ms"
        }

        # Create a mock result object that will be returned by the API
        mock_result = MagicMock()
        # When to_dict() is called on the result, it should return a list of dictionaries
        mock_result.to_dict.return_value = [mock_metric1_dict, mock_metric2_dict]

        self.client.catalog_api.get_application_catalog_metrics = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_application_metric_catalog())

        # Check that the mock was called
        self.client.catalog_api.get_application_catalog_metrics.assert_called_once()

        # Check that the result is correct
        self.assertIn("metrics", result)
        self.assertEqual(len(result["metrics"]), 2)
        self.assertEqual(result["metrics"][0], mock_metric1_dict)
        self.assertEqual(result["metrics"][1], mock_metric2_dict)

    def test_get_application_metric_catalog_dict_response(self):
        """Test get_application_metric_catalog with a dictionary response"""
        # Set up the mock response as a dictionary
        mock_result = {
            "metrics": [
                {
                    "id": "metric1",
                    "name": "Metric 1",
                    "unit": "count"
                },
                {
                    "id": "metric2",
                    "name": "Metric 2",
                    "unit": "ms"
                }
            ]
        }

        self.client.catalog_api.get_application_catalog_metrics = MagicMock(return_value=mock_result)

        # Call the method
        result = asyncio.run(self.client.get_application_metric_catalog())

        # Check that the mock was called
        self.client.catalog_api.get_application_catalog_metrics.assert_called_once()

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_application_metric_catalog_error(self):
        """Test get_application_metric_catalog error handling"""
        # Set up the mock to raise an exception
        self.client.catalog_api.get_application_catalog_metrics = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        result = asyncio.run(self.client.get_application_metric_catalog())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get application metric catalog", result["error"])
        self.assertIn("Test error", result["error"])


if __name__ == '__main__':
    unittest.main()

