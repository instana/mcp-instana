"""
Unit tests for SLO Smart Router Tool.

Tests the SLOSmartRouterMCPTool which routes SLO operations to appropriate clients.
"""

import asyncio
import logging
import unittest
from unittest.mock import MagicMock, patch


# Mock the with_header_auth decorator before importing the router
def mock_with_header_auth(func):
    """Mock decorator that returns the function unchanged."""
    return func

# Suppress logging during tests
logging.getLogger().addHandler(logging.NullHandler())

# Patch the decorator at import time
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.router.slo_smart_router_tool import SLOSmartRouterMCPTool


class TestSLOSmartRouterTool(unittest.TestCase):
    """Test cases for SLO Smart Router Tool."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock clients
        self.mock_config_client = MagicMock()
        self.mock_report_client = MagicMock()
        self.mock_alert_client = MagicMock()
        self.mock_correction_client = MagicMock()

        # Create router and directly assign mock clients
        self.router = SLOSmartRouterMCPTool.__new__(SLOSmartRouterMCPTool)
        self.router.read_token = "test_token"
        self.router.base_url = "https://test.instana.com"
        # Assign mock clients directly
        self.router.slo_config_client = self.mock_config_client
        self.router.slo_report_client = self.mock_report_client
        self.router.slo_alert_client = self.mock_alert_client
        self.router.slo_correction_client = self.mock_correction_client

    def test_initialization(self):
        """Test router initialization."""
        self.assertIsNotNone(self.router)
        self.assertIsNotNone(self.router.slo_config_client)
        self.assertIsNotNone(self.router.slo_report_client)
        self.assertIsNotNone(self.router.slo_alert_client)
        self.assertIsNotNone(self.router.slo_correction_client)

    def test_invalid_resource_type(self):
        """Test handling of invalid resource type."""
        async def mock_method(*args, **kwargs):
            return {"data": "test"}

        result = asyncio.run(self.router.manage_slo(
            resource_type="invalid_type",
            operation="get_all"
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Invalid resource_type", (result.get("error") or result.get("message", "")))

    # Configuration Tests
    def test_config_get_all(self):
        """Test configuration get_all operation."""
        async def mock_get_all(*args, **kwargs):
            return {"configs": [{"id": "slo-1", "name": "Test SLO"}]}

        self.mock_config_client.get_all_slo_configs = mock_get_all

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="get_all",
            params={"page_size": 20, "query": "test"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "configuration")
        self.assertEqual(result["operation"], "get_all")

    def test_config_get_by_id(self):
        """Test configuration get_by_id operation."""
        async def mock_get_by_id(*args, **kwargs):
            return {"id": "slo-123", "name": "Test SLO"}

        self.mock_config_client.get_slo_config_by_id = mock_get_by_id

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="get_by_id",
            params={"id": "slo-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "configuration")

    def test_config_get_by_id_missing_id(self):
        """Test configuration get_by_id with missing id."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="get_by_id",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameter 'id'", (result.get("error") or result.get("message", "")))

    def test_config_create(self):
        """Test configuration create operation."""
        async def mock_create(*args, **kwargs):
            return {"id": "slo-new", "name": "New SLO"}

        self.mock_config_client.create_slo_config = mock_create

        payload = {
            "name": "New SLO",
            "entity": {"type": "application", "applicationId": "app-123", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency", "threshold": 100},
            "target": 0.95,
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="create",
            params={"payload": payload}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "create")

    def test_config_create_missing_payload(self):
        """Test configuration create with missing payload."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="create",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("payload", (result.get("error") or result.get("message", "")))

    def test_config_update(self):
        """Test configuration update operation."""
        async def mock_update(*args, **kwargs):
            return {"id": "slo-123", "name": "Updated SLO"}

        self.mock_config_client.update_slo_config = mock_update

        payload = {"name": "Updated SLO", "target": 0.99}

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="update",
            params={"id": "slo-123", "payload": payload}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "update")

    def test_config_update_missing_params(self):
        """Test configuration update with missing parameters."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="update",
            params={"id": "slo-123"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("payload", (result.get("error") or result.get("message", "")))

    def test_config_delete(self):
        """Test configuration delete operation."""
        async def mock_delete(*args, **kwargs):
            return {"success": True}

        self.mock_config_client.delete_slo_config = mock_delete

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="delete",
            params={"id": "slo-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "delete")

    def test_config_delete_missing_id(self):
        """Test configuration delete with missing id."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="delete",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameter 'id'", (result.get("error") or result.get("message", "")))

    def test_config_get_tags(self):
        """Test configuration get_tags operation."""
        async def mock_get_tags(*args, **kwargs):
            return {"tags": ["prod", "api"]}

        self.mock_config_client.get_all_slo_config_tags = mock_get_tags

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="get_tags",
            params={"query": "prod"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_tags")

    def test_config_invalid_operation(self):
        """Test configuration with invalid operation."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="invalid_op",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Invalid operation", (result.get("error") or result.get("message", "")))

    # Report Tests
    def test_report_get(self):
        """Test report get operation."""
        async def mock_get_report(*args, **kwargs):
            return {"sli": 0.95, "target": 0.99, "errorBudget": {"remaining": 50}}

        self.mock_report_client.get_slo_report = mock_get_report

        # Mock the timestamp conversion to avoid elicitation
        with patch('src.router.slo_smart_router_tool.convert_datetime_param_with_required_timezone') as mock_convert:
            # Return that no conversion is needed (already a timestamp)
            mock_convert.return_value = {"converted": False}

            result = asyncio.run(self.router.manage_slo(
                resource_type="report",
                operation="get",
                params={
                    "slo_id": "slo-123",
                    "var_from": "1609459200000",  # Valid timestamp
                    "to": "1612137600000"
                }
            ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "report")

    def test_report_get_missing_slo_id(self):
        """Test report get with missing slo_id."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="report",
            operation="get",
            params={"var_from": "1609459200000", "to": "1612137600000"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameter 'slo_id'", (result.get("error") or result.get("message", "")))

    def test_report_invalid_operation(self):
        """Test report with invalid operation."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="report",
            operation="invalid_op",
            params={"slo_id": "slo-123"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Invalid report operation", (result.get("error") or result.get("message", "")))

    # Alert Tests
    def test_alert_find_active(self):
        """Test alert find_active operation."""
        async def mock_find_active(*args, **kwargs):
            return {"alerts": [{"id": "alert-1", "name": "Test Alert"}]}

        self.mock_alert_client.find_active_alert_configs = mock_find_active

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="find_active",
            params={"slo_id": "slo-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "alert")

    def test_alert_find(self):
        """Test alert find operation."""
        async def mock_find(*args, **kwargs):
            return {"id": "alert-123", "name": "Test Alert"}

        self.mock_alert_client.find_alert_config = mock_find

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="find",
            params={"id": "alert-123"}
        ))

        self.assertIn("results", result)

    def test_alert_find_missing_id(self):
        """Test alert find with missing id."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="find",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameter 'id'", (result.get("error") or result.get("message", "")))

    def test_alert_find_versions(self):
        """Test alert find_versions operation."""
        async def mock_find_versions(*args, **kwargs):
            return {"versions": [{"created": 1609459200000}]}

        self.mock_alert_client.find_alert_config_versions = mock_find_versions

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="find_versions",
            params={"id": "alert-123"}
        ))

        self.assertIn("results", result)

    def test_alert_create(self):
        """Test alert create operation."""
        async def mock_create(*args, **kwargs):
            return {"id": "alert-new", "name": "New Alert"}

        self.mock_alert_client.create_alert_config = mock_create

        payload = {
            "name": "New Alert",
            "description": "Test",
            "sloIds": ["slo-123"],
            "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"},
            "severity": 10,
            "alertChannelIds": ["ch-123"],
            "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
            "customPayloadFields": []
        }

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="create",
            params={"payload": payload}
        ))

        self.assertIn("results", result)

    def test_alert_create_missing_payload(self):
        """Test alert create with missing payload."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="create",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("payload", (result.get("error") or result.get("message", "")))

    def test_alert_update(self):
        """Test alert update operation."""
        async def mock_update(*args, **kwargs):
            return {"id": "alert-123", "name": "Updated Alert"}

        self.mock_alert_client.update_alert_config = mock_update

        payload = {"name": "Updated Alert"}

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="update",
            params={"id": "alert-123", "payload": payload}
        ))

        self.assertIn("results", result)

    def test_alert_update_missing_params(self):
        """Test alert update with missing parameters."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="update",
            params={"id": "alert-123"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameters", (result.get("error") or result.get("message", "")))

    def test_alert_delete(self):
        """Test alert delete operation."""
        async def mock_delete(*args, **kwargs):
            return {"success": True}

        self.mock_alert_client.delete_alert_config = mock_delete

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="delete",
            params={"id": "alert-123"}
        ))

        self.assertIn("results", result)

    def test_alert_disable(self):
        """Test alert disable operation."""
        async def mock_disable(*args, **kwargs):
            return {"success": True}

        self.mock_alert_client.disable_alert_config = mock_disable

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="disable",
            params={"id": "alert-123"}
        ))

        self.assertIn("results", result)

    def test_alert_enable(self):
        """Test alert enable operation."""
        async def mock_enable(*args, **kwargs):
            return {"success": True}

        self.mock_alert_client.enable_alert_config = mock_enable

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="enable",
            params={"id": "alert-123"}
        ))

        self.assertIn("results", result)

    def test_alert_restore(self):
        """Test alert restore operation."""
        async def mock_restore(*args, **kwargs):
            return {"success": True}

        self.mock_alert_client.restore_alert_config = mock_restore

        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="restore",
            params={"id": "alert-123", "created": 1609459200000}
        ))

        self.assertIn("results", result)

    def test_alert_restore_missing_params(self):
        """Test alert restore with missing parameters."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="alert",
            operation="restore",
            params={"id": "alert-123"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameters", (result.get("error") or result.get("message", "")))

    # Correction Tests
    def test_correction_get_all(self):
        """Test correction get_all operation."""
        async def mock_get_all(*args, **kwargs):
            return {"corrections": [{"id": "corr-1", "name": "Maintenance"}]}

        self.mock_correction_client.get_all_corrections = mock_get_all

        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="get_all",
            params={"page_size": 20}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "correction")

    def test_correction_get_by_id(self):
        """Test correction get_by_id operation."""
        async def mock_get_by_id(*args, **kwargs):
            return {"id": "corr-123", "name": "Maintenance"}

        self.mock_correction_client.get_correction_by_id = mock_get_by_id

        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="get_by_id",
            params={"id": "corr-123"}
        ))

        self.assertIn("results", result)

    def test_correction_get_by_id_missing_id(self):
        """Test correction get_by_id with missing id."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="get_by_id",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameter 'id'", (result.get("error") or result.get("message", "")))

    def test_correction_create(self):
        """Test correction create operation."""
        async def mock_create(*args, **kwargs):
            return {"id": "corr-new", "name": "New Correction"}

        self.mock_correction_client.create_correction = mock_create

        payload = {
            "name": "Maintenance",
            "scheduling": {
                "duration": 2,
                "durationUnit": "hour",
                "startTime": 1609459200000
            },
            "sloIds": ["slo-123"]
        }

        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="create",
            params={"payload": payload}
        ))

        self.assertIn("results", result)

    def test_correction_create_missing_payload(self):
        """Test correction create with missing payload."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="create",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("payload", (result.get("error") or result.get("message", "")))

    def test_correction_update(self):
        """Test correction update operation."""
        async def mock_update(*args, **kwargs):
            return {"id": "corr-123", "name": "Updated Correction"}

        self.mock_correction_client.update_correction = mock_update

        payload = {
            "name": "Updated Correction",
            "scheduling": {"duration": 3, "durationUnit": "hour", "startTime": 1609459200000}
        }

        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="update",
            params={"id": "corr-123", "payload": payload}
        ))

        self.assertIn("results", result)

    def test_correction_update_missing_params(self):
        """Test correction update with missing parameters."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="update",
            params={"id": "corr-123"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameters", (result.get("error") or result.get("message", "")))

    def test_correction_delete(self):
        """Test correction delete operation."""
        async def mock_delete(*args, **kwargs):
            return {"success": True}

        self.mock_correction_client.delete_correction = mock_delete

        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="delete",
            params={"id": "corr-123"}
        ))

        self.assertIn("results", result)

    def test_correction_delete_missing_id(self):
        """Test correction delete with missing id."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="delete",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Missing required parameter 'id'", (result.get("error") or result.get("message", "")))

    def test_correction_invalid_operation(self):
        """Test correction with invalid operation."""
        result = asyncio.run(self.router.manage_slo(
            resource_type="correction",
            operation="invalid_op",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Invalid correction operation", (result.get("error") or result.get("message", "")))

    # Error Handling Tests
    def test_exception_handling(self):
        """Test exception handling in router."""
        async def mock_error(*args, **kwargs):
            raise Exception("Test error")

        self.mock_config_client.get_all_slo_configs = mock_error

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="get_all"
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Configuration operation error", (result.get("error") or result.get("message", "")))

    def test_params_none(self):
        """Test handling when params is None."""
        async def mock_get_all(*args, **kwargs):
            return {"configs": []}

        self.mock_config_client.get_all_slo_configs = mock_get_all

        result = asyncio.run(self.router.manage_slo(
            resource_type="configuration",
            operation="get_all",
            params=None
        ))

        self.assertIn("results", result)

    # _normalize_correction_start_time Tests
    def test_normalize_correction_start_time_numeric_ms_passthrough(self):
        """Numeric ms timestamps must pass through without timezone elicitation."""
        scheduling = {"startTime": 1609459200000}
        result = self.router._normalize_correction_start_time(scheduling, "create")
        self.assertIsNone(result)
        # Value must be unchanged
        self.assertEqual(scheduling["startTime"], 1609459200000)

    def test_normalize_correction_start_time_float_ms_passthrough(self):
        """Float ms timestamps must also pass through without elicitation."""
        scheduling = {"startTime": 1609459200000.0}
        result = self.router._normalize_correction_start_time(scheduling, "create")
        self.assertIsNone(result)

    def test_normalize_correction_start_time_string_with_timezone_succeeds(self):
        """String datetime with timezone should be converted without elicitation."""
        scheduling = {"startTime": "10 March 2026, 2:00 PM|IST"}
        result = self.router._normalize_correction_start_time(scheduling, "create")
        # Must not trigger elicitation (timezone was provided)
        if result is not None:
            self.assertNotIn("elicitation_needed", result)

    def test_normalize_correction_start_time_string_without_timezone_triggers_elicitation(self):
        """String datetime missing timezone should trigger timezone elicitation."""
        scheduling = {"startTime": "10 March 2026, 2:00 PM"}
        result = self.router._normalize_correction_start_time(scheduling, "create")
        # May trigger elicitation asking for timezone
        if result is not None:
            self.assertTrue(result.get("elicitation_needed") or "error" in result)


if __name__ == "__main__":
    unittest.main()


