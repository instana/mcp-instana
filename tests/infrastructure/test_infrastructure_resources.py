"""
Unit tests for the InfrastructureResourcesMCPTools class
"""

import asyncio
import importlib
import json
import logging
import os
import sys
import types
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

# Add minimal model modules for post_snapshots
sys.modules['instana_client.models.get_snapshots_query'] = types.ModuleType('instana_client.models.get_snapshots_query')
sys.modules['instana_client.models.time_frame'] = types.ModuleType('instana_client.models.time_frame')

class SimpleModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def to_dict(self):
        def convert(value):
            if hasattr(value, 'to_dict'):
                return value.to_dict()
            if isinstance(value, list):
                return [convert(i) for i in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value

        return {k: convert(v) for k, v in self.__dict__.items()}

sys.modules['instana_client.models.get_snapshots_query'].GetSnapshotsQuery = SimpleModel
sys.modules['instana_client.models.time_frame'].TimeFrame = SimpleModel

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_resources_api = MagicMock()

# Add __name__ attribute to mock classes
mock_resources_api.__name__ = "InfrastructureResourcesApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_resources_api'].InfrastructureResourcesApi = mock_resources_api

def create_infrastructure_resources_client(read_token: str, base_url: str):
    with patch('src.core.utils.with_header_auth', mock_with_header_auth):
        module = importlib.import_module('src.infrastructure.infrastructure_resources')
        module = importlib.reload(module)
        return module.InfrastructureResourcesMCPTools(
            read_token=read_token,
            base_url=base_url,
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
        self.client = create_infrastructure_resources_client(
            read_token=self.read_token,
            base_url=self.base_url,
        )

        # Set up the client's API attribute
        self.client.resources_api = self.resources_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_monitoring_state_success(self):
        """Test get_monitoring_state with successful response"""
        mock_result = {
            "state": "healthy",
            "agents": 10,
            "entities": 250
        }
        self.resources_api.get_monitoring_state.return_value = mock_result

        result = asyncio.run(self.client.get_monitoring_state())

        self.resources_api.get_monitoring_state.assert_called_once()
        self.assertEqual(result, mock_result)

    def test_get_monitoring_state_error(self):
        """Test get_monitoring_state error handling"""
        self.resources_api.get_monitoring_state.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_monitoring_state())

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get monitoring state", (result.get("error") or result.get("message", "")))

    def test_get_snapshot_success(self):
        """Test get_snapshot with successful response via without_preload_content"""
        mock_result = {
            "id": "snap1",
            "timestamp": 1625184000000,
            "data": {"cpu.usage": 50.5}
        }
        response = MagicMock()
        response.status = 200
        response.data = json.dumps(mock_result).encode('utf-8')
        self.resources_api.get_snapshot_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertEqual(result, mock_result)

    def test_get_snapshot_missing_id(self):
        result = asyncio.run(self.client.get_snapshot(snapshot_id=""))
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("required", (result.get("error") or result.get("message", "")))

    def test_get_snapshot_not_found_error(self):
        response = MagicMock()
        response.status = 404
        response.data = b'{"error": "snapshot does not exist"}'
        self.resources_api.get_snapshot_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_snapshot_validation_error_fallback_json(self):
        response = MagicMock()
        response.status = 200
        response.data = b'{"id": "snap1", "label": "Snapshot 1"}'
        self.resources_api.get_snapshot.side_effect = Exception("Validation error")
        self.resources_api.get_snapshot_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertEqual(result["id"], "snap1")
        self.assertEqual(result["label"], "Snapshot 1")

    def test_get_snapshot_http_error(self):
        """Test get_snapshot returns error on non-200 response"""
        response = MagicMock()
        response.status = 404
        response.data = b'{"error": "not found"}'
        self.resources_api.get_snapshot_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertIn("error", result)

    def test_get_snapshot_error(self):
        """Test get_snapshot error handling"""
        self.resources_api.get_snapshot.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get snapshot", (result.get("error") or result.get("message", "")))

    def test_get_snapshots_success(self):
        """Test get_snapshots with successful response"""
        mock_result = [
            {"id": "snap1", "timestamp": 1625184000000},
            {"id": "snap2", "timestamp": 1625184060000}
        ]
        self.resources_api.get_snapshots.return_value = mock_result

        result = asyncio.run(self.client.get_snapshots(
            plugin="host",
            query="entity.tag=production"
        ))

        self.resources_api.get_snapshots.assert_called_once()
        self.assertIn("message", result)

    def test_get_snapshots_detailed_returns_raw_dict(self):
        self.resources_api.get_snapshots.return_value = {"items": [{"snapshotId": "s1"}]}

        result = asyncio.run(self.client.get_snapshots(
            plugin="host",
            query="entity.tag=production",
            detailed=True
        ))

        self.assertEqual(result, {"items": [{"snapshotId": "s1"}]})

    def test_summarize_get_snapshots_response_empty(self):
        result = self.client._summarize_get_snapshots_response({"items": []})

        self.assertEqual(result["total_found"], 0)
        self.assertEqual(result["snapshots"], [])

    def test_summarize_get_snapshots_response_with_aws_ecs_host(self):
        response_data = {
            "items": [
                {
                    "snapshotId": "snap-1",
                    "label": "Task 1",
                    "plugin": "docker",
                    "host": "arn:aws:ecs:us-south-1:123456789012:task/cluster-a/task-123"
                }
            ]
        }

        result = self.client._summarize_get_snapshots_response(response_data)

        self.assertEqual(result["total_found"], 1)
        self.assertIn("AWS ECS Task", result["snapshots"][0]["host_info"])
        self.assertIn("cluster-a", result["snapshots"][0]["host_info"])

    def test_summarize_get_snapshots_response_summary_exception(self):
        result = self.client._summarize_get_snapshots_response({"items": [None]})

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to summarize response", (result.get("error") or result.get("message", "")))

    def test_get_snapshots_error(self):
        """Test get_snapshots error handling"""
        self.resources_api.get_snapshots.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_snapshots(
            plugin="host",
            query="entity.tag=production"
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get snapshots", (result.get("error") or result.get("message", "")))

    def test_post_snapshots_string_ids_success(self):
        response = MagicMock()
        response.status = 200
        response.data = b'{"items":[{"snapshotId":"snap1","plugin":"jvmRuntimePlatform","label":"JVM","entityId":"e1","from":1,"to":2,"tags":[],"data":{"name":"Test JVM","pid":123,"jvm.version":"17","jvm.vendor":"OpenJDK","jvm.name":"TestJVM","jvm.build":"abc","memory.max":1024,"jvm.pools":{},"jvm.args":[],"jvm.collectors":[]}}]}'
        self.resources_api.post_snapshots_without_preload_content.return_value = response

        result = asyncio.run(self.client.post_snapshots(snapshot_ids='snap1,snap2', detailed=False))

        self.assertEqual(result["total_snapshots"], 1)
        self.assertEqual(result["snapshots"][0]["snapshotId"], "snap1")
        self.assertEqual(result["snapshots"][0]["plugin"], "jvmRuntimePlatform")

    def test_post_snapshots_missing_ids(self):
        result = asyncio.run(self.client.post_snapshots(snapshot_ids=[], detailed=False))
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("snapshot_ids parameter is required", (result.get("error") or result.get("message", "")))

    def test_post_snapshots_status_error(self):
        response = MagicMock()
        response.status = 500
        response.data = b'Internal error'
        self.resources_api.post_snapshots_without_preload_content.return_value = response

        result = asyncio.run(self.client.post_snapshots(snapshot_ids=['snap1'], detailed=False))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("SDK returned status 500", (result.get("error") or result.get("message", "")))

    def test_software_versions_list_response(self):
        self.resources_api.software_versions.return_value = [
            {"name": "App1"},
            {"name": "App2"}
        ]

        result = asyncio.run(self.client.software_versions())

        self.assertEqual(result["items"], [{"name": "App1"}, {"name": "App2"}])

    def test_software_versions_with_tag_tree(self):
        mock_result = {
            "tagTree": [
                {"label": "Service", "children": [{"tagName": "service.name", "description": "Service name"}]}
            ]
        }
        self.resources_api.software_versions.return_value = MagicMock(to_dict=MagicMock(return_value=mock_result))

        result = asyncio.run(self.client.software_versions())

        self.assertIn("tagNames", result)
        self.assertEqual(result["tagNames"][0]["tagName"], "service.name")

    def test_software_versions_unexpected_format(self):
        """Test software_versions with unexpected result format"""
        class UnexpectedType:
            pass

        self.resources_api.software_versions.return_value = UnexpectedType()

        result = asyncio.run(self.client.software_versions())

        self.assertIn("data", result)

    def test_software_versions_with_large_items_list(self):
        """Test software_versions with more than 10 items"""
        mock_result = {
            "items": [{"name": f"App{i}"} for i in range(15)]
        }
        self.resources_api.software_versions.return_value = mock_result

        result = asyncio.run(self.client.software_versions())

        self.assertIn("summary", result)
        self.assertEqual(len(result["items"]), 10)

    def test_get_plugin_payload_success(self):
        """Test get_plugin_payload with successful response"""
        mock_result = {"payload": "data"}
        self.resources_api.get_plugin_payload.return_value = mock_result

        result = asyncio.run(self.client.get_plugin_payload(
            snapshot_id="snap1",
            payload_key="key1"
        ))

        self.assertEqual(result, mock_result)

    def test_get_plugin_payload_error(self):
        """Test get_plugin_payload error handling"""
        self.resources_api.get_plugin_payload.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_plugin_payload(
            snapshot_id="snap1",
            payload_key="key1"
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_snapshot_with_to_dict_method(self):
        """Test get_snapshot returns parsed JSON from without_preload_content"""
        mock_result = {"id": "snap1", "data": "test"}
        response = MagicMock()
        response.status = 200
        response.data = json.dumps(mock_result).encode('utf-8')
        self.resources_api.get_snapshot_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertEqual(result["id"], "snap1")

    def test_get_snapshot_with_other_type(self):
        """Test get_snapshot returns error on exception"""
        self.resources_api.get_snapshot_without_preload_content.side_effect = Exception("unexpected")

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertIn("error", result)
        self.assertIn("Failed to get snapshot", result["error"])

    def test_get_snapshot_validation_error_fallback_http_error(self):
        """Test get_snapshot validation error with HTTP error in fallback"""
        response = MagicMock()
        response.status = 404
        self.resources_api.get_snapshot.side_effect = Exception("Validation error")
        self.resources_api.get_snapshot_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_snapshot_validation_error_fallback_exception(self):
        """Test get_snapshot validation error with exception in fallback"""
        self.resources_api.get_snapshot.side_effect = Exception("Validation error")
        self.resources_api.get_snapshot_without_preload_content.side_effect = Exception("Fallback error")

        result = asyncio.run(self.client.get_snapshot(snapshot_id="snap1"))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_snapshots_with_to_dict_method(self):
        """Test get_snapshots when result has to_dict method"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"items": [{"snapshotId": "s1"}]}
        self.resources_api.get_snapshots.return_value = mock_result

        result = asyncio.run(self.client.get_snapshots())

        self.assertIn("message", result)

    def test_get_snapshots_with_other_type(self):
        """Test get_snapshots when result is neither dict nor has to_dict"""
        self.resources_api.get_snapshots.return_value = "string_result"

        result = asyncio.run(self.client.get_snapshots())

        self.assertIn("message", result)

    def test_post_snapshots_with_list_string(self):
        """Test post_snapshots with list-formatted string"""
        response = MagicMock()
        response.status = 200
        response.data = b'{"items":[]}'
        self.resources_api.post_snapshots_without_preload_content.return_value = response

        result = asyncio.run(self.client.post_snapshots(snapshot_ids='["snap1","snap2"]'))

        self.assertEqual(result["total_snapshots"], 0)

    def test_post_snapshots_detailed_true(self):
        """Test post_snapshots with detailed=True"""
        response = MagicMock()
        response.status = 200
        response.data = b'{"items":[{"snapshotId":"snap1"}]}'
        self.resources_api.post_snapshots_without_preload_content.return_value = response

        result = asyncio.run(self.client.post_snapshots(snapshot_ids=['snap1'], detailed=True))

        self.assertIn("items", result)

    def test_summarize_snapshots_response_nodejs(self):
        """Test _summarize_snapshots_response with Node.js snapshot"""
        response_data = {
            "items": [{
                "snapshotId": "snap1",
                "plugin": "nodeJsRuntimePlatform",
                "label": "Node App",
                "entityId": "e1",
                "from": 1,
                "to": 2,
                "tags": [],
                "data": {
                    "name": "my-app",
                    "version": "1.0.1",
                    "description": "Test app",
                    "pid": 1234,
                    "versions": {"node": "16.0.0", "v8": "9.0.0", "uv": "1.0.1"},
                    "sensorVersion": "1.0.1",
                    "dependencies": {"express": "4.0.0"},
                    "startTime": 1234567890,
                    "http": {"/api": {}},
                    "gc.statsSupported": True,
                    "libuv.statsSupported": True
                }
            }]
        }

        result = self.client._summarize_snapshots_response(response_data)

        self.assertEqual(result["total_snapshots"], 1)
        self.assertIn("key_info", result["snapshots"][0])

    def test_summarize_snapshots_response_generic(self):
        """Test _summarize_snapshots_response with generic plugin"""
        response_data = {
            "items": [{
                "snapshotId": "snap1",
                "plugin": "customPlugin",
                "label": "Custom",
                "entityId": "e1",
                "from": 1,
                "to": 2,
                "tags": [],
                "data": {"field1": "value1", "field2": "value2"}
            }]
        }

        result = self.client._summarize_snapshots_response(response_data)

        self.assertEqual(result["total_snapshots"], 1)
        self.assertIn("data_keys", result["snapshots"][0]["key_info"])

    def test_summarize_snapshots_response_error(self):
        """Test _summarize_snapshots_response with error - function handles gracefully"""
        response_data = {"items": [{"invalid": "data"}]}

        result = self.client._summarize_snapshots_response(response_data)

        # The function handles missing fields gracefully, returning None values
        self.assertEqual(result["total_snapshots"], 1)
        self.assertIsNone(result["snapshots"][0]["snapshotId"])

    def test_post_snapshots_exception(self):
        """Test post_snapshots with exception"""
        self.resources_api.post_snapshots_without_preload_content.side_effect = Exception("Test error")

        result = asyncio.run(self.client.post_snapshots(snapshot_ids=['snap1']))

        self.assertTrue("error" in result or result.get("elicitation_needed"))


if __name__ == '__main__':
    unittest.main()
