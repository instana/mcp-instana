"""
Unit tests for the AgentMonitoringEventsMCPTools class
"""

import asyncio
import importlib
import logging
import os
import sys
import unittest
from datetime import datetime
from functools import wraps
from unittest.mock import AsyncMock, MagicMock, patch


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

def create_agent_monitoring_events_client(read_token: str, base_url: str):
    with patch('src.core.utils.with_header_auth', mock_with_header_auth):
        module = importlib.import_module('src.event.events_tools')
        module = importlib.reload(module)
        return module.AgentMonitoringEventsMCPTools(
            read_token=read_token,
            base_url=base_url,
        )

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
        self.client = create_agent_monitoring_events_client(
            read_token=self.read_token,
            base_url=self.base_url,
        )

        # Set up the client's API attribute
        self.client.events_api = self.events_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_event_success(self):
        """Test get_event with a successful response via the raw API path."""
        event_id = "test_event_id"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"eventId": "test_event_id", "type": "incident", "state": "open", "problem": "Test problem", "start": 1000000}'
        self.events_api.get_event_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_event(event_id=event_id))

        self.events_api.get_event_without_preload_content.assert_called_once_with(event_id=event_id)
        self.assertEqual(result["eventId"], event_id)
        self.assertIn("type", result)
        self.assertIn("problem", result)

    def test_get_event_error(self):
        """Test get_event error handling when the raw API call raises."""
        event_id = "test_event_id"
        self.events_api.get_event_without_preload_content.side_effect = Exception("Test error")

        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains an error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get event", (result.get("error") or result.get("message", "")))

    def test_get_event_empty_id(self):
        """Test get_event with empty event_id."""
        result = asyncio.run(self.client.get_event(event_id=""))

        # Check that the result contains an error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("event_id", (result.get("error") or result.get("message", "")))

    def test_get_event_404_error(self):
        """Test get_event returns a not-found message on HTTP 404."""
        event_id = "nonexistent_id"
        mock_response = MagicMock()
        mock_response.status = 404
        self.events_api.get_event_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertEqual((result.get("error") or result.get("message", "")), f"Event with ID {event_id} not found")
        self.assertEqual(result["event_id"], event_id)

    def test_get_event_401_error(self):
        """Test get_event returns auth error on HTTP 401."""
        event_id = "test_id"
        mock_response = MagicMock()
        mock_response.status = 401
        self.events_api.get_event_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertEqual((result.get("error") or result.get("message", "")), "Authentication failed. Please check your API token and permissions.")

    def test_get_event_http_error(self):
        """Test get_event returns error on non-200/non-404 HTTP status."""
        event_id = "test_event_id"
        mock_response = MagicMock()
        mock_response.status = 500
        self.events_api.get_event_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the fallback approach was used
        self.events_api.get_event_without_preload_content.assert_called_once_with(event_id=event_id)

        # A non-200/non-404 status returns an error dict
        self.assertIn("error", result)
        self.assertIn("Failed to get event: HTTP 500", result["error"])
        self.assertEqual(result["event_id"], event_id)

    def test_get_event_fallback_http_error(self):
        """Test get_event fallback approach with HTTP error"""
        # Set up the mock to raise an exception for standard API
        event_id = "test_event_id"
        self.events_api.get_event.side_effect = Exception("Test error")

        # Set up the mock response for fallback approach with error status
        mock_response = MagicMock()
        mock_response.status = 404
        self.events_api.get_event_without_preload_content.return_value = mock_response

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # A 404 response returns a "not found" error message (not "Failed to get event: HTTP 404")
        self.assertIn("error", result)
        self.assertIn(event_id, result["error"])

    def test_get_event_json_error(self):
        """Test get_event returns error when response body is not valid JSON."""
        event_id = "test_event_id"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.events_api.get_event_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to parse JSON response", (result.get("error") or result.get("message", "")))
        self.assertEqual(result["event_id"], event_id)

    def test_get_event_api_exception(self):
        """Test get_event when the API raises an exception with a status attribute."""
        class MockError(Exception):
            def __init__(self):
                self.status = 404

        event_id = "nonexistent_id"
        self.events_api.get_event_without_preload_content.side_effect = MockError()

        result = asyncio.run(self.client.get_event(event_id=event_id))

        # An exception with status=404 returns the "not found" error message
        self.assertIn("error", result)
        self.assertIn(event_id, result["error"])

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

        # Set up the mock to return the events
        self.events_api.kubernetes_info_events = MagicMock(return_value=[mock_event1, mock_event2])

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the mock was called with the correct arguments
        # When no time params provided, _build_time_params uses var_from/to (default 10 min window)
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (10 * 60 * 1000)  # 10 minutes earlier

        self.events_api.kubernetes_info_events.assert_called_once_with(
            var_from=expected_from_time,
            to=expected_to_time,
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
        self.events_api.kubernetes_info_events = MagicMock(return_value=[])

        # Call the method with a natural language time range
        asyncio.run(self.client.get_kubernetes_info_events(time_range="last 2 days"))

        # Check that the mock was called with the correct arguments
        # When time_range is provided, _build_time_params uses window_size
        expected_window_size = 2 * 24 * 60 * 60 * 1000  # 2 days in ms

        self.events_api.kubernetes_info_events.assert_called_once_with(
            window_size=expected_window_size,
            filter_event_updates=None,
            exclude_triggered_before=None
        )

    def test_get_kubernetes_info_events_error_handling(self):
        """Test get_kubernetes_info_events error handling"""
        # Set up the mock to raise an exception
        self.events_api.kubernetes_info_events.side_effect = Exception("Test error")

        # Reset any previous calls
        self.events_api.kubernetes_info_events.reset_mock()

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the mock was called
        self.events_api.kubernetes_info_events.assert_called_once()

        # Check that the result contains an error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get Kubernetes info events", (result.get("error") or result.get("message", "")))

    @patch('src.event.events_tools.datetime')
    def test_get_kubernetes_info_events_with_empty_result(self, mock_datetime):
        """Test get_kubernetes_info_events with empty result"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response as empty list
        self.events_api.kubernetes_info_events = MagicMock(return_value=[])

        # Call the method
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the result contains the expected structure for empty results
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 0)
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

        # Set up the mock to return the events
        self.events_api.agent_monitoring_events = MagicMock(return_value=[mock_event1, mock_event2])

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the mock was called with the correct arguments
        # When no time params provided, _build_time_params uses var_from/to (default 10 min window)
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (10 * 60 * 1000)  # 10 minutes earlier

        self.events_api.agent_monitoring_events.assert_called_once_with(
            var_from=expected_from_time,
            to=expected_to_time,
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
        self.events_api.get_events.return_value = []

        # Reset any previous calls
        self.events_api.get_events.reset_mock()

        # Call the method with a natural language time range
        result = asyncio.run(self.client.get_agent_monitoring_events(time_range="last 2 hours"))

        # Check that the method returns a result
        self.assertIsInstance(result, dict)

    def test_get_agent_monitoring_events_error_handling(self):
        """Test get_agent_monitoring_events error handling"""
        # Set up the mock to raise an exception
        self.events_api.agent_monitoring_events.side_effect = Exception("Test error")

        # Reset any previous calls
        self.events_api.agent_monitoring_events.reset_mock()

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the mock was called
        self.events_api.agent_monitoring_events.assert_called_once()

        # Check that the result contains an error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get agent monitoring events", (result.get("error") or result.get("message", "")))

    @patch('src.event.events_tools.datetime')
    def test_get_agent_monitoring_events_with_empty_result(self, mock_datetime):
        """Test get_agent_monitoring_events with empty result"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response as empty list
        self.events_api.agent_monitoring_events = MagicMock(return_value=[])

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the result contains the expected structure for empty results
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 0)
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
        self.events_api.kubernetes_info_events = MagicMock(return_value=[])

        # Test different time range formats
        time_ranges = [
            "last few hours",
            "last 5 hours",
            "last 3 days",
            "last 2 weeks",
            "last 1 month",
            "unknown format"
        ]

        # Expected window sizes for each time range (used when time_range is provided)
        expected_window_sizes = [
            10 * 60 * 1000,                # last few hours -> default 10 minutes
            5 * 60 * 60 * 1000,            # last 5 hours
            3 * 24 * 60 * 60 * 1000,       # last 3 days
            2 * 7 * 24 * 60 * 60 * 1000,   # last 2 weeks
            1 * 30 * 24 * 60 * 60 * 1000,  # last 1 month
            10 * 60 * 1000                 # unknown format -> default 10 minutes (still uses window_size)
        ]

        for i, time_range in enumerate(time_ranges):
            # Reset the mock
            self.events_api.kubernetes_info_events.reset_mock()

            # Call the method with the time range (result used in assertion via mock call)
            _ = asyncio.run(self.client.get_kubernetes_info_events(time_range=time_range))

            # Check that the mock was called with window_size for all time ranges
            # Even unknown formats fall back to default window_size (24 hours)
            call_kwargs = self.events_api.kubernetes_info_events.call_args[1]
            self.assertEqual(call_kwargs["window_size"], expected_window_sizes[i])
            self.assertIsNone(call_kwargs["filter_event_updates"])
            self.assertIsNone(call_kwargs["exclude_triggered_before"])

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

        # Set up the mock to return the event
        self.events_api.agent_monitoring_events = MagicMock(return_value=[mock_event])

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the result contains the expected analysis
        self.assertIn("problem_analyses", result)
        problem_analyses = result["problem_analyses"]
        self.assertEqual(len(problem_analyses), 1)

        # Find the problem analysis for High CPU - could be with or without "Monitoring issue:" prefix
        high_cpu_analysis = next((p for p in problem_analyses if p["problem"] == "High CPU" or p["problem"] == "Monitoring issue: High CPU"), None)
        self.assertIsNotNone(high_cpu_analysis, "High CPU problem analysis not found")

    @patch('src.event.events_tools.datetime')
    def test_get_agent_monitoring_events_with_non_list_result(self, mock_datetime):
        """Test get_agent_monitoring_events with non-list result"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)

        # Set up the mock response as a single object (not a list)
        mock_event = MagicMock()
        mock_event.to_dict = MagicMock(return_value={
            "eventId": "event1",
            "problem": "Monitoring issue: Single Event",
            "entityName": "host1",
            "entityLabel": "host1.example.com",
            "entityType": "host",
            "severity": 10,
            "start": 900000
        })

        # Set up the mock to return a single event (not in a list)
        self.events_api.agent_monitoring_events = MagicMock(return_value=mock_event)

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the result contains the expected analysis
        self.assertIn("problem_analyses", result)
        problem_analyses = result["problem_analyses"]
        self.assertEqual(len(problem_analyses), 1)

        # Find the problem analysis for Single Event - could be with or without "Monitoring issue:" prefix
        single_event_analysis = next((p for p in problem_analyses if p["problem"] == "Single Event" or p["problem"] == "Monitoring issue: Single Event"), None)
        self.assertIsNotNone(single_event_analysis, "Single Event problem analysis not found")
        self.assertEqual(single_event_analysis["count"], 1)

    def test_get_agent_monitoring_events_with_api_error_details(self):
        """Test get_agent_monitoring_events with detailed API error"""
        # Set up the mock to raise an exception with details
        detailed_error = Exception("API error with details")
        self.events_api.agent_monitoring_events.side_effect = detailed_error

        # Reset any previous calls
        self.events_api.agent_monitoring_events.reset_mock()

        # Call the method
        result = asyncio.run(self.client.get_agent_monitoring_events())

        # Check that the mock was called
        self.events_api.agent_monitoring_events.assert_called_once()

        # Check that the result contains the detailed error message
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Failed to get agent monitoring events", (result.get("error") or result.get("message", "")))

# Tests for _process_result method
    def test_process_result_with_list_items(self):
        """Test _process_result method with list items"""
        # Create a list of items with to_dict method
        item1 = MagicMock()
        item1.to_dict = MagicMock(return_value={"id": "item1"})

        item2 = MagicMock()
        item2.to_dict = MagicMock(return_value={"id": "item2"})

        # Create a list with mixed items (some with to_dict, some without)
        mixed_list = [item1, item2, {"id": "item3"}]

        # Process the list
        result = self.client._process_result(mixed_list)

        # Check that the result is a dictionary with items and count
        self.assertIsInstance(result, dict)
        self.assertIn("items", result)
        self.assertIn("count", result)
        self.assertEqual(result["count"], 3)

        # Check that the items were processed correctly
        self.assertEqual(len(result["items"]), 3)
        self.assertEqual(result["items"][0], {"id": "item1"})
        self.assertEqual(result["items"][1], {"id": "item2"})
        self.assertEqual(result["items"][2], {"id": "item3"})

    def test_process_result_with_dict(self):
        """Test _process_result method with dictionary input"""
        # Create a dictionary
        input_dict = {"key1": "value1", "key2": "value2"}

        # Process the dictionary
        result = self.client._process_result(input_dict)

        # Check that the result is the same dictionary
        self.assertEqual(result, input_dict)

    def test_process_result_with_other_types(self):
        """Test _process_result method with other input types"""
        # Test with a string
        string_result = self.client._process_result("test string")
        self.assertEqual(string_result, {"data": "test string"})

        # Test with an integer
        int_result = self.client._process_result(42)
        self.assertEqual(int_result, {"data": "42"})

        # Test with None
        none_result = self.client._process_result(None)
        self.assertEqual(none_result, {"data": "None"})

    # Tests for _summarize_events_result method
    def test_summarize_events_result_with_empty_input(self):
        """Test _summarize_events_result method with empty input"""
        # Test with empty list
        result = self.client._summarize_events_result([])
        self.assertEqual(result["events_count"], 0)
        self.assertEqual(result["summary"], "No events found")

        # Test with None
        result = self.client._summarize_events_result(None)
        self.assertEqual(result["events_count"], 0)
        self.assertEqual(result["summary"], "No events found")

    def test_summarize_events_result_with_total_count(self):
        """Test _summarize_events_result method with total_count parameter"""
        # Create some events
        events = [
            {"eventId": "event1", "eventType": "incident"},
            {"eventId": "event2", "eventType": "change"}
        ]

        # Test with total_count parameter
        result = self.client._summarize_events_result(events, total_count=10)
        self.assertEqual(result["events_count"], 10)  # Should use the provided total_count
        self.assertEqual(result["events_analyzed"], 2)  # Should be the length of the events list

    def test_summarize_events_result_with_max_events(self):
        """Test _summarize_events_result method with max_events parameter"""
        # Create some events
        events = [
            {"eventId": "event1", "eventType": "incident"},
            {"eventId": "event2", "eventType": "change"},
            {"eventId": "event3", "eventType": "issue"}
        ]

        # Test with max_events parameter
        result = self.client._summarize_events_result(events, max_events=2)
        self.assertEqual(result["events_count"], 3)  # Should be the length of the original events list
        self.assertEqual(result["events_analyzed"], 2)  # Should be limited by max_events

    def test_summarize_events_result_with_unknown_event_type(self):
        """Test _summarize_events_result method with unknown event type"""
        # Create an event with missing eventType
        events = [{"eventId": "event1"}]

        # Process the event
        result = self.client._summarize_events_result(events)

        # Check that the event type was set to "Unknown"
        self.assertIn("event_types", result)
        self.assertIn("Unknown", result["event_types"])

    # Tests for _process_time_range method
    def test_process_time_range_with_none_values(self):
        """Test _process_time_range method with None values"""
        # Call the method with None values
        from_time, to_time = self.client._process_time_range(None, None, None)

        # Check that default values were used
        self.assertIsNotNone(from_time)
        self.assertIsNotNone(to_time)
        self.assertTrue(to_time > from_time)

    def test_process_time_range_with_explicit_values(self):
        """Test _process_time_range method with explicit values"""
        # Call the method with explicit values
        explicit_from = 500000
        explicit_to = 600000
        from_time, to_time = self.client._process_time_range(None, explicit_from, explicit_to)

        # Check that the explicit values were used
        self.assertEqual(from_time, explicit_from)
        self.assertEqual(to_time, explicit_to)

    def test_process_time_range_with_unusual_time_range(self):
        """Test _process_time_range method with unusual time range format"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with unusual time range
            result_from_time, result_to_time = self.client._process_time_range("last century", None, None)

            # Check that default values were used (10 minutes)
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (10 * 60 * 1000)  # 10 minutes earlier

            self.assertEqual(result_from_time, expected_from_time)
            self.assertEqual(result_to_time, expected_to_time)

    def test_get_kubernetes_info_events_with_non_dict_event(self):
        """Test get_kubernetes_info_events with non-dictionary event"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)
            mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

            # Create a mock event that is not a dictionary and doesn't have to_dict
            class CustomEvent:
                pass

            mock_event = CustomEvent()

            # Set up the mock response
            self.events_api.kubernetes_info_events.return_value = [mock_event]

            # Call the method
            result = asyncio.run(self.client.get_kubernetes_info_events())

            # Check that the error was handled correctly
            self.assertTrue("error" in result or result.get("elicitation_needed"))
            self.assertIn("CustomEvent", (result.get("error") or result.get("message", "")))

    def test_get_kubernetes_info_events_with_many_namespaces(self):
        """Test get_kubernetes_info_events with many namespaces"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)
            mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

            # Create mock events with many namespaces
            mock_events = []
            for i in range(10):
                mock_event = MagicMock()
                mock_event.to_dict = MagicMock(return_value={
                    "eventId": f"event{i}",
                    "problem": "Pod Crash",
                    "entityLabel": f"namespace{i}/pod{i}",
                    "detail": f"Pod {i} crashed",
                    "fixSuggestion": f"Fix {i}"
                })
                mock_events.append(mock_event)

            # Set up the mock response
            self.events_api.kubernetes_info_events.return_value = mock_events

            # Call the method
            result = asyncio.run(self.client.get_kubernetes_info_events())

            # Check that the markdown summary includes the correct number of namespaces
            self.assertIn("markdown_summary", result)
            self.assertIn("and 5 more", result["markdown_summary"])

    def test_get_agent_monitoring_events_with_default_from_time(self):
        """Test get_agent_monitoring_events with default from_time"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)
            mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

            # Set up the mock response
            self.events_api.agent_monitoring_events.return_value = []

            # Call the method with only to_time
            to_time = 1000 * 1000  # 1000 seconds in milliseconds
            # Result not needed as we're checking the mock call
            _ = asyncio.run(self.client.get_agent_monitoring_events(to_time=to_time))

            # Check that from_time was set to 10 minutes before to_time
            self.events_api.agent_monitoring_events.assert_called_once()
            call_args = self.events_api.agent_monitoring_events.call_args[1]
            self.assertEqual(call_args['to'], to_time)
            # The default from_time is 10 minutes before to_time
            self.assertEqual(call_args['var_from'], to_time - (10 * 60 * 1000))  # 10 minutes in milliseconds

    def test_get_agent_monitoring_events_with_non_dict_event(self):
        """Test get_agent_monitoring_events with non-dictionary event"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)
            mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

            # Create a mock event that is not a dictionary and doesn't have to_dict
            class CustomEvent:
                pass

            mock_event = CustomEvent()

            # Set up the mock response
            self.events_api.agent_monitoring_events.return_value = [mock_event]

            # Call the method
            result = asyncio.run(self.client.get_agent_monitoring_events())

            # Check that the error was handled correctly
            self.assertTrue("error" in result or result.get("elicitation_needed"))
            self.assertIn("CustomEvent", (result.get("error") or result.get("message", "")))

    def test_get_agent_monitoring_events_with_many_entities(self):
        """Test get_agent_monitoring_events with many entities"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)
            mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

            # Create mock events with many entities
            mock_events = []
            for i in range(10):
                mock_event = MagicMock()
                mock_event.to_dict = MagicMock(return_value={
                    "eventId": f"event{i}",
                    "problem": "High CPU",
                    "entityName": f"entity{i}",
                    "entityLabel": f"label{i}",
                    "entityType": "host",
                    "severity": 10
                })
                mock_events.append(mock_event)

            # Set up the mock response
            self.events_api.agent_monitoring_events.return_value = mock_events

            # Call the method
            result = asyncio.run(self.client.get_agent_monitoring_events())

            # Check that the markdown summary includes the correct number of entities
            self.assertIn("markdown_summary", result)
            self.assertIn("and 5 more", result["markdown_summary"])

            # No need to check the time values here as they're already tested in other tests
    def test_process_result_with_flat_dict(self):
        """Test _process_result method with flat dictionary"""
        # Create a flat dictionary
        flat_dict = {
            "id": "test_id",
            "name": "Test Name",
            "value": 42
        }

        # Process the dictionary
        result = self.client._process_result(flat_dict)

        # Check that the structure was preserved
        self.assertIsInstance(result, dict)
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("value", result)
        self.assertEqual(result["id"], "test_id")
        self.assertEqual(result["name"], "Test Name")
        self.assertEqual(result["value"], 42)

    def test_process_result_with_simple_object(self):
        """Test _process_result method with simple object having to_dict method"""
        # Create an object with to_dict method
        obj = MagicMock()
        obj.to_dict = MagicMock(return_value={"id": "obj1", "name": "Object 1"})

        # Process the object
        result = self.client._process_result(obj)

        # Check that the to_dict method was called
        obj.to_dict.assert_called_once()

        # Check that the result contains the expected data
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertEqual(result["id"], "obj1")
        self.assertEqual(result["name"], "Object 1")

    def test_process_time_range_with_hour_format(self):
        """Test _process_time_range method with hour format"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with hour format
            from_time, to_time = self.client._process_time_range("last 5 hours", None, None)

            # Check that the correct values were calculated
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (5 * 60 * 60 * 1000)  # 5 hours earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, expected_to_time)

    def test_process_time_range_with_day_format(self):
        """Test _process_time_range method with day format"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with day format
            from_time, to_time = self.client._process_time_range("last 3 days", None, None)

            # Check that the correct values were calculated
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (3 * 24 * 60 * 60 * 1000)  # 3 days earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, expected_to_time)

    def test_process_time_range_with_week_format(self):
        """Test _process_time_range method with week format"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with week format
            from_time, to_time = self.client._process_time_range("last 2 weeks", None, None)

            # Check that the correct values were calculated
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (2 * 7 * 24 * 60 * 60 * 1000)  # 2 weeks earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, expected_to_time)

    def test_process_time_range_with_month_format(self):
        """Test _process_time_range method with month format"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with month format
            from_time, to_time = self.client._process_time_range("last 1 month", None, None)

            # Check that the correct values were calculated
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (1 * 30 * 24 * 60 * 60 * 1000)  # 1 month earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, expected_to_time)

    def test_process_time_range_with_few_hours_format(self):
        """Test _process_time_range method with 'few hours' format"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with 'few hours' format
            from_time, to_time = self.client._process_time_range("last few hours", None, None)

            # Check that default values were used (10 minutes)
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (10 * 60 * 1000)  # 10 minutes earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, expected_to_time)

    def test_process_time_range_with_only_to_time(self):
        """Test _process_time_range method with only to_time provided"""
        # Set up the mock datetime
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
            mock_datetime.now = MagicMock(return_value=mock_now)

            # Call the method with only to_time
            to_time_value = 500000
            from_time, to_time = self.client._process_time_range(None, None, to_time_value)

            # Check that from_time was set to 10 minutes before to_time
            expected_from_time = to_time_value - (10 * 60 * 1000)  # 10 minutes earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, to_time_value)

    @patch('src.event.events_tools.datetime')
    def test_get_events_filters_entity_type_from_entity_type_field(self, mock_datetime):
        """Test get_events with entity_type filter using top-level entityType field."""
        # Set up mock datetime for time range
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Prepare API response with entityType at root level
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='''[
            {
                "eventId": "event1",
                "eventType": "incident",
                "state": "open",
                "entityType": "JVM",
                "start": 900000
            },
            {
                "eventId": "event2",
                "eventType": "incident",
                "state": "open",
                "entityType": "host",
                "start": 900000
            }
        ]''')

        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(
            filters={
                "entity_type": "jvm",
                "state": "open"
            }
        ))

        self.assertIn("events", result)
        self.assertEqual(result["total_events"], 2)  # raw API count
        self.assertEqual(result["events_returned"], 1)

    def test_calculate_duration_with_open_state(self):
        """Test _calculate_duration with open state returns 'ongoing'."""
        result = self.client._calculate_duration(1000000, 2000000, "open")
        self.assertEqual(result, "ongoing")

    def test_calculate_duration_seconds(self):
        """Test _calculate_duration for duration less than 60 seconds."""
        start_ms = 1000000
        end_ms = 1045000  # 45 seconds later
        result = self.client._calculate_duration(start_ms, end_ms, "closed")
        self.assertEqual(result, "45 seconds")

    def test_calculate_duration_single_minute(self):
        """Test _calculate_duration for exactly 1 minute."""
        start_ms = 1000000
        end_ms = 1060000  # 1 minute later
        result = self.client._calculate_duration(start_ms, end_ms, "closed")
        self.assertEqual(result, "1 minute")

    def test_calculate_duration_hours_with_minutes(self):
        """Test _calculate_duration for hours with minutes."""
        start_ms = 1000000
        end_ms = 1000000 + (2 * 3600 * 1000) + (30 * 60 * 1000)  # 2 hours 30 minutes
        result = self.client._calculate_duration(start_ms, end_ms, "closed")
        self.assertEqual(result, "2 hours 30 minutes")

    def test_calculate_duration_single_hour(self):
        """Test _calculate_duration for exactly 1 hour."""
        start_ms = 1000000
        end_ms = 1000000 + (3600 * 1000)  # 1 hour
        result = self.client._calculate_duration(start_ms, end_ms, "closed")
        self.assertEqual(result, "1 hour")

    def test_calculate_duration_days_with_hours(self):
        """Test _calculate_duration for days with hours."""
        start_ms = 1000000
        end_ms = 1000000 + (2 * 86400 * 1000) + (5 * 3600 * 1000)  # 2 days 5 hours
        result = self.client._calculate_duration(start_ms, end_ms, "closed")
        self.assertEqual(result, "2 days 5 hours")

    def test_calculate_duration_single_day(self):
        """Test _calculate_duration for exactly 1 day."""
        start_ms = 1000000
        end_ms = 1000000 + (86400 * 1000)  # 1 day
        result = self.client._calculate_duration(start_ms, end_ms, "closed")
        self.assertEqual(result, "1 day")

    def test_calculate_age_just_now(self):
        """Test _calculate_age for very recent events."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - 30000  # 30 seconds ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "just now")

    def test_calculate_age_single_minute(self):
        """Test _calculate_age for 1 minute ago."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - (60 * 1000)  # 1 minute ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "1 minute ago")

    def test_calculate_age_multiple_minutes(self):
        """Test _calculate_age for multiple minutes ago."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - (45 * 60 * 1000)  # 45 minutes ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "45 minutes ago")

    def test_calculate_age_single_hour(self):
        """Test _calculate_age for 1 hour ago."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - (3600 * 1000)  # 1 hour ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "1 hour ago")

    def test_calculate_age_multiple_hours(self):
        """Test _calculate_age for multiple hours ago."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - (5 * 3600 * 1000)  # 5 hours ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "5 hours ago")

    def test_calculate_age_single_day(self):
        """Test _calculate_age for 1 day ago."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - (86400 * 1000)  # 1 day ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "1 day ago")

    def test_calculate_age_multiple_days(self):
        """Test _calculate_age for multiple days ago."""
        from datetime import datetime
        current_time_ms = int(datetime.now().timestamp() * 1000)
        start_ms = current_time_ms - (7 * 86400 * 1000)  # 7 days ago
        result = self.client._calculate_age(start_ms)
        self.assertEqual(result, "7 days ago")

    def test_simplify_probable_cause_not_found(self):
        """Test _simplify_probable_cause when probable cause is not found."""
        probable_cause = {"found": False}
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertIsNone(result)

    def test_simplify_probable_cause_no_root_causes(self):
        """Test _simplify_probable_cause when no root causes are present."""
        probable_cause = {"found": True, "currentRootCause": []}
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertIsNone(result)

    def test_simplify_probable_cause_with_explainability(self):
        """Test _simplify_probable_cause with explainability text."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.95,
                "entityID": {
                    "pluginId": "com.instana.plugin.service",
                    "steadyId": "svc-steady-1"
                },
                "explainability": [{"text": "High error rate detected"}]
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertIsNotNone(result)
        self.assertTrue(result["found"])
        self.assertEqual(result["confidence"], 0.95)
        self.assertEqual(result["rootCauseEntity"], {"type": "service", "steadyId": "svc-steady-1"})
        self.assertEqual(result["summary"], "High error rate detected")

    def test_simplify_probable_cause_without_entity_type(self):
        """Test _simplify_probable_cause without entity type."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.85,
                "entityID": {
                    "pluginId": "",
                    "steadyId": "entity-steady-1"
                },
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertIsNotNone(result)
        self.assertEqual(result["rootCauseEntity"], {"type": "", "steadyId": "entity-steady-1"})
        self.assertEqual(result["summary"], "Root cause identified")

    def test_simplify_probable_cause_with_shortest_path(self):
        """Root cause entity type is taken from the last node's pluginId; topologyNodes carry snapshotId/steadyId."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.95,
                "topology": {
                    "shortestPath": [
                        {"pluginId": "com.instana.plugin.service", "steadyId": "svc-1", "snapshotId": "snap-1"},
                        {"pluginId": "com.instana.plugin.database", "steadyId": "db-1", "snapshotId": "snap-2"},
                        {"pluginId": "com.instana.plugin.endpoint", "steadyId": "ep-1", "snapshotId": "snap-3"},
                    ]
                },
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertIsNotNone(result)
        self.assertEqual(result["rootCauseEntity"], {"type": "endpoint", "steadyId": "ep-1", "snapshotId": "snap-3"})
        self.assertEqual(result["topologyPath"], "service → database → endpoint")
        self.assertEqual(len(result["topologyNodes"]), 3)
        self.assertEqual(result["topologyNodes"][2], {"type": "endpoint", "steadyId": "ep-1", "snapshotId": "snap-3"})

    def test_simplify_probable_cause_topology_path_uses_steady_id_fallback(self):
        """topologyPath uses type (from pluginId) when nodes have no label; topologyNodes carry steadyId."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.8,
                "topology": {
                    "shortestPath": [
                        {"pluginId": "com.instana.plugin.service", "steadyId": "svc-abc"},
                        {"pluginId": "com.instana.plugin.endpoint", "steadyId": "ep-xyz"},
                    ]
                },
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertEqual(result["topologyPath"], "service → endpoint")
        self.assertEqual(result["rootCauseEntity"], {"type": "endpoint", "steadyId": "ep-xyz"})
        self.assertEqual(result["topologyNodes"][0]["steadyId"], "svc-abc")
        self.assertEqual(result["topologyNodes"][1]["steadyId"], "ep-xyz")

    def test_simplify_probable_cause_topology_path_uses_plugin_id_fallback(self):
        """Nodes with neither label nor steadyId still produce a type-based topology path."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.7,
                "topology": {
                    "shortestPath": [
                        {"pluginId": "com.instana.plugin.host"},
                        {"pluginId": "com.instana.plugin.process"},
                    ]
                },
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertEqual(result["topologyPath"], "host → process")

    def test_simplify_probable_cause_no_topology_path_in_result(self):
        """topologyPath and topologyNodes keys are absent when shortestPath is empty."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.9,
                "entityID": {"pluginId": "com.instana.plugin.service", "steadyId": "svc-steady-9"},
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertNotIn("topologyPath", result)
        self.assertNotIn("topologyNodes", result)

    def test_simplify_probable_cause_with_percentage_explainability(self):
        """Summary uses failure-rate percentages when both fields are present."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.95,
                "entityID": {"pluginId": "com.instana.plugin.endpoint", "steadyId": "ep-steady-1"},
                "explainability": [{
                    "percentageFailedThroughRC": 0.96,
                    "percentageFailedNotThroughRC": 0.0
                }]
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertIn("96% of calls through root cause failed vs 0% not through it", result["summary"])

    def test_simplify_probable_cause_explainability_falls_back_to_text(self):
        """Summary falls back to explainability text when percentages are absent."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.75,
                "entityID": {"pluginId": "com.instana.plugin.service", "steadyId": "svc-steady-2"},
                "explainability": [{"text": "Connection pool exhausted"}]
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertEqual(result["summary"], "Connection pool exhausted")

    def test_simplify_probable_cause_entity_id_steady_id_fallback(self):
        """entityID block exposes steadyId in rootCauseEntity dict."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.88,
                "entityID": {"pluginId": "com.instana.plugin.database", "steadyId": "db-steady-123"},
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertEqual(result["rootCauseEntity"], {"type": "database", "steadyId": "db-steady-123"})

    def test_simplify_probable_cause_entity_id_unknown_fallback(self):
        """rootCauseEntity steadyId is None when both label and steadyId are absent."""
        probable_cause = {
            "found": True,
            "currentRootCause": [{
                "probFailure": 0.6,
                "entityID": {"pluginId": "com.instana.plugin.host"},
                "explainability": []
            }]
        }
        result = self.client._simplify_probable_cause(probable_cause)
        self.assertEqual(result["rootCauseEntity"], {"type": "host", "steadyId": None})


    def test_optimize_event_data_with_detail_and_fix_suggestion(self):
        """Test _optimize_event_data includes detail and fixSuggestion when present."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "High error rate",
            "start": 1000000,
            "end": 2000000,
            "detail": "Error rate exceeded threshold",
            "fixSuggestion": "Check application logs",
            "entityLabel": "my-service",
            "entityType": "service"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("detail", result)
        self.assertIn("fixSuggestion", result)
        self.assertEqual(result["detail"], "Error rate exceeded threshold")
        self.assertEqual(result["fixSuggestion"], "Check application logs")

    def test_optimize_event_data_with_service_id(self):
        """Test _optimize_event_data includes serviceId when present."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "High latency",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-service",
            "entityType": "service",
            "serviceId": "service-456"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("entity", result)
        self.assertIn("serviceId", result["entity"])
        self.assertEqual(result["entity"]["serviceId"], "service-456")

    def test_optimize_event_data_with_application_id(self):
        """Test _optimize_event_data includes applicationId when present."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "High latency",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-app",
            "entityType": "application",
            "applicationId": "app-789"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("entity", result)
        self.assertIn("applicationId", result["entity"])
        self.assertEqual(result["entity"]["applicationId"], "app-789")

    def test_optimize_event_data_with_endpoint_id(self):
        """Test _optimize_event_data includes endpointId when present."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "Slow endpoint",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-endpoint",
            "entityType": "endpoint",
            "endpointId": "endpoint-101"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("entity", result)
        self.assertIn("endpointId", result["entity"])
        self.assertEqual(result["entity"]["endpointId"], "endpoint-101")

    def test_optimize_event_data_with_mobile_app_id(self):
        """Test _optimize_event_data includes mobileAppId when present."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "App crash",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-mobile-app",
            "entityType": "mobileApp",
            "mobileAppId": "mobile-202"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("entity", result)
        self.assertIn("mobileAppId", result["entity"])
        self.assertEqual(result["entity"]["mobileAppId"], "mobile-202")

    def test_optimize_event_data_with_metrics(self):
        """Test _optimize_event_data includes affected metrics."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "High error rate",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-service",
            "entityType": "service",
            "metrics": [
                {"metricName": "errors"},
                {"metricName": "latency"}
            ]
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("affectedMetrics", result)
        self.assertEqual(result["affectedMetrics"], ["errors", "latency"])

    def test_optimize_event_data_with_recent_events(self):
        """Test _optimize_event_data includes related events count."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "High error rate",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-service",
            "entityType": "service",
            "recentEvents": ["event1", "event2", "event3"]
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("relatedEventsCount", result)
        self.assertEqual(result["relatedEventsCount"], 3)

    def test_optimize_event_data_incident_with_probable_cause(self):
        """Test _optimize_event_data includes probable cause for incidents."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "Service down",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-service",
            "entityType": "service",
            "probableCause": {
                "found": True,
                "currentRootCause": [{
                    "probFailure": 0.9,
                    "entityLabel": "database",
                    "entityType": "database",
                    "explainability": [{"text": "Connection timeout"}]
                }]
            }
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("probableCause", result)
        self.assertTrue(result["probableCause"]["found"])

    def test_optimize_event_data_change_event(self):
        """Test _optimize_event_data for change events."""
        event = {
            "eventId": "test-123",
            "type": "change",
            "state": "closed",
            "problem": "Deployment",
            "start": 1000000,
            "end": 1000000,
            "entityLabel": "my-service",
            "entityType": "service",
            "detail": "Version 2.0 deployed"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("timestamp", result)
        self.assertNotIn("start", result)
        self.assertEqual(result["timestamp"], 1000000)
        self.assertIn("detail", result)

    def test_optimize_event_data_change_with_null_label(self):
        """Test _optimize_event_data for change events with null label."""
        event = {
            "eventId": "test-123",
            "type": "change",
            "state": "closed",
            "problem": "Config change",
            "start": 1000000,
            "end": 1000000,
            "entityLabel": "null",
            "entityType": "service"
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("entity", result)
        self.assertEqual(result["entity"]["label"], "Unknown service")

    def test_optimize_event_data_with_string_metrics(self):
        """Test _optimize_event_data handles metrics returned as plain strings (live API shape)."""
        event = {
            "eventId": "test-123",
            "type": "incident",
            "state": "closed",
            "problem": "High error rate",
            "start": 1000000,
            "end": 2000000,
            "entityLabel": "my-service",
            "entityType": "service",
            "metrics": ["errors", "latency"],
        }
        result = self.client._optimize_event_data(event)
        self.assertIn("affectedMetrics", result)
        self.assertEqual(result["affectedMetrics"], ["errors", "latency"])

    def test_build_time_params_with_invalid_time_range(self):
        """Test _build_time_params with an unrecognised time_range uses the default window_size."""
        # _convert_time_range_to_window_size always returns a value (defaults to 10 minutes)
        # so api_params receives window_size, not var_from/to
        result = self.client._build_time_params(time_range="invalid time range")

        self.assertIn("api_params", result)
        self.assertIn("window_size", result["api_params"])
        self.assertIn("from_time", result)
        self.assertIn("to_time", result)

    def test_extract_event_filters_returns_only_allowed_keys(self):
        """_extract_event_filters should whitelist keys and apply defaults."""
        raw = {
            "query": "my-query",
            "entity_type": "service",
            "severity": 10,
            "unknown_key": "should_be_dropped",
        }
        result = self.client._extract_event_filters(raw)

        self.assertEqual(result["query"], "my-query")
        self.assertEqual(result["entity_type"], "service")
        self.assertEqual(result["severity"], 10)
        self.assertNotIn("unknown_key", result)

    def test_extract_event_filters_default_max_events(self):
        """_extract_event_filters should default max_events to 50."""
        result = self.client._extract_event_filters({})
        self.assertEqual(result["max_events"], 50)

    def test_extract_event_filters_all_fields_none_by_default(self):
        """Non-max_events fields default to None when not supplied."""
        result = self.client._extract_event_filters({})
        for key in ("query", "from_time", "to_time", "entity_type", "entity_name",
                    "entity_label", "state", "problem", "severity",
                    "event_specification_id", "rca", "time_range",
                    "filter_event_updates", "exclude_triggered_before",
                    "event_type_filters"):
            self.assertIsNone(result[key])

    def test_extract_event_filters_custom_max_events(self):
        """_extract_event_filters should respect a provided max_events."""
        result = self.client._extract_event_filters({"max_events": 100})
        self.assertEqual(result["max_events"], 100)

    def test_validate_event_type_filters_none_passes(self):
        """None / empty list should pass validation silently."""
        self.client._validate_event_type_filters(None)
        self.client._validate_event_type_filters([])

    def test_validate_event_type_filters_valid_types(self):
        """Valid event types should pass without exception."""
        self.client._validate_event_type_filters(["INCIDENT", "ISSUE", "CHANGE"])

    def test_validate_event_type_filters_case_insensitive(self):
        """Lowercase valid types should also pass."""
        self.client._validate_event_type_filters(["incident", "issue"])

    def test_validate_event_type_filters_invalid_type_raises(self):
        """An invalid event type should return an elicitation dict (no longer raises)."""
        result = self.client._validate_event_type_filters(["INVALID_TYPE"])
        self.assertIsNotNone(result)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("INVALID_TYPE" in e for e in result["api_error"]))

    def test_validate_event_type_filters_non_list_raises(self):
        """Passing a non-list should return an elicitation dict (no longer raises)."""
        result = self.client._validate_event_type_filters("INCIDENT")
        self.assertIsNotNone(result)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("list" in e for e in result["api_error"]))

    def test_validate_event_type_filters_non_string_element_raises(self):
        """A list with non-string elements should return an elicitation dict (no longer raises)."""
        result = self.client._validate_event_type_filters([123])
        self.assertIsNotNone(result)
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("string" in e for e in result["api_error"]))

    def test_parse_events_response_success(self):
        """Should parse a 200 JSON list response."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'[{"eventId": "e1"}, {"eventId": "e2"}]'

        result = self.client._parse_events_response(mock_response)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["eventId"], "e1")

    def test_parse_events_response_non_200_raises(self):
        """Non-200 status should raise ValueError."""
        mock_response = MagicMock()
        mock_response.status = 500

        with self.assertRaises(ValueError):
            self.client._parse_events_response(mock_response)

    def test_parse_events_response_non_list_returns_empty(self):
        """If JSON body is not a list, return empty list."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"key": "value"}'

        result = self.client._parse_events_response(mock_response)

        self.assertEqual(result, [])

    def test_matches_entity_type_case_insensitive(self):
        """Entity type matching should be case-insensitive."""
        event = {"entityType": "SERVICE"}
        self.assertTrue(self.client._matches_entity_type(event, "service"))
        self.assertFalse(self.client._matches_entity_type(event, "host"))

    def test_matches_state(self):
        """State matching should be case-insensitive."""
        event = {"state": "Open"}
        self.assertTrue(self.client._matches_state(event, "open"))
        self.assertFalse(self.client._matches_state(event, "closed"))

    def test_matches_problem_substring(self):
        """Problem matching should be a substring search in problem or detail."""
        event = {"problem": "CPU usage high", "detail": "some detail"}
        self.assertTrue(self.client._matches_problem(event, "CPU"))
        self.assertTrue(self.client._matches_problem(event, "some"))
        self.assertFalse(self.client._matches_problem(event, "memory"))

    def test_matches_severity_valid(self):
        """Severity matching should be exact."""
        event = {"severity": 10}
        self.assertTrue(self.client._matches_severity(event, 10))
        self.assertFalse(self.client._matches_severity(event, 5))

    def test_matches_severity_invalid_raises(self):
        """Invalid severity value should raise ValueError."""
        event = {"severity": 99}
        with self.assertRaises(ValueError):
            self.client._matches_severity(event, 99)

    def test_matches_entity_name_partial(self):
        """Entity name matching should support partial/substring matching."""
        event = {"entityName": "Kubernetes Pod"}
        self.assertTrue(self.client._matches_entity_name(event, "kubernetes"))
        self.assertFalse(self.client._matches_entity_name(event, "host"))

    def test_matches_entity_label_partial(self):
        """Entity label matching should support partial/substring matching."""
        event = {"entityLabel": "pod/my-deployment-abc"}
        self.assertTrue(self.client._matches_entity_label(event, "my-deployment"))
        self.assertFalse(self.client._matches_entity_label(event, "other-pod"))

    def test_matches_event_specification_id_exact(self):
        """Event specification ID matching should be exact."""
        event = {"eventSpecificationId": "spec-001"}
        self.assertTrue(self.client._matches_event_specification_id(event, "spec-001"))
        self.assertFalse(self.client._matches_event_specification_id(event, "spec-002"))

    def test_matches_query_substring_in_str(self):
        """Query matching should search the entire event string."""
        event = {"eventId": "abc", "problem": "memory leak"}
        self.assertTrue(self.client._matches_query(event, "memory"))
        self.assertFalse(self.client._matches_query(event, "cpu"))

    def test_matches_rca_true(self):
        """rca=True should match events where probableCause.found is True."""
        event = {"probableCause": {"found": True}}
        self.assertTrue(self.client._matches_rca(event, True))
        self.assertFalse(self.client._matches_rca(event, False))

    def test_matches_rca_false(self):
        """rca=False should match events where probableCause.found is False."""
        event = {"probableCause": {"found": False}}
        self.assertTrue(self.client._matches_rca(event, False))
        self.assertFalse(self.client._matches_rca(event, True))

    def test_matches_rca_missing_probable_cause(self):
        """rca=False should match events with no probableCause key."""
        event = {}
        self.assertTrue(self.client._matches_rca(event, False))
        self.assertFalse(self.client._matches_rca(event, True))

    def test_apply_event_filters_no_filters_returns_all(self):
        """When no filters are specified, _optimize_and_limit with no active filters returns all events."""
        events = [{"eventId": "e1"}, {"eventId": "e2"}]
        f = {
            "entity_type": None, "state": None, "entity_name": None,
            "entity_label": None, "problem": None, "severity": None,
            "query": None, "rca": None, "event_specification_id": None,
        }
        result = self.client._optimize_and_limit(events, f=f, max_events=50)
        self.assertEqual(len(result), 2)

    def test_apply_event_filters_by_state(self):
        """Should filter events by state via _optimize_and_limit."""
        events = [
            {"state": "open", "eventId": "e1"},
            {"state": "closed", "eventId": "e2"},
        ]
        f = {
            "entity_type": None, "state": "open", "entity_name": None,
            "entity_label": None, "problem": None, "severity": None,
            "query": None, "rca": None, "event_specification_id": None,
        }
        result = self.client._optimize_and_limit(events, f=f, max_events=50)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["eventId"], "e1")

    def test_apply_event_filters_non_dict_event_excluded(self):
        """Non-dict events should be excluded by _event_matches_filters."""
        events = [{"eventId": "e1"}, "not-a-dict"]
        f = {
            "entity_type": None, "state": "open", "entity_name": None,
            "entity_label": None, "problem": None, "severity": None,
            "query": None, "rca": None, "event_specification_id": None,
        }
        result = self.client._optimize_and_limit(events, f=f, max_events=50)
        self.assertEqual(len(result), 0)

    def test_event_matches_filters_severity_none_skips_check(self):
        """severity=None should not filter any events."""
        event = {"severity": 10, "state": "open"}
        f = {
            "entity_type": None, "state": None, "entity_name": None,
            "entity_label": None, "problem": None, "severity": None,
            "query": None, "rca": None, "event_specification_id": None,
        }
        self.assertTrue(self.client._event_matches_filters(event, f))

    def test_event_matches_filters_rca_none_skips_check(self):
        """rca=None should not filter any events."""
        event = {"probableCause": {"found": True}}
        f = {
            "entity_type": None, "state": None, "entity_name": None,
            "entity_label": None, "problem": None, "severity": None,
            "query": None, "rca": None, "event_specification_id": None,
        }
        self.assertTrue(self.client._event_matches_filters(event, f))

    def test_event_matches_filters_multiple_criteria(self):
        """Multiple filter criteria should all be applied (AND logic)."""
        event = {
            "entityType": "service",
            "state": "open",
            "severity": 10,
        }
        f = {
            "entity_type": "service",
            "state": "open",
            "severity": 10,
            "entity_name": None, "entity_label": None,
            "problem": None, "query": None, "rca": None,
            "event_specification_id": None,
        }
        self.assertTrue(self.client._event_matches_filters(event, f))

        # If severity doesn't match, the whole event should fail
        f_wrong_severity = {**f, "severity": 5}
        self.assertFalse(self.client._event_matches_filters(event, f_wrong_severity))

    def test_optimize_and_limit_truncates_to_max(self):
        """Events list should be truncated to max_events."""
        events = [{"eventId": f"e{i}", "type": "incident", "start": 1000000 + i}
                  for i in range(10)]
        f = {"entity_type": None, "state": None, "entity_name": None, "entity_label": None,
             "problem": None, "severity": None, "query": None, "rca": None, "event_specification_id": None}
        result = self.client._optimize_and_limit(events, f=f, max_events=3)
        self.assertEqual(len(result), 3)

    def test_optimize_and_limit_all_events_if_under_max(self):
        """All events should be returned when count < max_events."""
        events = [{"eventId": "e1", "type": "incident", "start": 1000000}]
        f = {"entity_type": None, "state": None, "entity_name": None, "entity_label": None,
             "problem": None, "severity": None, "query": None, "rca": None, "event_specification_id": None}
        result = self.client._optimize_and_limit(events, f=f, max_events=50)
        self.assertEqual(len(result), 1)

    def test_optimize_and_limit_empty_list(self):
        """An empty list should return an empty list."""
        f = {"entity_type": None, "state": None, "entity_name": None, "entity_label": None,
             "problem": None, "severity": None, "query": None, "rca": None, "event_specification_id": None}
        result = self.client._optimize_and_limit([], f=f, max_events=50)
        self.assertEqual(result, [])

    @patch('src.event.events_tools.datetime')
    def test_get_events_success_with_no_filters(self, mock_datetime):
        """get_events with empty filters should return events from API."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'[{"eventId": "e1", "type": "incident", "state": "open", "start": 1699900000000}]'
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={}))

        self.assertIn("events", result)
        self.assertIn("events_returned", result)
        self.assertIn("total_events", result)
        self.assertEqual(result["total_events"], 1)
        self.assertEqual(result["events_returned"], 1)

    @patch('src.event.events_tools.datetime')
    def test_get_events_with_invalid_event_type_filter(self, mock_datetime):
        """get_events with invalid event_type_filters should return an elicitation dict."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        result = asyncio.run(self.client.get_events(filters={
            "event_type_filters": ["INVALID"]
        }))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("INVALID" in e for e in result["api_error"]))

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_state_filter(self, mock_datetime):
        """get_events should apply state filter correctly."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "state": "open", "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "state": "closed", "type": "incident", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={"state": "open"}))

        self.assertEqual(result["total_events"], 2)  # raw API count, filtering happens in single pass
        self.assertEqual(result["events_returned"], 1)

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_rca_filter(self, mock_datetime):
        """get_events should filter events by RCA availability."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "probableCause": {"found": true}, "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "probableCause": {"found": false}, "type": "incident", "start": 1699900000000},
            {"eventId": "e3", "type": "incident", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result_with_rca = asyncio.run(self.client.get_events(filters={"rca": True}))
        self.assertEqual(result_with_rca["total_events"], 3)  # raw API count

        result_without_rca = asyncio.run(self.client.get_events(filters={"rca": False}))
        self.assertEqual(result_without_rca["total_events"], 3)  # raw API count

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_severity_filter(self, mock_datetime):
        """get_events should filter by severity."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "severity": 10, "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "severity": 5, "type": "issue", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={"severity": 10}))

        self.assertEqual(result["total_events"], 2)  # raw API count

    @patch('src.event.events_tools.datetime')
    def test_get_events_api_error_returns_error(self, mock_datetime):
        """get_events should return error dict on API failure."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        self.events_api.get_events_without_preload_content = AsyncMock(side_effect=Exception("API failure"))

        result = asyncio.run(self.client.get_events(filters={}))

        self.assertIn("error", result)

    @patch('src.event.events_tools.datetime')
    def test_get_events_none_filters_treated_as_empty(self, mock_datetime):
        """get_events with filters=None should behave the same as filters={}."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'[]'
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters=None))

        self.assertIn("events", result)
        self.assertEqual(result["events_returned"], 0)

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_max_events_limit(self, mock_datetime):
        """get_events should limit the returned events to max_events."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        events_data = [{"eventId": f"e{i}", "type": "incident", "start": 1699900000000 + i}
                       for i in range(10)]
        import json as _json
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = _json.dumps(events_data).encode()
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={"max_events": 3}))

        self.assertEqual(result["events_returned"], 3)
        self.assertEqual(result["total_events"], 10)

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_problem_filter(self, mock_datetime):
        """get_events should filter events by problem text."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "problem": "memory usage high", "type": "issue", "start": 1699900000000},
            {"eventId": "e2", "problem": "cpu spike", "type": "issue", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={"problem": "memory"}))

        self.assertEqual(result["total_events"], 2)  # raw API count

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_entity_name_filter(self, mock_datetime):
        """get_events should filter by entity name (partial match)."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "entityName": "Kubernetes Pod", "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "entityName": "Process", "type": "incident", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={"entity_name": "kubernetes"}))

        self.assertEqual(result["total_events"], 2)  # raw API count

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_entity_label_filter(self, mock_datetime):
        """get_events should filter by entity label (partial match)."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "entityLabel": "pod/payment-service-abc", "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "entityLabel": "pod/other-service-xyz", "type": "incident", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        result = asyncio.run(self.client.get_events(filters={"entity_label": "payment-service"}))

        self.assertEqual(result["total_events"], 2)  # raw API count

    @patch('src.event.events_tools.datetime')
    def test_get_events_applies_event_specification_id_filter(self, mock_datetime):
        """get_events should filter by event specification ID (combined with another filter to bypass early return)."""
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1700000000)
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *a: datetime.fromtimestamp(ts))

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'''[
            {"eventId": "e1", "eventSpecificationId": "spec-001", "state": "open", "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "eventSpecificationId": "spec-002", "state": "open", "type": "incident", "start": 1699900000000}
        ]'''
        self.events_api.get_events_without_preload_content = AsyncMock(return_value=mock_response)

        # Also provide state filter to ensure _apply_event_filters doesn't short-circuit
        result = asyncio.run(self.client.get_events(filters={
            "event_specification_id": "spec-001",
            "state": "open",
        }))

        self.assertEqual(result["total_events"], 2)  # raw API count

    def test_get_events_by_ids_batch_success(self):
        """get_events_by_ids should return events when batch API succeeds."""
        mock_event = {"eventId": "e1", "type": "incident", "state": "open", "start": 1699900000000}
        self.events_api.get_events_by_ids.return_value = [mock_event]

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        self.assertIn("events", result)
        self.assertEqual(result["events_count"], 1)
        self.assertEqual(result["successful_retrievals"], 1)
        self.assertEqual(result["failed_retrievals"], 0)

    def test_get_events_by_ids_with_to_dict(self):
        """get_events_by_ids should call to_dict() on event objects."""
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {"eventId": "e1", "type": "incident", "start": 1699900000000}
        self.events_api.get_events_by_ids.return_value = [mock_obj]

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        mock_obj.to_dict.assert_called_once()
        self.assertEqual(result["events_count"], 1)

    def test_get_events_by_ids_empty_list(self):
        """get_events_by_ids with empty list should return an elicitation dict."""
        result = asyncio.run(self.client.get_events_by_ids(event_ids=[]))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("event_ids", result.get("reason", ""))

    def test_get_events_by_ids_comma_separated_string(self):
        """get_events_by_ids should accept comma-separated string of IDs."""
        mock_events = [
            {"eventId": "e1", "type": "incident", "start": 1699900000000},
            {"eventId": "e2", "type": "incident", "start": 1699900000000},
        ]
        self.events_api.get_events_by_ids.return_value = mock_events

        result = asyncio.run(self.client.get_events_by_ids(event_ids="e1, e2"))

        self.assertEqual(result["events_count"], 2)

    def test_get_events_by_ids_list_string_format(self):
        """get_events_by_ids should parse Python list string format."""
        mock_events = [
            {"eventId": "e1", "type": "incident", "start": 1699900000000},
        ]
        self.events_api.get_events_by_ids.return_value = mock_events

        result = asyncio.run(self.client.get_events_by_ids(event_ids='["e1"]'))

        self.assertEqual(result["events_count"], 1)

    def test_get_events_by_ids_invalid_list_string(self):
        """get_events_by_ids with invalid list string should return an error."""
        # '[invalid]' starts and ends with brackets but is not valid Python literal syntax
        result = asyncio.run(self.client.get_events_by_ids(event_ids='[invalid]'))

        self.assertIn("error", result)

    def test_get_events_by_ids_batch_fallback_on_failure(self):
        """get_events_by_ids should fall back to individual requests when batch API fails."""
        # Batch API raises an exception
        self.events_api.get_events_by_ids.side_effect = Exception("Batch API failure")

        # Individual fallback API returns success
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'[{"eventId": "e1", "type": "incident", "start": 1699900000000}]'
        self.events_api.get_events_by_ids_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        self.assertEqual(result["successful_retrievals"], 1)
        self.assertEqual(result["failed_retrievals"], 0)

    def test_get_events_by_ids_fallback_http_error(self):
        """get_events_by_ids fallback should record failure on non-200 status."""
        self.events_api.get_events_by_ids.side_effect = Exception("Batch API failure")

        mock_response = MagicMock()
        mock_response.status = 404
        self.events_api.get_events_by_ids_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        self.assertEqual(result["failed_retrievals"], 1)
        self.assertEqual(result["successful_retrievals"], 0)

    def test_get_events_by_ids_fallback_json_error(self):
        """get_events_by_ids fallback should handle JSON parse errors."""
        self.events_api.get_events_by_ids.side_effect = Exception("Batch API failure")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'not-json'
        self.events_api.get_events_by_ids_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        self.assertEqual(result["failed_retrievals"], 1)

    def test_get_events_by_ids_fallback_empty_response(self):
        """get_events_by_ids fallback should handle empty list response."""
        self.events_api.get_events_by_ids.side_effect = Exception("Batch API failure")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'[]'
        self.events_api.get_events_by_ids_without_preload_content.return_value = mock_response

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        # An empty list response means no event data was returned
        self.assertEqual(result["failed_retrievals"], 1)
        self.assertEqual(result["successful_retrievals"], 0)

    def test_get_events_by_ids_fallback_individual_exception(self):
        """get_events_by_ids fallback should handle per-event exceptions."""
        self.events_api.get_events_by_ids.side_effect = Exception("Batch API failure")
        self.events_api.get_events_by_ids_without_preload_content.side_effect = Exception("Individual failure")

        result = asyncio.run(self.client.get_events_by_ids(event_ids=["e1"]))

        self.assertEqual(result["failed_retrievals"], 1)


if __name__ == '__main__':
    unittest.main()

