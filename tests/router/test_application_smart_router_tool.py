"""
Unit tests for ApplicationSmartRouterMCPTool
"""

import asyncio
import logging
import os
import sys
import unittest
from functools import wraps
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass


# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the router logger and replace its handlers
router_logger = logging.getLogger('src.router.application_smart_router_tool')
router_logger.handlers = []
router_logger.addHandler(NullHandler())
router_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


def _build_mock_module(class_name: str) -> ModuleType:
    module = ModuleType(class_name)
    setattr(module, class_name, MagicMock())
    return module


mocked_application_modules = {
    "src.application.application_call_group": _build_mock_module("ApplicationCallGroupMCPTools"),
    "src.application.application_alert_config": _build_mock_module("ApplicationAlertMCPTools"),
    "src.application.application_global_alert_config": _build_mock_module("ApplicationGlobalAlertMCPTools"),
    "src.application.application_resources": _build_mock_module("ApplicationResourcesMCPTools"),
    "src.application.application_settings": _build_mock_module("ApplicationSettingsMCPTools"),
    "src.application.application_catalog": _build_mock_module("ApplicationCatalogMCPTools"),
    "src.application.application_analyze": _build_mock_module("ApplicationAnalyzeMCPTools"),
}


# Patch the with_header_auth decorator and client imports
with patch.dict(sys.modules, mocked_application_modules):
    with patch('src.core.utils.with_header_auth', mock_with_header_auth):
        from src.router.application_smart_router_tool import (
            ApplicationSmartRouterMCPTool,
        )


class TestApplicationSmartRouterMCPTool(unittest.TestCase):
    """Test class for ApplicationSmartRouterMCPTool"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock instances for all clients
        self.mock_call_group = MagicMock()
        self.mock_alert = MagicMock()
        self.mock_global_alert = MagicMock()
        self.mock_resources = MagicMock()
        self.mock_settings = MagicMock()
        self.mock_catalog = MagicMock()
        self.mock_analyze = MagicMock()

        with patch.dict(sys.modules, mocked_application_modules):
            # Create router instance
            self.router = ApplicationSmartRouterMCPTool(
                read_token="test_token",
                base_url="https://test.instana.com"
            )

        # Manually set the clients on the router
        self.router.app_call_group_client = self.mock_call_group
        self.router.app_alert_config_client = self.mock_alert
        self.router.app_global_alert_config_client = self.mock_global_alert
        self.router.app_resources_client = self.mock_resources
        self.router.app_settings_client = self.mock_settings
        self.router.app_catalog_client = self.mock_catalog
        self.router.app_analyze_client = self.mock_analyze

    def test_init(self):
        """Test router initialization"""
        self.assertEqual(self.router.read_token, "test_token")
        self.assertEqual(self.router.base_url, "https://test.instana.com")
        self.assertIsNotNone(self.router.app_call_group_client)

    def test_invalid_resource_type(self):
        """Test handling of invalid resource type"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="invalid_type",
            operation="test"
        ))

        self.assertIn("error", result)
        self.assertIn("invalid_type", result["error"].lower())

    def test_metrics_routing_success(self):
        """Test successful metrics routing"""
        # Mock the get_grouped_calls_metrics method
        async def mock_get_metrics(*args, **kwargs):
            return {"data": "test_metrics"}

        self.mock_call_group.get_grouped_calls_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="application",
            params={
                "metrics": [{"metric": "calls.count"}],
                "time_frame": {"to": 1234567890000, "windowSize": 3600000}
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "metrics")

    def test_invalid_metrics_operation(self):
        """Test invalid operation for metrics"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="invalid_op"
        ))

        self.assertIn("error", result)

    def test_alert_config_routing(self):
        """Test alert config routing"""
        async def mock_execute(*args, **kwargs):
            return {"alerts": []}

        self.mock_alert.execute_alert_config_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="alert_config",
            operation="find_active",
            params={"application_id": "app-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "alert_config")

    def test_global_alert_config_routing(self):
        """Test global alert config routing"""
        async def mock_execute(*args, **kwargs):
            return {"alerts": []}

        self.mock_global_alert.execute_alert_config_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="global_alert_config",
            operation="find_active",
            params={"application_id": "app-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "global_alert_config")

    def test_settings_routing(self):
        """Test settings routing"""
        async def mock_execute(*args, **kwargs):
            return [{"id": "app-1", "label": "App 1"}]

        self.mock_settings.execute_settings_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get_all",
            params={"resource_subtype": "application"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "settings")

    def test_settings_invalid_subtype(self):
        """Test settings with invalid resource_subtype"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get_all",
            params={"resource_subtype": "invalid"}
        ))

        self.assertIn("error", result)

    def test_catalog_get_tag_catalog(self):
        """Test catalog get_tag_catalog operation"""
        async def mock_get_tags(*args, **kwargs):
            return {"tags": []}

        self.mock_catalog.get_application_tag_catalog = mock_get_tags

        result = asyncio.run(self.router.manage_applications(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"use_case": "GROUPING", "data_source": "CALLS"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "catalog")

    def test_catalog_get_metric_catalog(self):
        """Test catalog get_metric_catalog operation"""
        async def mock_get_metrics(*args, **kwargs):
            return {"metrics": []}

        self.mock_catalog.get_application_metric_catalog = mock_get_metrics

        result = asyncio.run(self.router.manage_applications(
            resource_type="catalog",
            operation="get_metric_catalog"
        ))

        self.assertIn("results", result)

    def test_metrics_datetime_conversion_error(self):
        """Test metrics path - datetime conversion is no longer done in metrics handler."""
        # Datetime conversion was removed from the metrics handler
        # The test now verifies that metrics are called without conversion
        async def mock_get_metrics(*args, **kwargs):
            return {"items": [1, 2, 3]}

        self.mock_call_group.get_grouped_calls_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="application",
            params={"time_frame": {"to": "bad-date", "windowSize": 3600000}}
        ))

        # Should succeed and pass through to the metrics handler
        self.assertEqual(result["resource_type"], "metrics")
        self.assertIn("results", result)

    def test_metrics_invalid_operation_direct_handler(self):
        async def mock_get_metrics(*args, **kwargs):
            return {"items": []}

        self.mock_call_group.get_grouped_calls_metrics = mock_get_metrics
        result = asyncio.run(self.router._handle_metrics("wrong", {}, None))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "metrics")
        self.assertEqual(result["operation"], "wrong")

    def test_metrics_handler_wraps_client_result(self):
        async def mock_get_metrics(*args, **kwargs):
            return {"items": [1, 2, 3]}

        self.mock_call_group.get_grouped_calls_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="application",
            params={"metrics": [{"metric": "calls.count"}], "time_frame": {"to": 1234567890000, "windowSize": 3600000}}
        ))

        self.assertEqual(result["resource_type"], "metrics")
        self.assertIn("results", result)
        self.assertEqual(result["results"], {"items": [1, 2, 3]})

    def test_catalog_invalid_operation(self):
        result = asyncio.run(self.router.manage_applications(
            resource_type="catalog",
            operation="invalid_catalog_op",
            params={}
        ))
        self.assertIn("error", result)

    def test_resources_get_applications(self):
        async def mock_get_apps(*args, **kwargs):
            return {"items": []}

        # Router now delegates to execute_resources_operation dispatcher
        self.mock_resources.execute_resources_operation = mock_get_apps

        result = asyncio.run(self.router.manage_applications(
            resource_type="resources",
            operation="get_applications",
            params={}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "resources")
        self.assertEqual(result["operation"], "get_applications")

    def test_resources_invalid_operation(self):
        result = asyncio.run(self.router.manage_applications(
            resource_type="resources",
            operation="invalid_operation",
            params={}
        ))

        self.assertIn("error", result)

    def test_settings_missing_resource_subtype(self):
        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get_all",
            params={}
        ))
        self.assertIn("error", result)

    def test_exception_handling(self):
        """Test exception handling in router"""
        async def mock_error(*args, **kwargs):
            raise Exception("Test error")

        self.mock_call_group.get_grouped_calls_metrics = mock_error

        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="application",
            params={"time_frame": {"to": 1234567890000, "windowSize": 3600000}}
        ))

        self.assertIn("error", result)
        self.assertIn("Test error", str(result["error"]))

    def test_alert_config_resolves_application_name(self):
        """Test alert_config resolves application_name to application_id"""
        async def mock_resolve(application_name, ctx):
            return {"application_id": "resolved-app", "application_name": application_name}

        async def mock_execute(*args, **kwargs):
            return {"alerts": []}

        self.router._get_application_id_by_name = mock_resolve
        self.mock_alert.execute_alert_config_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="alert_config",
            operation="find",
            params={"application_name": "MyApp"}
        ))

        self.assertEqual(result["application_id"], "resolved-app")
        self.assertEqual(result["resource_type"], "alert_config")
        self.assertIn("results", result)

    def test_settings_resolve_application_name_not_found(self):
        """Test settings resolution failure when application name is missing"""
        async def mock_get_all(*args, **kwargs):
            return [{"id": "app-1", "label": "OtherApp"}]

        self.mock_settings.execute_settings_operation = mock_get_all

        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "MyApp"}
        ))

        self.assertIn("error", result)
        self.assertIn("No application perspective found with name 'MyApp'", result["error"])


    def test_settings_resolve_application_name_success(self):
        """Test settings resolution success when application name is found"""
        async def mock_get_all(*args, **kwargs):
            return [
                {"id": "app-1", "label": "MyApp"},
                {"id": "app-2", "label": "OtherApp"}
            ]

        async def mock_get(*args, **kwargs):
            return {"id": "app-1", "label": "MyApp", "scope": "INCLUDE_ALL_DOWNSTREAM"}

        self.mock_settings.execute_settings_operation = mock_get_all

        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "MyApp"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resolved_id"], "app-1")

    def test_settings_resolve_application_name_case_insensitive(self):
        """Test settings resolution is case-insensitive"""
        async def mock_get_all(*args, **kwargs):
            return [{"id": "app-1", "label": "MyApp"}]

        self.mock_settings.execute_settings_operation = mock_get_all

        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "myapp"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resolved_id"], "app-1")

    def test_settings_resolve_application_name_non_list_response(self):
        """Test settings resolution when get_all returns non-list"""
        async def mock_get_all(*args, **kwargs):
            return {"error": "Failed to fetch"}

        self.mock_settings.execute_settings_operation = mock_get_all

        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "MyApp"}
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to retrieve application perspectives for name resolution", result["error"])

    def test_alert_config_resolve_application_name_error(self):
        """Test alert_config when application name resolution fails"""
        async def mock_resolve(application_name, ctx):
            return {"error": "Application not found"}

        async def mock_execute(*args, **kwargs):
            return {"alerts": []}

        self.router._get_application_id_by_name = mock_resolve
        self.mock_alert.execute_alert_config_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="alert_config",
            operation="find",
            params={"application_name": "NonExistentApp"}
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to resolve application name", result["error"])

    def test_global_alert_config_resolve_application_name_success(self):
        """Test global_alert_config resolves application_name to application_id"""
        async def mock_resolve(application_name, ctx):
            return {"application_id": "resolved-app", "application_name": application_name}

        async def mock_execute(*args, **kwargs):
            return {"alerts": []}

        self.router._get_application_id_by_name = mock_resolve
        self.mock_global_alert.execute_alert_config_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="global_alert_config",
            operation="find",
            params={"application_name": "MyApp"}
        ))

        self.assertEqual(result["application_id"], "resolved-app")
        self.assertEqual(result["resource_type"], "global_alert_config")

    def test_global_alert_config_resolve_application_name_error(self):
        """Test global_alert_config when application name resolution fails"""
        async def mock_resolve(application_name, ctx):
            return {"error": "Application not found"}

        self.router._get_application_id_by_name = mock_resolve

        result = asyncio.run(self.router.manage_applications(
            resource_type="global_alert_config",
            operation="find",
            params={"application_name": "NonExistentApp"}
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to resolve application name", result["error"])

    def test_alert_config_invalid_operation(self):
        """Test alert_config with invalid operation"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="alert_config",
            operation="invalid_operation",
            params={"application_id": "app-123"}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_global_alert_config_invalid_operation(self):
        """Test global_alert_config with invalid operation"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="global_alert_config",
            operation="invalid_operation",
            params={"application_id": "app-123"}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_settings_invalid_operation(self):
        """Test settings with invalid operation"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="settings",
            operation="invalid_operation",
            params={"resource_subtype": "application"}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_get_application_id_by_name_success(self):
        """Test _get_application_id_by_name with successful resolution"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                return {
                    "items": [
                        {"id": "app-1", "label": "MyApp"},
                        {"id": "app-2", "label": "OtherApp"}
                    ]
                }

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("MyApp", None)

            self.assertIn("application_id", result)
            self.assertEqual(result["application_id"], "app-1")
            self.assertEqual(result["application_name"], "MyApp")

        asyncio.run(run_test())

    def test_get_application_id_by_name_case_insensitive(self):
        """Test _get_application_id_by_name is case-insensitive"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                return {
                    "items": [{"id": "app-1", "label": "MyApp"}]
                }

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("myapp", None)

            self.assertEqual(result["application_id"], "app-1")

        asyncio.run(run_test())

    def test_get_application_id_by_name_no_exact_match(self):
        """Test _get_application_id_by_name returns first result when no exact match"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                return {
                    "items": [
                        {"id": "app-1", "label": "SimilarApp"},
                        {"id": "app-2", "label": "OtherApp"}
                    ]
                }

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("MyApp", None)

            self.assertEqual(result["application_id"], "app-1")
            self.assertEqual(result["application_name"], "SimilarApp")

        asyncio.run(run_test())

    def test_get_application_id_by_name_no_items(self):
        """Test _get_application_id_by_name when no applications found"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                return {"items": []}

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("MyApp", None)

            self.assertIn("error", result)
            self.assertIn("No application found", result["error"])

        asyncio.run(run_test())

    def test_get_application_id_by_name_non_dict_result(self):
        """Test _get_application_id_by_name when API returns non-dict"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                return []

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("MyApp", None)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_application_id_by_name_exception(self):
        """Test _get_application_id_by_name exception handling"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                raise Exception("API error")

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("MyApp", None)

            self.assertIn("error", result)
            self.assertIn("Failed to fetch application ID", result["error"])

        asyncio.run(run_test())

    def test_get_application_id_by_name_item_without_id(self):
        """Test _get_application_id_by_name when item has no ID"""
        async def run_test():
            async def mock_get_apps(*args, **kwargs):
                return {
                    "items": [{"label": "MyApp"}]  # Missing id
                }

            self.mock_resources._get_applications_internal = mock_get_apps

            result = await self.router._get_application_id_by_name("MyApp", None)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_metrics_datetime_conversion_success(self):
        """Test metrics path - datetime conversion is no longer done in metrics handler"""
        # Datetime conversion was removed from the metrics handler
        async def mock_get_metrics(*args, **kwargs):
            return {"items": [1, 2, 3]}

        self.mock_call_group.get_grouped_calls_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="application",
            params={"time_frame": {"to": "2021-01-01 00:00:00", "windowSize": 3600000}}
        ))

        self.assertEqual(result["resource_type"], "metrics")
        self.assertIn("results", result)

    def test_metrics_with_all_optional_params(self):
        """Test metrics with all optional parameters"""
        async def mock_get_metrics(*args, **kwargs):
            return {"items": []}

        self.mock_call_group.get_grouped_calls_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_applications(
            resource_type="metrics",
            operation="application",
            params={
                "query": "test query",
                "metrics": [{"metric": "calls.count"}],
                "time_frame": {"to": 1234567890000, "windowSize": 3600000},
                "tag_filter_expression": {"type": "TAG_FILTER"},
                "group": {"groupbyTag": "service.name"},
                "order": {"by": "calls.count", "direction": "DESC"},
                "pagination": {"page": 1, "pageSize": 50},
                "include_internal": True,
                "include_synthetic": False
            }
        ))

        self.assertEqual(result["resource_type"], "metrics")
        self.assertIn("results", result)

    def test_manage_applications_with_none_params(self):
        """Test manage_applications initializes params when None"""
        result = asyncio.run(self.router.manage_applications(
            resource_type="invalid_type",
            operation="test",
            params=None
        ))

        self.assertIn("error", result)

    def test_analyze_invalid_operation(self):
        result = asyncio.run(self.router.manage_applications(
            resource_type="analyze",
            operation="invalid_operation",
            params={}
        ))
        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_analyze_timeframe_conversion_error(self):
        result = asyncio.run(self.router.manage_applications(
            resource_type="analyze",
            operation="get_all_traces",
            params={"payload": {"timeFrame": {"to": "not-a-date", "windowSize": 3600000}}}
        ))
        self.assertIn("error", result)
        self.assertEqual(result["resource_type"], "analyze")

    def test_analyze_ingestion_time_conversion_error(self):
        result = asyncio.run(self.router.manage_applications(
            resource_type="analyze",
            operation="get_trace_details",
            params={"id": "trace-1", "ingestionTime": "bad-date-time"}
        ))
        self.assertIn("error", result)
        self.assertEqual(result["resource_type"], "analyze")

    def test_analyze_routes_get_trace_groups(self):
        async def mock_execute(*args, **kwargs):
            return {"items": [{"group": "service-a"}], "itemCount": 1}

        self.mock_analyze.execute_analyze_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="analyze",
            operation="get_trace_groups",
            params={"payload": {"timeFrame": {"to": 1710658800000, "windowSize": 3600000}}}
        ))

        self.assertEqual(result["resource_type"], "analyze")
        self.assertEqual(result["operation"], "get_trace_groups")
        self.assertIn("results", result)

    def test_analyze_converts_ingestion_time_datetime_and_routes(self):
        captured = {}

        async def mock_execute(*args, **kwargs):
            captured.update(kwargs.get("params", {}))
            return {"items": []}

        self.mock_analyze.execute_analyze_operation = mock_execute

        result = asyncio.run(self.router.manage_applications(
            resource_type="analyze",
            operation="get_trace_details",
            params={"id": "trace-1", "ingestionTime": "19 March 2026, 2:47 PM|IST"}
        ))

        self.assertEqual(result["resource_type"], "analyze")
        self.assertIn("results", result)
        self.assertIsInstance(captured.get("ingestionTime"), int)


if __name__ == '__main__':
    unittest.main()

