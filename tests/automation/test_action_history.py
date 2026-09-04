"""
Tests for Action History MCP Tools

This module contains tests for the automation action history tools.
"""

import asyncio
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

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the automation logger and replace its handlers
automation_logger = logging.getLogger('src.automation.action_history')
automation_logger.handlers = []
automation_logger.addHandler(NullHandler())
automation_logger.propagate = False  # Prevent logs from propagating to parent loggers

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
            # Just pass the API client directly from the instance
            if hasattr(self, 'action_history_api'):
                kwargs['api_client'] = self.action_history_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes BEFORE importing
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.action_history_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.action_instance_request'] = MagicMock()

# Set up mock classes
mock_action_history_api_class = MagicMock()
mock_action_instance_request_class = MagicMock()

# Add __name__ attribute to mock classes
mock_action_history_api_class.__name__ = "ActionHistoryApi"
mock_action_instance_request_class.__name__ = "ActionInstanceRequest"

sys.modules['instana_client.api.action_history_api'].ActionHistoryApi = mock_action_history_api_class
sys.modules['instana_client.models.action_instance_request'].ActionInstanceRequest = mock_action_instance_request_class

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.automation.action_history import ActionHistoryMCPTools

class TestActionHistoryMCPTools(unittest.TestCase):
    """Test class for ActionHistoryMCPTools"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_action_history_api_class.reset_mock()
        mock_action_instance_request_class.reset_mock()

        # Create a mock API client instance for this test
        self.action_history_api = MagicMock()

        # Create an instance of ActionHistoryMCPTools for testing
        self.action_history_tools = ActionHistoryMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        # Set up the client's API attribute
        self.action_history_tools.action_history_api = self.action_history_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.action_history_tools.read_token, "test_token")
        self.assertEqual(self.action_history_tools.base_url, "https://test.instana.com")

    def test_submit_automation_action_success(self):
        """Test successful submit_automation_action call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "instance123",
            "status": "SUBMITTED",
            "actionId": "action456",
            "hostId": "host789"
        }
        self.action_history_api.add_action_instance.return_value = mock_response

        # Test payload
        payload = {
            "hostId": "host789",
            "actionId": "action456",
            "async": "true",
            "timeout": "600"
        }

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the mock was called
        self.action_history_api.add_action_instance.assert_called_once()

        # Check that the result is correct
        self.assertIn("id", result)
        self.assertEqual(result["id"], "instance123")
        self.assertEqual(result["status"], "SUBMITTED")

    def test_submit_automation_action_missing_payload(self):
        """Test submit_automation_action with missing payload"""
        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=None,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("payload is required", (result.get("error") or result.get("message", "")))

    def test_submit_automation_action_string_payload(self):
        """Test submit_automation_action with string payload"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"id": "instance123"}
        self.action_history_api.add_action_instance.return_value = mock_response

        # Test with JSON string payload
        payload = '{"hostId": "host789", "actionId": "action456"}'

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result is correct
        self.assertIn("id", result)

    def test_submit_automation_action_string_payload_with_single_quotes(self):
        """Test submit_automation_action with string payload using single quotes"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"id": "instance123"}
        self.action_history_api.add_action_instance.return_value = mock_response

        # Test with Python dict string (single quotes)
        payload = "{'hostId': 'host789', 'actionId': 'action456'}"

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result is correct
        self.assertIn("id", result)

    def test_submit_automation_action_invalid_json_payload(self):
        """Test submit_automation_action with invalid JSON string payload"""
        # Test with invalid JSON string
        payload = '{invalid json}'

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_submit_automation_action_missing_required_field(self):
        """Test submit_automation_action with missing required field"""
        # Test payload without required 'hostId' field
        payload = {"actionId": "action456"}

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error about missing field
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("hostId", (result.get("error") or result.get("message", "")))

    def test_submit_automation_action_missing_action_id(self):
        """Test submit_automation_action with missing actionId field"""
        # Test payload without required 'actionId' field
        payload = {"hostId": "host789"}

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error about missing field
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("actionId", (result.get("error") or result.get("message", "")))

    def test_submit_automation_action_with_optional_fields(self):
        """Test submit_automation_action with optional fields"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"id": "instance123"}
        self.action_history_api.add_action_instance.return_value = mock_response

        # Test payload with optional fields
        payload = {
            "hostId": "host789",
            "actionId": "action456",
            "policyId": "policy123",
            "inputParameters": [
                {"name": "param1", "type": "string", "value": "value1"}
            ],
            "eventId": "event123",
            "async": "true",
            "timeout": "600"
        }

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result is correct
        self.assertIn("id", result)

    def test_submit_automation_action_error_handling(self):
        """Test error handling in submit_automation_action"""
        # Mock API client to raise an exception
        self.action_history_api.add_action_instance.side_effect = Exception("API Error")

        payload = {"hostId": "host789", "actionId": "action456"}

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_submit_automation_action_no_to_dict(self):
        """Test submit_automation_action when response has no to_dict method"""
        # Mock response without to_dict method
        self.action_history_api.add_action_instance.return_value = None

        payload = {"hostId": "host789", "actionId": "action456"}

        result = asyncio.run(self.action_history_tools.submit_automation_action(
            payload=payload,
            api_client=self.action_history_api
        ))

        # Check that the result contains success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_get_action_instance_details_success(self):
        """Test successful get_action_instance_details call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "instance123",
            "status": "SUCCESS",
            "actionId": "action456",
            "hostId": "host789",
            "startTime": 1234567890000,
            "endTime": 1234567900000
        }
        self.action_history_api.get_action_instance.return_value = mock_response

        result = asyncio.run(self.action_history_tools.get_action_instance_details(
            action_instance_id="instance123",
            api_client=self.action_history_api
        ))

        # Check that the mock was called with the correct arguments
        self.action_history_api.get_action_instance.assert_called_once_with(
            action_instance_id="instance123",
            window_size=None,
            to=None
        )

        # Check that the result is correct
        self.assertIn("id", result)
        self.assertEqual(result["id"], "instance123")
        self.assertEqual(result["status"], "SUCCESS")

    def test_get_action_instance_details_with_parameters(self):
        """Test get_action_instance_details with window_size and to parameters"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"id": "instance123"}
        self.action_history_api.get_action_instance.return_value = mock_response

        result = asyncio.run(self.action_history_tools.get_action_instance_details(
            action_instance_id="instance123",
            window_size=600000,
            to=1234567890000,
            api_client=self.action_history_api
        ))

        # Check that the mock was called with the correct arguments
        self.action_history_api.get_action_instance.assert_called_once_with(
            action_instance_id="instance123",
            window_size=600000,
            to=1234567890000
        )

        # Check that the result is correct
        self.assertIn("id", result)

    def test_get_action_instance_details_missing_id(self):
        """Test get_action_instance_details with missing action_instance_id"""
        result = asyncio.run(self.action_history_tools.get_action_instance_details(
            action_instance_id=None,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("action_instance_id is required", (result.get("error") or result.get("message", "")))

    def test_get_action_instance_details_error_handling(self):
        """Test error handling in get_action_instance_details"""
        # Mock API client to raise an exception
        self.action_history_api.get_action_instance.side_effect = Exception("API Error")

        result = asyncio.run(self.action_history_tools.get_action_instance_details(
            action_instance_id="instance123",
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_instance_details_no_to_dict(self):
        """Test get_action_instance_details when response has no to_dict method"""
        # Mock response without to_dict method
        self.action_history_api.get_action_instance.return_value = None

        result = asyncio.run(self.action_history_tools.get_action_instance_details(
            action_instance_id="instance123",
            api_client=self.action_history_api
        ))

        # Check that the result contains success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_list_action_instances_success(self):
        """Test successful list_action_instances call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {"id": "instance1", "status": "SUCCESS"},
                {"id": "instance2", "status": "FAILED"}
            ],
            "totalHits": 2
        }
        self.action_history_api.get_action_instances.return_value = mock_response

        result = asyncio.run(self.action_history_tools.list_action_instances(
            filters={},
            api_client=self.action_history_api
        ))

        # Check that the mock was called
        self.action_history_api.get_action_instances.assert_called_once()

        # Check that the result is correct
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 2)

    def test_list_action_instances_with_all_parameters(self):
        """Test list_action_instances with all parameters"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        self.action_history_api.get_action_instances.return_value = mock_response

        result = asyncio.run(self.action_history_tools.list_action_instances(
            filters={
                "window_size": 3600000,
                "to": 1234567890000,
                "page": 1,
                "page_size": 50,
                "target_snapshot_id": "snap123",
                "event_id": "event456",
                "event_specification_id": "spec789",
                "search": "test",
                "types": ["script", "webhook"],
                "action_statuses": ["SUCCESS", "FAILED"],
                "order_by": "timestamp",
                "order_direction": "DESC",
            },
            api_client=self.action_history_api
        ))

        # Check that the mock was called with all parameters
        self.action_history_api.get_action_instances.assert_called_once_with(
            window_size=3600000,
            to=1234567890000,
            page=1,
            page_size=50,
            target_snapshot_id="snap123",
            event_id="event456",
            event_specification_id="spec789",
            search="test",
            types=["script", "webhook"],
            action_statuses=["SUCCESS", "FAILED"],
            order_by="timestamp",
            order_direction="DESC"
        )

        # Check that the result is correct
        self.assertIn("items", result)

    def test_list_action_instances_error_handling(self):
        """Test error handling in list_action_instances"""
        # Mock API client to raise an exception
        self.action_history_api.get_action_instances.side_effect = Exception("API Error")

        result = asyncio.run(self.action_history_tools.list_action_instances(
            filters={},
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_list_action_instances_no_to_dict(self):
        """Test list_action_instances when response has no to_dict method"""
        # Mock response without to_dict method
        self.action_history_api.get_action_instances.return_value = None

        result = asyncio.run(self.action_history_tools.list_action_instances(
            filters={},
            api_client=self.action_history_api
        ))

        # Check that the result contains success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_delete_action_instance_success(self):
        """Test successful delete_action_instance call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "success": True,
            "message": "Action instance deleted"
        }
        self.action_history_api.delete_action_instance.return_value = mock_response

        result = asyncio.run(self.action_history_tools.delete_action_instance(
            action_instance_id="instance123",
            from_time=1234567890000,
            to_time=1234567900000,
            api_client=self.action_history_api
        ))

        # Check that the mock was called with the correct arguments
        self.action_history_api.delete_action_instance.assert_called_once_with(
            action_instance_id="instance123",
            var_from=1234567890000,
            to=1234567900000
        )

        # Check that the result is correct
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_delete_action_instance_missing_id(self):
        """Test delete_action_instance with missing action_instance_id"""
        result = asyncio.run(self.action_history_tools.delete_action_instance(
            action_instance_id=None,
            from_time=1234567890000,
            to_time=1234567900000,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("action_instance_id is required", (result.get("error") or result.get("message", "")))

    def test_delete_action_instance_missing_from_time(self):
        """Test delete_action_instance with missing from_time"""
        result = asyncio.run(self.action_history_tools.delete_action_instance(
            action_instance_id="instance123",
            from_time=None,
            to_time=1234567900000,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("from_time is required", (result.get("error") or result.get("message", "")))

    def test_delete_action_instance_missing_to_time(self):
        """Test delete_action_instance with missing to_time"""
        result = asyncio.run(self.action_history_tools.delete_action_instance(
            action_instance_id="instance123",
            from_time=1234567890000,
            to_time=None,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("to_time is required", (result.get("error") or result.get("message", "")))

    def test_delete_action_instance_error_handling(self):
        """Test error handling in delete_action_instance"""
        # Mock API client to raise an exception
        self.action_history_api.delete_action_instance.side_effect = Exception("API Error")

        result = asyncio.run(self.action_history_tools.delete_action_instance(
            action_instance_id="instance123",
            from_time=1234567890000,
            to_time=1234567900000,
            api_client=self.action_history_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_delete_action_instance_no_to_dict(self):
        """Test delete_action_instance when response has no to_dict method"""
        # Mock response without to_dict method
        self.action_history_api.delete_action_instance.return_value = None

        result = asyncio.run(self.action_history_tools.delete_action_instance(
            action_instance_id="instance123",
            from_time=1234567890000,
            to_time=1234567900000,
            api_client=self.action_history_api
        ))

        # Check that the result contains success message
        self.assertIn("success", result)
        self.assertTrue(result["success"])


if __name__ == '__main__':
    unittest.main()
