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
            # Just pass the API client directly
            kwargs['api_client'] = self.action_catalog_api
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

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.action_catalog_tools.read_token, "test_token")
        self.assertEqual(self.action_catalog_tools.base_url, "https://test.instana.com")

    @patch('src.automation.action_catalog.ActionSearchSpace')
    def test_get_action_matches_success(self, mock_action_search_space_class):
        """Test successful get_action_matches call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "matches": [
                {"id": "action1", "name": "Test Action 1"},
                {"id": "action2", "name": "Test Action 2"}
            ]
        }
        self.action_catalog_api.get_action_matches.return_value = [mock_response]

        # Test payload
        payload = {
            "name": "CPU spends significant time waiting for input/output",
            "description": "Checks whether the system spends significant time waiting for input/output."
        }

        # Mock the ActionSearchSpace constructor
        mock_config_object = MagicMock()
        mock_action_search_space_class.return_value = mock_config_object

        # Run the test
        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            target_snapshot_id="test_snapshot",
            api_client=self.action_catalog_api
        ))

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Action matches retrieved successfully")
        self.assertIn("data", result)
        self.assertEqual(result["count"], 1)

    def test_get_action_matches_missing_payload(self):
        """Test get_action_matches with missing payload"""
        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=None,
            api_client=self.action_catalog_api
        ))

        self.assertIn("error", result)
        self.assertIn("payload is required", result["error"])

    def test_get_actions_success(self):
        """Test successful get_actions call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "actions": [
                {"id": "action1", "name": "Action 1", "type": "script"},
                {"id": "action2", "name": "Action 2", "type": "command"}
            ],
            "total": 2
        }
        self.action_catalog_api.get_actions.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_actions(
            page=1,
            page_size=10,
            search="test",
            types=["script"],
            order_by="name",
            order_direction="asc",
            api_client=self.action_catalog_api
        ))

        self.assertIn("actions", result)
        self.assertEqual(result["total"], 2)
        self.action_catalog_api.get_actions.assert_called_once()

    def test_get_action_details_success(self):
        """Test successful get_action_details call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "action1",
            "name": "Test Action",
            "description": "A test action",
            "type": "script",
            "parameters": []
        }
        self.action_catalog_api.get_action.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_details(
            action_id="action1",
            api_client=self.action_catalog_api
        ))

        self.assertEqual(result["id"], "action1")
        self.assertEqual(result["name"], "Test Action")
        self.action_catalog_api.get_action.assert_called_once_with(action_id="action1")

    def test_get_action_details_missing_id(self):
        """Test get_action_details with missing action_id"""
        result = asyncio.run(self.action_catalog_tools.get_action_details(
            action_id=None,
            api_client=self.action_catalog_api
        ))

        self.assertIn("error", result)
        self.assertIn("action_id is required", result["error"])

    def test_search_actions_success(self):
        """Test successful search_actions call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "actions": [
                {"id": "action1", "name": "CPU Action", "type": "script"},
                {"id": "action2", "name": "Memory Action", "type": "command"}
            ],
            "total": 2
        }
        self.action_catalog_api.search_actions.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.search_actions(
            search="CPU",
            page=1,
            page_size=10,
            types=["script"],
            order_by="name",
            order_direction="asc",
            api_client=self.action_catalog_api
        ))

        self.assertIn("actions", result)
        self.assertEqual(result["total"], 2)
        self.action_catalog_api.search_actions.assert_called_once()

    def test_search_actions_missing_search(self):
        """Test search_actions with missing search parameter"""
        result = asyncio.run(self.action_catalog_tools.search_actions(
            search=None,
            api_client=self.action_catalog_api
        ))

        self.assertIn("error", result)
        self.assertIn("search parameter is required", result["error"])

    def test_get_action_types_success(self):
        """Test successful get_action_types call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "types": ["script", "command", "http", "email"]
        }
        self.action_catalog_api.get_action_types.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_types(
            api_client=self.action_catalog_api
        ))

        self.assertIn("types", result)
        self.assertIn("script", result["types"])
        self.assertIn("command", result["types"])
        self.action_catalog_api.get_action_types.assert_called_once()

    def test_get_action_categories_success(self):
        """Test successful get_action_categories call"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "categories": [
                {"id": "monitoring", "name": "Monitoring"},
                {"id": "maintenance", "name": "Maintenance"},
                {"id": "troubleshooting", "name": "Troubleshooting"}
            ]
        }
        self.action_catalog_api.get_action_categories.return_value = mock_response

        result = asyncio.run(self.action_catalog_tools.get_action_categories(
            api_client=self.action_catalog_api
        ))

        self.assertIn("categories", result)
        self.assertEqual(len(result["categories"]), 3)
        self.action_catalog_api.get_action_categories.assert_called_once()

    @patch('src.automation.action_catalog.ActionSearchSpace')
    def test_get_action_matches_string_payload(self, mock_action_search_space_class):
        """Test get_action_matches with string payload"""
        # Mock response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "matches": [{"id": "action1", "name": "Test Action"}]
        }
        self.action_catalog_api.get_action_matches.return_value = [mock_response]

        # Test with JSON string payload
        payload = '{"name": "Test Action", "description": "A test action"}'

        # Mock the ActionSearchSpace constructor
        mock_config_object = MagicMock()
        mock_action_search_space_class.return_value = mock_config_object

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        self.assertTrue(result["success"])
        self.assertIn("data", result)

    @patch('src.automation.action_catalog.ActionSearchSpace')
    def test_get_action_matches_error_handling(self, mock_action_search_space_class):
        """Test error handling in get_action_matches"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_action_matches.side_effect = Exception("API Error")

        payload = {"name": "Test Action"}

        # Mock the ActionSearchSpace constructor
        mock_config_object = MagicMock()
        mock_action_search_space_class.return_value = mock_config_object

        result = asyncio.run(self.action_catalog_tools.get_action_matches(
            payload=payload,
            api_client=self.action_catalog_api
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to get action matches", result["error"])

    def test_get_actions_error_handling(self):
        """Test error handling in get_actions"""
        # Mock API client to raise an exception
        self.action_catalog_api.get_actions.side_effect = Exception("API Error")

        result = asyncio.run(self.action_catalog_tools.get_actions(
            api_client=self.action_catalog_api
        ))

        self.assertIn("error", result)
        self.assertIn("Failed to get actions", result["error"])
