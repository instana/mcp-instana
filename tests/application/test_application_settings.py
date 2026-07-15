"""
Unit tests for the ApplicationSettingsMCPTools class.

Tests focus on the public execute_settings_operation method which routes
to private internal methods. Tests for the private methods themselves
are removed since they are internal implementation details.
"""

import asyncio
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import AsyncMock, MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass


# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.application.application_settings')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.settings_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# Set up mock modules (defined outside patch.dict so they persist after import)
mock_mcp = MagicMock()
mock_mcp_types = MagicMock()
mock_tool_annotations = MagicMock()
mock_mcp_types.ToolAnnotations = mock_tool_annotations

mock_instana_client = MagicMock()
mock_instana_api = MagicMock()
mock_settings_api_mod = MagicMock()
mock_instana_api_client = MagicMock()
mock_instana_configuration = MagicMock()
mock_instana_models = MagicMock()
mock_app_config_mod = MagicMock()
mock_endpoint_config_mod = MagicMock()
mock_manual_service_config_mod = MagicMock()
mock_new_app_config_mod = MagicMock()
mock_new_manual_service_config_mod = MagicMock()
mock_service_config_mod = MagicMock()
mock_fastmcp = MagicMock()
mock_fastmcp_server = MagicMock()
mock_fastmcp_deps = MagicMock()
mock_pydantic = MagicMock()

# Mock the get_http_headers function
mock_get_http_headers = MagicMock(return_value={})
mock_fastmcp_deps.get_http_headers = mock_get_http_headers

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_settings_api = MagicMock()
mock_application_config = MagicMock()
mock_endpoint_config = MagicMock()
mock_manual_service_config = MagicMock()
mock_new_application_config = MagicMock()
mock_new_manual_service_config = MagicMock()
mock_service_config = MagicMock()

# Add __name__ attribute to mock classes
mock_settings_api.__name__ = "ApplicationSettingsApi"
mock_application_config.__name__ = "ApplicationConfig"
mock_endpoint_config.__name__ = "EndpointConfig"
mock_manual_service_config.__name__ = "ManualServiceConfig"
mock_new_application_config.__name__ = "NewApplicationConfig"
mock_new_manual_service_config.__name__ = "NewManualServiceConfig"
mock_service_config.__name__ = "ServiceConfig"

mock_instana_configuration.Configuration = mock_configuration
mock_instana_api_client.ApiClient = mock_api_client
mock_instana_api.ApplicationSettingsApi = mock_settings_api
mock_instana_models.ApplicationConfig = mock_application_config
mock_instana_models.EndpointConfig = mock_endpoint_config
mock_instana_models.ManualServiceConfig = mock_manual_service_config
mock_instana_models.NewApplicationConfig = mock_new_application_config
mock_instana_models.NewManualServiceConfig = mock_new_manual_service_config
mock_instana_models.ServiceConfig = mock_service_config
mock_instana_models.TagFilter = MagicMock()
mock_instana_models.TagFilterExpression = MagicMock()

# Mock src.prompts
mock_src_prompts = MagicMock()

# Mock src.core and src.core.utils
mock_src_core = MagicMock()
mock_src_core_utils = MagicMock()


class MockBaseInstanaClient:
    def __init__(self, read_token: str, base_url: str):
        self.read_token = read_token
        self.base_url = base_url
        self.settings_api = None  # Will be set in test setUp

    def get_headers(self, auth_token=None, csrf_token=None):
        """Mock get_headers method"""
        headers = {
            "Authorization": f"apiToken {self.read_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MCP-server/0.8.1"
        }
        if auth_token and csrf_token:
            headers["X-CSRF-TOKEN"] = csrf_token
            headers["Cookie"] = f"instanaAuthToken={auth_token}"
            del headers["Authorization"]
        return headers

    async def make_request(self, endpoint, params=None, method="GET", json=None):
        """Mock make_request method"""
        return {"data": "mock_response"}


from src.core.utils import decode_response as _real_decode_response
from src.core.utils import parse_payload as _real_parse_payload

mock_src_core_utils.BaseInstanaClient = MockBaseInstanaClient
mock_src_core_utils.register_as_tool = lambda *args, **kwargs: lambda func: func
mock_src_core_utils.with_header_auth = mock_with_header_auth
mock_src_core_utils.parse_payload = _real_parse_payload
mock_src_core_utils.decode_response = _real_decode_response

# Build the full mocks dict for patch.dict
_mocks = {
    'mcp': mock_mcp,
    'mcp.types': mock_mcp_types,
    'instana_client': mock_instana_client,
    'instana_client.api': mock_instana_api,
    'instana_client.api.application_settings_api': mock_settings_api_mod,
    'instana_client.api_client': mock_instana_api_client,
    'instana_client.configuration': mock_instana_configuration,
    'instana_client.models': mock_instana_models,
    'instana_client.models.application_config': mock_app_config_mod,
    'instana_client.models.endpoint_config': mock_endpoint_config_mod,
    'instana_client.models.manual_service_config': mock_manual_service_config_mod,
    'instana_client.models.new_application_config': mock_new_app_config_mod,
    'instana_client.models.new_manual_service_config': mock_new_manual_service_config_mod,
    'instana_client.models.service_config': mock_service_config_mod,
    'instana_client.models.tag_filter_all_of_value': MagicMock(),
    'fastmcp': mock_fastmcp,
    'fastmcp.server': mock_fastmcp_server,
    'fastmcp.server.dependencies': mock_fastmcp_deps,
    'pydantic': mock_pydantic,
    'src.prompts': mock_src_prompts,
    'src.core': mock_src_core,
    'src.core.utils': mock_src_core_utils,
}

# Import the actual module FIRST so coverage can track it
# We need to set up the mocks in sys.modules BEFORE importing
_original_modules = {}
for module_name, mock_obj in _mocks.items():
    # Save original module if it exists
    if module_name in sys.modules:
        _original_modules[module_name] = sys.modules[module_name]
    sys.modules[module_name] = mock_obj

# Now import with the decorator patched
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.application.application_settings import ApplicationSettingsMCPTools

# Clean up mocks from sys.modules to prevent interference with other tests
for module_name in _mocks:
    if module_name in _original_modules:
        # Restore original module
        sys.modules[module_name] = _original_modules[module_name]
    elif module_name in sys.modules:
        # Remove mock if there was no original
        del sys.modules[module_name]


class TestApplicationSettingsMCPTools(unittest.TestCase):
    """Test the ApplicationSettingsMCPTools class.

    Tests focus on execute_settings_operation routing. Private methods
    (_get_all_applications_configs, _add_application_config, etc.) are
    internal implementation details and not tested directly.
    """

    def setUp(self):
        """Set up test fixtures"""
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_settings_api.reset_mock()

        # Reset all side_effects to None
        for attr_name in dir(mock_settings_api):
            attr = getattr(mock_settings_api, attr_name)
            if callable(attr) and not attr_name.startswith('_'):
                if hasattr(attr, 'side_effect'):
                    attr.side_effect = None

        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.settings_api = mock_settings_api

        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"

        self.patcher = patch('src.core.utils.with_header_auth', mock_with_header_auth)
        self.patcher.start()

        self.client = ApplicationSettingsMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.client.settings_api = mock_settings_api

        patcher = patch('src.application.application_settings.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_execute_settings_operation_application_get_all(self):
        """Test execute_settings_operation routes application/get_all correctly"""
        expected = [{"id": "app1", "label": "My App"}]
        self.client._get_all_applications_configs = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get_all",
            resource_subtype="application"
        ))

        self.client._get_all_applications_configs.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_application_get(self):
        """Test execute_settings_operation routes application/get correctly"""
        expected = {"id": "app1", "label": "My App"}
        self.client._get_application_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get",
            resource_subtype="application",
            id="app1"
        ))

        self.client._get_application_config.assert_called_once_with("app1", None)
        self.assertEqual(result, expected)

    def test_execute_settings_operation_application_create(self):
        """Test execute_settings_operation routes application/create correctly"""
        expected = {"id": "new-app", "label": "New App"}
        self.client._add_application_config = AsyncMock(return_value=expected)
        payload = {"label": "New App"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="create",
            resource_subtype="application",
            payload=payload
        ))

        self.client._add_application_config.assert_called_once_with(payload, None)
        self.assertEqual(result, expected)

    def test_execute_settings_operation_application_delete(self):
        """Test execute_settings_operation routes application/delete correctly"""
        expected = {"message": "Deleted"}
        self.client._delete_application_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="delete",
            resource_subtype="application",
            id="app1"
        ))

        self.client._delete_application_config.assert_called_once_with("app1", None)
        self.assertEqual(result, expected)

    def test_execute_settings_operation_manual_service_get_all(self):
        """Test execute_settings_operation routes manual_service/get_all correctly"""
        expected = [{"id": "ms1"}]
        self.client._get_all_manual_service_configs = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get_all",
            resource_subtype="manual_service"
        ))

        self.client._get_all_manual_service_configs.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_unsupported_returns_error(self):
        """Test execute_settings_operation returns error for unsupported operation/subtype"""
        result = asyncio.run(self.client.execute_settings_operation(
            operation="unknown_op",
            resource_subtype="unknown_type"
        ))

        self.assertIn("error", result)
        self.assertIn("unknown_op", result["error"])
        self.assertIn("unknown_type", result["error"])

    def test_execute_settings_operation_exception_handling(self):
        """Test execute_settings_operation handles exceptions gracefully"""
        self.client._get_all_applications_configs = AsyncMock(
            side_effect=Exception("API failure")
        )

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get_all",
            resource_subtype="application"
        ))

        self.assertIn("error", result)
        self.assertIn("API failure", result["error"])

    # Tests for _validate_and_prepare_application_payload
    def test_validate_and_prepare_application_payload_missing_label(self):
        """Test validation fails when label is missing"""
        result = self.client._validate_and_prepare_application_payload({})

        self.assertIn("error", result)
        self.assertIn("missing_fields", result)
        self.assertIn("label", result["missing_fields"])

    def test_validate_and_prepare_application_payload_with_label_only(self):
        """Test validation succeeds with label and applies defaults"""
        payload = {"label": "Test App"}
        result = self.client._validate_and_prepare_application_payload(payload)

        self.assertIn("payload", result)
        validated = result["payload"]
        self.assertEqual(validated["label"], "Test App")
        self.assertEqual(validated["scope"], "INCLUDE_ALL_DOWNSTREAM")
        self.assertEqual(validated["boundaryScope"], "ALL")
        self.assertIn("accessRules", validated)
        self.assertIn("tagFilterExpression", validated)

    def test_validate_and_prepare_application_payload_with_string_json(self):
        """Test validation with JSON string payload"""
        import json
        payload_str = json.dumps({"label": "Test App"})
        result = self.client._validate_and_prepare_application_payload(payload_str)

        self.assertIn("payload", result)
        self.assertEqual(result["payload"]["label"], "Test App")

    def test_validate_and_prepare_application_payload_with_invalid_json(self):
        """Test validation with invalid JSON string"""
        result = self.client._validate_and_prepare_application_payload("{invalid json")

        self.assertIn("error", result)

    def test_validate_and_prepare_application_payload_with_tag_filter_expression(self):
        """Test validation with EXPRESSION type tag filter"""
        payload = {
            "label": "Test App",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [
                    {
                        "type": "TAG_FILTER",
                        "name": "service.name",
                        "operator": "EQUALS",
                        "entity": "DESTINATION"
                    }
                ]
            }
        }
        result = self.client._validate_and_prepare_application_payload(payload)

        self.assertIn("payload", result)
        self.assertIn("tagFilterExpression", result["payload"])

    def test_validate_and_prepare_application_payload_with_simple_tag_filter(self):
        """Test validation with TAG_FILTER type — result is a TagFilter model object"""
        payload = {
            "label": "Test App",
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "CONTAINS",
                "entity": "DESTINATION",
                "value": "my-service"
            }
        }
        result = self.client._validate_and_prepare_application_payload(payload)

        self.assertIn("payload", result)
        # tagFilterExpression is now a TagFilter SDK model object (MagicMock in tests),
        # not a plain dict — just confirm it is present and not an error.
        self.assertIn("tagFilterExpression", result["payload"])
        self.assertNotIn("error", result)

    # Tests for application config operations
    def test_add_application_config_no_payload(self):
        """Test _add_application_config with no payload"""
        result = asyncio.run(self.client._add_application_config(None))

        self.assertIn("error", result)
        self.assertIn("payload is required", result["error"])

    def test_add_application_config_success(self):
        """Test _add_application_config with valid payload"""
        # Reset any side_effect from previous tests
        mock_settings_api.add_application_config.side_effect = None

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "new-app", "label": "Test App"}
        mock_settings_api.add_application_config.return_value = mock_result

        payload = {"label": "Test App"}
        result = asyncio.run(self.client._add_application_config(payload))

        self.assertIn("id", result)
        self.assertIn("message", result)

    def test_add_application_config_exception(self):
        """Test _add_application_config handles exceptions"""
        mock_settings_api.add_application_config.side_effect = Exception("API Error")

        payload = {"label": "Test App"}
        result = asyncio.run(self.client._add_application_config(payload))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_get_application_config_no_id(self):
        """Test _get_application_config with no ID"""
        result = asyncio.run(self.client._get_application_config(None))

        self.assertIn("error", result)
        self.assertIn("id is required", result["error"])

    def test_get_application_config_success(self):
        """Test _get_application_config with valid ID"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "app1", "label": "Test App"}
        mock_settings_api.get_application_config.return_value = mock_result

        result = asyncio.run(self.client._get_application_config("app1"))

        self.assertEqual(result["id"], "app1")

    def test_update_application_config_no_id_or_payload(self):
        """Test _update_application_config with missing parameters"""
        result = asyncio.run(self.client._update_application_config(None, None))

        self.assertIn("error", result)

    def test_update_application_config_success(self):
        """Test _update_application_config with valid parameters"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "app1", "label": "Updated"}
        mock_settings_api.put_application_config.return_value = mock_result

        payload = {"label": "Updated", "scope": "INCLUDE_ALL_DOWNSTREAM"}
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("id", result)

    def test_delete_application_config_no_id(self):
        """Test _delete_application_config with no ID"""
        result = asyncio.run(self.client._delete_application_config(None))

        self.assertIn("error", result)

    def test_delete_application_config_success(self):
        """Test _delete_application_config with valid ID"""
        mock_settings_api.delete_application_config.return_value = None

        result = asyncio.run(self.client._delete_application_config("app1"))

        self.assertIn("success", result)
        self.assertTrue(result["success"])

    # Tests for endpoint config operations
    def test_get_all_endpoint_configs_success(self):
        """Test _get_all_endpoint_configs"""
        mock_result = MagicMock()
        mock_result.data.decode.return_value = '[{"id": "ep1"}]'
        mock_settings_api.get_endpoint_configs_without_preload_content.return_value = mock_result

        result = asyncio.run(self.client._get_all_endpoint_configs())

        self.assertIsInstance(result, list)

    def test_get_endpoint_config_no_id(self):
        """Test _get_endpoint_config with no ID"""
        result = asyncio.run(self.client._get_endpoint_config(None))

        self.assertIn("error", result)

    def test_create_endpoint_config_no_payload(self):
        """Test _create_endpoint_config with no payload"""
        result = asyncio.run(self.client._create_endpoint_config(None))

        self.assertIn("error", result)

    def test_create_endpoint_config_success(self):
        """Test _create_endpoint_config with valid payload"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ep1"}
        mock_settings_api.create_endpoint_config.return_value = mock_result

        payload = {"label": "Test Endpoint"}
        result = asyncio.run(self.client._create_endpoint_config(payload))

        self.assertIn("id", result)

    def test_update_endpoint_config_success(self):
        """Test _update_endpoint_config with valid parameters"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ep1"}
        mock_settings_api.update_endpoint_config.return_value = mock_result

        payload = {"label": "Updated Endpoint"}
        result = asyncio.run(self.client._update_endpoint_config("ep1", payload))

        self.assertIn("id", result)

    def test_delete_endpoint_config_success(self):
        """Test _delete_endpoint_config with valid ID"""
        mock_settings_api.delete_endpoint_config.return_value = None

        result = asyncio.run(self.client._delete_endpoint_config("ep1"))

        self.assertIn("success", result)

    # Tests for service config operations
    def test_get_all_service_configs_success(self):
        """Test _get_all_service_configs"""
        mock_result = MagicMock()
        mock_result.data.decode.return_value = '[{"id": "svc1"}]'
        mock_settings_api.get_service_configs_without_preload_content.return_value = mock_result

        result = asyncio.run(self.client._get_all_service_configs())

        self.assertIsInstance(result, list)

    def test_get_service_config_no_id(self):
        """Test _get_service_config with no ID"""
        result = asyncio.run(self.client._get_service_config(None))

        self.assertIn("error", result)

    def test_add_service_config_no_payload(self):
        """Test _add_service_config with no payload"""
        result = asyncio.run(self.client._add_service_config(None))

        self.assertIn("error", result)

    def test_add_service_config_success(self):
        """Test _add_service_config with valid payload"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "svc1"}
        mock_settings_api.add_service_config.return_value = mock_result

        payload = {"label": "Test Service"}
        result = asyncio.run(self.client._add_service_config(payload))

        self.assertIn("id", result)

    def test_update_service_config_success(self):
        """Test _update_service_config with valid parameters"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "svc1"}
        mock_settings_api.update_service_config.return_value = mock_result

        payload = {"label": "Updated Service"}
        result = asyncio.run(self.client._update_service_config("svc1", payload))

        self.assertIn("id", result)

    def test_delete_service_config_success(self):
        """Test _delete_service_config with valid ID"""
        mock_settings_api.delete_service_config.return_value = None

        result = asyncio.run(self.client._delete_service_config("svc1"))

        self.assertIn("success", result)

    # Tests for manual service config operations
    def test_get_all_manual_service_configs_success(self):
        """Test _get_all_manual_service_configs"""
        mock_result = MagicMock()
        mock_result.data.decode.return_value = '[{"id": "ms1"}]'
        mock_settings_api.get_manual_service_configs_without_preload_content.return_value = mock_result

        result = asyncio.run(self.client._get_all_manual_service_configs())

        self.assertIsInstance(result, list)

    def test_add_manual_service_config_no_payload(self):
        """Test _add_manual_service_config with no payload"""
        result = asyncio.run(self.client._add_manual_service_config(None))

        self.assertIn("error", result)

    def test_add_manual_service_config_success(self):
        """Test _add_manual_service_config with valid payload"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ms1"}
        mock_settings_api.add_manual_service_config.return_value = mock_result

        payload = {"label": "Manual Service"}
        result = asyncio.run(self.client._add_manual_service_config(payload))

        self.assertIn("id", result)

    def test_update_manual_service_config_success(self):
        """Test _update_manual_service_config with valid parameters"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ms1"}
        mock_settings_api.update_manual_service_config.return_value = mock_result

        payload = {"label": "Updated Manual Service"}
        result = asyncio.run(self.client._update_manual_service_config("ms1", payload))

        self.assertIn("id", result)

    def test_delete_manual_service_config_no_id(self):
        """Test _delete_manual_service_config with no ID"""
        result = asyncio.run(self.client._delete_manual_service_config(None))

        self.assertIn("error", result)

    def test_delete_manual_service_config_success(self):
        """Test _delete_manual_service_config with valid ID"""
        mock_settings_api.delete_manual_service_config.return_value = None

        result = asyncio.run(self.client._delete_manual_service_config("ms1"))

        self.assertIn("success", result)

    # Additional routing tests for complete coverage
    def test_execute_settings_operation_application_update(self):
        """Test execute_settings_operation routes application/update correctly"""
        expected = {"id": "app1", "label": "Updated"}
        self.client._update_application_config = AsyncMock(return_value=expected)
        payload = {"label": "Updated"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="update",
            resource_subtype="application",
            id="app1",
            payload=payload
        ))

        self.client._update_application_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_endpoint_get_all(self):
        """Test execute_settings_operation routes endpoint/get_all correctly"""
        expected = [{"id": "ep1"}]
        self.client._get_all_endpoint_configs = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get_all",
            resource_subtype="endpoint"
        ))

        self.client._get_all_endpoint_configs.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_endpoint_get(self):
        """Test execute_settings_operation routes endpoint/get correctly"""
        expected = {"id": "ep1"}
        self.client._get_endpoint_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get",
            resource_subtype="endpoint",
            id="ep1"
        ))

        self.client._get_endpoint_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_endpoint_create(self):
        """Test execute_settings_operation routes endpoint/create correctly"""
        expected = {"id": "ep1"}
        self.client._create_endpoint_config = AsyncMock(return_value=expected)
        payload = {"label": "Endpoint"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="create",
            resource_subtype="endpoint",
            payload=payload
        ))

        self.client._create_endpoint_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_endpoint_update(self):
        """Test execute_settings_operation routes endpoint/update correctly"""
        expected = {"id": "ep1"}
        self.client._update_endpoint_config = AsyncMock(return_value=expected)
        payload = {"label": "Updated"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="update",
            resource_subtype="endpoint",
            id="ep1",
            payload=payload
        ))

        self.client._update_endpoint_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_endpoint_delete(self):
        """Test execute_settings_operation routes endpoint/delete correctly"""
        expected = {"success": True}
        self.client._delete_endpoint_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="delete",
            resource_subtype="endpoint",
            id="ep1"
        ))

        self.client._delete_endpoint_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_service_get_all(self):
        """Test execute_settings_operation routes service/get_all correctly"""
        expected = [{"id": "svc1"}]
        self.client._get_all_service_configs = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get_all",
            resource_subtype="service"
        ))

        self.client._get_all_service_configs.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_service_get(self):
        """Test execute_settings_operation routes service/get correctly"""
        expected = {"id": "svc1"}
        self.client._get_service_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="get",
            resource_subtype="service",
            id="svc1"
        ))

        self.client._get_service_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_service_create(self):
        """Test execute_settings_operation routes service/create correctly"""
        expected = {"id": "svc1"}
        self.client._add_service_config = AsyncMock(return_value=expected)
        payload = {"label": "Service"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="create",
            resource_subtype="service",
            payload=payload
        ))

        self.client._add_service_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_service_update(self):
        """Test execute_settings_operation routes service/update correctly"""
        expected = {"id": "svc1"}
        self.client._update_service_config = AsyncMock(return_value=expected)
        payload = {"label": "Updated"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="update",
            resource_subtype="service",
            id="svc1",
            payload=payload
        ))

        self.client._update_service_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_service_delete(self):
        """Test execute_settings_operation routes service/delete correctly"""
        expected = {"success": True}
        self.client._delete_service_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="delete",
            resource_subtype="service",
            id="svc1"
        ))

        self.client._delete_service_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_manual_service_create(self):
        """Test execute_settings_operation routes manual_service/create correctly"""
        expected = {"id": "ms1"}
        self.client._add_manual_service_config = AsyncMock(return_value=expected)
        payload = {"label": "Manual Service"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="create",
            resource_subtype="manual_service",
            payload=payload
        ))

        self.client._add_manual_service_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_manual_service_update(self):
        """Test execute_settings_operation routes manual_service/update correctly"""
        expected = {"id": "ms1"}
        self.client._update_manual_service_config = AsyncMock(return_value=expected)
        payload = {"label": "Updated"}

        result = asyncio.run(self.client.execute_settings_operation(
            operation="update",
            resource_subtype="manual_service",
            id="ms1",
            payload=payload
        ))

        self.client._update_manual_service_config.assert_called_once()
        self.assertEqual(result, expected)

    def test_execute_settings_operation_manual_service_delete(self):
        """Test execute_settings_operation routes manual_service/delete correctly"""
        expected = {"success": True}
        self.client._delete_manual_service_config = AsyncMock(return_value=expected)

        result = asyncio.run(self.client.execute_settings_operation(
            operation="delete",
            resource_subtype="manual_service",
            id="ms1"
        ))

        self.client._delete_manual_service_config.assert_called_once()
        self.assertEqual(result, expected)

    # Additional tests for error handling and edge cases
    def test_get_all_applications_configs_json_decode_error(self):
        """Test _get_all_applications_configs handles JSON decode errors"""
        mock_result = MagicMock()
        mock_result.data.decode.return_value = "invalid json"
        mock_settings_api.get_application_configs_without_preload_content.return_value = mock_result

        result = asyncio.run(self.client._get_all_applications_configs())

        self.assertIsInstance(result, list)
        self.assertIn("error", result[0])

    def test_get_all_applications_configs_single_object_response(self):
        """Test _get_all_applications_configs handles single object response"""
        mock_result = MagicMock()
        mock_result.data.decode.return_value = '{"id": "app1", "label": "App"}'
        mock_settings_api.get_application_configs_without_preload_content.return_value = mock_result

        result = asyncio.run(self.client._get_all_applications_configs())

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_get_all_applications_configs_empty_response(self):
        """Test _get_all_applications_configs handles empty response"""
        mock_result = MagicMock()
        mock_result.data.decode.return_value = 'null'
        mock_settings_api.get_application_configs_without_preload_content.return_value = mock_result

        result = asyncio.run(self.client._get_all_applications_configs())

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_all_applications_configs_exception(self):
        """Test _get_all_applications_configs handles general exceptions"""
        mock_settings_api.get_application_configs_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_all_applications_configs())

        self.assertIsInstance(result, list)
        self.assertIn("error", result[0])

    def test_get_application_config_exception(self):
        """Test _get_application_config handles exceptions"""
        mock_settings_api.get_application_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_application_config("app1"))

        self.assertIn("error", result)

    def test_get_application_config_no_to_dict(self):
        """Test _get_application_config when result doesn't have to_dict"""
        mock_result = {"id": "app1", "label": "App"}
        mock_settings_api.get_application_config.return_value = mock_result

        result = asyncio.run(self.client._get_application_config("app1"))

        self.assertEqual(result, mock_result)

    def test_add_application_config_validation_error(self):
        """Test _add_application_config with validation error"""
        result = asyncio.run(self.client._add_application_config({"invalid": "data"}))

        self.assertIn("error", result)
        self.assertIn("missing_fields", result)

    def test_add_application_config_no_to_dict(self):
        """Test _add_application_config when result doesn't have to_dict"""
        mock_settings_api.add_application_config.side_effect = None
        mock_settings_api.add_application_config.return_value = None

        payload = {"label": "Test App"}
        result = asyncio.run(self.client._add_application_config(payload))

        self.assertIn("success", result)

    def test_update_application_config_with_string_payload(self):
        """Test _update_application_config with string JSON payload"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "app1", "label": "Updated"}
        mock_settings_api.put_application_config.return_value = mock_result

        payload = '{"label": "Updated"}'
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("id", result)

    def test_update_application_config_with_ast_literal_eval(self):
        """Test _update_application_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "app1", "label": "Updated"}
        mock_settings_api.put_application_config.return_value = mock_result

        payload = "{'label': 'Updated'}"
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("id", result)

    def test_update_application_config_invalid_string_payload(self):
        """Test _update_application_config with invalid string payload"""
        payload = "{invalid python dict"
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("error", result)

    def test_update_application_config_with_tag_filter_expression(self):
        """Test _update_application_config with EXPRESSION tag filter"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "app1"}
        mock_settings_api.put_application_config.return_value = mock_result

        payload = {
            "label": "Test",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [
                    {
                        "type": "TAG_FILTER",
                        "name": "service.name",
                        "operator": "EQUALS",
                        "entity": "DESTINATION"
                    }
                ]
            }
        }
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("id", result)

    def test_update_application_config_with_simple_tag_filter(self):
        """Test _update_application_config with TAG_FILTER type"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "app1"}
        mock_settings_api.put_application_config.return_value = mock_result

        payload = {
            "label": "Test",
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "CONTAINS",
                "entity": "DESTINATION",
                "value": "my-service"
            }
        }
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("id", result)

    def test_update_application_config_no_to_dict(self):
        """Test _update_application_config when result doesn't have to_dict"""
        mock_settings_api.put_application_config.return_value = None

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("success", result)

    def test_update_application_config_exception(self):
        """Test _update_application_config handles exceptions"""
        mock_settings_api.put_application_config.side_effect = Exception("API Error")

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_application_config("app1", payload))

        self.assertIn("error", result)

    def test_delete_application_config_exception(self):
        """Test _delete_application_config handles exceptions"""
        mock_settings_api.delete_application_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._delete_application_config("app1"))

        self.assertIn("error", result)

    def test_get_all_endpoint_configs_exception(self):
        """Test _get_all_endpoint_configs handles exceptions"""
        mock_settings_api.get_endpoint_configs_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_all_endpoint_configs())

        self.assertIsInstance(result, list)
        self.assertIn("error", result[0])

    def test_get_endpoint_config_exception(self):
        """Test _get_endpoint_config handles exceptions"""
        mock_settings_api.get_endpoint_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_endpoint_config("ep1"))

        self.assertIn("error", result)

    def test_get_endpoint_config_no_to_dict(self):
        """Test _get_endpoint_config when result doesn't have to_dict"""
        mock_result = {"id": "ep1"}
        mock_settings_api.get_endpoint_config.return_value = mock_result

        result = asyncio.run(self.client._get_endpoint_config("ep1"))

        self.assertEqual(result, mock_result)

    def test_create_endpoint_config_with_ast_literal_eval(self):
        """Test _create_endpoint_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ep1"}
        mock_settings_api.create_endpoint_config.return_value = mock_result

        payload = "{'label': 'Endpoint'}"
        result = asyncio.run(self.client._create_endpoint_config(payload))

        self.assertIn("id", result)

    def test_create_endpoint_config_no_to_dict(self):
        """Test _create_endpoint_config when result doesn't have to_dict"""
        mock_settings_api.create_endpoint_config.return_value = None

        payload = {"label": "Endpoint"}
        result = asyncio.run(self.client._create_endpoint_config(payload))

        self.assertIn("success", result)

    def test_create_endpoint_config_exception(self):
        """Test _create_endpoint_config handles exceptions"""
        mock_settings_api.create_endpoint_config.side_effect = Exception("API Error")

        payload = {"label": "Endpoint"}
        result = asyncio.run(self.client._create_endpoint_config(payload))

        self.assertIn("error", result)

    def test_update_endpoint_config_with_ast_literal_eval(self):
        """Test _update_endpoint_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ep1"}
        mock_settings_api.update_endpoint_config.return_value = mock_result

        payload = "{'label': 'Updated'}"
        result = asyncio.run(self.client._update_endpoint_config("ep1", payload))

        self.assertIn("id", result)

    def test_update_endpoint_config_no_to_dict(self):
        """Test _update_endpoint_config when result doesn't have to_dict"""
        mock_settings_api.update_endpoint_config.return_value = None

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_endpoint_config("ep1", payload))

        self.assertIn("success", result)

    def test_update_endpoint_config_exception(self):
        """Test _update_endpoint_config handles exceptions"""
        mock_settings_api.update_endpoint_config.side_effect = Exception("API Error")

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_endpoint_config("ep1", payload))

        self.assertIn("error", result)

    def test_delete_endpoint_config_exception(self):
        """Test _delete_endpoint_config handles exceptions"""
        mock_settings_api.delete_endpoint_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._delete_endpoint_config("ep1"))

        self.assertIn("error", result)

    def test_get_all_service_configs_exception(self):
        """Test _get_all_service_configs handles exceptions"""
        mock_settings_api.get_service_configs_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_all_service_configs())

        self.assertIsInstance(result, list)
        self.assertIn("error", result[0])

    def test_get_service_config_exception(self):
        """Test _get_service_config handles exceptions"""
        mock_settings_api.get_service_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_service_config("svc1"))

        self.assertIn("error", result)

    def test_get_service_config_no_to_dict(self):
        """Test _get_service_config when result doesn't have to_dict"""
        mock_result = {"id": "svc1"}
        mock_settings_api.get_service_config.return_value = mock_result

        result = asyncio.run(self.client._get_service_config("svc1"))

        self.assertEqual(result, mock_result)

    def test_add_service_config_with_ast_literal_eval(self):
        """Test _add_service_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "svc1"}
        mock_settings_api.add_service_config.return_value = mock_result

        payload = "{'label': 'Service'}"
        result = asyncio.run(self.client._add_service_config(payload))

        self.assertIn("id", result)

    def test_add_service_config_no_to_dict(self):
        """Test _add_service_config when result doesn't have to_dict"""
        mock_settings_api.add_service_config.return_value = None

        payload = {"label": "Service"}
        result = asyncio.run(self.client._add_service_config(payload))

        self.assertIn("success", result)

    def test_add_service_config_exception(self):
        """Test _add_service_config handles exceptions"""
        mock_settings_api.add_service_config.side_effect = Exception("API Error")

        payload = {"label": "Service"}
        result = asyncio.run(self.client._add_service_config(payload))

        self.assertIn("error", result)

    def test_update_service_config_with_ast_literal_eval(self):
        """Test _update_service_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "svc1"}
        mock_settings_api.update_service_config.return_value = mock_result

        payload = "{'label': 'Updated'}"
        result = asyncio.run(self.client._update_service_config("svc1", payload))

        self.assertIn("id", result)

    def test_update_service_config_no_to_dict(self):
        """Test _update_service_config when result doesn't have to_dict"""
        mock_settings_api.update_service_config.return_value = None

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_service_config("svc1", payload))

        self.assertIn("success", result)

    def test_update_service_config_exception(self):
        """Test _update_service_config handles exceptions"""
        mock_settings_api.update_service_config.side_effect = Exception("API Error")

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_service_config("svc1", payload))

        self.assertIn("error", result)

    def test_delete_service_config_exception(self):
        """Test _delete_service_config handles exceptions"""
        mock_settings_api.delete_service_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._delete_service_config("svc1"))

        self.assertIn("error", result)

    def test_get_all_manual_service_configs_exception(self):
        """Test _get_all_manual_service_configs handles exceptions"""
        mock_settings_api.get_manual_service_configs_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.client._get_all_manual_service_configs())

        self.assertIsInstance(result, list)
        self.assertIn("error", result[0])

    def test_add_manual_service_config_with_ast_literal_eval(self):
        """Test _add_manual_service_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ms1"}
        mock_settings_api.add_manual_service_config.return_value = mock_result

        payload = "{'label': 'Manual Service'}"
        result = asyncio.run(self.client._add_manual_service_config(payload))

        self.assertIn("id", result)

    def test_add_manual_service_config_no_to_dict(self):
        """Test _add_manual_service_config when result doesn't have to_dict"""
        mock_settings_api.add_manual_service_config.return_value = None

        payload = {"label": "Manual Service"}
        result = asyncio.run(self.client._add_manual_service_config(payload))

        self.assertIn("success", result)

    def test_add_manual_service_config_exception(self):
        """Test _add_manual_service_config handles exceptions"""
        mock_settings_api.add_manual_service_config.side_effect = Exception("API Error")

        payload = {"label": "Manual Service"}
        result = asyncio.run(self.client._add_manual_service_config(payload))

        self.assertIn("error", result)

    def test_update_manual_service_config_with_ast_literal_eval(self):
        """Test _update_manual_service_config with Python dict string"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"id": "ms1"}
        mock_settings_api.update_manual_service_config.return_value = mock_result

        payload = "{'label': 'Updated'}"
        result = asyncio.run(self.client._update_manual_service_config("ms1", payload))

        self.assertIn("id", result)

    def test_update_manual_service_config_no_to_dict(self):
        """Test _update_manual_service_config when result doesn't have to_dict"""
        mock_settings_api.update_manual_service_config.return_value = None

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_manual_service_config("ms1", payload))

        self.assertIn("success", result)

    def test_update_manual_service_config_exception(self):
        """Test _update_manual_service_config handles exceptions"""
        mock_settings_api.update_manual_service_config.side_effect = Exception("API Error")

        payload = {"label": "Updated"}
        result = asyncio.run(self.client._update_manual_service_config("ms1", payload))

        self.assertIn("error", result)

    def test_delete_manual_service_config_exception(self):
        """Test _delete_manual_service_config handles exceptions"""
        mock_settings_api.delete_manual_service_config.side_effect = Exception("API Error")

        result = asyncio.run(self.client._delete_manual_service_config("ms1"))

        self.assertIn("error", result)

    def test_validate_and_prepare_application_payload_with_non_dict_element(self):
        """Test validation with non-dict element in tag filter expression"""
        payload = {
            "label": "Test App",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": ["non-dict-element"]
            }
        }
        result = self.client._validate_and_prepare_application_payload(payload)

        self.assertIn("payload", result)

    def test_validate_and_prepare_application_payload_tag_filter_with_string_value(self):
        """Test validation with TAG_FILTER having stringValue — result is a TagFilter model object"""
        payload = {
            "label": "Test App",
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "CONTAINS",
                "entity": "DESTINATION",
                "stringValue": "my-service"
            }
        }
        result = self.client._validate_and_prepare_application_payload(payload)

        self.assertIn("payload", result)
        # tagFilterExpression is now a TagFilter SDK model object (MagicMock in tests),
        # not a plain dict — just confirm it is present and not an error.
        self.assertIn("tagFilterExpression", result["payload"])
        self.assertNotIn("error", result)


if __name__ == '__main__':
    unittest.main()
