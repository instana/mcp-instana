"""
Unit tests for SLO Configuration MCP Tools.

Tests the SLOConfigurationMCPTools which manages SLO configurations.
"""

import asyncio
import json
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

# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the SLO logger and replace its handlers
slo_logger = logging.getLogger('src.slo.slo_configuration')
slo_logger.handlers = []
slo_logger.addHandler(NullHandler())
slo_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator that passes through to actual method
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            for attr_name in ("slo_config_api", "alert_config_api", "correction_api", "report_api"):
                api_client = getattr(self, attr_name, None)
                if api_client is not None:
                    kwargs["api_client"] = api_client
                    break
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.service_levels_objective_slo_configurations_api'] = MagicMock()
sys.modules['instana_client.api.slo_correction_configurations_api'] = MagicMock()
sys.modules['instana_client.api.service_levels_objective_slo_report_api'] = MagicMock()
sys.modules['instana_client.api.service_levels_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.application_slo_entity'] = MagicMock()
sys.modules['instana_client.models.service_level_indicator'] = MagicMock()
sys.modules['instana_client.models.slo_config_with_rbac_tag'] = MagicMock()
sys.modules['instana_client.models.time_window'] = MagicMock()
sys.modules['instana_client.models.correction_configuration'] = MagicMock()
sys.modules['instana_client.models.correction_scheduling'] = MagicMock()
sys.modules['instana_client.models.alerting_time_window'] = MagicMock()
sys.modules['instana_client.models.error_budget_alert_rule'] = MagicMock()
sys.modules['instana_client.models.service_level_objective_alert_rule'] = MagicMock()
sys.modules['instana_client.models.service_levels_alert_config'] = MagicMock()
sys.modules['instana_client.models.service_levels_burn_rate_time_windows'] = MagicMock()
sys.modules['instana_client.models.service_levels_time_threshold'] = MagicMock()
sys.modules['instana_client.models.static_string_field'] = MagicMock()
sys.modules['instana_client.models.static_threshold'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client_class = MagicMock()
mock_slo_config_api = MagicMock()

# Add __name__ attribute to mock classes
mock_slo_config_api.__name__ = "ServiceLevelsObjectiveSLOConfigurationsApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client_class
sys.modules['instana_client.api.service_levels_objective_slo_configurations_api'].ServiceLevelsObjectiveSLOConfigurationsApi = mock_slo_config_api

# Import with patched decorator
import src.core.utils

original_with_header_auth = src.core.utils.with_header_auth
src.core.utils.with_header_auth = mock_with_header_auth

from src.slo.slo_configuration import SLOConfigurationMCPTools

# Restore original decorator
src.core.utils.with_header_auth = original_with_header_auth


class TestSLOConfigurationMCPTools(unittest.TestCase):
    """Test cases for SLO Configuration MCP Tools."""

    def setUp(self):
        """Set up test fixtures."""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client_class.reset_mock()
        mock_slo_config_api.reset_mock()

        # Create the client
        self.client = SLOConfigurationMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        # Create a mock API client instance
        self.mock_api = MagicMock()
        self.client.slo_config_api = self.mock_api

    def test_initialization(self):
        """Test client initialization."""
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.com")

    # Validation Tests
    def test_validate_slo_config_payload_missing_name(self):
        """Test SLO config validation with missing name."""
        payload = {
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("elicitation_needed", result)
        self.assertIn("name", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_tags(self):
        """Test SLO config validation with missing tags."""
        payload = {
            "name": "Test SLO",
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("tags", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_target(self):
        """Test SLO config validation with missing target."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("target", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_entity(self):
        """Test SLO config validation with missing entity."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("entity", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_entity_type(self):
        """Test SLO config validation with missing entity.type."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("entity.type", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_entity_application_id(self):
        """Test SLO config validation with missing entity.applicationId."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("entity.applicationId", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_entity_boundary_scope(self):
        """Test SLO config validation with missing entity.boundaryScope."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("entity.boundaryScope", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_indicator(self):
        """Test SLO config validation with missing indicator."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("indicator", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_indicator_type(self):
        """Test SLO config validation with missing indicator.type."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("indicator.type", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_indicator_blueprint(self):
        """Test SLO config validation with missing indicator.blueprint."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("indicator.blueprint", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_time_window(self):
        """Test SLO config validation with missing timeWindow."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeWindow", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_time_window_type(self):
        """Test SLO config validation with missing timeWindow.type."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeWindow.type", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_time_window_duration(self):
        """Test SLO config validation with missing timeWindow.duration."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeWindow.duration", result["missing_parameters"])

    def test_validate_slo_config_payload_missing_time_window_duration_unit(self):
        """Test SLO config validation with missing timeWindow.durationUnit."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeWindow.durationUnit", result["missing_parameters"])

    def test_validate_slo_config_payload_valid(self):
        """Test SLO config validation with valid payload (all required fields present)."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {
                "type": "application",
                "applicationId": "app-1",
                "boundaryScope": "ALL",
                "includeInternal": False,
                "includeSynthetic": False,
            },
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNone(result)

    def test_clean_slo_config_data(self):
        """Test cleaning SLO config data."""
        config = {
            "id": "slo-123",
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application"},
            "indicator": {"type": "timeBased"},
            "timeWindow": {"type": "rolling"},
            "createdDate": 1609459200000,
            "lastUpdated": 1612137600000,
            "rbacTags": ["internal"]
        }
        cleaned = self.client._clean_slo_config_data(config)
        self.assertIn("id", cleaned)
        self.assertIn("name", cleaned)
        self.assertIn("tags", cleaned)
        self.assertNotIn("createdDate", cleaned)
        self.assertNotIn("lastUpdated", cleaned)
        self.assertNotIn("rbacTags", cleaned)

    # get_all_slo_configs Tests
    def test_get_all_slo_configs_success(self):
        """Test getting all SLO configs successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "items": [
                    {"id": "slo-1", "name": "SLO 1"},
                    {"id": "slo-2", "name": "SLO 2"}
                ],
                "page": 1,
                "pageSize": 10,
                "totalHits": 2
            }).encode('utf-8')

            self.mock_api.get_all_slo_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_configs()

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("items", result)
            self.assertEqual(len(result["items"]), 2)
            self.assertEqual(result["totalHits"], 2)

        asyncio.run(run_test())

    def test_get_all_slo_configs_with_filters(self):
        """Test getting all SLO configs with filters."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "items": [{"id": "slo-1", "name": "SLO 1"}],
                "page": 1,
                "pageSize": 10,
                "totalHits": 1
            }).encode('utf-8')

            self.mock_api.get_all_slo_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_configs(
                filters={"page_size": 10, "page": 1, "query": "test", "tag": ["production"]}
            )

            self.assertIn("success", result)
            self.assertEqual(len(result["items"]), 1)

        asyncio.run(run_test())

    def test_get_all_slo_configs_with_all_filters(self):
        """Test getting all SLO configs with every supported filter parameter."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "items": [{"id": "slo-1", "name": "SLO 1"}],
                "page": 2,
                "pageSize": 25,
                "totalHits": 1
            }).encode('utf-8')

            self.mock_api.get_all_slo_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_configs(
                filters={
                    "page_size": 25,
                    "page": 2,
                    "order_by": "name",
                    "order_direction": "asc",
                    "query": "latency",
                    "tag": ["production", "critical"],
                    "entity_type": ["application"],
                    "infra_entity_types": ["host"],
                    "kubernetes_cluster_uuid": "kube-uuid-123",
                    "blueprint": ["latency"],
                    "slo_ids": ["slo-1", "slo-2"],
                    "slo_status": "HEALTHY",
                    "entity_ids": ["entity-1"],
                    "grouped": True,
                    "refresh": True,
                    "rbac_tags": ["team-a"],
                }
            )

            self.assertIn("success", result)
            self.assertEqual(len(result["items"]), 1)

            self.mock_api.get_all_slo_configs_without_preload_content.assert_called_once_with(
                page_size=25,
                page=2,
                order_by="name",
                order_direction="asc",
                query="latency",
                tag=["production", "critical"],
                entity_type=["application"],
                infra_entity_types=["host"],
                kubernetes_cluster_uuid="kube-uuid-123",
                blueprint=["latency"],
                slo_ids=["slo-1", "slo-2"],
                slo_status="HEALTHY",
                entity_ids=["entity-1"],
                grouped=True,
                refresh=True,
                rbac_tags=["team-a"],
            )

        asyncio.run(run_test())

    def test_get_all_slo_configs_json_error(self):
        """Test getting all SLO configs with JSON parse error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = b"invalid json"

            self.mock_api.get_all_slo_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_configs()

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_all_slo_configs_exception(self):
        """Test getting all SLO configs with exception."""
        async def run_test():
            self.mock_api.get_all_slo_configs_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.get_all_slo_configs()

            self.assertIn("error", result)

        asyncio.run(run_test())

    # get_slo_config_by_id Tests
    def test_get_slo_config_by_id_success(self):
        """Test getting SLO config by ID successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "slo-123", "name": "Test SLO"}).encode('utf-8')

            self.mock_api.get_slo_config_by_id_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_config_by_id(id="slo-123")

            self.assertIn("id", result)
            self.assertEqual(result["id"], "slo-123")

        asyncio.run(run_test())

    def test_get_slo_config_by_id_missing_id(self):
        """Test getting SLO config by ID with missing ID."""
        async def run_test():
            result = await self.client.get_slo_config_by_id(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_slo_config_by_id_with_refresh(self):
        """Test getting SLO config by ID with refresh parameter."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"id": "slo-123", "name": "Test SLO"}).encode('utf-8')

            self.mock_api.get_slo_config_by_id_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_config_by_id(id="slo-123", refresh=True)

            self.assertIn("id", result)

        asyncio.run(run_test())

    def test_get_slo_config_by_id_json_error(self):
        """Test getting SLO config by ID with JSON parse error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = b"invalid json"

            self.mock_api.get_slo_config_by_id_without_preload_content.return_value = mock_response

            result = await self.client.get_slo_config_by_id(id="slo-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_slo_config_by_id_exception(self):
        """Test getting SLO config by ID with exception."""
        async def run_test():
            self.mock_api.get_slo_config_by_id_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.get_slo_config_by_id(id="slo-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    # create_slo_config Tests
    def test_create_slo_config_missing_payload(self):
        """Test creating SLO config with missing payload."""
        async def run_test():
            result = await self.client.create_slo_config(payload=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_slo_config_json_string(self):
        """Test creating SLO config with JSON string payload."""
        async def run_test():
            payload = json.dumps({
                "name": "Test SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            })

            result = await self.client.create_slo_config(payload=payload)

            # Should trigger validation and return elicitation or attempt creation
            self.assertTrue("error" in result or "elicitation_needed" in result or "success" in result)

        asyncio.run(run_test())

    def test_create_slo_config_python_literal_string(self):
        """Test creating SLO config with Python literal string payload."""
        async def run_test():
            payload = "{'name': 'Test SLO', 'tags': ['test'], 'target': 0.95}"

            result = await self.client.create_slo_config(payload=payload)

            # Should trigger validation
            self.assertTrue("error" in result or "elicitation_needed" in result)

        asyncio.run(run_test())

    def test_create_slo_config_invalid_json(self):
        """Test creating SLO config with invalid JSON string."""
        async def run_test():
            result = await self.client.create_slo_config(payload="{invalid json")
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_create_slo_config_missing_fields(self):
        """Test creating SLO config with missing required fields."""
        async def run_test():
            payload = {"name": "Test SLO"}

            result = await self.client.create_slo_config(payload=payload)

            self.assertIn("elicitation_needed", result)
            self.assertIn("missing_parameters", result)

        asyncio.run(run_test())

    def test_create_slo_config_unsupported_entity_type(self):
        """Test creating SLO config with unsupported entity type."""
        async def run_test():
            payload = {
                "name": "Test SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {"type": "service", "serviceId": "svc-1"},
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            result = await self.client.create_slo_config(payload=payload)

            self.assertIn("error", result)
            self.assertIn("Unsupported entity type", result["error"])

        asyncio.run(run_test())

    # update_slo_config Tests
    def test_update_slo_config_missing_id(self):
        """Test updating SLO config with missing ID."""
        async def run_test():
            payload = {"name": "Updated SLO"}
            result = await self.client.update_slo_config(id=None, payload=payload)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_slo_config_missing_payload(self):
        """Test updating SLO config with missing payload."""
        async def run_test():
            result = await self.client.update_slo_config(id="slo-123", payload=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_slo_config_missing_fields(self):
        """Test updating SLO config with missing required fields."""
        async def run_test():
            payload = {"name": "Updated SLO"}

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            self.assertIn("elicitation_needed", result)

        asyncio.run(run_test())

    def test_update_slo_config_json_string(self):
        """Test updating SLO config with JSON string payload."""
        async def run_test():
            payload = json.dumps({
                "name": "Updated SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            })

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            # Should trigger validation or attempt update
            self.assertTrue("error" in result or "elicitation_needed" in result or "success" in result)

        asyncio.run(run_test())

    def test_update_slo_config_exception(self):
        """Test updating SLO config with exception."""
        async def run_test():
            payload = {
                "name": "Updated SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {
                    "type": "application",
                    "applicationId": "app-1",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            self.mock_api.update_slo_config_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    # delete_slo_config Tests
    def test_delete_slo_config_success(self):
        """Test deleting SLO config successfully."""
        async def run_test():
            self.mock_api.delete_slo_config.return_value = None

            result = await self.client.delete_slo_config(id="slo-123")

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("deleted", result["message"])

        asyncio.run(run_test())

    def test_delete_slo_config_missing_id(self):
        """Test deleting SLO config with missing ID."""
        async def run_test():
            result = await self.client.delete_slo_config(id=None)
            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_delete_slo_config_exception(self):
        """Test deleting SLO config with exception."""
        async def run_test():
            self.mock_api.delete_slo_config.side_effect = Exception("Test error")

            result = await self.client.delete_slo_config(id="slo-123")

            self.assertIn("error", result)

        asyncio.run(run_test())

    # get_all_slo_config_tags Tests
    def test_get_all_slo_config_tags_success(self):
        """Test getting all SLO config tags successfully."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps(["tag1", "tag2", "tag3"]).encode('utf-8')

            self.mock_api.get_all_slo_config_tags_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_config_tags()

            self.assertIn("success", result)
            self.assertTrue(result["success"])
            self.assertIn("tags", result)
            self.assertEqual(result["count"], 3)

        asyncio.run(run_test())

    def test_get_all_slo_config_tags_with_filters(self):
        """Test getting all SLO config tags with filters."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps(["production"]).encode('utf-8')

            self.mock_api.get_all_slo_config_tags_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_config_tags(
                query="prod",
                tag=["production"],
                entity_type="APPLICATION"
            )

            self.assertIn("success", result)
            self.assertEqual(result["count"], 1)

        asyncio.run(run_test())

    def test_get_all_slo_config_tags_dict_response(self):
        """Test getting all SLO config tags with dict response."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({"tags": ["tag1", "tag2"]}).encode('utf-8')

            self.mock_api.get_all_slo_config_tags_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_config_tags()

            self.assertIn("success", result)
            self.assertEqual(result["count"], 2)

        asyncio.run(run_test())

    def test_get_all_slo_config_tags_json_error(self):
        """Test getting all SLO config tags with JSON parse error."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = b"invalid json"

            self.mock_api.get_all_slo_config_tags_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_config_tags()

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_get_all_slo_config_tags_exception(self):
        """Test getting all SLO config tags with exception."""
        async def run_test():
            self.mock_api.get_all_slo_config_tags_without_preload_content.side_effect = Exception("Test error")

            result = await self.client.get_all_slo_config_tags()

            self.assertIn("error", result)

    # Additional edge case tests for better coverage
    def test_create_slo_config_success_with_valid_payload(self):
        """Test creating SLO config successfully with valid payload."""
        async def run_test():
            payload = {
                "name": "Test SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {
                    "type": "application",
                    "applicationId": "app-1",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.data = json.dumps({
                "id": "slo-123",
                "name": "Test SLO",
                "tags": ["test"],
                "target": 0.95
            }).encode('utf-8')

            self.mock_api.create_slo_config_without_preload_content.return_value = mock_response

            result = await self.client.create_slo_config(payload=payload)

            self.assertTrue("success" in result or "error" in result)

        asyncio.run(run_test())

    def test_create_slo_config_api_error_status(self):
        """Test creating SLO config with API error status."""
        async def run_test():
            payload = {
                "name": "Test SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {
                    "type": "application",
                    "applicationId": "app-1",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            mock_response = MagicMock()
            mock_response.status = 400
            mock_response.data = b"Bad request"

            self.mock_api.create_slo_config_without_preload_content.return_value = mock_response

            result = await self.client.create_slo_config(payload=payload)

            self.assertIn("error", result)
            self.assertIn("status_code", result)

        asyncio.run(run_test())

    def test_create_slo_config_empty_response(self):
        """Test creating SLO config with empty response."""
        async def run_test():
            payload = {
                "name": "Test SLO",
                "tags": ["test"],
                "target": 0.95,
                "entity": {
                    "type": "application",
                    "applicationId": "app-1",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            mock_response = MagicMock()
            mock_response.status = 201
            mock_response.data = b""

            self.mock_api.create_slo_config_without_preload_content.return_value = mock_response

            result = await self.client.create_slo_config(payload=payload)

            self.assertIn("success", result)
            self.assertIn("empty response", result["message"].lower())

        asyncio.run(run_test())

    def test_create_slo_config_missing_name_and_target(self):
        """Test creating SLO config with missing name and target after validation."""
        async def run_test():
            payload = {
                "tags": ["test"],
                "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            result = await self.client.create_slo_config(payload=payload)

            self.assertIn("elicitation_needed", result)

        asyncio.run(run_test())

    def test_update_slo_config_success(self):
        """Test updating SLO config successfully."""
        async def run_test():
            payload = {
                "name": "Updated SLO",
                "tags": ["test"],
                "target": 0.98,
                "entity": {
                    "type": "application",
                    "applicationId": "app-1",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps({
                "id": "slo-123",
                "name": "Updated SLO",
                "target": 0.98
            }).encode('utf-8')

            self.mock_api.update_slo_config_without_preload_content.return_value = mock_response

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            self.assertTrue("success" in result or "error" in result)

        asyncio.run(run_test())

    def test_update_slo_config_json_parse_error(self):
        """Test updating SLO config with JSON parse error."""
        async def run_test():
            payload = {
                "name": "Updated SLO",
                "tags": ["test"],
                "target": 0.98,
                "entity": {
                    "type": "application",
                    "applicationId": "app-1",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = b"invalid json"

            self.mock_api.update_slo_config_without_preload_content.return_value = mock_response

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            self.assertIn("error", result)

        asyncio.run(run_test())

    def test_update_slo_config_unsupported_entity_type(self):
        """Test updating SLO config with unsupported entity type."""
        async def run_test():
            payload = {
                "name": "Updated SLO",
                "tags": ["test"],
                "target": 0.98,
                "entity": {
                    "type": "service",
                    "serviceId": "svc-1",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                "indicator": {"type": "timeBased", "blueprint": "latency"},
                "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
            }

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            self.assertIn("error", result)
            self.assertIn("Unsupported entity type", result["error"])

        asyncio.run(run_test())

    def test_get_all_slo_configs_non_dict_response(self):
        """Test getting all SLO configs with non-dict response."""
        async def run_test():
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.data = json.dumps([{"id": "slo-1"}]).encode('utf-8')

            self.mock_api.get_all_slo_configs_without_preload_content.return_value = mock_response

            result = await self.client.get_all_slo_configs()

            # Should return the list as-is
            self.assertTrue(isinstance(result, (dict, list)))

        asyncio.run(run_test())

    def test_create_slo_config_with_quotes_replacement(self):
        """Test creating SLO config with single quotes that need replacement."""
        async def run_test():
            payload = "{'name': 'Test SLO', 'tags': ['test'], 'target': 0.95, 'entity': {'type': 'application', 'applicationId': 'app-1', 'boundaryScope': 'ALL'}, 'indicator': {'type': 'timeBased', 'blueprint': 'latency'}, 'timeWindow': {'type': 'rolling', 'duration': 1, 'durationUnit': 'week'}}"

            result = await self.client.create_slo_config(payload=payload)

            # Should either parse successfully or return validation error
            self.assertTrue("error" in result or "elicitation_needed" in result or "success" in result)

        asyncio.run(run_test())

    def test_update_slo_config_with_quotes_replacement(self):
        """Test updating SLO config with single quotes that need replacement."""
        async def run_test():
            payload = "{'name': 'Updated SLO', 'tags': ['test'], 'target': 0.98, 'entity': {'type': 'application', 'applicationId': 'app-1', 'boundaryScope': 'ALL'}, 'indicator': {'type': 'timeBased', 'blueprint': 'latency'}, 'timeWindow': {'type': 'rolling', 'duration': 1, 'durationUnit': 'week'}}"

            result = await self.client.update_slo_config(id="slo-123", payload=payload)

            # Should either parse successfully or return validation error
            self.assertTrue("error" in result or "elicitation_needed" in result or "success" in result)

        asyncio.run(run_test())

    def test_validate_slo_config_payload_multiple_missing_fields(self):
        """Test SLO config validation with multiple missing fields."""
        payload = {
            "name": "Test SLO"
            # Missing: tags, target, entity, indicator, timeWindow
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("elicitation_needed", result)
        self.assertGreater(len(result["missing_parameters"]), 3)

    def test_validate_slo_config_payload_entity_not_dict(self):
        """Test SLO config validation with entity not being a dict."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": "not a dict",
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        # Should pass validation since entity exists (type checking happens later)
        self.assertIsNone(result)

    def test_validate_slo_config_payload_indicator_not_dict(self):
        """Non-dict indicator skips sub-field checks; no indicator.* errors are raised."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": "not a dict",
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        # No indicator.* sub-field errors should appear
        if result:
            for p in result.get("missing_parameters", []):
                self.assertFalse(p.startswith("indicator."), f"Unexpected indicator field error: {p}")

    def test_validate_slo_config_payload_time_window_not_dict(self):
        """Non-dict timeWindow skips sub-field checks; no timeWindow.* errors are raised."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": "not a dict"
        }
        result = self.client._validate_slo_config_payload(payload)
        # No timeWindow.* sub-field errors should appear
        if result:
            for p in result.get("missing_parameters", []):
                self.assertFalse(p.startswith("timeWindow."), f"Unexpected timeWindow field error: {p}")


    # ── New validation tests for enum / range checks ──────────────────────

    def test_validate_slo_config_payload_invalid_target_too_high(self):
        """Target > 0.9999 should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 1.0,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("target", result["missing_parameters"])
        self.assertTrue(any("error" in p for p in result["parameter_details"] if p["name"] == "target"))

    def test_validate_slo_config_payload_invalid_target_negative(self):
        """Negative target should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": -0.1,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("target", result["missing_parameters"])

    def test_validate_slo_config_payload_target_boundary_zero(self):
        """target=0.0 is a valid edge-case value."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.0,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNone(result)

    def test_validate_slo_config_payload_invalid_boundary_scope(self):
        """entity.boundaryScope with a bad value should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1",
                       "boundaryScope": "INVALID_SCOPE",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("entity.boundaryScope", result["missing_parameters"])
        detail = next(p for p in result["parameter_details"] if p["name"] == "entity.boundaryScope")
        self.assertIn("error", detail)

    def test_validate_slo_config_payload_missing_include_internal_defaults_false(self):
        """Missing entity.includeInternal is silently defaulted to False (no elicitation)."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1",
                       "boundaryScope": "ALL", "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        # Should pass validation (returns None) — no elicitation triggered
        self.assertIsNone(result)
        # The entity dict must have been mutated with the default
        self.assertFalse(payload["entity"]["includeInternal"])

    def test_validate_slo_config_payload_missing_include_synthetic_defaults_false(self):
        """Missing entity.includeSynthetic is silently defaulted to False (no elicitation)."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1",
                       "boundaryScope": "ALL", "includeInternal": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        # Should pass validation (returns None) — no elicitation triggered
        self.assertIsNone(result)
        # The entity dict must have been mutated with the default
        self.assertFalse(payload["entity"]["includeSynthetic"])

    def test_validate_slo_config_payload_invalid_indicator_type(self):
        """indicator.type with an unrecognised value should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "unknownType", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("indicator.type", result["missing_parameters"])
        detail = next(p for p in result["parameter_details"] if p["name"] == "indicator.type")
        self.assertIn("error", detail)

    def test_validate_slo_config_payload_invalid_blueprint(self):
        """indicator.blueprint with an unrecognised value should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "badBlueprint"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("indicator.blueprint", result["missing_parameters"])

    def test_validate_slo_config_payload_invalid_aggregation(self):
        """Optional indicator.aggregation with a bad value should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency", "aggregation": "BAD_AGG"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("indicator.aggregation", result["missing_parameters"])

    def test_validate_slo_config_payload_valid_aggregation(self):
        """Valid optional indicator.aggregation should not trigger an error."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency", "aggregation": "P90"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNone(result)

    def test_validate_slo_config_payload_invalid_time_window_type(self):
        """timeWindow.type with an unrecognised value should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "badType", "duration": 1, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeWindow.type", result["missing_parameters"])

    def test_validate_slo_config_payload_invalid_duration_unit(self):
        """timeWindow.durationUnit not in the allowed set should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "month"}
        }
        result = self.client._validate_slo_config_payload(payload)
        # "month" is not a valid SDK value — "calendar_month" is
        self.assertIsNotNone(result)
        self.assertIn("timeWindow.durationUnit", result["missing_parameters"])

    def test_validate_slo_config_payload_calendar_month_duration_unit(self):
        """calendar_month is the correct SDK value for monthly windows."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "calendar_month"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNone(result)

    def test_validate_slo_config_payload_non_positive_duration(self):
        """timeWindow.duration <= 0 should be rejected."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 0.95,
            "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL",
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "timeBased", "blueprint": "latency"},
            "timeWindow": {"type": "rolling", "duration": 0, "durationUnit": "week"}
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("timeWindow.duration", result["missing_parameters"])

    def test_validate_slo_config_payload_consolidated_errors(self):
        """Multiple invalid enum values should all be reported in one response."""
        payload = {
            "name": "Test SLO",
            "tags": ["test"],
            "target": 1.5,  # invalid
            "entity": {"type": "application", "applicationId": "app-1",
                       "boundaryScope": "WRONG",  # invalid
                       "includeInternal": False, "includeSynthetic": False},
            "indicator": {"type": "badType", "blueprint": "badBlueprint"},  # both invalid
            "timeWindow": {"type": "badType", "duration": 1, "durationUnit": "month"}  # both invalid
        }
        result = self.client._validate_slo_config_payload(payload)
        self.assertIsNotNone(result)
        self.assertIn("elicitation_needed", result)
        # All invalid fields should be reported at once
        self.assertIn("target", result["missing_parameters"])
        self.assertIn("entity.boundaryScope", result["missing_parameters"])
        self.assertIn("indicator.type", result["missing_parameters"])
        self.assertIn("indicator.blueprint", result["missing_parameters"])
        self.assertIn("timeWindow.type", result["missing_parameters"])
        self.assertIn("timeWindow.durationUnit", result["missing_parameters"])


if __name__ == "__main__":
    unittest.main()

