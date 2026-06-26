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
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()


class TestMaintenanceWindowSmartRouter(unittest.TestCase):
    """Tests for MaintenanceWindowSmartRouterMCPTool"""

    def setUp(self):
        """Set up test fixtures with a mocked maintenance window client."""
        # Patch the underlying tool so we don't need real Instana credentials
        with patch('src.maintenance_window.maintenance_window_tool.MaintenanceWindowMCPTools'):
            from src.router.maintenance_window_smart_router import (
                MaintenanceWindowSmartRouterMCPTool,
            )
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
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="unknown_type",
            operation="create"
        ))
        self.assertIn("error", result)
        self.assertIn("unknown_type", result["error"])

    def test_valid_resource_type_window(self):
        """resource_type='window' routes to _handle_window."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"status": "ok"}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_active"
        ))
        self.assertEqual(result["resource_type"], "window")
        self.assertEqual(result["operation"], "list_active")

    def test_valid_resource_type_templates(self):
        """resource_type='templates' routes to _handle_templates."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"templates": {}}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="templates",
            operation="get"
        ))
        self.assertEqual(result["resource_type"], "templates")
        self.assertEqual(result["operation"], "get")

    # -------------------------------------------------------------------------
    # operation validation
    # -------------------------------------------------------------------------

    def test_invalid_window_operation_returns_error(self):
        """Invalid operation for resource_type='window' returns an error."""
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="nonexistent_op"
        ))
        self.assertIn("error", result)

    def test_invalid_templates_operation_returns_error(self):
        """Invalid operation for resource_type='templates' returns an error."""
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="templates",
            operation="create"
        ))
        self.assertIn("error", result)

    # -------------------------------------------------------------------------
    # create operation
    # -------------------------------------------------------------------------

    def test_create_window_passes_flat_params(self):
        """create operation passes all flat string params to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            imap_code="EAL-012471",
            start_time="in 2 hours",
            duration_minutes="120",
            reason="Deployment",
            template="deployment",
            change_request_id="CHG0012345"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "create")
        self.assertEqual(call_kwargs["imap_code"], "EAL-012471")
        self.assertEqual(call_kwargs["start_time"], "in 2 hours")
        self.assertEqual(call_kwargs["duration_minutes"], "120")
        self.assertEqual(call_kwargs["reason"], "Deployment")
        self.assertEqual(call_kwargs["template"], "deployment")
        self.assertEqual(call_kwargs["change_request_id"], "CHG0012345")

    def test_create_window_result_structure(self):
        """create operation returns correct result structure."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"window_id": "mw-001"}

        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            imap_code="EAL-012471",
            start_time="2026-06-01T14:00:00Z",
            duration_minutes="60"
        ))

        self.assertEqual(result["resource_type"], "window")
        self.assertEqual(result["operation"], "create")
        self.assertIn("results", result)

    # -------------------------------------------------------------------------
    # modify operation
    # -------------------------------------------------------------------------

    def test_modify_window_passes_window_id(self):
        """modify operation passes window_id to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"updated": True}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="modify",
            window_id="mw-789",
            duration_minutes="60"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "modify")
        self.assertEqual(call_kwargs["window_id"], "mw-789")
        self.assertEqual(call_kwargs["duration_minutes"], "60")

    # -------------------------------------------------------------------------
    # close operation
    # -------------------------------------------------------------------------

    def test_close_window_passes_completion_notes(self):
        """close operation passes completion_notes to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"closed": True}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="close",
            window_id="mw-789",
            completion_notes="Completed successfully"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "close")
        self.assertEqual(call_kwargs["window_id"], "mw-789")
        self.assertEqual(call_kwargs["completion_notes"], "Completed successfully")

    # -------------------------------------------------------------------------
    # list operations
    # -------------------------------------------------------------------------

    def test_list_active_no_filter(self):
        """list_active with no imap_code calls the client correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}

        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_active"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "list_active")
        self.assertIsNone(call_kwargs.get("imap_code"))
        self.assertEqual(result["operation"], "list_active")

    def test_list_active_with_imap_filter(self):
        """list_active with imap_code passes it to the client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_active",
            imap_code="EAL-012471"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["imap_code"], "EAL-012471")

    def test_list_all_operation(self):
        """list_all operation routes correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_all"
        ))
        self.assertEqual(result["operation"], "list_all")

    def test_list_scheduled_operation(self):
        """list_scheduled operation routes correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_scheduled"
        ))
        self.assertEqual(result["operation"], "list_scheduled")

    def test_list_expired_operation(self):
        """list_expired operation routes correctly."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"windows": []}
        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_expired"
        ))
        self.assertEqual(result["operation"], "list_expired")

    # -------------------------------------------------------------------------
    # bulk_create operation
    # -------------------------------------------------------------------------

    def test_bulk_create_parses_json_array_imap_codes(self):
        """bulk_create parses JSON array string for imap_codes."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"created": 2}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="bulk_create",
            imap_codes='["EAL-012471","ORZ-000012"]',
            start_time="2026-06-01T02:00:00Z",
            duration_hours="2"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["imap_codes"], ["EAL-012471", "ORZ-000012"])

    def test_bulk_create_parses_comma_separated_imap_codes(self):
        """bulk_create parses comma-separated string for imap_codes."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"created": 2}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="bulk_create",
            imap_codes="EAL-012471,ORZ-000012",
            start_time="2026-06-01T02:00:00Z",
            duration_minutes="120"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["imap_codes"], ["EAL-012471", "ORZ-000012"])

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

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            imap_code="EAL-012471",
            start_time="in 1 hour",
            use_tag_filter_expression="true",
            tag_name="environment:production"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertTrue(call_kwargs["use_tag_filter_expression"])

    def test_use_tag_filter_false_string(self):
        """use_tag_filter_expression='false' is parsed as False."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            imap_code="EAL-012471",
            start_time="in 1 hour",
            use_tag_filter_expression="false"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertFalse(call_kwargs["use_tag_filter_expression"])

    def test_use_tag_filter_default_is_false(self):
        """use_tag_filter_expression defaults to False when not provided."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {}

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_active"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertFalse(call_kwargs["use_tag_filter_expression"])

    # -------------------------------------------------------------------------
    # templates resource type
    # -------------------------------------------------------------------------

    def test_get_templates_calls_get_templates_operation(self):
        """templates/get routes to get_templates operation on the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {
            "deployment": {"default_duration": 60},
            "routine": {"default_duration": 30}
        }

        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="templates",
            operation="get"
        ))

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

        asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="create",
            imap_code="ORZ-000012",
            start_time="in 3 hours",
            duration_minutes="30",
            rrule="FREQ=DAILY;INTERVAL=1",
            until_date="2026-06-17T23:59:59Z"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["rrule"], "FREQ=DAILY;INTERVAL=1")
        self.assertEqual(call_kwargs["until_date"], "2026-06-17T23:59:59Z")

    # -------------------------------------------------------------------------
    # Error handling
    # -------------------------------------------------------------------------

    def test_exception_in_client_returns_error(self):
        """If the underlying client raises an exception, the router returns an error dict."""
        self.mock_mw_client.execute_maintenance_operation.side_effect = Exception("Instana API unavailable")

        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="list_active"
        ))

        self.assertIn("error", result)
        self.assertIn("Instana API unavailable", result["error"])

    def test_validate_operation(self):
        """validate operation routes correctly to the underlying client."""
        self.mock_mw_client.execute_maintenance_operation.return_value = {"valid": True}

        result = asyncio.run(self.router.manage_maintenance_windows(
            resource_type="window",
            operation="validate",
            imap_code="EAL-012471",
            start_time="in 1 hour",
            duration_minutes="60"
        ))

        call_kwargs = self.mock_mw_client.execute_maintenance_operation.call_args.kwargs
        self.assertEqual(call_kwargs["operation"], "validate")
        self.assertEqual(result["operation"], "validate")


if __name__ == '__main__':
    unittest.main()
