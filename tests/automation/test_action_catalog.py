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
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # For testing, we need to ensure the API client is properly set
            # The decorator should inject the API client into kwargs
            if 'api_client' not in kwargs or kwargs['api_client'] is None:
                # Use the existing API client from the instance
                if hasattr(self, 'action_catalog_api'):
                    kwargs['api_client'] = self.action_catalog_api
                else:
                    # Fallback to the global mock
                    kwargs['api_client'] = mock_action_catalog_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.action_catalog_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.action_search_space'] = MagicMock()

# Set up mock classes
mock_action_catalog_api = MagicMock()
mock_action_search_space = MagicMock()

# Add __name__ attribute to mock classes
mock_action_catalog_api.__name__ = "ActionCatalogApi"
mock_action_search_space.__name__ = "ActionSearchSpace"

sys.modules['instana_client.api.action_catalog_api'].ActionCatalogApi = mock_action_catalog_api
sys.modules['instana_client.models.action_search_space'].ActionSearchSpace = mock_action_search_space

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.automation.action_catalog import ActionCatalogMCPTools

class TestActionCatalogMCPTools(unittest.TestCase):
    """Test class for ActionCatalogMCPTools"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_action_catalog_api.reset_mock()
        mock_action_search_space.reset_mock()

        # Store references to the global mocks
        self.mock_action_catalog_api = mock_action_catalog_api
        self.action_catalog_api = MagicMock()

        # Create an instance of ActionCatalogMCPTools for testing
        self.action_catalog_tools = ActionCatalogMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )

        # Set the action_catalog_api attribute on the instance
        self.action_catalog_tools.action_catalog_api = self.action_catalog_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.action_catalog_tools.read_token, "test_token")
        self.assertEqual(self.action_catalog_tools.base_url, "https://test.instana.com")

    def test_get_action_matches_success(self):
        """Test successful get_action_matches call"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
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
        self.assertIn("error", result)

    def test_get_action_matches_string_payload(self):
        """Test get_action_matches with string payload"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
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
        self.assertIn("error", result)

    def test_get_actions_success(self):
        """Test successful get_actions call"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
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
        self.assertIn("error", result)

    def test_get_action_details_success(self):
        """Test successful get_action_details call"""
        # Mock response - the method expects a response object with data attribute
        mock_response = MagicMock()
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

        # Check that the result contains an error
        self.assertIn("error", result)

    def test_get_action_types_success(self):
        """Test successful get_action_types call"""
        # Mock response - the method calls get_actions_without_preload_content
        mock_response = MagicMock()
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


if __name__ == '__main__':
    unittest.main()
