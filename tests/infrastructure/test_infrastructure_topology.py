"""
Unit tests for the InfrastructureTopologyMCPTools class
"""

import asyncio
import importlib
import json
import logging
import os
import sys
import unittest
from functools import wraps
from types import ModuleType
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.infrastructure.infrastructure_topology')
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
            kwargs['api_client'] = self.topology_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_topology_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_topology_api = MagicMock()

# Add __name__ attribute to mock classes
mock_topology_api.__name__ = "InfrastructureTopologyApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_topology_api'].InfrastructureTopologyApi = mock_topology_api

# Mock fastmcp and mcp modules before importing src.core.utils
sys.modules['fastmcp'] = MagicMock()
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()

# Import src.core.utils first to ensure it's available for patching
import src.core.utils


def create_infrastructure_topology_client(read_token: str, base_url: str):
    with patch.object(src.core.utils, 'with_header_auth', mock_with_header_auth):
        module = importlib.import_module('src.infrastructure.infrastructure_topology')
        module = importlib.reload(module)
        return module.InfrastructureTopologyMCPTools(
            read_token=read_token,
            base_url=base_url,
        )

class TestInfrastructureTopologyMCPTools(unittest.TestCase):
    """Test the InfrastructureTopologyMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_topology_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.topology_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = create_infrastructure_topology_client(
            read_token=self.read_token,
            base_url=self.base_url,
        )

        # Set up the client's API attribute
        self.client.topology_api = self.topology_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_related_hosts_success(self):
        """Test get_related_hosts with a successful response"""
        # Set up the mock response - return a list as the method expects
        mock_result = ["host1", "host2", "host3"]
        self.topology_api.get_related_hosts.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_related_hosts(snapshot_id="test_snapshot"))

        # Check that the API was called with the correct arguments
        self.topology_api.get_related_hosts.assert_called_once_with(
            snapshot_id="test_snapshot",
            to=None,
            window_size=None
        )

        # Check that the result is processed correctly
        expected_result = {
            "relatedHosts": ["host1", "host2", "host3"],
            "count": 3,
            "snapshotId": "test_snapshot"
        }
        self.assertEqual(result, expected_result)

    def test_get_related_hosts_with_optional_params(self):
        """Test get_related_hosts with optional parameters"""
        # Set up the mock response - return a list as the method expects
        mock_result = ["host1", "host2"]
        self.topology_api.get_related_hosts.return_value = mock_result

        # Call the method with optional parameters
        result = asyncio.run(self.client.get_related_hosts(
            snapshot_id="test_snapshot",
            to_time=1625184000000,
            window_size=3600000
        ))

        # Check that the API was called with the correct arguments
        self.topology_api.get_related_hosts.assert_called_once_with(
            snapshot_id="test_snapshot",
            to=1625184000000,
            window_size=3600000
        )

        # Check that the result is processed correctly
        expected_result = {
            "relatedHosts": ["host1", "host2"],
            "count": 2,
            "snapshotId": "test_snapshot"
        }
        self.assertEqual(result, expected_result)

    def test_get_related_hosts_error(self):
        """Test get_related_hosts error handling"""
        # Set up the mock to raise an exception
        self.topology_api.get_related_hosts.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_related_hosts(snapshot_id="test_snapshot"))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get related hosts", result["error"])

    def test_get_topology_success(self):
        """Test get_topology with a successful response"""
        # Set up the mock response
        mock_result = {
            "nodes": [
                {"id": "node1", "plugin": "host", "label": "Host 1"},
                {"id": "node2", "plugin": "process", "label": "Process 1"}
            ],
            "edges": [
                {"from": "node1", "to": "node2", "type": "hosts"}
            ]
        }
        # Set up the mock response for get_topology_without_preload_content
        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.get_topology(include_data=True))

        # Check that the API was called with the correct arguments
        self.topology_api.get_topology_without_preload_content.assert_called_once_with(include_data=True)

        # Check that the result has the expected structure (it transforms the response)
        self.assertIn("summary", result)
        self.assertIn("totalNodes", result["summary"])
        self.assertIn("totalEdges", result["summary"])
        self.assertEqual(result["summary"]["totalNodes"], 2)

    def test_get_topology_error(self):
        """Test get_topology error handling"""
        # Set up the mock to raise an exception
        self.topology_api.get_topology_without_preload_content.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_topology())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get topology", result["error"])

    def test_get_topology_invalid_json(self):
        """Test get_topology handles invalid JSON response"""
        mock_response = MagicMock()
        mock_response.data = b'invalid json'
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("error", result)
        self.assertIn("Failed to parse JSON response", result["error"])

    def test_get_topology_data_without_nodes(self):
        """Test get_topology returns summary when no nodes are present"""
        mock_response = MagicMock()
        mock_response.data = b'{"data": "raw topology"}'
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        self.assertTrue(result.get("rawDataAvailable", False))

    def test_debug_print_logs_debug(self):
        """Test debug_print writes a debug log entry"""
        from src.infrastructure.infrastructure_topology import debug_print

        with patch('src.infrastructure.infrastructure_topology.logger') as mock_logger:
            debug_print('hello', 'world')
            mock_logger.debug.assert_called_once()

    def test_get_related_hosts_missing_snapshot_id(self):
        """Test get_related_hosts with missing snapshot_id"""
        result = asyncio.run(self.client.get_related_hosts(snapshot_id=""))

        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_get_related_hosts_non_list_result(self):
        """Test get_related_hosts with non-list result"""
        self.topology_api.get_related_hosts.return_value = "string_result"

        result = asyncio.run(self.client.get_related_hosts(snapshot_id="snap1"))

        self.assertIn("data", result)
        self.assertEqual(result["snapshotId"], "snap1")

    def test_get_topology_with_to_dict_method(self):
        """Test get_topology when result has to_dict method"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "nodes": [{"id": "n1", "plugin": "host", "label": "Host"}],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result.to_dict()).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)

    def test_get_topology_with_dict_result(self):
        """Test get_topology when result is already a dict"""
        mock_result = {
            "nodes": [{"id": "n1", "plugin": "host", "label": "Host"}],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)

    def test_get_topology_with_kubernetes_resources(self):
        """Test get_topology with Kubernetes resources"""
        mock_result = {
            "nodes": [
                {"id": "n1", "plugin": "kubernetespod", "label": "Pod 1"},
                {"id": "n2", "plugin": "kubernetesdeployment", "label": "Deploy 1"},
                {"id": "n3", "plugin": "host", "label": "Host 1"}
            ],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        self.assertIn("kubernetesTypes", result["summary"]["infrastructureOverview"])

    def test_get_topology_with_containers(self):
        """Test get_topology with container resources"""
        mock_result = {
            "nodes": [
                {"id": "n1", "plugin": "docker", "label": "Container 1"},
                {"id": "n2", "plugin": "containerd", "label": "Container 2"},
                {"id": "n3", "plugin": "crio", "label": "Container 3"}
            ],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        self.assertIn("estimatedContainers", result["summary"]["infrastructureOverview"])

    def test_get_topology_with_processes(self):
        """Test get_topology with process resources"""
        mock_result = {
            "nodes": [
                {"id": "n1", "plugin": "process", "label": "Process 1"},
                {"id": "n2", "plugin": "process", "label": "Process 2"}
            ],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        self.assertIn("estimatedProcesses", result["summary"]["infrastructureOverview"])

    def test_get_topology_with_edges(self):
        """Test get_topology with edge analysis"""
        mock_result = {
            "nodes": [
                {"id": "n1", "plugin": "host", "label": "Host 1"},
                {"id": "n2", "plugin": "process", "label": "Process 1"}
            ],
            "edges": [
                {"from": "n1", "to": "n2", "type": "hosts"},
                {"from": "n1", "to": "n2", "type": "runs"}
            ]
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        self.assertIn("connectionAnalysis", result["summary"])

    def test_get_topology_with_large_dataset(self):
        """Test get_topology with more than 30 nodes (sampling)"""
        nodes = [{"id": f"n{i}", "plugin": "host", "label": f"Host {i}"} for i in range(50)]
        mock_result = {"nodes": nodes, "edges": []}

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        self.assertEqual(result["summary"]["totalNodes"], 50)
        self.assertIn("sampleAnalysis", result["summary"])

    def test_get_topology_unexpected_format(self):
        """Test get_topology with unexpected data format"""
        mock_result = {"unexpected": "format"}

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("error", result)

    def test_get_topology_with_invalid_node(self):
        """Test get_topology with invalid node format"""
        mock_result = {
            "nodes": ["invalid_node", {"id": "n1", "plugin": "host", "label": "Host"}],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)

    def test_get_topology_with_long_labels(self):
        """Test get_topology with long node labels (truncation at 80 chars)"""
        long_label = "A" * 100
        mock_result = {
            "nodes": [{"id": "n1", "plugin": "host", "label": long_label}],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        # Check that label was truncated in sample nodes (at 80 chars, not 40)
        if result.get("sampleNodes"):
            self.assertLessEqual(len(result["sampleNodes"][0]["label"]), 80)

    def test_get_topology_with_long_ids(self):
        """Test get_topology with long node IDs (no truncation - full IDs preserved)"""
        long_id = "A" * 100
        mock_result = {
            "nodes": [{"id": long_id, "plugin": "host", "label": "Host"}],
            "edges": []
        }

        mock_response = MagicMock()
        mock_response.data = json.dumps(mock_result).encode('utf-8')
        self.topology_api.get_topology_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_topology())

        self.assertIn("summary", result)
        # Verify that full IDs are preserved (not truncated) for lookups
        if result.get("sampleNodes"):
            self.assertEqual(result["sampleNodes"][0]["id"], long_id)


if __name__ == '__main__':
    unittest.main()
