"""
Tests for Action Catalog MCP Tools

This module contains tests for the automation action catalog tools.
"""

import asyncio
import logging
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch
import os


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the automation logger and replace its handlers
automation_logger = logging.getLogger('src.automation.action_catalog')
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
            if hasattr(self, 'action_catalog_api'):
                kwargs['api_client'] = self.action_catalog_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes BEFORE importing
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.action_catalog_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.action_search_space'] = MagicMock()

# Set up mock classes
mock_action_catalog_api_class = MagicMock()
mock_action_search_space_class = MagicMock()

# Add __name__ attribute to mock classes
mock_action_catalog_api_class.__name__ = "ActionCatalogApi"
mock_action_search_space_class.__name__ = "ActionSearchSpace"

sys.modules['instana_client.api.action_catalog_api'].ActionCatalogApi = mock_action_catalog_api_class
sys.modules['instana_client.models.action_search_space'].ActionSearchSpace = mock_action_search_space_class

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.automation.action_catalog import ActionCatalogMCPTools

class TestActionCatalogMCPTools(unittest.TestCase):
    """Test class for ActionCatalogMCPTools"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_action_catalog_api_class.reset_mock()
        mock_action_search_space_class.reset_mock()

        # Create a mock API client instance for this test
        self.action_catalog_api = MagicMock()

        # Create an instance of ActionCatalogMCPTools for testing
        self.action_catalog_tools = ActionCatalogMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        # Set up the client's API attribute
        self.action_catalog_tools.action_catalog_api = self.action_catalog_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.action_catalog_tools.read_token, "test_token")
        self.assertEqual(self.action_catalog_tools.base_url, "https://test.instana.com")

    def test_get_action_matches_success(self):
        """Test successful get_action_matches call"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {
            "matches": [
                {"id": "action1", "name": "Action 1", "score": 0.95},
                {"id": "action2", "name": "Action 2", "score": 0.87}
            ]
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_without_preload_content.return_value = mock_response

        # Test payload
        payload = {
            "name": "CPU usage high",
            "description": "Check CPU usage"
        }

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            target_snapshot_id="snapshot123",
            api_client=self.action_catalog_api
        ))

        # Check that the mock was called
        self.action_catalog_api.get_action_matches_without_preload_content.assert_called_once()

        # Check that the result is correct
        self.assertIn("data", result)
        self.assertIn("matches", result["data"])
        self.assertEqual(len(result["data"]["matches"]), 2)
        self.assertEqual(result["data"]["matches"][0]["name"], "Action 1")

    def test_get_action_matches_missing_payload(self):
        """Test get_action_matches with missing payload"""
        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=None,
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_matches_string_payload(self):
        """Test get_action_matches with string payload"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {
            "matches": [
                {"id": "action1", "name": "Action 1", "score": 0.95}
            ]
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_without_preload_content.return_value = mock_response

        # Test with JSON string payload
        payload = '{"name": "CPU usage high", "description": "Check CPU usage"}'

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("data", result)
        self.assertIn("matches", result["data"])
        self.assertEqual(len(result["data"]["matches"]), 1)

    def test_get_action_matches_error_handling(self):
        """Test error handling in get_action_matches"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_action_matches_without_preload_content.side_effect = Exception("API Error")

        payload = {"name": "test"}

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_raw_response_http_error(self):
        """A non-2xx raw response is returned as an HTTP error, not parsed as data"""
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.data = b'{"errors": ["boom"]}'
        api = self.action_catalog_api
        api.get_actions_without_preload_content.return_value = mock_response
        api.get_action_by_id_without_preload_content.return_value = mock_response
        api.get_action_matches_without_preload_content.return_value = mock_response
        api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = mock_response
        tools = self.action_catalog_tools

        results = [
            asyncio.run(tools.get_actions(api_client=api)),
            asyncio.run(tools.get_action_types(api_client=api)),
            asyncio.run(tools.get_action_tags(api_client=api)),
            asyncio.run(tools.get_action_details(action_id="a1", api_client=api)),
            asyncio.run(tools.get_action_matches(payload={"name": "CPU"}, api_client=api)),
            asyncio.run(tools.get_action_matches_by_id_and_time_window(application_id="app-1", api_client=api)),
        ]
        for result in results:
            self.assertEqual(result["status_code"], 500)
            self.assertIn("HTTP 500", result["error"])

    def test_get_actions_success(self):
        """Test successful get_actions call"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {"id": "action1", "name": "Action 1", "type": "script"},
            {"id": "action2", "name": "Action 2", "type": "command"}
        ]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_actions(
            api_client=self.action_catalog_api
        ))

        # Check that the mock was called
        self.action_catalog_api.get_actions_without_preload_content.assert_called_once()

        # Check that the result is correct
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Action 1")

    def test_get_actions_error_handling(self):
        """Test error handling in get_actions"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_actions_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.action_catalog_tools.get_actions(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_details_success(self):
        """Test successful get_action_details call"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {
            "id": "action1",
            "name": "Test Action",
            "description": "A test action",
            "type": "script",
            "parameters": []
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_by_id_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_details(
            action_id="action1",
            api_client=self.action_catalog_api
        ))

        # Check that the mock was called with the correct arguments
        self.action_catalog_api.get_action_by_id_without_preload_content.assert_called_once_with(id="action1")

        # Check that the result is correct
        self.assertIn("id", result)
        self.assertEqual(result["id"], "action1")
        self.assertEqual(result["name"], "Test Action")

    def test_get_action_details_missing_id(self):
        """Test get_action_details with missing action_id"""
        result = asyncio.run(self.action_catalog_tools.get_action_details(
            action_id=None,
            api_client=self.action_catalog_api
        ))

        # Missing required param returns an elicitation response, not a plain error
        self.assertTrue(result.get("elicitation_needed"))

    def test_get_action_types_success(self):
        """Test successful get_action_types call"""
        # Mock response - the method calls get_actions_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {"id": "action1", "name": "Action 1", "type": "script"},
            {"id": "action2", "name": "Action 2", "type": "command"},
            {"id": "action3", "name": "Action 3", "type": "http"},
            {"id": "action4", "name": "Action 4", "type": "email"}
        ]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_types(
            api_client=self.action_catalog_api
        ))

        # Check that the mock was called
        self.action_catalog_api.get_actions_without_preload_content.assert_called_once()

        # Check that the result is correct
        self.assertIsInstance(result, dict)
        self.assertIn("types", result)
        self.assertEqual(len(result["types"]), 4)
        self.assertIn("script", result["types"])

    def test_get_action_tags_success(self):
        """Test successful get_action_tags call"""
        # Mock response - the method calls get_actions_without_preload_content
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {"id": "action1", "name": "Action 1", "tags": ["monitoring", "cpu"]},
            {"id": "action2", "name": "Action 2", "tags": ["maintenance", "memory"]},
            {"id": "action3", "name": "Action 3", "tags": ["troubleshooting", "network"]}
        ]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_tags(
            api_client=self.action_catalog_api
        ))

        # Check that the mock was called
        self.action_catalog_api.get_actions_without_preload_content.assert_called_once()

        # Check that the result is correct
        self.assertIsInstance(result, dict)
        self.assertIn("tags", result)
        self.assertEqual(len(result["tags"]), 6)  # monitoring, cpu, maintenance, memory, troubleshooting, network
        self.assertIn("monitoring", result["tags"])

    def test_get_action_details_error_handling(self):
        """Test error handling in get_action_details"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_action_by_id_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.action_catalog_tools.get_action_details(
            action_id="action1",
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_types_error_handling(self):
        """Test error handling in get_action_types"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_actions_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.action_catalog_tools.get_action_types(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_tags_error_handling(self):
        """Test error handling in get_action_tags"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_actions_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.action_catalog_tools.get_action_tags(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_matches_invalid_json_payload(self):
        """Test get_action_matches with invalid JSON string payload"""
        # Test with invalid JSON string
        payload = '{invalid json}'

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_matches_missing_required_field(self):
        """Test get_action_matches with missing required field"""
        # Test payload without required 'name' field
        payload = {"description": "Test description"}

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error about missing field
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("name", (result.get("error") or result.get("message", "")))

    def test_get_action_matches_with_target_snapshot_id(self):
        """Test get_action_matches with target_snapshot_id"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {
            "matches": [
                {"id": "action1", "name": "Action 1", "score": 0.95}
            ]
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_without_preload_content.return_value = mock_response

        payload = {"name": "CPU usage high"}

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            target_snapshot_id="snapshot123",
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("data", result)

    def test_get_action_matches_json_decode_error(self):
        """Test get_action_matches with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.action_catalog_api.get_action_matches_without_preload_content.return_value = mock_response

        payload = {"name": "test"}

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_actions_json_decode_error(self):
        """Test get_actions with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_actions(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_details_json_decode_error(self):
        """Test get_action_details with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.action_catalog_api.get_action_by_id_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_details(
            action_id="action1",
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_types_json_decode_error(self):
        """Test get_action_types with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_types(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_tags_json_decode_error(self):
        """Test get_action_tags with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_tags(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_matches_by_id_and_time_window_success(self):
        """Test successful get_action_matches_by_id_and_time_window call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {
                "score": 0.95,
                "aiEngine": "test-engine",
                "confidence": 0.9,
                "action": {
                    "id": "action1",
                    "name": "Action 1",
                    "description": "Test action",
                    "type": "script",
                    "tags": ["test"],
                    "inputParameters": [
                        {
                            "name": "param1",
                            "label": "Parameter 1",
                            "description": "Test parameter",
                            "required": True,
                            "type": "string",
                            "value": "default"
                        }
                    ]
                }
            }
        ]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            window_size=3600000,
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)

    def test_get_action_matches_by_id_and_time_window_missing_ids(self):
        """Test get_action_matches_by_id_and_time_window with missing IDs"""
        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("application_id", (result.get("error") or result.get("message", "")))

    def test_get_action_matches_by_id_and_time_window_invalid_timestamp(self):
        """Test get_action_matches_by_id_and_time_window with invalid timestamp"""
        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            to=123,  # Invalid timestamp (too short)
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("timestamp", (result.get("error") or result.get("message", "")))

    def test_get_action_matches_by_id_and_time_window_negative_window_size(self):
        """Test get_action_matches_by_id_and_time_window with negative window_size"""
        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            window_size=-1000,
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("window_size", (result.get("error") or result.get("message", "")))

    def test_get_action_matches_by_id_and_time_window_with_snapshot_id(self):
        """Test get_action_matches_by_id_and_time_window with snapshot_id"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = []
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            snapshot_id="snap123",
            to=1234567890000,
            window_size=600000,
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_get_action_matches_by_id_and_time_window_api_error(self):
        """Test get_action_matches_by_id_and_time_window with API error response"""
        # Mock response with error
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {"errors": ["API error occurred"]}
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_matches_by_id_and_time_window_json_decode_error(self):
        """Test get_action_matches_by_id_and_time_window with JSON decode error"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = b'invalid json'
        self.action_catalog_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_action_matches_by_id_and_time_window_exception(self):
        """Test get_action_matches_by_id_and_time_window with exception"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_action_matches_by_id_and_time_window_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            api_client=self.action_catalog_api
        ))

        # Check that the result contains an error
        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_clean_action_data(self):
        """Test _clean_action_data helper method"""
        # Create a sample action with all fields
        action = {
            "id": "action1",
            "name": "Test Action",
            "description": "A test action",
            "type": "script",
            "tags": ["monitoring", "cpu"],
            "fields": "base64encodeddata",  # Should be removed
            "readOnly": True,  # Should be removed
            "builtIn": False,  # Should be removed
            "createdAt": 1234567890,  # Should be removed
            "modifiedAt": 1234567891,  # Should be removed
            "inputParameters": [
                {
                    "name": "param1",
                    "label": "Parameter 1",
                    "description": "Test parameter",
                    "required": True,
                    "type": "string",
                    "value": "default",
                    "hidden": False,  # Should be removed
                    "secured": False,  # Should be removed
                    "valueType": "text"  # Should be removed
                }
            ]
        }

        cleaned = self.action_catalog_tools._clean_action_data(action)

        # Check that essential fields are kept
        self.assertEqual(cleaned["id"], "action1")
        self.assertEqual(cleaned["name"], "Test Action")
        self.assertEqual(cleaned["description"], "A test action")
        self.assertEqual(cleaned["type"], "script")
        self.assertEqual(cleaned["tags"], ["monitoring", "cpu"])

        # Check that internal fields are removed
        self.assertNotIn("fields", cleaned)
        self.assertNotIn("readOnly", cleaned)
        self.assertNotIn("builtIn", cleaned)
        self.assertNotIn("createdAt", cleaned)
        self.assertNotIn("modifiedAt", cleaned)

        # Check that input parameters are cleaned
        self.assertIn("inputParameters", cleaned)
        self.assertEqual(len(cleaned["inputParameters"]), 1)
        param = cleaned["inputParameters"][0]
        self.assertEqual(param["name"], "param1")
        self.assertEqual(param["label"], "Parameter 1")
        self.assertEqual(param["required"], True)
        self.assertNotIn("hidden", param)
        self.assertNotIn("secured", param)
        self.assertNotIn("valueType", param)

    def test_clean_action_data_without_input_parameters(self):
        """Test _clean_action_data with action without input parameters"""
        action = {
            "id": "action1",
            "name": "Test Action",
            "description": "A test action",
            "type": "script",
            "tags": []
        }

        cleaned = self.action_catalog_tools._clean_action_data(action)

        # Check that essential fields are kept
        self.assertEqual(cleaned["id"], "action1")
        self.assertEqual(cleaned["name"], "Test Action")
        self.assertNotIn("inputParameters", cleaned)

    def test_get_actions_dict_format(self):
        """Test get_actions with dict format response"""
        # Mock response with dict format
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {
            "actions": [
                {"id": "action1", "name": "Action 1", "type": "script"}
            ]
        }
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_actions(
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_get_actions_unexpected_format(self):
        """Test get_actions with unexpected format"""
        # Mock response with unexpected format
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {"unexpected": "format"}
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_actions(
            api_client=self.action_catalog_api
        ))

        # Check that the result is returned as is
        self.assertIsInstance(result, dict)
        self.assertIn("unexpected", result)

    def test_get_action_types_empty_list(self):
        """Test get_action_types with empty actions list"""
        # Mock response with empty list
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = []
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_types(
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("types", result)
        self.assertEqual(len(result["types"]), 0)

    def test_get_action_tags_empty_list(self):
        """Test get_action_tags with empty actions list"""
        # Mock response with empty list
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = []
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_tags(
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("tags", result)
        self.assertEqual(len(result["tags"]), 0)

    def test_get_action_tags_non_list_format(self):
        """Test get_action_tags with non-list format"""
        # Mock response with dict format
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {"unexpected": "format"}
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_actions_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_tags(
            api_client=self.action_catalog_api
        ))

        # Check that the result returns empty tags
        self.assertIn("tags", result)
        self.assertEqual(len(result["tags"]), 0)

    def test_get_action_matches_list_response(self):
        """Test get_action_matches with list response format"""
        # Mock response with list format
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {
                "score": 0.95,
                "aiEngine": "test",
                "confidence": 0.9,
                "action": {
                    "id": "action1",
                    "name": "Action 1",
                    "type": "script",
                    "tags": []
                }
            }
        ]
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_without_preload_content.return_value = mock_response

        payload = {"name": "test"}

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("data", result)
        self.assertIsInstance(result["data"], list)

    def test_get_action_matches_by_id_and_time_window_dict_response(self):
        """Test get_action_matches_by_id_and_time_window with dict response"""
        # Mock response with dict format
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {"result": "data"}
        import json
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.action_catalog_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_matches_by_id_and_time_window(
            application_id="app123",
            api_client=self.action_catalog_api
        ))

        # Check that the result is correct
        self.assertIn("success", result)
        self.assertIn("data", result)


if __name__ == '__main__':
    unittest.main()