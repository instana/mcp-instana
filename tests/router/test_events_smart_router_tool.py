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


if __name__ == '__main__':
    unittest.main()

