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
            # Check if catalog_api attribute exists, if not try to find any *_api attribute
            api_client = None
            if hasattr(self, 'catalog_api'):
                api_client = self.catalog_api
            else:
                # Find any attribute ending with '_api'
                for attr_name in dir(self):
                    if attr_name.endswith('_api'):
                        api_client = getattr(self, attr_name)
                        break

            if api_client is None:
                # Create a mock API client if none exists
                api_client = MagicMock()

            kwargs['api_client'] = api_client
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
_mocks = {
    'instana_client': MagicMock(),
    'instana_client.api': MagicMock(),
    'instana_client.api.infrastructure_catalog_api': MagicMock(),
    'instana_client.configuration': MagicMock(),
    'instana_client.api_client': MagicMock(),
}

# Save original modules
_original_modules = {}
for module_name in _mocks:
    if module_name in sys.modules:
        _original_modules[module_name] = sys.modules[module_name]

# Apply mocks
for module_name, mock_obj in _mocks.items():
    sys.modules[module_name] = mock_obj

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_catalog_api = MagicMock()

# Add __name__ attribute to mock classes
mock_catalog_api.__name__ = "InfrastructureCatalogApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_catalog_api'].InfrastructureCatalogApi = mock_catalog_api

# Mock fastmcp and mcp modules before importing src.core.utils
sys.modules['fastmcp'] = MagicMock()
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()

# Import src.core.utils first to ensure it's available for patching
import src.core.utils

# Patch the with_header_auth decorator
with patch.object(src.core.utils, 'with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.infrastructure.infrastructure_catalog import InfrastructureCatalogMCPTools

# Note: We don't clean up mocks here because it interferes with pytest's test discovery
# The mocks will remain in sys.modules for the duration of the test run

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

        def bind_mock_api(method_name):
            original = getattr(InfrastructureCatalogMCPTools, method_name)

            @wraps(original)
            async def patched(*args, **kwargs):
                kwargs["api_client"] = self.catalog_api
                return await original(self.client, *args, **kwargs)

            setattr(self.client, method_name, patched)

        for method_name in (
            "get_available_payload_keys_by_plugin_id",
            "get_infrastructure_catalog_metrics",
            "get_infrastructure_catalog_plugins",
            "get_infrastructure_catalog_plugins_with_custom_metrics",
            "get_tag_catalog",
            "get_tag_catalog_all",
            "get_infrastructure_catalog_search_fields",
        ):
            bind_mock_api(method_name)

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_available_payload_keys_missing_plugin_id(self):
        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id=""))
        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_get_available_payload_keys_dict_result(self):
        mock_result = {"payload_keys": ["k1", "k2"]}
        self.catalog_api.get_available_payload_keys_by_plugin_id.return_value = mock_result

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result, mock_result)

    def test_get_available_payload_keys_list_result(self):
        self.catalog_api.get_available_payload_keys_by_plugin_id.return_value = ["k1", "k2"]

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result["payload_keys"], ["k1", "k2"])
        self.assertEqual(result["plugin_id"], "host")

    def test_get_available_payload_keys_string_result(self):
        self.catalog_api.get_available_payload_keys_by_plugin_id.return_value = "payload not available"

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="db2Database"))

        self.assertEqual(result["message"], "payload not available")
        self.assertEqual(result["plugin_id"], "db2Database")

    def test_get_available_payload_keys_fallback_json_list(self):
        response = MagicMock()
        response.status = 200
        response.data = b'["key1", "key2"]'
        self.catalog_api.get_available_payload_keys_by_plugin_id.side_effect = Exception("sdk failed")
        self.catalog_api.get_available_payload_keys_by_plugin_id_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result["payload_keys"], ["key1", "key2"])
        self.assertEqual(result["plugin_id"], "host")

    def test_get_available_payload_keys_fallback_non_json_string(self):
        response = MagicMock()
        response.status = 200
        response.data = b"plain text response"
        self.catalog_api.get_available_payload_keys_by_plugin_id.side_effect = Exception("sdk failed")
        self.catalog_api.get_available_payload_keys_by_plugin_id_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result["message"], "plain text response")
        self.assertEqual(result["plugin_id"], "host")

    def test_get_available_payload_keys_fallback_http_error(self):
        response = MagicMock()
        response.status = 500
        response.data = b""
        self.catalog_api.get_available_payload_keys_by_plugin_id.side_effect = Exception("sdk failed")
        self.catalog_api.get_available_payload_keys_by_plugin_id_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    def test_get_infrastructure_catalog_metrics_missing_plugin(self):
        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin=""))
        self.assertEqual(result, {"error": "plugin parameter is required"})

    def test_get_infrastructure_catalog_metrics_list_of_dicts(self):
        response = MagicMock()
        response.status = 200
        response.data = b'[{"metricId": "cpu.usage"}, {"label": "memory.used"}, {"other": "value"}]'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        self.assertEqual(result['metrics'], ["cpu.usage", "memory.used", "{'other': 'value'}"])
        self.assertEqual(result['plugin'], "host")
        self.assertEqual(result['total'], 3)

    def test_get_infrastructure_catalog_metrics_to_dict_with_metrics_field_not_list(self):
        response = MagicMock()
        response.status = 200
        response.data = b'{"metrics": "invalid"}'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        # The implementation now returns error dict for unexpected formats
        self.assertEqual(result, {"error": "Unexpected response format for plugin host"})

    def test_get_infrastructure_catalog_metrics_to_dict_unexpected_structure(self):
        response = MagicMock()
        response.status = 200
        response.data = b'{"unexpected": []}'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        # The implementation now returns error dict for unexpected formats
        self.assertEqual(result, {"error": "Unexpected response format for plugin host"})

    def test_get_infrastructure_catalog_plugins_returns_cached_list(self):
        """Test that get_infrastructure_catalog_plugins returns cached list of 422 plugins"""
        result = asyncio.run(self.client.get_infrastructure_catalog_plugins())

        # Verify structure
        self.assertIn("plugins", result)
        self.assertIn("message", result)
        self.assertIn("total_available", result)
        self.assertIn("note", result)

        # Verify it returns exactly 422 plugins
        self.assertEqual(len(result["plugins"]), 422)
        self.assertEqual(result["total_available"], 422)

        # Verify message indicates cached response
        self.assertIn("cached response", result["note"])

        # Verify some known plugins are in the list
        self.assertIn("host", result["plugins"])
        self.assertIn("containerd", result["plugins"])
        self.assertIn("jvmRuntimePlatform", result["plugins"])
        self.assertIn("kubernetesPod", result["plugins"])
        self.assertIn("docker", result["plugins"])

    def test_get_infrastructure_catalog_plugins_no_api_call(self):
        """Test that get_infrastructure_catalog_plugins doesn't make API calls"""
        # Set up a mock that would fail if called
        self.catalog_api.get_infrastructure_catalog_plugins.side_effect = Exception("API should not be called")
        self.catalog_api.get_infrastructure_catalog_plugins_without_preload_content.side_effect = Exception("API should not be called")

        # Should still succeed because it uses cached data
        result = asyncio.run(self.client.get_infrastructure_catalog_plugins())

        self.assertEqual(len(result["plugins"]), 422)
        self.assertIn("cached response", result["note"])

        # Verify API was never called
        self.catalog_api.get_infrastructure_catalog_plugins.assert_not_called()
        self.catalog_api.get_infrastructure_catalog_plugins_without_preload_content.assert_not_called()

    def test_get_infrastructure_catalog_plugins_all_plugins_present(self):
        """Test that all expected plugins are present in cached list"""
        result = asyncio.run(self.client.get_infrastructure_catalog_plugins())

        plugins = result["plugins"]

        # Test a comprehensive sample of plugins across different categories
        expected_plugins = [
            # Infrastructure
            "host", "process", "docker", "containerd", "podman", "crio",
            # Kubernetes
            "kubernetes", "kubernetesCluster", "kubernetesNode", "kubernetesPod",
            "kubernetesDeployment", "kubernetesService", "kubernetesDaemonSet",
            "kubernetesStatefulSet", "kubernetesReplicaSet", "kubernetesJob",
            # Cloud providers (specific services, not generic "aws")
            "azure", "gce", "ec2", "awsRds", "awsS3", "awsLambdaFunction",
            # Databases
            "mongoDb", "redis", "mySqlDatabase", "postgreSqlDatabase", "oracleDB",
            "cassandraCluster", "elasticsearchCluster", "db2Database",
            # Application servers
            "jvmRuntimePlatform", "nodeJsRuntimePlatform", "pythonRuntimePlatform",
            "tomcatApplicationContainer", "webSphereLibertyApplicationContainer",
            # Messaging
            "kafka", "rabbitMq", "activeMQ", "ibmMqQueue",
            # Monitoring
            "application", "service", "endpoint", "website", "mobileApp",
            # OpenTelemetry
            "openTelemetry", "otelHost", "otelProcess", "oTelK8sContainer",
            "oTelK8sPod", "oTelK8sNode", "oTelK8sCluster", "oTelLLM"
        ]

        for plugin in expected_plugins:
            self.assertIn(plugin, plugins, f"Expected plugin '{plugin}' not found in cached list")

    def test_get_infrastructure_catalog_plugins_with_custom_metrics_list(self):
        response = MagicMock()
        response.status = 200
        response.data = b'[{"plugin": "host"}, {"plugin": "jvm"}]'
        self.catalog_api.get_infrastructure_catalog_plugins_with_custom_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_plugins_with_custom_metrics())

        self.assertEqual(result["plugins_with_custom_metrics"], [{"plugin": "host"}, {"plugin": "jvm"}])

    def test_get_tag_catalog_missing_plugin(self):
        result = asyncio.run(self.client.get_tag_catalog(plugin=""))
        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_get_tag_catalog_sdk_success(self):
        mock_result = {"tags": ["host.name", "zone"]}
        self.catalog_api.get_tag_catalog.return_value = mock_result

        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        self.assertEqual(result, mock_result)

    def test_get_tag_catalog_fallback_406_json(self):
        class NotAcceptableError(Exception):
            status = 406

            def __str__(self):
                return "406 Not Acceptable"

        self.catalog_api.get_tag_catalog.side_effect = NotAcceptableError()
        response = MagicMock()
        response.status = 200
        response.data = b'{"tags": ["host.name", "zone"]}'
        self.catalog_api.get_tag_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        self.assertEqual(result, {"tags": ["host.name", "zone"]})

    def test_get_tag_catalog_fallback_pydantic_error(self):
        """Test get_tag_catalog with Pydantic validation error - string matching triggers fallback"""
        # The implementation checks for pydantic errors by string matching (lines 482-490)
        # It looks for ("pydantic" in err_str and "validation" in err_str) or ("validation error" in err_str)
        # When detected, it calls the fallback method which successfully returns the result

        class PydanticError(Exception):
            def __str__(self):
                return "validation error for pydantic"

        self.catalog_api.get_tag_catalog.side_effect = PydanticError()
        response = MagicMock()
        response.status = 200
        response.data = b'{"tags": ["tag1"]}'
        self.catalog_api.get_tag_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        # The fallback method successfully returns the parsed result
        self.assertIn("tags", result)
        self.assertEqual(result["tags"], ["tag1"])

    def test_get_tag_catalog_fallback_http_error(self):
        """Test get_tag_catalog fallback with HTTP error"""
        self.catalog_api.get_tag_catalog.side_effect = Exception("406 Not Acceptable")
        response = MagicMock()
        response.status = 500
        self.catalog_api.get_tag_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    def test_get_tag_catalog_fallback_json_decode_error(self):
        """Test get_tag_catalog fallback with JSON decode error"""
        self.catalog_api.get_tag_catalog.side_effect = Exception("406 Not Acceptable")
        response = MagicMock()
        response.status = 200
        response.data = b"invalid json"
        self.catalog_api.get_tag_catalog_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        self.assertIn("error", result)
        self.assertIn("Failed to parse JSON", result["error"])

    def test_get_tag_catalog_non_406_error(self):
        """Test get_tag_catalog with non-406 error"""
        self.catalog_api.get_tag_catalog.side_effect = Exception("Some other error")

        result = asyncio.run(self.client.get_tag_catalog(plugin="host"))

        self.assertIn("error", result)
        self.assertIn("Failed to get tag catalog", result["error"])

    def test_get_tag_catalog_all_success(self):
        """Test get_tag_catalog_all with successful response"""
        mock_result = {
            "tagTree": [
                {
                    "label": "Infrastructure",
                    "children": [
                        {"label": "host.name"},
                        {"label": "zone"}
                    ]
                }
            ]
        }
        self.catalog_api.get_tag_catalog_all.return_value = mock_result

        result = asyncio.run(self.client.get_tag_catalog_all())

        self.assertIn("allLabels", result)
        self.assertIn("host.name", result["allLabels"])
        self.assertIn("zone", result["allLabels"])

    def test_get_tag_catalog_all_fallback(self):
        """Test get_tag_catalog_all with fallback method"""
        self.catalog_api.get_tag_catalog_all.side_effect = Exception("SDK failed")
        response = MagicMock()
        response.status = 200
        response.data = b'{"tagTree": [{"label": "Cat", "children": [{"label": "tag1"}]}]}'
        self.catalog_api.get_tag_catalog_all_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog_all())

        self.assertIn("allLabels", result)
        self.assertIn("tag1", result["allLabels"])

    def test_get_tag_catalog_all_fallback_http_error(self):
        """Test get_tag_catalog_all fallback with HTTP error"""
        self.catalog_api.get_tag_catalog_all.side_effect = Exception("SDK failed")
        response = MagicMock()
        response.status = 401
        self.catalog_api.get_tag_catalog_all_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog_all())

        self.assertIn("error", result)
        self.assertIn("Authentication failed", result["error"])

    def test_get_tag_catalog_all_fallback_403_error(self):
        """Test get_tag_catalog_all fallback with 403 error"""
        self.catalog_api.get_tag_catalog_all.side_effect = Exception("SDK failed")
        response = MagicMock()
        response.status = 403
        self.catalog_api.get_tag_catalog_all_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog_all())

        self.assertIn("error", result)
        self.assertIn("Authentication failed", result["error"])

    def test_get_tag_catalog_all_fallback_json_error(self):
        """Test get_tag_catalog_all fallback with JSON decode error"""
        self.catalog_api.get_tag_catalog_all.side_effect = Exception("SDK failed")
        response = MagicMock()
        response.status = 200
        response.data = b"invalid json"
        self.catalog_api.get_tag_catalog_all_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_tag_catalog_all())

        self.assertIn("error", result)
        self.assertIn("Failed to parse JSON", result["error"])

    def test_get_tag_catalog_all_exception(self):
        """Test get_tag_catalog_all with general exception"""
        self.catalog_api.get_tag_catalog_all.side_effect = Exception("Test error")
        self.catalog_api.get_tag_catalog_all_without_preload_content.side_effect = Exception("Fallback error")

        result = asyncio.run(self.client.get_tag_catalog_all())

        self.assertIn("error", result)

    def test_summarize_tag_catalog_empty(self):
        """Test _summarize_tag_catalog with empty catalog"""
        result = self.client._summarize_tag_catalog({})

        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["allLabels"]), 0)

    def test_summarize_tag_catalog_no_children(self):
        """Test _summarize_tag_catalog with categories but no children"""
        catalog = {
            "tagTree": [
                {"label": "Category1"},
                {"label": "Category2", "children": []}
            ]
        }

        result = self.client._summarize_tag_catalog(catalog)

        self.assertEqual(result["count"], 0)

    def test_summarize_tag_catalog_with_duplicates(self):
        """Test _summarize_tag_catalog removes duplicates"""
        catalog = {
            "tagTree": [
                {"label": "Cat1", "children": [{"label": "tag1"}, {"label": "tag2"}]},
                {"label": "Cat2", "children": [{"label": "tag1"}, {"label": "tag3"}]}
            ]
        }

        result = self.client._summarize_tag_catalog(catalog)

        self.assertEqual(result["count"], 3)
        self.assertIn("tag1", result["allLabels"])
        self.assertIn("tag2", result["allLabels"])
        self.assertIn("tag3", result["allLabels"])

    def test_get_infrastructure_catalog_search_fields_success(self):
        """Test get_infrastructure_catalog_search_fields with successful response"""
        response = MagicMock()
        response.status = 200
        response.data = b'[{"keyword": "host.name"}, {"keyword": "zone"}]'
        self.catalog_api.get_infrastructure_catalog_search_fields_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_search_fields())

        self.assertIn("search_fields", result)
        self.assertEqual(len(result["search_fields"]), 2)
        self.assertIn("host.name", result["search_fields"])

    def test_get_infrastructure_catalog_search_fields_with_getattr(self):
        """Test get_infrastructure_catalog_search_fields using getattr"""
        response = MagicMock()
        response.status = 200
        response.data = b'[{"keyword": "test.keyword"}]'
        self.catalog_api.get_infrastructure_catalog_search_fields_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_search_fields())

        self.assertIn("search_fields", result)
        self.assertIn("test.keyword", result["search_fields"])

    def test_get_infrastructure_catalog_search_fields_exception(self):
        """Test get_infrastructure_catalog_search_fields with exception"""
        self.catalog_api.get_infrastructure_catalog_search_fields.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_infrastructure_catalog_search_fields())

        self.assertIn("error", result)

    def test_get_infrastructure_catalog_search_fields_skip_invalid(self):
        """Test get_infrastructure_catalog_search_fields skips invalid fields"""
        response = MagicMock()
        response.status = 200
        response.data = b'[{"invalid": "field"}, {"keyword": "valid.keyword"}]'
        self.catalog_api.get_infrastructure_catalog_search_fields_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_search_fields())

        self.assertIn("search_fields", result)
        self.assertEqual(len(result["search_fields"]), 1)
        self.assertIn("valid.keyword", result["search_fields"])

    def test_get_infrastructure_catalog_metrics_list_of_strings(self):
        """Test get_infrastructure_catalog_metrics with list of strings"""
        response = MagicMock()
        response.status = 200
        response.data = b'["metric1", "metric2", "metric3"]'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        self.assertEqual(result['metrics'], ["metric1", "metric2", "metric3"])
        self.assertEqual(result['plugin'], "host")
        self.assertEqual(result['total'], 3)

    def test_get_infrastructure_catalog_metrics_to_dict_list(self):
        """Test get_infrastructure_catalog_metrics with to_dict returning list"""
        response = MagicMock()
        response.status = 200
        response.data = b'[{"metricId": "m1"}, {"metricId": "m2"}]'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        self.assertEqual(result['metrics'], ["m1", "m2"])
        self.assertEqual(result['plugin'], "host")
        self.assertEqual(result['total'], 2)

    def test_get_infrastructure_catalog_metrics_to_dict_with_metrics(self):
        """Test get_infrastructure_catalog_metrics with metrics field"""
        response = MagicMock()
        response.status = 200
        response.data = b'[{"metricId": "m1"}, "m2"]'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        self.assertEqual(result['metrics'], ["m1", "m2"])
        self.assertEqual(result['plugin'], "host")
        self.assertEqual(result['total'], 2)

    def test_get_infrastructure_catalog_metrics_unexpected_type(self):
        """Test get_infrastructure_catalog_metrics with unexpected result type"""
        response = MagicMock()
        response.status = 200
        response.data = b'12345'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        # When parsing "12345" as JSON, it becomes an integer, which is unexpected
        self.assertEqual(result, {"error": "Unexpected response format for plugin host"})

    def test_get_infrastructure_catalog_metrics_exception(self):
        """Test get_infrastructure_catalog_metrics with exception"""
        self.catalog_api.get_infrastructure_catalog_metrics.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        self.assertIn("error", result)
        self.assertIn("Failed to get infrastructure catalog metrics", result["error"])

    def test_get_infrastructure_catalog_metrics_with_filter(self):
        """Test get_infrastructure_catalog_metrics with filter parameter"""
        response = MagicMock()
        response.status = 200
        response.data = b'["metric1"]'
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host", filter="custom"))

        self.assertEqual(result['metrics'], ["metric1"])
        self.assertEqual(result['plugin'], "host")
        self.assertEqual(result['total'], 1)
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.assert_called_once_with(plugin="host", filter="custom")

    def test_get_plugin_schema_success(self):
        """Test get_plugin_schema successfully combines metrics and tags"""
        # Mock metrics response
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = MagicMock(
            status=200,
            data=b'["metric1", "metric2", "metric3"]'
        )

        # Mock tags response
        self.catalog_api.get_tag_catalog.return_value = {
            "tagTree": {
                "type": "CATEGORY",
                "children": [
                    {"type": "TAG", "tagName": "host.name"},
                    {"type": "TAG", "tagName": "host.ip"}
                ]
            }
        }

        result = asyncio.run(self.client.get_plugin_schema(plugin="host"))

        self.assertEqual(result["plugin"], "host")
        self.assertEqual(len(result["metrics"]), 3)
        self.assertIn("metric1", result["metrics"])
        self.assertEqual(len(result["tags"]), 2)
        self.assertIn("host.name", result["tags"])
        self.assertIn("host.ip", result["tags"])
        self.assertEqual(result["summary"]["total_metrics"], 3)
        self.assertEqual(result["summary"]["total_tags"], 2)
        self.assertFalse(result["summary"]["has_errors"])

    def test_get_plugin_schema_missing_plugin(self):
        """Test get_plugin_schema with missing plugin parameter"""
        result = asyncio.run(self.client.get_plugin_schema(plugin=""))

        self.assertIn("error", result)
        self.assertIn("required", result["error"])

    def test_get_plugin_schema_metrics_error(self):
        """Test get_plugin_schema handles metrics error"""
        # Mock metrics to return error
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = MagicMock(
            status=400,
            data=b''
        )

        # Mock tags response (successful)
        self.catalog_api.get_tag_catalog.return_value = {
            "tagTree": {
                "children": [{"type": "TAG", "tagName": "tag1"}]
            }
        }

        result = asyncio.run(self.client.get_plugin_schema(plugin="invalid"))

        self.assertEqual(result["plugin"], "invalid")
        self.assertEqual(len(result["metrics"]), 0)
        self.assertTrue(len(result["errors"]) > 0)
        self.assertTrue(result["summary"]["has_errors"])

    def test_get_plugin_schema_tags_error(self):
        """Test get_plugin_schema handles tags error"""
        # Mock metrics response (successful)
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = MagicMock(
            status=200,
            data=b'["metric1"]'
        )

        # Mock tags to return error
        self.catalog_api.get_tag_catalog.return_value = {"error": "Failed to get tags"}

        result = asyncio.run(self.client.get_plugin_schema(plugin="host"))

        self.assertEqual(result["plugin"], "host")
        self.assertEqual(len(result["metrics"]), 1)
        self.assertEqual(len(result["tags"]), 0)
        self.assertTrue(len(result["errors"]) > 0)
        self.assertIn("Tags:", result["errors"][0])

    def test_get_plugin_schema_with_filter(self):
        """Test get_plugin_schema with filter parameter"""
        # Mock metrics response
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = MagicMock(
            status=200,
            data=b'["custom_metric1"]'
        )

        # Mock tags response
        self.catalog_api.get_tag_catalog.return_value = {"tagTree": {"children": []}}

        result = asyncio.run(self.client.get_plugin_schema(plugin="host", filter="custom"))

        self.assertEqual(result["plugin"], "host")
        self.assertIn("custom_metric1", result["metrics"])

    def test_get_plugin_schema_exception(self):
        """Test get_plugin_schema handles general exception"""
        # Force an exception
        with patch.object(self.client, 'get_infrastructure_catalog_metrics', side_effect=Exception("Test error")):
            result = asyncio.run(self.client.get_plugin_schema(plugin="host"))

            # The error is in the errors list, not as a top-level error key
            self.assertTrue(result["summary"]["has_errors"])
            self.assertTrue(len(result["errors"]) > 0)
            self.assertIn("Failed to get metrics", result["errors"][0])

    def test_extract_tag_names_nested_structure(self):
        """Test extract_tag_names_from_tree (moved to utils) with nested tag structure"""
        from src.core.utils import extract_tag_names_from_tree
        tag_data = {
            "tagTree": {
                "type": "CATEGORY",
                "children": [
                    {
                        "type": "CATEGORY",
                        "children": [
                            {"type": "TAG", "tagName": "nested.tag1"},
                            {"type": "TAG", "tagName": "nested.tag2"}
                        ]
                    },
                    {"type": "TAG", "tagName": "root.tag"}
                ]
            }
        }

        result = extract_tag_names_from_tree(tag_data)

        self.assertEqual(len(result), 3)
        self.assertIn("nested.tag1", result)
        self.assertIn("nested.tag2", result)
        self.assertIn("root.tag", result)

    def test_extract_tag_names_tags_array(self):
        """Test extract_tag_names_from_tree (moved to utils) with tags array structure"""
        from src.core.utils import extract_tag_names_from_tree
        tag_data = {
            "tags": [
                {"type": "TAG", "tagName": "tag1"},
                {"type": "TAG", "tagName": "tag2"}
            ]
        }

        result = extract_tag_names_from_tree(tag_data)

        self.assertEqual(len(result), 2)
        self.assertIn("tag1", result)
        self.assertIn("tag2", result)

    def test_extract_tag_names_empty(self):
        """Test extract_tag_names_from_tree (moved to utils) with empty data"""
        from src.core.utils import extract_tag_names_from_tree
        result = extract_tag_names_from_tree({})

        self.assertEqual(len(result), 0)

    def test_extract_tag_names_list_input(self):
        """Test extract_tag_names_from_tree (moved to utils) with list input wrapped in dict"""
        from src.core.utils import extract_tag_names_from_tree
        tag_data = {
            "items": [
                {"type": "TAG", "tagName": "tag1"},
                {"type": "TAG", "tagName": "tag2"}
            ]
        }

        result = extract_tag_names_from_tree(tag_data)

        # The method doesn't traverse arbitrary keys, only specific ones
        # So this should return empty list
        self.assertEqual(len(result), 0)

    def test_get_infrastructure_catalog_plugins_with_custom_metrics_dict(self):
        """Test get_infrastructure_catalog_plugins_with_custom_metrics with dict result"""
        response = MagicMock()
        response.status = 200
        response.data = b'{"plugins": ["p1"]}'
        self.catalog_api.get_infrastructure_catalog_plugins_with_custom_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_plugins_with_custom_metrics())

        self.assertEqual(result, {"plugins": ["p1"]})

    def test_get_infrastructure_catalog_plugins_with_custom_metrics_to_dict(self):
        """Test get_infrastructure_catalog_plugins_with_custom_metrics with to_dict"""
        response = MagicMock()
        response.status = 200
        response.data = b'{"data": "test"}'
        self.catalog_api.get_infrastructure_catalog_plugins_with_custom_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_plugins_with_custom_metrics())

        self.assertEqual(result, {"data": "test"})

    def test_get_infrastructure_catalog_plugins_with_custom_metrics_exception(self):
        """Test get_infrastructure_catalog_plugins_with_custom_metrics with exception"""
        self.catalog_api.get_infrastructure_catalog_plugins_with_custom_metrics.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_infrastructure_catalog_plugins_with_custom_metrics())

        self.assertIn("error", result)

    def test_get_available_payload_keys_to_dict(self):
        """Test get_available_payload_keys_by_plugin_id with to_dict"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"keys": ["k1", "k2"]}
        self.catalog_api.get_available_payload_keys_by_plugin_id.return_value = mock_result

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result, {"keys": ["k1", "k2"]})

    def test_get_available_payload_keys_other_type(self):
        """Test get_available_payload_keys_by_plugin_id with other type"""
        self.catalog_api.get_available_payload_keys_by_plugin_id.return_value = 12345

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result["data"], "12345")

    def test_get_available_payload_keys_fallback_dict(self):
        """Test get_available_payload_keys_by_plugin_id fallback with dict"""
        response = MagicMock()
        response.status = 200
        response.data = b'{"key": "value"}'
        self.catalog_api.get_available_payload_keys_by_plugin_id.side_effect = Exception("sdk failed")
        self.catalog_api.get_available_payload_keys_by_plugin_id_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result, {"key": "value"})

    def test_get_available_payload_keys_fallback_other_type(self):
        """Test get_available_payload_keys_by_plugin_id fallback with other type"""
        response = MagicMock()
        response.status = 200
        response.data = b'123'
        self.catalog_api.get_available_payload_keys_by_plugin_id.side_effect = Exception("sdk failed")
        self.catalog_api.get_available_payload_keys_by_plugin_id_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertEqual(result["data"], 123)

    def test_get_available_payload_keys_fallback_exception(self):
        """Test get_available_payload_keys_by_plugin_id fallback with exception"""
        self.catalog_api.get_available_payload_keys_by_plugin_id.side_effect = Exception("sdk failed")
        self.catalog_api.get_available_payload_keys_by_plugin_id_without_preload_content.side_effect = Exception("fallback failed")

        result = asyncio.run(self.client.get_available_payload_keys_by_plugin_id(plugin_id="host"))

        self.assertIn("error", result)

    def test_get_infrastructure_catalog_metrics_limit_50(self):
        """Test get_infrastructure_catalog_metrics limits to 50 items"""
        # Create 60 metrics
        metrics = [f"metric{i}" for i in range(60)]
        response = MagicMock()
        response.status = 200
        import json
        response.data = json.dumps(metrics).encode('utf-8')
        self.catalog_api.get_infrastructure_catalog_metrics_without_preload_content.return_value = response

        result = asyncio.run(self.client.get_infrastructure_catalog_metrics(plugin="host"))

        # Should be limited to 50
        self.assertEqual(len(result['metrics']), 50)
        self.assertEqual(result['total'], 50)
        self.assertEqual(result['plugin'], "host")



if __name__ == '__main__':
    unittest.main()
