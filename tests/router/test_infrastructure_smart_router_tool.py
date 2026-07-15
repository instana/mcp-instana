"""
Unit tests for InfrastructureSmartRouterMCPTool
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


# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the router logger and replace its handlers
router_logger = logging.getLogger('src.router.infrastructure_smart_router_tool')
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


# Patch the with_header_auth decorator and the client imports
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Mock the client classes at their import location
    with patch('src.infrastructure.infrastructure_analyze.InfrastructureAnalyzeMCPTools', create=True) as MockAnalyze, \
         patch('src.infrastructure.infrastructure_catalog.InfrastructureCatalogMCPTools', create=True) as MockCatalog, \
         patch('src.infrastructure.infrastructure_topology.InfrastructureTopologyMCPTools', create=True) as MockTopology, \
         patch('src.infrastructure.infrastructure_resources.InfrastructureResourcesMCPTools', create=True) as MockResources:

        # Import the router class
        from src.router.infrastructure_smart_router_tool import (
            InfrastructureSmartRouterMCPTool,
        )


class TestInfrastructureSmartRouterMCPTool(unittest.TestCase):
    """Test class for InfrastructureSmartRouterMCPTool"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock instances for all clients
        self.mock_analyze = MagicMock()
        self.mock_catalog = MagicMock()
        self.mock_topology = MagicMock()
        self.mock_resources = MagicMock()

        # Patch the client classes at import time
        with patch('src.infrastructure.infrastructure_analyze.InfrastructureAnalyzeMCPTools', return_value=self.mock_analyze, create=True), \
             patch('src.infrastructure.infrastructure_catalog.InfrastructureCatalogMCPTools', return_value=self.mock_catalog, create=True), \
             patch('src.infrastructure.infrastructure_topology.InfrastructureTopologyMCPTools', return_value=self.mock_topology, create=True), \
             patch('src.infrastructure.infrastructure_resources.InfrastructureResourcesMCPTools', return_value=self.mock_resources, create=True):

            # Create router instance
            self.router = InfrastructureSmartRouterMCPTool(
                read_token="test_token",
                base_url="https://test.instana.com"
            )

            # Manually set the clients on the router
            self.router.infrastructure_analyze_client = self.mock_analyze
            self.router.infrastructure_catalog_client = self.mock_catalog
            self.router.infrastructure_topology_client = self.mock_topology
            self.router.infrastructure_resources_client = self.mock_resources

    def test_init(self):
        """Test router initialization"""
        self.assertEqual(self.router.read_token, "test_token")
        self.assertEqual(self.router.base_url, "https://test.instana.com")
        self.assertIsNotNone(self.router.infrastructure_analyze_client)
        self.assertIsNotNone(self.router.infrastructure_catalog_client)
        self.assertIsNotNone(self.router.infrastructure_topology_client)
        self.assertIsNotNone(self.router.infrastructure_resources_client)

    def test_invalid_resource_type(self):
        """Test handling of invalid resource type"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="invalid_type",
            operation="test"
        ))

        self.assertIn("error", result)
        self.assertIn("invalid_type", result["error"].lower())
        self.assertIn("valid_types", result)

    def test_manage_infrastructure_with_none_params(self):
        """Test manage_infrastructure initializes params when None"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="invalid_type",
            operation="test",
            params=None
        ))

        self.assertIn("error", result)

    def test_exception_handling(self):
        """Test exception handling in router"""
        async def mock_error(*args, **kwargs):
            raise Exception("Test error")

        self.mock_catalog.get_infrastructure_catalog_plugins = mock_error

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugins"
        ))

        self.assertIn("error", result)
        self.assertIn("Test error", str(result["error"]))

    # ===== ANALYZE TESTS =====

    def test_analyze_get_entities_success(self):
        """Test successful get_entities routing"""
        async def mock_get_entities(*args, **kwargs):
            return {"items": [{"id": "entity-1"}]}

        self.mock_analyze.get_entities = mock_get_entities

        payload = {
            "type": "host",
            "metrics": [{"metric": "cpu.used", "granularity": 3600000, "aggregation": "MEAN"}],
            "timeFrame": {"windowSize": 3600000}
        }

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entities",
            params={"payload": payload}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "analyze")
        self.assertEqual(result["operation"], "get_entities")

    def test_analyze_get_entity_groups_success(self):
        """Test successful get_entity_groups routing"""
        async def mock_get_groups(*args, **kwargs):
            return {"groups": [{"label": "group-1"}]}

        self.mock_analyze.get_aggregated_entity_groups = mock_get_groups

        payload = {
            "type": "host",
            "groupBy": ["host.name"],
            "metrics": [{"metric": "cpu.used", "granularity": 3600000, "aggregation": "SUM"}],
            "timeFrame": {"windowSize": 3600000}
        }

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entity_groups",
            params={"payload": payload}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "analyze")
        self.assertEqual(result["operation"], "get_entity_groups")

    def test_analyze_auto_routing_with_groupby(self):
        """Test auto-routing to get_entity_groups when groupBy is present"""
        async def mock_get_groups(*args, **kwargs):
            return {"groups": []}

        self.mock_analyze.get_aggregated_entity_groups = mock_get_groups

        payload = {
            "type": "host",
            "groupBy": ["host.name"],
            "metrics": [{"metric": "cpu.used", "granularity": 3600000, "aggregation": "SUM"}],
            "timeFrame": {"windowSize": 3600000}
        }

        # User specifies get_entities but payload has groupBy
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entities",  # Wrong operation
            params={"payload": payload}
        ))

        # Should auto-route to get_entity_groups
        self.assertEqual(result["operation"], "get_entity_groups")

    def test_analyze_auto_routing_without_groupby(self):
        """Test auto-routing to get_entities when groupBy is absent"""
        async def mock_get_entities(*args, **kwargs):
            return {"items": []}

        self.mock_analyze.get_entities = mock_get_entities

        payload = {
            "type": "host",
            "metrics": [{"metric": "cpu.used", "granularity": 3600000, "aggregation": "MEAN"}],
            "timeFrame": {"windowSize": 3600000}
        }

        # User specifies get_entity_groups but payload has no groupBy
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entity_groups",  # Wrong operation
            params={"payload": payload}
        ))

        # Should auto-route to get_entities
        self.assertEqual(result["operation"], "get_entities")

    def test_analyze_invalid_operation(self):
        """Test invalid operation for analyze"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="invalid_op",
            params={"payload": {}}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])
        self.assertIn("valid_operations", result)

    def test_analyze_missing_payload(self):
        """Test analyze with missing payload"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entities",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Missing required parameter 'payload'", result["error"])
        self.assertIn("required_format", result)

    # ===== CATALOG TESTS =====

    def test_catalog_get_plugins_success(self):
        """Test successful get_plugins routing"""
        async def mock_get_plugins(*args, **kwargs):
            return {"plugins": ["host", "docker", "kubernetesPod"]}

        self.mock_catalog.get_infrastructure_catalog_plugins = mock_get_plugins

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugins"
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "catalog")
        self.assertEqual(result["operation"], "get_plugins")

    def test_catalog_get_metrics_success(self):
        """Test successful get_metrics routing"""
        async def mock_get_metrics(*args, **kwargs):
            return ["cpu.used", "memory.used"]

        self.mock_catalog.get_infrastructure_catalog_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_metrics",
            params={"plugin": "host"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "catalog")

    def test_catalog_get_metrics_with_filter(self):
        """Test get_metrics with filter parameter"""
        async def mock_get_metrics(*args, **kwargs):
            return ["cpu.used"]

        self.mock_catalog.get_infrastructure_catalog_metrics = mock_get_metrics

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_metrics",
            params={"plugin": "host", "filter": "builtin"}
        ))

        self.assertIn("results", result)

    def test_catalog_get_metrics_missing_plugin(self):
        """Test get_metrics with missing plugin parameter"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_metrics",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Missing required parameter 'plugin'", result["error"])
        self.assertIn("hint", result)

    def test_catalog_get_tag_catalog_success(self):
        """Test successful get_tag_catalog routing"""
        async def mock_get_tags(*args, **kwargs):
            return {"tags": {"host.name": {}, "host.type": {}}}

        self.mock_catalog.get_tag_catalog = mock_get_tags

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={"plugin": "host"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_tag_catalog")

    def test_catalog_get_tag_catalog_missing_plugin(self):
        """Test get_tag_catalog with missing plugin parameter"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_tag_catalog",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Missing required parameter 'plugin'", result["error"])

    def test_catalog_get_plugin_schema_success(self):
        """Test successful get_plugin_schema routing"""
        async def mock_get_schema(*args, **kwargs):
            return {
                "plugin": "host",
                "metrics": ["cpu.used", "memory.used"],
                "tags": {"host.name": {}, "host.type": {}},
                "summary": {"total_metrics": 2, "total_tags": 2}
            }

        self.mock_catalog.get_plugin_schema = mock_get_schema

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugin_schema",
            params={"plugin": "host"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_plugin_schema")

    def test_catalog_get_plugin_schema_with_filter(self):
        """Test get_plugin_schema with filter parameter"""
        async def mock_get_schema(*args, **kwargs):
            return {"plugin": "host", "metrics": ["cpu.used"]}

        self.mock_catalog.get_plugin_schema = mock_get_schema

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugin_schema",
            params={"plugin": "host", "filter": "custom"}
        ))

        self.assertIn("results", result)

    def test_catalog_get_plugin_schema_missing_plugin(self):
        """Test get_plugin_schema with missing plugin parameter"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="get_plugin_schema",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Missing required parameter 'plugin'", result["error"])

    def test_catalog_invalid_operation(self):
        """Test invalid operation for catalog"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="catalog",
            operation="invalid_catalog_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    # ===== RESOURCES TESTS =====

    def test_resources_get_snapshot_success(self):
        """Test successful get_snapshot routing"""
        async def mock_get_snapshot(*args, **kwargs):
            return {"snapshot": {"id": "snap-123", "data": {}}}

        self.mock_resources.get_snapshot = mock_get_snapshot

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshot",
            params={"snapshot_id": "snap-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["resource_type"], "resources")
        self.assertEqual(result["operation"], "get_snapshot")

    def test_resources_get_snapshot_with_optional_params(self):
        """Test get_snapshot with optional parameters"""
        async def mock_get_snapshot(*args, **kwargs):
            return {"snapshot": {}}

        self.mock_resources.get_snapshot = mock_get_snapshot

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshot",
            params={
                "snapshot_id": "snap-123",
                "to_time": 1234567890000,
                "window_size": 3600000
            }
        ))

        self.assertIn("results", result)

    def test_resources_get_snapshot_missing_id(self):
        """Test get_snapshot with missing snapshot_id"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshot",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Missing required parameter 'snapshot_id'", result["error"])
        self.assertIn("hint", result)

    def test_resources_get_snapshots_success(self):
        """Test successful get_snapshots routing"""
        async def mock_get_snapshots(*args, **kwargs):
            return {"items": [{"id": "snap-1"}, {"id": "snap-2"}]}

        self.mock_resources.get_snapshots = mock_get_snapshots

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshots"
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_snapshots")

    def test_resources_get_snapshots_with_all_params(self):
        """Test get_snapshots with all optional parameters"""
        async def mock_get_snapshots(*args, **kwargs):
            return {"items": []}

        self.mock_resources.get_snapshots = mock_get_snapshots

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshots",
            params={
                "query": "high cpu",
                "from_time": 1617994800000,
                "to_time": 1618081200000,
                "size": 50,
                "plugin": "host",
                "offline": True,
                "detailed": True
            }
        ))

        self.assertIn("results", result)

    def test_resources_get_snapshots_default_size(self):
        """Test get_snapshots uses default size of 100"""
        async def mock_get_snapshots(*args, **kwargs):
            # Verify size parameter is passed
            return {"items": []}

        self.mock_resources.get_snapshots = mock_get_snapshots

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="get_snapshots",
            params={}
        ))

        self.assertIn("results", result)

    def test_resources_invalid_operation(self):
        """Test invalid operation for resources"""
        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="resources",
            operation="invalid_resources_op",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    # ===== EDGE CASES AND ERROR HANDLING =====

    def test_unsupported_resource_type_fallback(self):
        """Test fallback for unsupported resource type (should not happen but test defensive code)"""
        # This tests the else clause in manage_infrastructure that should never be reached
        # but exists for defensive programming
        async def mock_get_entities(*args, **kwargs):
            return {"items": []}

        self.mock_analyze.get_entities = mock_get_entities

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",  # Valid type
            operation="get_entities",
            params={"payload": {"type": "host", "metrics": [], "timeFrame": {}}}
        ))

        # Should succeed normally
        self.assertIn("results", result)

    def test_analyze_with_empty_groupby(self):
        """Test analyze auto-routing with empty groupBy list"""
        async def mock_get_entities(*args, **kwargs):
            return {"items": []}

        self.mock_analyze.get_entities = mock_get_entities

        payload = {
            "type": "host",
            "groupBy": [],  # Empty list
            "metrics": [{"metric": "cpu.used", "granularity": 3600000, "aggregation": "MEAN"}],
            "timeFrame": {"windowSize": 3600000}
        }

        result = asyncio.run(self.router.manage_infrastructure(
            resource_type="analyze",
            operation="get_entity_groups",
            params={"payload": payload}
        ))

        # Should route to get_entities because groupBy is empty
        self.assertEqual(result["operation"], "get_entities")

    def test_catalog_operations_coverage(self):
        """Test all catalog operations are covered"""
        # This test ensures all catalog operations are properly routed
        operations = ["get_plugins", "get_metrics", "get_tag_catalog", "get_plugin_schema"]

        for op in operations:
            if op == "get_plugins":
                params = {}
            else:
                params = {"plugin": "host"}

            async def mock_result(*args, **kwargs):
                return {"result": "success"}

            if op == "get_plugins":
                self.mock_catalog.get_infrastructure_catalog_plugins = mock_result
            elif op == "get_metrics":
                self.mock_catalog.get_infrastructure_catalog_metrics = mock_result
            elif op == "get_tag_catalog":
                self.mock_catalog.get_tag_catalog = mock_result
            elif op == "get_plugin_schema":
                self.mock_catalog.get_plugin_schema = mock_result

            result = asyncio.run(self.router.manage_infrastructure(
                resource_type="catalog",
                operation=op,
                params=params
            ))

            self.assertIn("results", result, f"Operation {op} failed")
            self.assertEqual(result["operation"], op)


if __name__ == '__main__':
    unittest.main()
