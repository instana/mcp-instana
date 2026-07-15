"""
Tests for Maintenance Window Smart Router MCP Tool

This module contains unit tests for the maintenance window smart router,
covering resource_type routing, flat parameter handling, JSON list parsing,
and error handling.
"""

import asyncio
import logging
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Suppress logs during tests
logging.basicConfig(level=logging.ERROR)
router_logger = logging.getLogger('src.router.maintenance_window_smart_router')
router_logger.handlers = []
router_logger.propagate = False

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Mock instana_client before any src imports
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.maintenance_configuration_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.maintenance_config_v2'] = MagicMock()

# Mock mcp module
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.lowlevel'] = MagicMock()
sys.modules['mcp.server.lowlevel.server'] = MagicMock()
mock_tool_annotations = MagicMock()
sys.modules['mcp.types'].ToolAnnotations = mock_tool_annotations

# Mock fastmcp module
sys.modules['fastmcp'] = MagicMock()
sys.modules['fastmcp.server'] = MagicMock()
sys.modules['fastmcp.server.context'] = MagicMock()
mock_context = MagicMock()
sys.modules['fastmcp'].Context = mock_context


class TestMaintenanceWindowSmartRouter(unittest.TestCase):
    """Tests for MaintenanceWindowSmartRouterMCPTool"""

    def setUp(self):
        """Set up test fixtures with a mocked maintenance window client."""
        # Import and create router
        from src.router.maintenance_window_smart_router import (
            MaintenanceWindowSmartRouterMCPTool,
        )

        # Patch the MaintenanceWindowMCPTools where it's imported (inside __init__)
        with patch('src.maintenance_window.maintenance_window_tool.MaintenanceWindowMCPTools'):
            self.router = MaintenanceWindowSmartRouterMCPTool(
                read_token="test_token",
                base_url="https://test.instana.com"
            )

        # Replace the underlying client with a mock
        self.mock_mw_client = MagicMock()
        self.mock_mw_client.execute_maintenance_operation = AsyncMock()
        self.router.maintenance_window_client = self.mock_mw_client

    # -------------------------------------------------------------------------
    # Initialisation
    # -------------------------------------------------------------------------

    def test_init(self):
        """Router is initialised with correct credentials."""
        self.assertEqual(self.router.read_token, "test_token")
        self.assertEqual(self.router.base_url, "https://test.instana.com")

    # -------------------------------------------------------------------------
    # resource_type validation
    # -------------------------------------------------------------------------

    def test_invalid_resource_type_returns_error(self):
        """Unknown resource_type returns an error dict."""
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="unknown_type", operation="create"))
        self.assertIn("error", result)
        self.assertIn("unknown_type", result["error"])

    def test_valid_resource_type_window(self):
        """resource_type='window' routes to _handle_window."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_active"))
        self.assertEqual(result["resource_type"], "window")
        self.assertEqual(result["operation"], "list_active")

    def test_valid_resource_type_templates(self):
        """resource_type='templates' routes to _handle_templates."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"templates": {}}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="templates", operation="get"))
        self.assertEqual(result["resource_type"], "templates")
        self.assertEqual(result["operation"], "get")

    # -------------------------------------------------------------------------
    # operation validation
    # -------------------------------------------------------------------------

    def test_invalid_window_operation_returns_error(self):
        """Invalid operation for resource_type='window' returns an error."""
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="nonexistent_op"))
        self.assertIn("error", result)

    def test_invalid_templates_operation_returns_error(self):
        """Invalid operation for resource_type='templates' returns an error."""
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="templates", operation="create"))
        self.assertIn("error", result)

    # -------------------------------------------------------------------------
    # create operation
    # -------------------------------------------------------------------------

    def test_create_window_passes_flat_params(self):
        """create operation passes all flat string params to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 2 hours", "duration_minutes": "120", "reason": "Deployment", "template": "deployment", "change_request_id": "CHG0012345"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "create")
        self.assertEqual(call_kwargs["params"]["imap_code"], "EAL-012471")
        self.assertEqual(call_kwargs["params"]["start_time"], "in 2 hours")
        self.assertEqual(call_kwargs["params"]["duration_minutes"], "120")
        self.assertEqual(call_kwargs["params"]["reason"], "Deployment")
        self.assertEqual(call_kwargs["params"]["template"], "deployment")
        self.assertEqual(call_kwargs["params"]["change_request_id"], "CHG0012345")

    def test_create_window_result_structure(self):
        """create operation returns correct result structure."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "2026-06-01T14:00:00Z", "duration_minutes": "60"}))

        self.assertEqual(result["resource_type"], "window")
        self.assertEqual(result["operation"], "create")
        self.assertIn("results", result)

    # -------------------------------------------------------------------------
    # modify operation
    # -------------------------------------------------------------------------

    def test_modify_window_passes_window_id(self):
        """modify operation passes window_id to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"updated": True}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="modify", params={"window_id": "mw-789", "duration_minutes": "60"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "modify")
        self.assertEqual(call_kwargs["params"]["window_id"], "mw-789")
        self.assertEqual(call_kwargs["params"]["duration_minutes"], "60")

    # -------------------------------------------------------------------------
    # close operation
    # -------------------------------------------------------------------------

    def test_close_window_passes_completion_notes(self):
        """close operation passes completion_notes to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"closed": True}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="close", params={"window_id": "mw-789", "completion_notes": "Completed successfully"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "close")
        self.assertEqual(call_kwargs["params"]["window_id"], "mw-789")
        self.assertEqual(call_kwargs["params"]["completion_notes"], "Completed successfully")

    # -------------------------------------------------------------------------
    # list operations
    # -------------------------------------------------------------------------

    def test_list_active_no_filter(self):
        """list_active with no imap_code calls the client correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}

        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_active"))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "list_active")
        self.assertIsNone(call_kwargs.get("imap_code"))
        self.assertEqual(result["operation"], "list_active")

    def test_list_active_with_imap_filter(self):
        """list_active with imap_code passes it to the client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_active", params={"imap_code": "EAL-012471"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["imap_code"], "EAL-012471")

    def test_list_all_operation(self):
        """list_all operation routes correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_all"))
        self.assertEqual(result["operation"], "list_all")

    def test_list_scheduled_operation(self):
        """list_scheduled operation routes correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_scheduled"))
        self.assertEqual(result["operation"], "list_scheduled")

    def test_list_expired_operation(self):
        """list_expired operation routes correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_expired"))
        self.assertEqual(result["operation"], "list_expired")

    # -------------------------------------------------------------------------
    # bulk_create operation
    # -------------------------------------------------------------------------

    def test_bulk_create_parses_json_array_imap_codes(self):
        """bulk_create parses JSON array string for imap_codes."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"created": 2}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="bulk_create", params={"imap_codes": '["EAL-012471","ORZ-000012"]', "start_time": "2026-06-01T02:00:00Z", "duration_hours": "2"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["imap_codes"], ["EAL-012471", "ORZ-000012"])

    def test_bulk_create_parses_comma_separated_imap_codes(self):
        """bulk_create parses comma-separated string for imap_codes."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"created": 2}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="bulk_create", params={"imap_codes": "EAL-012471,ORZ-000012", "start_time": "2026-06-01T02:00:00Z", "duration_minutes": "120"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["imap_codes"], ["EAL-012471", "ORZ-000012"])

    # -------------------------------------------------------------------------
    # JSON list parsing (_parse_json_list)
    # -------------------------------------------------------------------------

    def test_parse_json_list_none_returns_none(self):
        """_parse_json_list returns None for None input."""
        self.assertIsNone(self.router._parse_json_list(None))

    def test_parse_json_list_empty_string_returns_none(self):
        """_parse_json_list returns None for empty string."""
        self.assertIsNone(self.router._parse_json_list(""))

    def test_parse_json_list_json_array(self):
        """_parse_json_list correctly parses a JSON array string."""
        result = self.router._parse_json_list('["a", "b", "c"]')
        self.assertEqual(result, ["a", "b", "c"])

    def test_parse_json_list_comma_separated(self):
        """_parse_json_list correctly parses a comma-separated string."""
        result = self.router._parse_json_list("a,b,c")
        self.assertEqual(result, ["a", "b", "c"])

    def test_parse_json_list_already_a_list(self):
        """_parse_json_list returns the list unchanged if already a list."""
        result = self.router._parse_json_list(["x", "y"])
        self.assertEqual(result, ["x", "y"])

    # -------------------------------------------------------------------------
    # Boolean string parsing (use_tag_filter_expression)
    # -------------------------------------------------------------------------

    def test_use_tag_filter_true_string(self):
        """use_tag_filter_expression='true' is parsed as True."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 1 hour", "use_tag_filter_expression": "true", "tag_name": "environment:production"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertTrue(call_kwargs["params"]["use_tag_filter_expression"])

    def test_use_tag_filter_false_string(self):
        """use_tag_filter_expression='false' is parsed as False."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 1 hour", "use_tag_filter_expression": "false"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertFalse(call_kwargs["params"]["use_tag_filter_expression"])

    def test_use_tag_filter_default_is_false(self):
        """use_tag_filter_expression defaults to False when not provided."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_active"))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertFalse(call_kwargs["params"]["use_tag_filter_expression"])

    # -------------------------------------------------------------------------
    # templates resource type
    # -------------------------------------------------------------------------

    def test_get_templates_calls_get_templates_operation(self):
        """templates/get routes to get_templates operation on the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {
            "deployment": {"default_duration": 60},
            "routine": {"default_duration": 30}
        }

        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="templates", operation="get"))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "get_templates")
        self.assertEqual(result["resource_type"], "templates")
        self.assertIn("results", result)

    # -------------------------------------------------------------------------
    # Recurring window (rrule / until_date)
    # -------------------------------------------------------------------------

    def test_create_recurring_window_passes_rrule(self):
        """create with rrule and until_date passes them to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-rec-001"}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "ORZ-000012", "start_time": "in 3 hours", "duration_minutes": "30", "rrule": "FREQ=DAILY;INTERVAL=1", "until_date": "2026-06-17T23:59:59Z"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["rrule"], "FREQ=DAILY;INTERVAL=1")
        self.assertEqual(call_kwargs["params"]["until_date"], "2026-06-17T23:59:59Z")

    # -------------------------------------------------------------------------
    # Error handling
    # -------------------------------------------------------------------------

    def test_exception_in_client_returns_error(self):
        """If the underlying client raises an exception, the router returns an error dict."""
        self.mock_mw_client.execute_maintenance_operation.side_effect = Exception("Instana API unavailable")

        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_active"))

        self.assertIn("error", result)
        self.assertIn("Instana API unavailable", result["error"])

    def test_validate_operation(self):
        """validate operation routes correctly to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"valid": True}

        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="validate", params={"imap_code": "EAL-012471", "start_time": "in 1 hour", "duration_minutes": "60"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "validate")
        self.assertEqual(result["operation"], "validate")

    # -------------------------------------------------------------------------
    # Resource type aliases
    # -------------------------------------------------------------------------

    def test_resource_type_alias_maintenance(self):
        """resource_type='maintenance' is normalized to 'window'."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="maintenance", operation="list_active"))
        self.assertEqual(result["resource_type"], "window")

    def test_resource_type_alias_maintenance_window(self):
        """resource_type='maintenance_window' is normalized to 'window'."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="maintenance_window", operation="list_active"))
        self.assertEqual(result["resource_type"], "window")

    def test_resource_type_alias_windows(self):
        """resource_type='windows' is normalized to 'window'."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="windows", operation="list_active"))
        self.assertEqual(result["resource_type"], "window")

    def test_resource_type_alias_template(self):
        """resource_type='template' is normalized to 'templates'."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"templates": {}}
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="template", operation="get"))
        self.assertEqual(result["resource_type"], "templates")

    # -------------------------------------------------------------------------
    # Default parameter handling
    # -------------------------------------------------------------------------

    def test_default_resource_type(self):
        """resource_type defaults to 'window' when not provided."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(
            operation="list_active"
        ))
        self.assertEqual(result["resource_type"], "window")

    def test_default_operation(self):
        """operation defaults to 'list_scheduled' when not provided."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window"
        ))
        self.assertEqual(result["operation"], "list_scheduled")

    def test_none_resource_type_uses_default(self):
        """None resource_type uses default 'window'."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type=None,
            operation="list_active"
        ))
        self.assertEqual(result["resource_type"], "window")

    def test_none_operation_uses_default(self):
        """None operation uses default 'list_scheduled'."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation=None
        ))
        self.assertEqual(result["operation"], "list_scheduled")

    # -------------------------------------------------------------------------
    # Additional parameter passing tests
    # -------------------------------------------------------------------------

    def test_create_with_all_optional_params(self):
        """create operation passes all optional parameters."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 2 hours", "duration_minutes": "120", "reason": "Deployment", "template": "deployment", "change_request_id": "CHG0012345", "affected_services": '["service1","service2"]', "notification_channels": '["slack","email"]', "use_tag_filter_expression": "true", "tag_name": "environment:production", "rrule": "FREQ=DAILY;INTERVAL=1", "until_date": "2026-06-17T23:59:59Z"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["imap_code"], "EAL-012471")
        self.assertEqual(call_kwargs["params"]["affected_services"], ["service1", "service2"])
        self.assertEqual(call_kwargs["params"]["notification_channels"], ["slack", "email"])
        self.assertTrue(call_kwargs["params"]["use_tag_filter_expression"])
        self.assertEqual(call_kwargs["params"]["tag_name"], "environment:production")

    def test_create_with_application_id(self):
        """create operation accepts application_id parameter."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"application_id": "app-123", "start_time": "in 2 hours", "duration_minutes": "60"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["application_id"], "app-123")

    def test_create_with_duration_days(self):
        """create operation accepts duration_days parameter."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 2 hours", "duration_days": "2"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["duration_days"], "2")

    def test_create_with_end_time(self):
        """create operation accepts end_time parameter."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "1748786400000", "end_time": "1748790000000"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["end_time"], "1748790000000")

    def test_modify_with_end_time(self):
        """modify operation accepts end_time parameter."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"updated": True}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="modify", params={"window_id": "mw-789", "end_time": "1748790000000"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["end_time"], "1748790000000")

    def test_modify_with_rrule_and_until_date(self):
        """modify operation accepts rrule and until_date parameters."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"updated": True}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="modify", params={"window_id": "mw-789", "rrule": "FREQ=WEEKLY;INTERVAL=1", "until_date": "2026-12-31T23:59:59Z"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["rrule"], "FREQ=WEEKLY;INTERVAL=1")
        self.assertEqual(call_kwargs["params"]["until_date"], "2026-12-31T23:59:59Z")

    def test_list_active_with_application_id(self):
        """list_active accepts application_id parameter."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="list_active", params={"application_id": "app-123"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["application_id"], "app-123")

    def test_bulk_create_with_application_ids(self):
        """bulk_create accepts application_ids parameter."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"created": 2}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="bulk_create", params={"application_ids": '["app-123","app-456"]', "start_time": "2026-06-01T02:00:00Z", "duration_minutes": "120"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["params"]["application_ids"], ["app-123", "app-456"])

    # -------------------------------------------------------------------------
    # JSON parsing edge cases
    # -------------------------------------------------------------------------

    def test_parse_json_list_with_whitespace(self):
        """_parse_json_list handles whitespace in comma-separated values."""
        result = self.router._parse_json_list("  a  ,  b  ,  c  ")
        self.assertEqual(result, ["a", "b", "c"])

    def test_parse_json_list_single_item(self):
        """_parse_json_list handles single item."""
        result = self.router._parse_json_list("single")
        self.assertEqual(result, ["single"])

    def test_parse_json_list_json_with_spaces(self):
        """_parse_json_list handles JSON array with spaces."""
        result = self.router._parse_json_list('[ "a" , "b" , "c" ]')
        self.assertEqual(result, ["a", "b", "c"])

    def test_parse_json_list_invalid_json_falls_back_to_csv(self):
        """_parse_json_list falls back to CSV for invalid JSON."""
        result = self.router._parse_json_list('[invalid,json')
        self.assertEqual(result, ["[invalid", "json"])

    def test_parse_json_list_empty_items_filtered(self):
        """_parse_json_list filters out empty items in CSV."""
        result = self.router._parse_json_list("a,,b,,c")
        self.assertEqual(result, ["a", "b", "c"])

    # -------------------------------------------------------------------------
    # Boolean parsing edge cases
    # -------------------------------------------------------------------------

    def test_use_tag_filter_case_insensitive_true(self):
        """use_tag_filter_expression='True' (capital T) is parsed as True."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 1 hour", "use_tag_filter_expression": "True"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertTrue(call_kwargs["params"]["use_tag_filter_expression"])

    def test_use_tag_filter_case_insensitive_false(self):
        """use_tag_filter_expression='False' (capital F) is parsed as False."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 1 hour", "use_tag_filter_expression": "False"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertFalse(call_kwargs["params"]["use_tag_filter_expression"])

    def test_use_tag_filter_non_boolean_string(self):
        """use_tag_filter_expression with non-boolean string is parsed as False."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="create", params={"imap_code": "EAL-012471", "start_time": "in 1 hour", "use_tag_filter_expression": "yes"}))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertFalse(call_kwargs["params"]["use_tag_filter_expression"])

    # -------------------------------------------------------------------------
    # Error message validation
    # -------------------------------------------------------------------------

    def test_invalid_resource_type_provides_suggestion(self):
        """Invalid resource_type error includes suggestion."""
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="invalid", operation="create"))
        self.assertIn("error", result)
        self.assertIn("suggestion", result)

    def test_invalid_window_operation_lists_valid_operations(self):
        """Invalid window operation error lists valid operations."""
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="window", operation="invalid_op"))
        self.assertIn("error", result)
        self.assertIn("valid_operations", result)

    def test_invalid_templates_operation_provides_hint(self):
        """Invalid templates operation error provides hint."""
        result = asyncio.run(self.router.manage_maintenance_windows(resource_type="templates", operation="create"))
        self.assertIn("error", result)
        self.assertIn("hint", result)

    # -------------------------------------------------------------------------
    # Context parameter passing
    # -------------------------------------------------------------------------

    def test_ctx_parameter_passed_through(self):
        """ctx parameter is passed through to underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        mock_ctx = {"user": "test_user"}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_active",
            ctx=mock_ctx
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["ctx"], mock_ctx)



if __name__ == '__main__':
    unittest.main()
