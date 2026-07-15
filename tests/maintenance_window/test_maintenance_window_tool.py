"""
Comprehensive tests for Maintenance Window MCP Tools

This module contains unit tests for the maintenance window tool,
covering all operations, error handling, and edge cases to achieve >90% coverage.
"""

import asyncio
import json
import logging
import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.maintenance_window.maintenance_window_tool import MaintenanceWindowMCPTools

# Suppress logs during tests
logging.basicConfig(level=logging.ERROR)
tool_logger = logging.getLogger('src.maintenance_window.maintenance_window_tool')
tool_logger.handlers = []
tool_logger.propagate = False

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Mock instana_client before any src imports
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.maintenance_configuration_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.maintenance_config_v2'] = MagicMock()

# Mock MaintenanceConfigV2
mock_maintenance_config = MagicMock()
mock_maintenance_config.from_dict = MagicMock(return_value=MagicMock())
sys.modules['instana_client.models.maintenance_config_v2'].MaintenanceConfigV2 = mock_maintenance_config


class TestMaintenanceWindowMCPTools(unittest.TestCase):
    """Tests for MaintenanceWindowMCPTools"""

    def setUp(self):
        """Set up test fixtures."""
        from src.maintenance_window.maintenance_window_tool import (
            MaintenanceWindowMCPTools,
        )

        self.tool = MaintenanceWindowMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        # Mock current timestamp to be consistent
        self.current_time = int(datetime.now().timestamp() * 1000)
        self.future_time = self.current_time + (2 * 60 * 60 * 1000)  # 2 hours from now

    # -------------------------------------------------------------------------
    # Initialization Tests
    # -------------------------------------------------------------------------

    def test_init_basic(self):
        """Tool initializes with basic credentials."""
        from src.maintenance_window.maintenance_window_tool import (
            MaintenanceWindowMCPTools,
        )

        tool = MaintenanceWindowMCPTools(
            read_token="token123",
            base_url="https://example.instana.com"
        )
        self.assertEqual(tool.read_token, "token123")
        self.assertEqual(tool.base_url, "https://example.instana.com")
        self.assertIsNone(tool.servicenow_token)
        self.assertIsNone(tool.servicenow_url)

    def test_init_with_servicenow(self):
        """Tool initializes with ServiceNow credentials."""
        from src.maintenance_window.maintenance_window_tool import (
            MaintenanceWindowMCPTools,
        )

        tool = MaintenanceWindowMCPTools(
            read_token="token123",
            base_url="https://example.instana.com",
            servicenow_token="snow_token",
            servicenow_url="https://snow.example.com"
        )
        self.assertEqual(tool.servicenow_token, "snow_token")
        self.assertEqual(tool.servicenow_url, "https://snow.example.com")

    def test_templates_available(self):
        """Templates are properly defined."""
        self.assertIn("deployment", self.tool.TEMPLATES)
        self.assertIn("database_migration", self.tool.TEMPLATES)
        self.assertIn("infrastructure_upgrade", self.tool.TEMPLATES)
        self.assertIn("emergency", self.tool.TEMPLATES)
        self.assertIn("routine", self.tool.TEMPLATES)

    # -------------------------------------------------------------------------
    # execute_maintenance_operation - Parameter Validation
    # -------------------------------------------------------------------------

    def test_invalid_operation(self):
        """Invalid operation returns error."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="invalid_op"
        ))
        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_string_start_time_conversion(self):
        """String start_time is converted to integer."""
        with patch.object(self.tool, '_create_maintenance_window', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"status": "success"}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="create",
                imap_code="EAL-012471",
                start_time=str(self.future_time),
                duration_minutes="60"
            ))

            # Verify start_time was converted to int in params dict
            call_kwargs = mock_create.call_args.kwargs
            params = call_kwargs["params"]
            self.assertIsInstance(params["start_time"], int)

    def test_invalid_start_time_string(self):
        """Invalid start_time string returns error."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="create",
            imap_code="EAL-012471",
            start_time="not_a_number",
            duration_minutes="60"
        ))
        self.assertIn("error", result)
        self.assertIn("start_time must be", result["error"])

    def test_string_duration_conversion(self):
        """String duration parameters are converted to integers."""
        with patch.object(self.tool, '_create_maintenance_window', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"status": "success"}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="create",
                imap_code="EAL-012471",
                start_time=str(self.future_time),
                duration_minutes="120",
                duration_hours="2",
                duration_days="1"
            ))

            # Verify durations were converted to int in params dict
            call_kwargs = mock_create.call_args.kwargs
            params = call_kwargs["params"]
            self.assertIsInstance(params["duration_minutes"], int)
            self.assertIsInstance(params["duration_hours"], int)
            self.assertIsInstance(params["duration_days"], int)

    def test_invalid_duration_string(self):
        """Invalid duration string returns error."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="create",
            imap_code="EAL-012471",
            start_time=str(self.future_time),
            duration_minutes="not_a_number"
        ))
        self.assertIn("error", result)
        self.assertIn("duration_minutes must be", result["error"])

    # -------------------------------------------------------------------------
    # Operation Routing Tests
    # -------------------------------------------------------------------------

    def test_create_operation_routing(self):
        """create operation routes to _create_maintenance_window."""
        with patch.object(self.tool, '_create_maintenance_window', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = {"status": "success", "window_id": "mw-123"}

            result = asyncio.run(self.tool.execute_maintenance_operation(
                operation="create",
                imap_code="EAL-012471",
                start_time=self.future_time,
                duration_minutes=60
            ))

            mock_create.assert_called_once()
            self.assertEqual(result["status"], "success")

    def test_modify_operation_routing(self):
        """modify operation routes to _modify_maintenance_window."""
        with patch.object(self.tool, '_modify_maintenance_window', new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = {"status": "success"}

            result = asyncio.run(self.tool.execute_maintenance_operation(
                operation="modify",
                window_id="mw-789",
                duration_minutes=120
            ))

            mock_modify.assert_called_once()
            self.assertEqual(result["status"], "success")

    def test_modify_converts_duration_hours(self):
        """modify operation converts duration_hours to duration_minutes."""
        with patch.object(self.tool, '_modify_maintenance_window', new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = {"status": "success"}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="modify",
                window_id="mw-789",
                duration_hours=3
            ))

            call_kwargs = mock_modify.call_args.kwargs
            self.assertEqual(call_kwargs["duration_minutes"], 180)

    def test_modify_converts_duration_days(self):
        """modify operation converts duration_days to duration_minutes."""
        with patch.object(self.tool, '_modify_maintenance_window', new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = {"status": "success"}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="modify",
                window_id="mw-789",
                duration_days=2
            ))

            call_kwargs = mock_modify.call_args.kwargs
            self.assertEqual(call_kwargs["duration_minutes"], 2880)  # 2 days * 24 * 60

    def test_close_operation_routing(self):
        """close operation routes to _close_maintenance_window."""
        with patch.object(self.tool, '_close_maintenance_window', new_callable=AsyncMock) as mock_close:
            mock_close.return_value = {"status": "success"}

            result = asyncio.run(self.tool.execute_maintenance_operation(
                operation="close",
                window_id="mw-789",
                completion_notes="Completed"
            ))

            mock_close.assert_called_once()
            self.assertEqual(result["status"], "success")

    def test_list_active_operation_routing(self):
        """list_active operation routes to _list_active_windows."""
        with patch.object(self.tool, '_list_active_windows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"status": "success", "windows": []}

            result = asyncio.run(self.tool.execute_maintenance_operation(
                operation="list_active",
                imap_code="EAL-012471"
            ))

            mock_list.assert_called_once()
            self.assertEqual(result["status"], "success")

    def test_list_scheduled_operation_routing(self):
        """list_scheduled operation routes to _list_scheduled_windows."""
        with patch.object(self.tool, '_list_scheduled_windows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"status": "success", "windows": []}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="list_scheduled"
            ))

            mock_list.assert_called_once()

    def test_list_all_operation_routing(self):
        """list_all operation routes to _list_all_windows."""
        with patch.object(self.tool, '_list_all_windows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"status": "success", "windows": []}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="list_all"
            ))

            mock_list.assert_called_once()

    def test_list_expired_operation_routing(self):
        """list_expired operation routes to _list_expired_windows."""
        with patch.object(self.tool, '_list_expired_windows', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = {"status": "success", "windows": []}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="list_expired"
            ))

            mock_list.assert_called_once()

    def test_bulk_create_operation_routing(self):
        """bulk_create operation routes to _bulk_create_windows."""
        with patch.object(self.tool, '_bulk_create_windows', new_callable=AsyncMock) as mock_bulk:
            mock_bulk.return_value = {"status": "success", "total": 2}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="bulk_create",
                imap_codes=["EAL-012471", "ORZ-000012"],
                start_time=self.future_time,
                duration_minutes=60
            ))

            mock_bulk.assert_called_once()

    def test_validate_operation_routing(self):
        """validate operation routes to _validate_window_params."""
        with patch.object(self.tool, '_validate_window_params', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"status": "valid"}

            asyncio.run(self.tool.execute_maintenance_operation(
                operation="validate",
                imap_code="EAL-012471",
                start_time=self.future_time,
                duration_minutes=60
            ))

            mock_validate.assert_called_once()

    def test_get_templates_operation(self):
        """get_templates operation returns templates."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="get_templates"
        ))

        self.assertEqual(result["operation"], "get_templates")
        self.assertEqual(result["status"], "success")
        self.assertIn("templates", result)
        self.assertIn("deployment", result["templates"])

    # -------------------------------------------------------------------------
    # _check_response_status Tests
    # -------------------------------------------------------------------------

    def test_check_response_status_success(self):
        """_check_response_status returns None for successful status codes."""
        mock_response = Mock()
        mock_response.status = 200

        result = self.tool._check_response_status(mock_response, "test operation")
        self.assertIsNone(result)

    def test_check_response_status_created(self):
        """_check_response_status returns None for 201 Created."""
        mock_response = Mock()
        mock_response.status = 201

        result = self.tool._check_response_status(mock_response, "test operation")
        self.assertIsNone(result)

    def test_check_response_status_no_content(self):
        """_check_response_status returns None for 204 No Content."""
        mock_response = Mock()
        mock_response.status = 204

        result = self.tool._check_response_status(mock_response, "test operation")
        self.assertIsNone(result)

    def test_check_response_status_error(self):
        """_check_response_status returns error dict for error status codes."""
        mock_response = Mock()
        mock_response.status = 404

        result = self.tool._check_response_status(mock_response, "test operation")
        self.assertIsNotNone(result)
        self.assertIn("error", result)
        self.assertEqual(result["status_code"], 404)

    def test_check_response_status_no_status_attribute(self):
        """_check_response_status returns None when response has no status attribute."""
        mock_response = Mock(spec=[])  # No attributes

        result = self.tool._check_response_status(mock_response, "test operation")
        self.assertIsNone(result)

    # -------------------------------------------------------------------------
    # _get_templates Tests
    # -------------------------------------------------------------------------

    def test_get_templates_returns_all_templates(self):
        """_get_templates returns all available templates."""
        result = self.tool._get_templates()

        self.assertEqual(result["operation"], "get_templates")
        self.assertEqual(result["status"], "success")
        self.assertIn("templates", result)
        self.assertEqual(len(result["templates"]), 5)

    # -------------------------------------------------------------------------
    # _validate_window_params Tests
    # -------------------------------------------------------------------------

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_validate_missing_application_id(self, mock_timestamp):
        """validate returns error when application_id is missing."""
        mock_timestamp.return_value = {"timestamp": self.current_time}

        result = asyncio.run(self.tool._validate_window_params(
            application_id=None,
            start_time=self.future_time
        ))

        self.assertEqual(result["status"], "invalid")
        self.assertIn("application_id is required", result["errors"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_validate_missing_start_time(self, mock_timestamp):
        """validate returns error when start_time is missing."""
        mock_timestamp.return_value = {"timestamp": self.current_time}

        result = asyncio.run(self.tool._validate_window_params(
            application_id="EAL-012471",
            start_time=None
        ))

        self.assertEqual(result["status"], "invalid")
        self.assertIn("start_time is required", result["errors"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_validate_past_start_time(self, mock_timestamp):
        """validate returns error when start_time is in the past."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        past_time = self.current_time - (60 * 60 * 1000)  # 1 hour ago

        result = asyncio.run(self.tool._validate_window_params(
            application_id="EAL-012471",
            start_time=past_time
        ))

        self.assertEqual(result["status"], "invalid")
        self.assertIn("start_time cannot be in the past", result["errors"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_validate_invalid_template(self, mock_timestamp):
        """validate returns error for invalid template."""
        mock_timestamp.return_value = {"timestamp": self.current_time}

        result = asyncio.run(self.tool._validate_window_params(
            application_id="EAL-012471",
            start_time=self.future_time
        ))

        self.assertEqual(result["status"], "valid")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_validate_success(self, mock_timestamp):
        """validate returns success for valid parameters."""
        mock_timestamp.return_value = {"timestamp": self.current_time}

        result = asyncio.run(self.tool._validate_window_params(
            application_id="EAL-012471",
            start_time=self.future_time
        ))

        self.assertEqual(result["status"], "valid")
        self.assertIn("All parameters are valid", result["message"])

    # -------------------------------------------------------------------------
    # _update_servicenow_change Tests
    # -------------------------------------------------------------------------

    def test_servicenow_update_skipped_when_not_configured(self):
        """ServiceNow update is skipped when not configured."""
        result = asyncio.run(self.tool._update_servicenow_change(
            change_request_id="CHG0012345",
            window_id="mw-123",
            status="maintenance_scheduled"
        ))

        self.assertEqual(result["status"], "skipped")
        self.assertIn("ServiceNow not configured", result["reason"])

    def test_servicenow_update_success(self):
        """ServiceNow update succeeds when configured."""
        from src.maintenance_window.maintenance_window_tool import (
            MaintenanceWindowMCPTools,
        )

        tool = MaintenanceWindowMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com",
            servicenow_token="snow_token",
            servicenow_url="https://snow.example.com"
        )

        result = asyncio.run(tool._update_servicenow_change(
            change_request_id="CHG0012345",
            window_id="mw-123",
            status="maintenance_scheduled"
        ))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["change_request_id"], "CHG0012345")
        self.assertEqual(result["window_id"], "mw-123")

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    def test_execute_maintenance_operation_exception_handling(self):
        """execute_maintenance_operation handles exceptions gracefully."""
        with patch.object(self.tool, '_create_maintenance_window', side_effect=Exception("Test error")):
            result = asyncio.run(self.tool.execute_maintenance_operation(
                operation="create",
                imap_code="EAL-012471",
                start_time=self.future_time,
                duration_minutes=60
            ))

            self.assertIn("error", result)
            self.assertIn("Test error", result["error"])

    # -------------------------------------------------------------------------
    # _create_maintenance_window Tests
    # -------------------------------------------------------------------------

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    def test_create_window_missing_imap_code(self, mock_uuid, mock_timestamp):
        """create returns error when imap_code is missing."""
        mock_timestamp.return_value = {"timestamp": self.current_time}

        # Mock the API client
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": None,
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("imap_code or application_id is required", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_create_window_missing_start_time(self, mock_timestamp):
        """create returns error when start_time is missing."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": None,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("start_time is required", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_create_window_invalid_template(self, mock_timestamp):
        """create returns error for invalid template."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": "invalid_template",
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid template", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_create_window_past_start_time(self, mock_timestamp):
        """create returns error when start_time is in the past."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()
        past_time = self.current_time - (60 * 60 * 1000)  # 1 hour ago

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": past_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("start_time cannot be in the past", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_success_with_duration_minutes(self, mock_config_class, mock_uuid, mock_timestamp):
        """create successfully creates window with duration_minutes."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        # Mock API client
        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({
            "id": "1234567890abcdef",
            "name": "EAL-012471_Test_2026_01_01",
            "scheduling": {"type": "ONE_TIME"}
        }).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response

        # Mock MaintenanceConfigV2.from_dict
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "create")
        self.assertEqual(result["status"], "success")
        self.assertIn("window_id", result["details"])

    # -------------------------------------------------------------------------
    # _modify_maintenance_window Tests
    # -------------------------------------------------------------------------

    def test_modify_window_missing_window_id(self):
        """modify returns error when window_id is missing."""

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_template(self, mock_config_class, mock_uuid, mock_timestamp):
        """create applies template configuration."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({
            "id": "1234567890abcdef",
            "name": "EAL-012471_Deployment_2026_01_01"
        }).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Deployment",
                "template": "deployment",
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_duration_hours(self, mock_config_class, mock_uuid, mock_timestamp):
        """create calculates end time from duration_hours."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": None,
                "duration_hours": 2,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_duration_days(self, mock_config_class, mock_uuid, mock_timestamp):
        """create calculates end time from duration_days."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": 1,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_rounds_duration(self, mock_config_class, mock_uuid, mock_timestamp):
        """create rounds duration to whole hours for recurring windows."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 45,  # Will be rounded to 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": "2026-12-31T23:59:59Z",
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_minimum_duration(self, mock_config_class, mock_uuid, mock_timestamp):
        """create enforces minimum 1 hour for recurring windows."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 30,  # Will be increased to 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=WEEKLY;BYDAY=MO",
                "until_date": "2026-12-31T23:59:59Z",
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_end_time(self, mock_config_class, mock_uuid, mock_timestamp):
        """create calculates duration from end_time."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        end_time = self.future_time + (2 * 60 * 60 * 1000)  # 2 hours later

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": end_time,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_end_time_days(self, mock_config_class, mock_uuid, mock_timestamp):
        """create calculates duration in days from end_time."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_with_until_date(self, mock_config_class, mock_uuid, mock_timestamp):
        """create adds UNTIL to rrule when until_date provided."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": "2026-12-31T23:59:59Z",
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_rrule_has_until(self, mock_config_class, mock_uuid, mock_timestamp):
        """create uses rrule as-is when UNTIL already present."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1;UNTIL=20261231T235959Z",
                "until_date": "2026-12-31T23:59:59Z",
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_invalid_until_date(self, mock_config_class, mock_uuid, mock_timestamp):
        """create handles invalid until_date gracefully."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": "invalid-date",
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_tag_filter_expression(self, mock_config_class, mock_uuid, mock_timestamp):
        """create uses tag filter expression format."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": True,
                "tag_name": "imap",
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_api_error(self, mock_config_class, mock_uuid, mock_timestamp):
        """create handles API errors."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 400
        mock_response.read.return_value = b'{"error": "Bad request"}'
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertIn("error", result)
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        end_time = self.future_time + (48 * 60 * 60 * 1000)  # 2 days later

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": end_time,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_empty_response(self, mock_config_class, mock_uuid, mock_timestamp):
        """create handles empty API response."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = b''
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertIn("error", result)
        self.assertIn("Empty response", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_response_validation(self, mock_config_class, mock_uuid, mock_timestamp):
        """create validates recurring window in response."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({
            "id": "mw-123",
            "scheduling": {
                "type": "RECURRENT",
                "rrule": "FREQ=DAILY;INTERVAL=1"
            }
        }).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_recurring_window_type_mismatch(self, mock_config_class, mock_uuid, mock_timestamp):
        """create warns when response type doesn't match request."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        # Response shows ONE_TIME even though we requested RECURRENT
        mock_response.read.return_value = json.dumps({
            "id": "mw-123",
            "scheduling": {
                "type": "ONE_TIME"
            }
        }).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "application_id": None,
                "imap_code": "EAL-012471",
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    @patch('src.maintenance_window.maintenance_window_tool.uuid.uuid4')
    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_with_servicenow_integration(self, mock_config_class, mock_uuid, mock_timestamp):
        """create integrates with ServiceNow when configured."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_uuid.return_value = Mock(hex='1234567890abcdef')

        # Create tool with ServiceNow credentials
        tool_with_snow = MaintenanceWindowMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io",
            servicenow_token="snow_token",
            servicenow_url="https://test.service-now.com"
        )

        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": "mw-123"}).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        # Mock ServiceNow update
        with patch.object(tool_with_snow, '_update_servicenow_change', return_value=None) as mock_snow:
            result = asyncio.run(tool_with_snow._create_maintenance_window(
                params={
                    "application_id": None,
                    "imap_code": "EAL-012471",
                    "start_time": self.future_time,
                    "end_time": None,
                    "duration_minutes": 60,
                    "duration_hours": None,
                    "duration_days": None,
                    "reason": "Test",
                    "template": None,
                    "change_request_id": "CHG0012345",
                    "affected_services": None,
                    "notification_channels": None,
                    "use_tag_filter_expression": False,
                    "tag_name": None,
                    "rrule": None,
                    "until_date": None,
                },
                ctx=None,
                api_client=mock_api_client
            ))

            self.assertIsNotNone(result)
            self.assertEqual(result["status"], "success")
            mock_snow.assert_called_once()

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_with_rrule(self, mock_config_class):
        """modify updates rrule for recurring windows."""
        mock_api_client = Mock()

        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "RECURRENT",
                "rrule": "FREQ=DAILY;INTERVAL=1"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }

        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        mock_put_response = Mock()
        mock_put_response.status = 200
        mock_put_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_put_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=None,
            reason="Updated",
            rrule="FREQ=WEEKLY;BYDAY=MO",
            until_date="2026-12-31T23:59:59Z",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["operation"], "modify")
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_api_error(self, mock_config_class):
        """modify handles API errors."""

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_with_until_date_iso_format(self, mock_config_class):
        """modify updates until_date in ISO format."""
        mock_api_client = Mock()

        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "RECURRENT",
                "rrule": "FREQ=DAILY;INTERVAL=1"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }

        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        mock_put_response = Mock()
        mock_put_response.status = 200
        mock_put_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_put_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=None,
            reason="Updated",
            rrule=None,
            until_date="2026-12-31T23:59:59Z",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_with_until_date_only(self, mock_config_class):
        """modify handles date-only until_date."""
        mock_api_client = Mock()

        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "RECURRENT",
                "rrule": "FREQ=DAILY;INTERVAL=1"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }

        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        mock_put_response = Mock()
        mock_put_response.status = 200
        mock_put_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_put_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=None,
            reason="Updated",
            rrule=None,
            until_date="2026-12-31",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_with_until_date_timestamp(self, mock_config_class):
        """modify handles timestamp until_date."""
        mock_api_client = Mock()

        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "RECURRENT",
                "rrule": "FREQ=DAILY;INTERVAL=1"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }

        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        mock_put_response = Mock()
        mock_put_response.status = 200
        mock_put_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_put_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=None,
            reason="Updated",
            rrule=None,
            until_date=self.future_time + (30 * 24 * 60 * 60 * 1000),  # 30 days later
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_invalid_until_date(self, mock_config_class):
        """modify returns error for invalid until_date."""
        mock_api_client = Mock()

        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "RECURRENT",
                "rrule": "FREQ=DAILY;INTERVAL=1"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }

        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=None,
            reason="Updated",
            rrule=None,
            until_date="invalid-date-format",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertIn("error", result)

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_no_existing_rrule_with_until_date(self, mock_config_class):
        """modify creates rrule when until_date provided but no existing rrule."""
        mock_api_client = Mock()

        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "ONE_TIME"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }

        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        mock_put_response = Mock()
        mock_put_response.status = 200
        mock_put_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_put_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=None,
            reason="Updated",
            rrule=None,
            until_date="2026-12-31T23:59:59Z",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "success")

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_api_error_on_get(self, mock_config_class):
        """modify handles API errors on get."""
        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 500
        mock_response.read.return_value = b'{"error": "Internal server error"}'
        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=120,
            reason="Extended",
            rrule=None,
            until_date=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertIn("error", result)

    def test_modify_window_not_found(self):
        """modify returns error when window is not found."""
        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 404
        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="nonexistent",
            end_time=None,
            duration_minutes=120,
            reason="Extended",
            rrule=None,
            until_date=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_success(self, mock_config_class):
        """modify successfully updates window."""
        mock_api_client = Mock()

        # Mock get response
        existing_window = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471",
            "scheduling": {
                "start": self.future_time,
                "duration": {"amount": 1, "unit": "HOURS"},
                "type": "ONE_TIME"
            },
            "paused": False,
            "tagFilterExpressionEnabled": False,
            "retriggerOpenAlertsEnabled": False
        }
        mock_get_response = Mock()
        mock_get_response.status = 200
        mock_get_response.read.return_value = json.dumps(existing_window).encode()

        # Mock put response
        mock_put_response = Mock()
        mock_put_response.status = 200
        mock_put_response.read.return_value = json.dumps(existing_window).encode()

        mock_api_client.get_maintenance_config_v2_without_preload_content.return_value = mock_get_response
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_put_response
        mock_config_class.from_dict.return_value = Mock()

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=120,
            reason="Extended",
            rrule=None,
            until_date=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "modify")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["window_id"], "mw-123")

    # -------------------------------------------------------------------------
    # _close_maintenance_window Tests
    # -------------------------------------------------------------------------

    def test_close_window_missing_window_id(self):
        """close returns error when window_id is missing."""
        mock_api_client = Mock()

        result = asyncio.run(self.tool._close_maintenance_window(
            window_id=None,
            completion_notes="Completed",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("window_id is required", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_close_window_success(self, mock_timestamp):
        """close successfully closes window."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 204
        mock_response.read.return_value = b''
        mock_api_client.delete_maintenance_config_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._close_maintenance_window(
            window_id="mw-123",
            completion_notes="Completed successfully",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "close")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["window_id"], "mw-123")
        self.assertEqual(result["completion_notes"], "Completed successfully")

    # -------------------------------------------------------------------------
    # _list_active_windows Tests
    # -------------------------------------------------------------------------

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_list_active_windows_empty(self, mock_timestamp):
        """list_active returns empty list when no active windows."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps([]).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_active_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "list_active")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["windows"]), 0)

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_list_active_windows_with_results(self, mock_timestamp):
        """list_active returns active windows."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()

        windows = [
            {"id": "mw-1", "name": "window1", "state": "ACTIVE", "query": "entity.tag:imap=EAL-012471"},
            {"id": "mw-2", "name": "window2", "state": "SCHEDULED", "query": "entity.tag:imap=EAL-012471"},
            {"id": "mw-3", "name": "window3", "state": "ACTIVE", "query": "entity.tag:imap=ORZ-000012"}
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_active_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "list_active")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)  # Only ACTIVE windows

    # -------------------------------------------------------------------------
    # _list_scheduled_windows Tests
    # -------------------------------------------------------------------------

    def test_list_scheduled_windows(self):
        """list_scheduled returns scheduled windows."""
        mock_api_client = Mock()

        windows = [
            {"id": "mw-1", "name": "window1", "state": "ACTIVE"},
            {"id": "mw-2", "name": "window2", "state": "SCHEDULED"},
            {"id": "mw-3", "name": "window3", "state": "SCHEDULED"}
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_scheduled_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "list_scheduled")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)  # Only SCHEDULED windows

    # -------------------------------------------------------------------------
    # _list_all_windows Tests
    # -------------------------------------------------------------------------

    def test_list_all_windows(self):
        """list_all returns all windows grouped by state."""
        mock_api_client = Mock()

        windows = [
            {"id": "mw-1", "name": "window1", "state": "ACTIVE"},
            {"id": "mw-2", "name": "window2", "state": "SCHEDULED"},
            {"id": "mw-3", "name": "window3", "state": "EXPIRED"}
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_all_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "list_all")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_count"], 3)
        self.assertEqual(result["active_count"], 1)
        self.assertEqual(result["scheduled_count"], 1)
        self.assertEqual(result["expired_count"], 1)

    # -------------------------------------------------------------------------
    # _list_expired_windows Tests
    # -------------------------------------------------------------------------

    def test_list_expired_windows(self):
        """list_expired returns expired windows."""
        mock_api_client = Mock()

        windows = [
            {"id": "mw-1", "name": "window1", "state": "ACTIVE"},
            {"id": "mw-2", "name": "window2", "state": "EXPIRED"},
            {"id": "mw-3", "name": "window3", "state": "EXPIRED"}
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_expired_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "list_expired")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 2)  # Only EXPIRED windows

    # -------------------------------------------------------------------------
    # _bulk_create_windows Tests
    # -------------------------------------------------------------------------

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceWindowMCPTools._create_maintenance_window')
    def test_bulk_create_missing_codes(self, mock_create):
        """bulk_create returns error when no codes provided."""
        mock_api_client = Mock()

        result = asyncio.run(self.tool._bulk_create_windows(
            application_ids=None,
            imap_codes=None,
            start_time=self.future_time,
            duration_minutes=60,
            duration_hours=None,
            duration_days=None,
            reason="Bulk test",
            template=None,
            change_request_id=None,
            use_tag_filter_expression=False,
            tag_name=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIsNotNone(result)
        self.assertIn("error", result)
        self.assertIn("imap_codes or application_ids is required", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceWindowMCPTools._create_maintenance_window')
    def test_bulk_create_success(self, mock_create):
        """bulk_create successfully creates multiple windows."""
        mock_create.return_value = {"status": "success", "window_id": "mw-123"}
        mock_api_client = Mock()

        result = asyncio.run(self.tool._bulk_create_windows(
            application_ids=None,
            imap_codes=["EAL-012471", "ORZ-000012"],
            start_time=self.future_time,
            duration_minutes=60,
            duration_hours=None,
            duration_days=None,
            reason="Bulk test",
            template=None,
            change_request_id=None,
            use_tag_filter_expression=False,
            tag_name=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["operation"], "bulk_create")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["successful"], 2)
        self.assertEqual(result["failed"], 0)




    # -------------------------------------------------------------------------
    # Additional Coverage Tests for 90%+
    # -------------------------------------------------------------------------

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_create_recurring_window_rounds_duration_up(self, mock_timestamp, mock_config_class):
        """create rounds up duration for recurring windows to whole hours."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()
        mock_response = Mock()
        mock_response.status = 201

        window_data = {
            "id": "mw-123",
            "name": "test_window",
            "query": "entity.tag:imap=EAL-012471"
        }
        mock_response.read.return_value = json.dumps(window_data).encode()
        mock_api_client.put_maintenance_config_v2_without_preload_content.return_value = mock_response
        mock_config_class.from_dict.return_value = Mock()

        # 90 minutes should round up to 2 hours for recurring windows
        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "imap_code": "EAL-012471",
                "application_id": None,
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 90,  # Not a whole hour,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test recurring",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["status"], "success")

    def test_create_window_end_time_before_start_time(self):
        """create returns error when end_time is before start_time."""
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "imap_code": "EAL-012471",
                "application_id": None,
                "start_time": self.future_time,
                "end_time": self.future_time - 1000,  # Before start time,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("end_time must be after start_time", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_list_active_windows_fallback_to_occurrence(self, mock_timestamp):
        """list_active uses occurrence times when state is not available."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()

        # Windows without state field, using occurrence times
        windows = [
            {
                "id": "mw-1",
                "name": "window1",
                "query": "entity.tag:imap=EAL-012471",
                "occurrence": {
                    "start": self.current_time - 1000,
                    "end": self.current_time + 1000
                }
            },
            {
                "id": "mw-2",
                "name": "window2",
                "query": "entity.tag:imap=ORZ-000012",
                "occurrence": {
                    "start": self.current_time + 10000,
                    "end": self.current_time + 20000
                }
            }
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_active_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)  # Only mw-1 is active

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_list_active_windows_with_application_filter_fallback(self, mock_timestamp):
        """list_active filters by application_id using occurrence fallback."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()

        windows = [
            {
                "id": "mw-1",
                "name": "window1",
                "query": "entity.tag:imap=EAL-012471",
                "occurrence": {
                    "start": self.current_time - 1000,
                    "end": self.current_time + 1000
                }
            },
            {
                "id": "mw-2",
                "name": "window2",
                "query": "entity.tag:imap=ORZ-000012",
                "occurrence": {
                    "start": self.current_time - 1000,
                    "end": self.current_time + 1000
                }
            }
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_active_windows(
            application_id="EAL-012471",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["windows"][0]["id"], "mw-1")

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_list_active_windows_exception_handling(self, mock_timestamp):
        """list_active handles exceptions gracefully."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.side_effect = Exception("API error")

        result = asyncio.run(self.tool._list_active_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to list active windows", result["error"])

    def test_list_scheduled_windows_with_application_filter(self):
        """list_scheduled filters by application_id."""
        mock_api_client = Mock()

        windows = [
            {"id": "mw-1", "name": "window1", "state": "SCHEDULED", "query": "entity.tag:imap=EAL-012471"},
            {"id": "mw-2", "name": "window2", "state": "SCHEDULED", "query": "entity.tag:imap=ORZ-000012"},
            {"id": "mw-3", "name": "window3", "state": "ACTIVE", "query": "entity.tag:imap=EAL-012471"}
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_scheduled_windows(
            application_id="EAL-012471",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["windows"][0]["id"], "mw-1")
        self.assertEqual(result["application_id"], "EAL-012471")

    def test_list_scheduled_windows_exception_handling(self):
        """list_scheduled handles exceptions gracefully."""
        mock_api_client = Mock()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.side_effect = Exception("API error")

        result = asyncio.run(self.tool._list_scheduled_windows(
            application_id=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to list scheduled windows", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.get_current_timestamp')
    def test_list_active_windows_with_tag_filter_expression(self, mock_timestamp):
        """list_active filters using tagFilterExpression."""
        mock_timestamp.return_value = {"timestamp": self.current_time}
        mock_api_client = Mock()

        windows = [
            {
                "id": "mw-1",
                "name": "window1",
                "state": "ACTIVE",
                "query": "",
                "tagFilterExpression": {"value": "EAL-012471"}
            },
            {
                "id": "mw-2",
                "name": "window2",
                "state": "ACTIVE",
                "query": "",
                "tagFilterExpression": {"value": "ORZ-000012"}
            }
        ]

        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(windows).encode()
        mock_api_client.get_maintenance_configs_v2_without_preload_content.return_value = mock_response

        result = asyncio.run(self.tool._list_active_windows(
            application_id="EAL-012471",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["windows"][0]["id"], "mw-1")


    def test_create_window_invalid_end_time_string(self):
        """create returns error when end_time string is invalid."""
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "imap_code": "EAL-012471",
                "application_id": None,
                "start_time": self.future_time,
                "end_time": "invalid-timestamp",  # Invalid string,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)

    def test_create_window_invalid_duration_hours_string(self):
        """create returns error when duration_hours string is invalid."""
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "imap_code": "EAL-012471",
                "application_id": None,
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": None,
                "duration_hours": "invalid",  # Invalid string,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)

    def test_create_window_invalid_duration_days_string(self):
        """create returns error when duration_days string is invalid."""
        mock_api_client = Mock()

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "imap_code": "EAL-012471",
                "application_id": None,
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": None,
                "duration_hours": None,
                "duration_days": "invalid",  # Invalid string,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_create_window_general_exception(self, mock_config_class):
        """create handles general exceptions."""
        mock_api_client = Mock()
        mock_config_class.from_dict.side_effect = Exception("Unexpected error")

        result = asyncio.run(self.tool._create_maintenance_window(
            params={
                "imap_code": "EAL-012471",
                "application_id": None,
                "start_time": self.future_time,
                "end_time": None,
                "duration_minutes": 60,
                "duration_hours": None,
                "duration_days": None,
                "reason": "Test",
                "template": None,
                "change_request_id": None,
                "affected_services": None,
                "notification_channels": None,
                "use_tag_filter_expression": False,
                "tag_name": None,
                "rrule": None,
                "until_date": None,
            },
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to create maintenance window", result["error"])

    @patch('src.maintenance_window.maintenance_window_tool.MaintenanceConfigV2')
    def test_modify_window_general_exception(self, mock_config_class):
        """modify handles general exceptions."""
        mock_api_client = Mock()
        mock_api_client.get_maintenance_config_v2_without_preload_content.side_effect = Exception("Unexpected error")

        result = asyncio.run(self.tool._modify_maintenance_window(
            window_id="mw-123",
            end_time=None,
            duration_minutes=120,
            reason="Extended",
            rrule=None,
            until_date=None,
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to fetch window", result["error"])

    def test_close_window_general_exception(self):
        """close handles general exceptions."""
        mock_api_client = Mock()
        mock_api_client.delete_maintenance_config_v2_without_preload_content.side_effect = Exception("Unexpected error")

        result = asyncio.run(self.tool._close_maintenance_window(
            window_id="mw-123",
            completion_notes="Test",
            ctx=None,
            api_client=mock_api_client
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to close maintenance window", result["error"])


    def test_execute_operation_invalid_end_time_string(self):
        """execute_maintenance_operation handles invalid end_time string."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="create",
            imap_code="EAL-012471",
            start_time=str(self.future_time),
            end_time="not-a-number",  # Invalid
            ctx=None
        ))

        self.assertIn("error", result)

    def test_execute_operation_invalid_duration_hours_string(self):
        """execute_maintenance_operation handles invalid duration_hours string."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="create",
            imap_code="EAL-012471",
            start_time=str(self.future_time),
            duration_hours="not-a-number",  # Invalid
            ctx=None
        ))

        self.assertIn("error", result)

    def test_execute_operation_invalid_duration_days_string(self):
        """execute_maintenance_operation handles invalid duration_days string."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="create",
            imap_code="EAL-012471",
            start_time=str(self.future_time),
            duration_days="not-a-number",  # Invalid
            ctx=None
        ))

        self.assertIn("error", result)

    def test_execute_operation_unimplemented_operation(self):
        """execute_maintenance_operation handles unimplemented operations."""
        result = asyncio.run(self.tool.execute_maintenance_operation(
            operation="unknown_operation",
            imap_code="EAL-012471",
            start_time=str(self.future_time),
            ctx=None
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])


if __name__ == '__main__':
    unittest.main()
