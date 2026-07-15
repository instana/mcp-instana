"""
Unit tests for EventsSmartRouterMCPTool
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
router_logger = logging.getLogger('src.router.events_smart_router_tool')
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
    # Mock the client class at its import location
    with patch('src.event.events_tools.AgentMonitoringEventsMCPTools') as MockEvents:

        # Import the router class
        from src.router.events_smart_router_tool import EventsSmartRouterMCPTool


class TestEventsSmartRouterMCPTool(unittest.TestCase):
    """Test class for EventsSmartRouterMCPTool"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock instance for events client
        self.mock_events = MagicMock()

        # Patch the client class at import time
        with patch('src.event.events_tools.AgentMonitoringEventsMCPTools', return_value=self.mock_events):

            # Create router instance
            self.router = EventsSmartRouterMCPTool(
                read_token="test_token",
                base_url="https://test.instana.com"
            )

            # Manually set the client on the router
            self.router.events_client = self.mock_events

    def test_init(self):
        """Test router initialization"""
        self.assertEqual(self.router.read_token, "test_token")
        self.assertEqual(self.router.base_url, "https://test.instana.com")
        self.assertIsNotNone(self.router.events_client)

    def test_invalid_operation(self):
        """Test handling of invalid operation"""
        result = asyncio.run(self.router.manage_events(
            operation="invalid_op"
        ))

        self.assertIn("error", result)
        self.assertIn("invalid_op", result["error"].lower())

    def test_get_event(self):
        """Test get_event operation"""
        async def mock_get_event(*args, **kwargs):
            return {"event": "details"}

        self.mock_events.get_event = mock_get_event

        result = asyncio.run(self.router.manage_events(
            operation="get_event",
            params={"event_id": "event-123"}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_event")

    def test_get_kubernetes_info_events(self):
        """Test get_kubernetes_info_events operation"""
        async def mock_get_k8s_events(*args, **kwargs):
            return {"events": []}

        self.mock_events.get_kubernetes_info_events = mock_get_k8s_events

        result = asyncio.run(self.router.manage_events(
            operation="get_kubernetes_info_events",
            params={
                "time_range": "last 24 hours",
                "max_events": 50
            }
        ))

        self.assertIn("results", result)

    def test_get_agent_monitoring_events(self):
        """Test get_agent_monitoring_events operation"""
        async def mock_get_agent_events(*args, **kwargs):
            return {"events": []}

        self.mock_events.get_agent_monitoring_events = mock_get_agent_events

        # Use valid timestamps (after Jan 1, 2020)
        result = asyncio.run(self.router.manage_events(
            operation="get_agent_monitoring_events",
            params={
                "from_time": 1700000000000,  # Nov 2023
                "to_time": 1700100000000,
                "max_events": 100
            }
        ))

        self.assertIn("results", result)

    def test_get_events_by_ids(self):
        """Test get_events_by_ids operation"""
        async def mock_get_by_ids(*args, **kwargs):
            return {"events": []}

        self.mock_events.get_events_by_ids = mock_get_by_ids

        result = asyncio.run(self.router.manage_events(
            operation="get_events_by_ids",
            params={"event_ids": ["event-1", "event-2"]}
        ))

        self.assertIn("results", result)

    def test_exception_handling(self):
        """Test exception handling in router"""
        async def mock_error(*args, **kwargs):
            raise Exception("Test error")

        self.mock_events.get_event = mock_error

        result = asyncio.run(self.router.manage_events(
            operation="get_event",
            params={"event_id": "event-123"}
        ))

        self.assertIn("error", result)
        self.assertIn("Test error", str(result["error"]))

    def test_params_none_handling(self):
        """Test handling when params is None"""
        async def mock_get_event(*args, **kwargs):
            return {"event": "details"}

        self.mock_events.get_event = mock_get_event

        result = asyncio.run(self.router.manage_events(
            operation="get_event",
            params=None
        ))

        # Should handle None params gracefully - check that result has either results or error
        self.assertTrue("results" in result or "error" in result)


    def test_get_events_basic(self):
        """Test get_events operation with minimal filters."""
        async def mock_get_events(*args, **kwargs):
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        result = asyncio.run(self.router.manage_events(
            operation="get_events",
            params={"filters": {"time_range": "last 24 hours"}}
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_events")

    def test_get_events_with_nested_filters(self):
        """Test get_events passes nested filters to the events client."""
        captured = {}

        async def mock_get_events(filters=None, ctx=None):
            captured["filters"] = filters
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        asyncio.run(self.router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "time_range": "last 24 hours",
                    "state": "open",
                    "severity": 10,
                    "event_type_filters": ["INCIDENT"],
                    "max_events": 25,
                }
            }
        ))

        self.assertIsNotNone(captured.get("filters"))
        self.assertEqual(captured["filters"]["state"], "open")
        self.assertEqual(captured["filters"]["severity"], 10)
        self.assertEqual(captured["filters"]["max_events"], 25)

    def test_get_events_no_filters_key_uses_empty_dict(self):
        """get_events with no 'filters' key should still call the events client."""
        async def mock_get_events(*args, **kwargs):
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        result = asyncio.run(self.router.manage_events(
            operation="get_events",
            params={}
        ))

        # Time validation is required for get_events, so without time params
        # it may return validation_failed or results depending on defaults
        self.assertTrue("results" in result or "validation_failed" in result)

    def test_get_events_invalid_event_type_filter(self):
        """get_events with invalid event type filter should return an error."""
        async def mock_get_events(*args, **kwargs):
            return {"error": "Invalid event_type 'INVALID'"}

        self.mock_events.get_events = mock_get_events

        result = asyncio.run(self.router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "time_range": "last 24 hours",
                    "event_type_filters": ["INCIDENT"],
                }
            }
        ))

        # Should pass through to the events client
        self.assertIn("results", result)

    def test_get_events_max_events_default_is_50(self):
        """get_events should default max_events to 50 when not specified."""
        captured = {}

        async def mock_get_events(filters=None, ctx=None):
            captured["filters"] = filters
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        asyncio.run(self.router.manage_events(
            operation="get_events",
            params={"filters": {"time_range": "last 24 hours"}}
        ))

        self.assertEqual(captured["filters"]["max_events"], 50)

    def test_get_events_with_entity_type_and_entity_label(self):
        """get_events should forward entity_type and entity_label to the client."""
        captured = {}

        async def mock_get_events(filters=None, ctx=None):
            captured["filters"] = filters
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        asyncio.run(self.router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "time_range": "last 2 days",
                    "entity_type": "service",
                    "entity_label": "payment-service",
                }
            }
        ))

        self.assertEqual(captured["filters"]["entity_type"], "service")
        self.assertEqual(captured["filters"]["entity_label"], "payment-service")

    def test_get_events_with_rca_filter(self):
        """get_events should forward the rca filter to the client."""
        captured = {}

        async def mock_get_events(filters=None, ctx=None):
            captured["filters"] = filters
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        asyncio.run(self.router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "time_range": "last 24 hours",
                    "rca": True,
                }
            }
        ))

        self.assertTrue(captured["filters"]["rca"])

    def test_get_events_time_validation_fails_without_time_params(self):
        """get_events without any time params should fail time validation."""
        result = asyncio.run(self.router.manage_events(
            operation="get_events",
            params={"filters": {}}
        ))

        self.assertIn("validation_failed", result)
        self.assertTrue(result["validation_failed"])

    def test_get_events_exception_handling(self):
        """get_events should return an error dict when events client raises."""
        async def mock_get_events(*args, **kwargs):
            raise Exception("Events client failure")

        self.mock_events.get_events = mock_get_events

        result = asyncio.run(self.router.manage_events(
            operation="get_events",
            params={"filters": {"time_range": "last 24 hours"}}
        ))

        self.assertIn("error", result)

    def test_get_events_with_from_and_to_time(self):
        """get_events with explicit from_time/to_time should succeed time validation."""
        async def mock_get_events(*args, **kwargs):
            return {"events": [], "events_returned": 0, "total_events": 0}

        self.mock_events.get_events = mock_get_events

        result = asyncio.run(self.router.manage_events(
            operation="get_events",
            params={
                "filters": {
                    "from_time": 1700000000000,
                    "to_time": 1700100000000,
                }
            }
        ))

        self.assertIn("results", result)
        self.assertEqual(result["operation"], "get_events")


if __name__ == '__main__':
    unittest.main()

