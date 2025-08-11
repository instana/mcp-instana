"""
Unit tests for the AgentMonitoringEventsMCPTools class
"""

import asyncio
import logging
import os
import sys
import unittest
from datetime import datetime
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.event.events_tools')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False  # Prevent logs from propagating to parent loggers

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    # Skip printing exceptions from the mock side_effect
    if isinstance(value, Exception) and str(value) == "Test error":
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
    # Just do nothing - this will suppress all traceback printing from print_exc
    pass

traceback.print_exception = custom_print_exception
traceback.print_exc = custom_print_exc

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.events_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.events_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_events_api = MagicMock()

# Add __name__ attribute to mock classes
mock_events_api.__name__ = "EventsApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.events_api'].EventsApi = mock_events_api

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.event.events_tools import AgentMonitoringEventsMCPTools

class TestAgentMonitoringEventsMCPTools(unittest.TestCase):
    """Test the AgentMonitoringEventsMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_events_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.events_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = AgentMonitoringEventsMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.events_api = self.events_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_event_success(self):
        """Test get_event with a successful response"""
        # Set up the mock response
        event_id = "test_event_id"
        mock_result = {"eventId": event_id, "data": "test_data"}
        self.events_api.get_event.return_value = mock_result

        # Call the method
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the mock was called with the correct arguments
        self.events_api.get_event.assert_called_once_with(event_id=event_id)

        # Check that the result is correct
        self.assertEqual(result, mock_result)

    def test_get_event_error(self):
        """Test get_event error handling"""
        # Set up the mock to raise an exception
        event_id = "test_event_id"
        self.events_api.get_event.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get event", result["error"])

    @patch('src.event.events_tools.datetime')
    def test_get_kubernetes_info_events_with_defaults(self, mock_datetime):
        """Test get_kubernetes_info_events with default parameters"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_event1 = MagicMock()
        mock_event1.to_dict = MagicMock(return_value={
            "eventId": "event1",
            "problem": "Pod Crash",
            "entityLabel": "namespace1/pod1",
            "detail": "Pod crashed due to OOM",
            "fixSuggestion": "Increase memory limits",
            "start": 900000  # milliseconds
        })

        mock_event2 = MagicMock()
        mock_event2.to_dict = MagicMock(return_value={
            "eventId": "event2",
            "problem": "Pod Crash",
            "entityLabel": "namespace1/pod2",
            "detail": "Pod crashed due to OOM",
            "fixSuggestion": "Increase memory limits",
            "start": 950000  # milliseconds
        })

        self.events_api.kubernetes_info_events.return_value = [mock_event1, mock_event2]

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the mock was called with the correct arguments
        # Default time range should be 24 hours
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier

        self.events_api.kubernetes_info_events.assert_called_once_with(
            to=expected_to_time,
            var_from=expected_from_time,
            window_size=None,
            filter_event_updates=None,
            exclude_triggered_before=None
        )

        # Check that the result contains the expected analysis
        self.assertIn("summary", result)
        self.assertIn("time_range", result)
        self.assertIn("events_count", result)
        self.assertIn("problem_analyses", result)
        self.assertIn("markdown_summary", result)

        # Check that the problem analysis is correct
        problem_analyses = result["problem_analyses"]
        self.assertEqual(len(problem_analyses), 1)  # Only one problem type
        self.assertEqual(problem_analyses[0]["problem"], "Pod Crash")
        self.assertEqual(problem_analyses[0]["count"], 2)
        self.assertEqual(problem_analyses[0]["affected_namespaces"], ["namespace1"])
        self.assertEqual(problem_analyses[0]["details"], ["Pod crashed due to OOM"])
        self.assertEqual(problem_analyses[0]["fix_suggestions"], ["Increase memory limits"])

    @patch('src.event.events_tools.datetime')
    def test_get_kubernetes_info_events_with_time_range(self, mock_datetime):
        """Test get_kubernetes_info_events with natural language time range"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response (empty list for simplicity)
        self.events_api.kubernetes_info_events.return_value = []

        # Call the method with a natural language time range
        asyncio.run(self.client.get_kubernetes_info_events(time_range="last 2 days"))

        # Check that the mock was called with the correct arguments
        # Time range should be 2 days
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (2 * 24 * 60 * 60 * 1000)  # 2 days earlier

        self.events_api.kubernetes_info_events.assert_called_once_with(
            to=expected_to_time,
            var_from=expected_from_time,
            window_size=None,
            filter_event_updates=None,
            exclude_triggered_before=None
        )

    def test_get_kubernetes_info_events_error_handling(self):
        """Test get_kubernetes_info_events error handling"""
        # Set up the mock to raise an exception
        self.events_api.kubernetes_info_events.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get Kubernetes info events", result["error"])

    @patch('src.event.events_tools.datetime')
    def test_get_kubernetes_info_events_with_empty_result(self, mock_datetime):
        """Test get_kubernetes_info_events with empty result"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response as empty list
        self.events_api.kubernetes_info_events.return_value = []

        # Call the method
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the result contains the expected analysis for empty results
        self.assertIn("analysis", result)
        self.assertIn("No Kubernetes events found", result["analysis"])
        self.assertIn("time_range", result)
        self.assertEqual(result["events_count"], 0)

    @patch('src.event.events_tools.datetime')
    def test_get_agent_monitoring_events_with_defaults(self, mock_datetime):
        """Test get_agent_monitoring_events with default parameters"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_event1 = MagicMock()
        mock_event1.to_dict = MagicMock(return_value={
            "eventId": "event1",
            "problem": "Monitoring issue: High CPU",
            "entityName": "host1",
            "entityLabel": "host1.example.com",
            "entityType": "host",
            "severity": 10,
            "start": 900000  # milliseconds
        })

        mock_event2 = MagicMock()
        mock_event2.to_dict = MagicMock(return_value={
            "eventId": "event2",
            "problem": "Monitoring issue: High CPU",
            "entityName": "host2",
            "entityLabel": "host2.example.com",
            "entityType": "host",
            "severity": 10,
            "start": 950000  # milliseconds
        })

        self.events_api.agent_monitoring_events.return_value = [mock_event1, mock_event2]

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the mock was called with the correct arguments
        # Default time range should be 1 hour
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (60 * 60 * 1000)  # 1 hour earlier

        self.events_api.agent_monitoring_events.assert_called_once_with(
            to=expected_to_time,
            var_from=expected_from_time,
            window_size=None,
            filter_event_updates=None,
            exclude_triggered_before=None
        )

        # Check that the result contains the expected analysis
        self.assertIn("summary", result)
        self.assertIn("time_range", result)
        self.assertIn("events_count", result)
        self.assertIn("problem_analyses", result)
        self.assertIn("markdown_summary", result)

        # Check that the problem analysis is correct
        problem_analyses = result["problem_analyses"]
        self.assertEqual(len(problem_analyses), 1)  # Only one problem type
        self.assertEqual(problem_analyses[0]["problem"], "High CPU")  # Should strip "Monitoring issue: " prefix
        self.assertEqual(problem_analyses[0]["count"], 2)
        self.assertEqual(len(problem_analyses[0]["affected_entities"]), 2)
        self.assertEqual(problem_analyses[0]["entity_types"], ["host"])

    @patch('src.event.events_tools.datetime')
    def test_get_agent_monitoring_events_with_time_range(self, mock_datetime):
        """Test get_agent_monitoring_events with natural language time range"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response (empty list for simplicity)
        self.events_api.agent_monitoring_events.return_value = []

        # Call the method with a natural language time range
        result = asyncio.run(self.client.get_agent_monitoring_events(time_range="last 2 hours"))

        # Check that the method returns a result
        self.assertIsInstance(result, dict)

    def test_get_agent_monitoring_events_error_handling(self):
        """Test get_agent_monitoring_events error handling"""
        # Set up the mock to raise an exception
        self.events_api.agent_monitoring_events.side_effect = Exception("Test error")

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get agent monitoring events", result["error"])

    @patch('src.event.events_tools.datetime')
    def test_get_agent_monitoring_events_with_empty_result(self, mock_datetime):
        """Test get_agent_monitoring_events with empty result"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response as empty list
        self.events_api.agent_monitoring_events.return_value = []

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the result contains the expected analysis for empty results
        self.assertIn("analysis", result)
        self.assertIn("No agent monitoring events found", result["analysis"])
        self.assertIn("time_range", result)
        self.assertEqual(result["events_count"], 0)

    @patch('src.event.events_tools.datetime')
    def test_get_kubernetes_info_events_with_various_time_ranges(self, mock_datetime):
        """Test get_kubernetes_info_events with various time range formats"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response (empty list for simplicity)
        self.events_api.kubernetes_info_events.return_value = []

        # Test different time range formats
        time_ranges = [
            "last few hours",
            "last 5 hours",
            "last 3 days",
            "last 2 weeks",
            "last 1 month",
            "unknown format"
        ]

        expected_from_times = [
            1000 * 1000 - (24 * 60 * 60 * 1000),  # last few hours -> 24 hours
            1000 * 1000 - (5 * 60 * 60 * 1000),   # last 5 hours
            1000 * 1000 - (3 * 24 * 60 * 60 * 1000),  # last 3 days
            1000 * 1000 - (2 * 7 * 24 * 60 * 60 * 1000),  # last 2 weeks
            1000 * 1000 - (1 * 30 * 24 * 60 * 60 * 1000),  # last 1 month
            1000 * 1000 - (24 * 60 * 60 * 1000)   # unknown format -> default 24 hours
        ]

        for i, time_range in enumerate(time_ranges):
            # Reset the mock
            self.events_api.kubernetes_info_events.reset_mock()

            # Call the method with the time range
            asyncio.run(self.client.get_kubernetes_info_events(time_range=time_range))

            # Check that the mock was called with the correct arguments
            self.events_api.kubernetes_info_events.assert_called_once_with(
                to=1000 * 1000,
                var_from=expected_from_times[i],
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @patch('src.event.events_tools.datetime')
    def test_get_agent_monitoring_events_with_problem_no_prefix(self, mock_datetime):
        """Test get_agent_monitoring_events with problem field that doesn't have the 'Monitoring issue:' prefix"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response
        mock_event = MagicMock()
        mock_event.to_dict = MagicMock(return_value={
            "eventId": "event1",
            "problem": "High CPU",  # No "Monitoring issue:" prefix
            "entityName": "host1",
            "entityLabel": "host1.example.com",
            "entityType": "host",
            "severity": 10,
            "start": 900000  # milliseconds
        })

        self.events_api.agent_monitoring_events.return_value = [mock_event]

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the result contains the expected analysis
        self.assertIn("problem_analyses", result)
        problem_analyses = result["problem_analyses"]
        self.assertEqual(len(problem_analyses), 1)
        # Should use the problem field as is since it doesn't have the prefix
        self.assertEqual(problem_analyses[0]["problem"], "High CPU")


if __name__ == '__main__':
    unittest.main()
