"""
Unit tests for the InfrastructureMetricsMCPTools class
"""

import asyncio
import logging
import sys
import traceback
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch

# Configure logging to suppress logs during tests
logging.basicConfig(level=logging.CRITICAL)

# Create a NullHandler to discard log messages
null_handler = logging.NullHandler()
logging.getLogger('src.infrastructure.infrastructure_metrics').addHandler(null_handler)
logging.getLogger('src.infrastructure.infrastructure_metrics').propagate = False

# Patch traceback to suppress exception traces
original_print_exception = traceback.print_exception

def silent_print_exception(*args, **kwargs):
    pass

traceback.print_exception = silent_print_exception


# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.metrics_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_metrics_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_combined_metrics'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_metrics_api = MagicMock()
mock_combined_metrics = MagicMock()

# Add __name__ attribute to mock classes
mock_metrics_api.__name__ = "InfrastructureMetricsApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_metrics_api'].InfrastructureMetricsApi = mock_metrics_api
sys.modules['instana_client.models.get_combined_metrics'].GetCombinedMetrics = mock_combined_metrics

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Also patch the GetCombinedMetrics import in the source module
    with patch('src.infrastructure.infrastructure_metrics.GetCombinedMetrics', mock_combined_metrics):
        # Import the class to test
        from src.infrastructure.infrastructure_metrics import (
            InfrastructureMetricsMCPTools,
        )

class TestInfrastructureMetricsMCPTools(unittest.TestCase):
    """Test the InfrastructureMetricsMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_metrics_api.reset_mock()
        mock_combined_metrics.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.metrics_api = mock_metrics_api
        self.mock_combined_metrics = mock_combined_metrics

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = InfrastructureMetricsMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.metrics_api = mock_metrics_api

        # Patch loggers to prevent output during tests
        self.logger_patcher = patch('logging.Logger.error')
        self.logger_mock = self.logger_patcher.start()
        self.logger_mock.side_effect = lambda *args, **kwargs: None

        # Patch traceback to suppress exception traces
        self.traceback_patcher = patch('traceback.print_exception')
        self.traceback_mock = self.traceback_patcher.start()
        self.traceback_mock.side_effect = lambda *args, **kwargs: None

    def tearDown(self):
        """Clean up after tests"""
        # Stop the patchers
        self.logger_patcher.stop()
        self.traceback_patcher.stop()

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_infrastructure_metrics_missing_metrics(self):
        """Test get_infrastructure_metrics with missing metrics parameter"""
        # Call the method without metrics
        result = asyncio.run(self.client.get_infrastructure_metrics(
            plugin="host",
            query="entity.type:host"
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual("Metrics is required for this operation", result["error"])

    def test_get_infrastructure_metrics_missing_plugin(self):
        """Test get_infrastructure_metrics with missing plugin parameter"""
        # Call the method without plugin
        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=["cpu.usage"],
            query="entity.type:host"
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual("Plugin is required for this operation", result["error"])

    def test_get_infrastructure_metrics_missing_query(self):
        """Test get_infrastructure_metrics with missing query parameter"""
        # Call the method without query
        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=["cpu.usage"],
            plugin="host"
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual("Query is required for this operation", result["error"])

    @patch('src.infrastructure.infrastructure_metrics.datetime')
    def test_get_infrastructure_metrics_with_defaults(self, mock_datetime):
        """Test get_infrastructure_metrics with default time_frame and rollup"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "host1", "metrics": {"cpu.usage": [{"value": 10}]}},
                {"id": "host2", "metrics": {"cpu.usage": [{"value": 20}]}},
                {"id": "host3", "metrics": {"cpu.usage": [{"value": 30}]}},
                {"id": "host4", "metrics": {"cpu.usage": [{"value": 40}]}}  # This should be trimmed
            ]
        }
        self.client.metrics_api.get_infrastructure_metrics = MagicMock(return_value=mock_result)

        # Call the method with minimal required parameters
        metrics = ["cpu.usage"]
        plugin = "host"
        query = "entity.type:host"

        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=metrics,
            plugin=plugin,
            query=query
        ))

        # Check that the result contains the expected data and is trimmed
        self.assertEqual(len(result["items"]), 3)  # Should be trimmed to 3 items
        self.assertEqual(result["items"][0]["id"], "host1")
        self.assertEqual(result["items"][1]["id"], "host2")
        self.assertEqual(result["items"][2]["id"], "host3")

    def test_get_infrastructure_metrics_with_custom_params(self):
        """Test get_infrastructure_metrics with custom parameters"""
        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "host1", "metrics": {"cpu.usage": [{"value": 10}]}}
            ]
        }
        self.client.metrics_api.get_infrastructure_metrics = MagicMock(return_value=mock_result)

        # Call the method with custom parameters
        metrics = ["cpu.usage", "memory.used"]
        plugin = "host"
        query = "entity.type:host AND entity.name:host1"
        time_frame = {"from": 1625097600000, "to": 1625184000000}
        rollup = 300
        snapshot_ids = "snapshot123"
        offline = True

        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=metrics,
            plugin=plugin,
            query=query,
            time_frame=time_frame,
            rollup=rollup,
            snapshot_ids=snapshot_ids,
            offline=offline
        ))

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_infrastructure_metrics_with_snapshot_ids_list(self):
        """Test get_infrastructure_metrics with snapshot_ids as a list"""
        # Set up the mock response
        mock_result = {
            "items": [
                {"id": "host1", "metrics": {"cpu.usage": [{"value": 10}]}}
            ]
        }
        self.client.metrics_api.get_infrastructure_metrics = MagicMock(return_value=mock_result)

        # Call the method with snapshot_ids as a list
        metrics = ["cpu.usage"]
        plugin = "host"
        query = "entity.type:host"
        snapshot_ids = ["snapshot123", "snapshot456"]

        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=metrics,
            plugin=plugin,
            query=query,
            snapshot_ids=snapshot_ids
        ))

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_infrastructure_metrics_with_invalid_snapshot_ids(self):
        """Test get_infrastructure_metrics with invalid snapshot_ids parameter"""
        # Call the method with invalid snapshot_ids (using an integer)
        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=["cpu.usage"],
            plugin="host",
            query="entity.type:host",
            snapshot_ids=123  # Integer, not a string or list
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual("snapshot_ids must be a string or list of strings", result["error"])

    def test_get_infrastructure_metrics_with_list_response(self):
        """Test get_infrastructure_metrics with a list response"""
        # Set up the mock response as a list
        mock_result = [
            {"id": "host1", "metrics": {"cpu.usage": [{"value": 10}]}},
            {"id": "host2", "metrics": {"cpu.usage": [{"value": 20}]}},
            {"id": "host3", "metrics": {"cpu.usage": [{"value": 30}]}},
            {"id": "host4", "metrics": {"cpu.usage": [{"value": 40}]}}  # This should be trimmed
        ]
        self.client.metrics_api.get_infrastructure_metrics = MagicMock(return_value=mock_result)

        # Call the method
        metrics = ["cpu.usage"]
        plugin = "host"
        query = "entity.type:host"

        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=metrics,
            plugin=plugin,
            query=query
        ))

        # Check that the result is properly formatted
        self.assertEqual(len(result["items"]), 3)  # Should be trimmed to 3 items

    def test_get_infrastructure_metrics_error(self):
        """Test get_infrastructure_metrics error handling"""
        # Set up the mock to raise an exception
        self.client.metrics_api.get_infrastructure_metrics = MagicMock(side_effect=Exception("Test error"))

        # Call the method
        metrics = ["cpu.usage"]
        plugin = "host"
        query = "entity.type:host"

        result = asyncio.run(self.client.get_infrastructure_metrics(
            metrics=metrics,
            plugin=plugin,
            query=query
        ))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get Infra metrics", result["error"])
        self.assertIn("Test error", result["error"])


if __name__ == '__main__':
    unittest.main()

