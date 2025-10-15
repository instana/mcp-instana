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

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get event", result["error"])

    def test_get_event_empty_id(self):
        """Test get_event with empty event_id"""
        # Call the method with empty event_id and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=""))

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "event_id parameter is required")

    def test_get_event_404_error(self):
        """Test get_event with 404 error"""
        # Create a mock error with status attribute
        class MockError(Exception):
            def __init__(self):
                self.status = 404

        mock_error = MockError()

        # Set up the mock to raise the error
        event_id = "nonexistent_id"
        self.events_api.get_event.side_effect = mock_error

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], f"Event with ID {event_id} not found")
        self.assertEqual(result["event_id"], event_id)

    def test_get_event_401_error(self):
        """Test get_event with 401 error"""
        # Create a mock error with status attribute
        class MockError(Exception):
            def __init__(self):
                self.status = 401

        mock_error = MockError()

        # Set up the mock to raise the error
        event_id = "test_id"
        self.events_api.get_event.side_effect = mock_error

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Authentication failed. Please check your API token and permissions.")

    def test_get_event_fallback_success(self):
        """Test get_event fallback approach success"""
        # Set up the mock to raise an exception for standard API
        event_id = "test_event_id"
        self.events_api.get_event.side_effect = Exception("Test error")

        # Set up the mock response for fallback approach
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'{"eventId": "test_event_id", "data": "fallback_data"}'
        self.events_api.get_event_without_preload_content.return_value = mock_response

        # Call the method
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the fallback approach was used
        self.events_api.get_event_without_preload_content.assert_called_once_with(event_id=event_id)

        # Check that the result contains the expected data
        self.assertEqual(result["eventId"], "test_event_id")
        self.assertEqual(result["data"], "fallback_data")

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

        # Check that the result contains the expected error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to get event: HTTP 404")
        self.assertEqual(result["event_id"], event_id)

    def test_get_event_fallback_json_error(self):
        """Test get_event fallback approach with JSON decode error"""
        # Set up the mock to raise an exception for standard API
        event_id = "test_event_id"
        self.events_api.get_event.side_effect = Exception("Test error")

        # Set up the mock response for fallback approach with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.events_api.get_event_without_preload_content.return_value = mock_response

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
        self.assertIn("error", result)
        self.assertIn("Failed to parse JSON response", result["error"])
        self.assertEqual(result["event_id"], event_id)

    def test_get_event_fallback_error(self):
        """Test get_event fallback approach with error"""
        # Set up the mock to raise an exception for standard API
        event_id = "test_event_id"
        self.events_api.get_event.side_effect = Exception("Test error")

        # Set up the mock to raise an exception for fallback approach
        self.events_api.get_event_without_preload_content.side_effect = Exception("Fallback error")

        # Call the method and store result for assertions
        result = asyncio.run(self.client.get_event(event_id=event_id))

        # Check that the result contains the expected error message
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

        # Set up the mock to return the events
        self.events_api.kubernetes_info_events = MagicMock(return_value=[mock_event1, mock_event2])

        # Call the method with minimal parameters
        result = asyncio.run(self.client.get_kubernetes_info_events())

        # Check that the mock was called with the correct arguments
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier

        self.events_api.kubernetes_info_events.assert_called_once_with(
            var_from=expected_from_time,
            to=expected_to_time,
            window_size=50,
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
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (2 * 24 * 60 * 60 * 1000)  # 2 days earlier

        self.events_api.kubernetes_info_events.assert_called_once_with(
            var_from=expected_from_time,
            to=expected_to_time,
            window_size=50,
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
        # Default time range should be 24 hours as per _process_time_range
        expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
        expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier

        self.events_api.agent_monitoring_events.assert_called_once_with(
            var_from=expected_from_time,
            to=expected_to_time,
            window_size=50,
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

            # Call the method with the time range (result used in assertion via mock call)
            _ = asyncio.run(self.client.get_kubernetes_info_events(time_range=time_range))

            # Check that the mock was called with the correct arguments
            self.events_api.kubernetes_info_events.assert_called_once_with(
                var_from=expected_from_times[i],
                to=1000 * 1000,
                window_size=50,
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
        self.assertIn("error", result)
        self.assertIn("Failed to get agent monitoring events", result["error"])

    # Tests for get_changes method
    @patch('src.event.events_tools.datetime')
    def test_get_changes_method_success(self, mock_datetime):
        """Test get_changes method with successful response"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response for get_events_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='''[
            {
                "eventId": "change1",
                "eventType": "change",
                "changeType": "deployment",
                "start": 900000
            },
            {
                "eventId": "change2",
                "eventType": "change",
                "changeType": "configuration",
                "start": 950000
            }
        ]''')

        # Mock the API client method used in get_changes
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the get_changes method
        result = asyncio.run(self.client.get_changes())

        # Assertions
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 2)
        self.assertEqual(result["events_count"], 2)
        self.assertEqual(result["events"][0]["eventId"], "change1")
        self.assertEqual(result["events"][1]["eventId"], "change2")

        # Verify the API call was made with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # Corrected to match actual call
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=100,     # default size
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["change"]
        )

    def test_get_changes_method_error(self):
        """Test get_changes method with API error"""
        # Set up the mock to raise an exception
        self.events_api.get_events.side_effect = Exception("API error")

        # Call the get_changes method directly and store result for assertions
        result = asyncio.run(self.client.get_changes())
        self.assertIn("error", result)
        self.assertIn("Failed to get change events", result["error"])

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

    # Additional tests for error handling and edge cases
    @patch('src.event.events_tools.datetime')
    def test_get_issues_with_exception_in_processing(self, mock_datetime):
        """Test get_issues method with exception during event processing"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response to simulate an exception during JSON parsing
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='invalid_json')  # Triggers JSONDecodeError

        # Mock the API client method used in get_issues
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the get_issues method
        result = asyncio.run(self.client.get_issues())

        # Check that the method handled the exception and returned an error
        self.assertIn("error", result)
        self.assertIn("Failed to get issue events", result["error"])
        self.assertIn("Expecting value", result["error"])  # Adjusted to match actual JSONDecodeError message

        # Verify the API call was made with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # 24-hour default, consistent with previous tests
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=100,     # default size
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["issue"]
        )

    @patch('src.event.events_tools.datetime')
    def test_get_incidents_with_exception_in_processing(self, mock_datetime):
        """Test get_incidents method with exception during event processing"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response to simulate an exception during JSON parsing
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='invalid_json')  # Triggers JSONDecodeError

        # Mock the API client method used in get_incidents
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the get_incidents method
        result = asyncio.run(self.client.get_incidents())

        # Check that the method handled the exception and returned an error
        self.assertIn("error", result)
        self.assertIn("Failed to get incident events", result["error"])
        self.assertIn("Expecting value", result["error"])  # Adjusted to match actual JSONDecodeError message

        # Verify the API call was made with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # 24-hour default, consistent with previous tests
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=100,     # default size
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["incident"]
        )

    # Test for import error handling
    def test_import_error_handling(self):
        """Test import error handling in the module"""
        # Create a client instance with test values
        client = AgentMonitoringEventsMCPTools(read_token="test_token", base_url="https://test.instana.io")

        # Simulate an import error by setting the events_api attribute to None
        client.events_api = None

        # Call a method that would use the events_api
        result = asyncio.run(client.get_issues())

        # Check that the result contains an error message
        self.assertIn("error", result)
        self.assertIn("Failed to get issue events", result["error"])  # Corrected to match implementation
        self.assertIn("'NoneType' object has no attribute", result["error"])

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

            # Check that default values were used (24 hours)
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier

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
            self.assertIn("error", result)
            self.assertIn("CustomEvent", result["error"])

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

            # Check that from_time was set to 1 hour before to_time
            self.events_api.agent_monitoring_events.assert_called_once()
            call_args = self.events_api.agent_monitoring_events.call_args[1]
            self.assertEqual(call_args['to'], to_time)
            # The default from_time is 24 hours before to_time, not 1 hour
            self.assertEqual(call_args['var_from'], to_time - (24 * 60 * 60 * 1000))  # 24 hours in milliseconds

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
            self.assertIn("error", result)
            self.assertIn("CustomEvent", result["error"])

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

    # Additional tests for edge cases
    @patch('src.event.events_tools.datetime')
    def test_get_issues_with_severity_filtering(self, mock_datetime):
        """Test get_issues method with severity filtering"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response for get_events_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='''[
            {
                "eventId": "issue1",
                "eventType": "issue",
                "severity": 10
            },
            {
                "eventId": "issue2",
                "eventType": "issue",
                "severity": 5
            },
            {
                "eventId": "issue3",
                "eventType": "issue",
                "severity": 1
            }
        ]''')

        # Mock the API client method used in get_issues
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the get_issues method with a query for severity filtering
        result = asyncio.run(self.client.get_issues(query="severity:5"))

        # Check that all events were included
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 3)
        self.assertEqual(result["events_count"], 3)

        # Check that the events are returned as provided by the API
        events = result["events"]
        self.assertEqual(events[0]["eventId"], "issue1")
        self.assertEqual(events[1]["eventId"], "issue2")
        self.assertEqual(events[2]["eventId"], "issue3")

        # Verify the API call was made with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # Corrected to match actual call (24 hours)
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=100,     # default size
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["issue"]
        )

    @patch('src.event.events_tools.datetime')
    def test_get_changes_with_missing_fields(self, mock_datetime):
        """Test get_changes method with missing fields"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response for get_events_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='''[
            {
                "eventId": "change1",
                "eventType": "change"
            }
        ]''')

        # Mock the API client method used in get_changes
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the get_changes method
        result = asyncio.run(self.client.get_changes())

        # Check that the event was processed correctly
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 1)
        self.assertEqual(result["events_count"], 1)

        # Check that the event has the expected fields
        event = result["events"][0]
        self.assertEqual(event["eventId"], "change1")
        self.assertEqual(event["eventType"], "change")
        self.assertNotIn("changeType", event)  # Verify missing field

        # Verify the API call was made with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # Corrected to match actual call (24 hours)
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=100,     # default size
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["change"]
        )

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

            # Check that default values were used (24 hours)
            expected_to_time = 1000 * 1000  # Convert seconds to milliseconds
            expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier

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

            # Check that from_time was set to 24 hours before to_time
            expected_from_time = to_time_value - (24 * 60 * 60 * 1000)  # 24 hours earlier

            self.assertEqual(from_time, expected_from_time)
            self.assertEqual(to_time, to_time_value)

    @patch('src.event.events_tools.datetime')
    def test_get_issues_with_size_parameter(self, mock_datetime):
        """Test get_issues with size parameter"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response for get_events_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='[]')  # Empty JSON array

        # Mock the API client method used in get_issues
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the method with size parameter
        size = 200
        result = asyncio.run(self.client.get_issues(size=size))

        # Check that the API was called with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once()
        call_args = self.events_api.get_events_without_preload_content.call_args[1]
        self.assertEqual(call_args['window_size'], size)

        # Check the result for correctness
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 0)
        self.assertEqual(result["events_count"], 0)

    @patch('src.event.events_tools.datetime')
    def test_get_incidents_with_size_parameter(self, mock_datetime):
        """Test get_incidents with size parameter"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response for get_events_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='[]')  # Empty JSON array

        # Mock the API client method used in get_incidents
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the method with size parameter
        size = 200
        result = asyncio.run(self.client.get_incidents(size=size))

        # Check that the API was called with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once()
        call_args = self.events_api.get_events_without_preload_content.call_args[1]
        self.assertEqual(call_args['window_size'], size)

        # Check the result for correctness
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 0)
        self.assertEqual(result["events_count"], 0)

        # Verify the API call parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # 24-hour default, consistent with previous tests
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=200,     # size parameter passed to get_incidents
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["incident"]
        )

    @patch('src.event.events_tools.datetime')
    def test_get_changes_with_size_parameter(self, mock_datetime):
        """Test get_changes with size parameter"""
        # Set up the mock datetime
        mock_now = MagicMock()
        mock_now.timestamp = MagicMock(return_value=1000)  # 1000 seconds since epoch
        mock_datetime.now = MagicMock(return_value=mock_now)
        mock_datetime.fromtimestamp = MagicMock(side_effect=lambda ts, *args: datetime.fromtimestamp(ts))

        # Set up the mock response for get_events_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data.decode = MagicMock(return_value='[]')  # Empty JSON array

        # Mock the API client method used in get_changes
        self.events_api.get_events_without_preload_content.return_value = mock_response

        # Call the method with size parameter
        size = 200
        result = asyncio.run(self.client.get_changes(size=size))

        # Check that the API was called with the correct parameters
        self.events_api.get_events_without_preload_content.assert_called_once()
        call_args = self.events_api.get_events_without_preload_content.call_args[1]
        self.assertEqual(call_args['window_size'], size)

        # Check the result for correctness
        self.assertIn("events", result)
        self.assertEqual(len(result["events"]), 0)
        self.assertEqual(result["events_count"], 0)

        # Verify the API call parameters
        self.events_api.get_events_without_preload_content.assert_called_once_with(
            var_from=-85400000,  # 24-hour default, consistent with previous tests
            to=1000000,          # 1000 seconds * 1000 (milliseconds)
            window_size=200,     # size parameter passed to get_incidents
            filter_event_updates=None,
            exclude_triggered_before=None,
            event_type_filters=["change"]
        )

