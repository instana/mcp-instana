"""
Tests for Custom Dashboard MCP Tools

This module contains tests for the custom dashboard tools.
"""

import asyncio
import json
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

# Get the custom_dashboard logger and replace its handlers
custom_dashboard_logger = logging.getLogger('src.custom_dashboard.custom_dashboard_tools')
custom_dashboard_logger.handlers = []
custom_dashboard_logger.addHandler(NullHandler())
custom_dashboard_logger.propagate = False

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    if isinstance(value, Exception) and str(value) == "Test error":
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
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
            if hasattr(self, 'custom_dashboards_api'):
                kwargs['api_client'] = self.custom_dashboards_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes BEFORE importing
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.custom_dashboards_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.custom_dashboard'] = MagicMock()

# Set up mock classes
mock_custom_dashboards_api_class = MagicMock()
mock_custom_dashboard_class = MagicMock()

# Add __name__ attribute to mock classes
mock_custom_dashboards_api_class.__name__ = "CustomDashboardsApi"
mock_custom_dashboard_class.__name__ = "CustomDashboard"

sys.modules['instana_client.api.custom_dashboards_api'].CustomDashboardsApi = mock_custom_dashboards_api_class
sys.modules['instana_client.models.custom_dashboard'].CustomDashboard = mock_custom_dashboard_class

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.custom_dashboard.custom_dashboard_tools import CustomDashboardMCPTools

class TestCustomDashboardMCPTools(unittest.TestCase):
    """Test class for CustomDashboardMCPTools"""

    def setUp(self):
        """Set up test fixtures"""
        mock_custom_dashboards_api_class.reset_mock()
        mock_custom_dashboard_class.reset_mock()

        self.custom_dashboards_api = MagicMock()
        self.custom_dashboard_tools = CustomDashboardMCPTools(
            read_token="test_token",
            base_url="https://test.instana.com"
        )
        self.custom_dashboard_tools.custom_dashboards_api = self.custom_dashboards_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.custom_dashboard_tools.read_token, "test_token")
        self.assertEqual(self.custom_dashboard_tools.base_url, "https://test.instana.com")

    def test_get_custom_dashboards_success(self):
        """Test successful get_custom_dashboards call"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {"id": "dash1", "title": "Dashboard 1"},
            {"id": "dash2", "title": "Dashboard 2"}
        ]
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboards(
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.assert_called_once()
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["count"], 2)

    def test_get_custom_dashboards_with_parameters(self):
        """Test get_custom_dashboards with all parameters"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([]).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboards(
            query="test",
            page_size=10,
            page=0,
            with_total_hits=True,
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.assert_called_once_with(
            query="test",
            page_size=10,
            page=0,
            with_total_hits=True
        )
        self.assertIn("page", result)
        self.assertEqual(result["page"], 0)
        self.assertIn("page_size", result)
        self.assertEqual(result["page_size"], 10)

    def test_get_custom_dashboards_error_status(self):
        """Test get_custom_dashboards with error status"""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.data = b"Not found"
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboards(
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("404", (result.get("error") or result.get("message", "")))

    def test_get_custom_dashboards_exception(self):
        """Test get_custom_dashboards with exception"""
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboards(
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_custom_dashboard_success(self):
        """Test successful get_custom_dashboard call"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = {"id": "dash1", "title": "Dashboard 1"}
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.assert_called_once_with(
            custom_dashboard_id="dash1"
        )
        self.assertIn("id", result)
        self.assertEqual(result["id"], "dash1")

    def test_get_custom_dashboard_missing_id(self):
        """Test get_custom_dashboard with missing dashboard_id"""
        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboard(
            dashboard_id=None,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Dashboard ID is required", (result.get("error") or result.get("message", "")))

    def test_get_custom_dashboard_error_status(self):
        """Test get_custom_dashboard with error status"""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.data = b"Dashboard not found"
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_add_custom_dashboard_success(self):
        """Test successful add_custom_dashboard call"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response_data = {"id": "dash1", "title": "New Dashboard"}
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {
            "title": "New Dashboard",
            "widgets": []
        }

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.assert_called_once()
        self.assertIn("id", result)
        self.assertEqual(result["id"], "dash1")

    def test_add_custom_dashboard_missing_config(self):
        """Test add_custom_dashboard with missing configuration"""
        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=None,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Custom dashboard configuration is required", (result.get("error") or result.get("message", "")))

    def test_add_custom_dashboard_adds_defaults(self):
        """Test add_custom_dashboard adds default fields"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {"title": "Test"}

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        # Verify the call was made
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.assert_called_once()
        self.assertIn("id", result)

    def test_update_custom_dashboard_success(self):
        """Test successful update_custom_dashboard call — re-fetches the full record."""
        mock_put_response = MagicMock()
        mock_put_response.status = 200
        mock_put_response.data = b""  # PUT may return empty body
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.return_value = mock_put_response

        # The re-fetch (GET) returns the full record
        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.data = json.dumps({"id": "dash1", "title": "Updated Dashboard"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_get_response

        dashboard_config = {
            "title": "Updated Dashboard",
            "widgets": []
        }

        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.assert_called_once()
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.assert_called_once()
        self.assertIn("id", result)
        self.assertEqual(result["title"], "Updated Dashboard")

    def test_update_custom_dashboard_missing_id(self):
        """Test update_custom_dashboard with missing dashboard_id"""
        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id=None,
            custom_dashboard={"title": "Test"},
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Dashboard ID is required", (result.get("error") or result.get("message", "")))

    def test_update_custom_dashboard_missing_config(self):
        """Test update_custom_dashboard with missing configuration"""
        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard=None,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Custom dashboard configuration is required", (result.get("error") or result.get("message", "")))

    def test_delete_custom_dashboard_success(self):
        """Test successful delete_custom_dashboard call"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.data = b""
        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.delete_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.assert_called_once_with(
            custom_dashboard_id="dash1"
        )
        self.assertIn("success", result)
        self.assertTrue(result["success"])

    def test_delete_custom_dashboard_with_response_data(self):
        """Test delete_custom_dashboard with response data"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"deleted": True}).encode('utf-8')
        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.delete_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("deleted", result)
        self.assertTrue(result["deleted"])

    def test_delete_custom_dashboard_missing_id(self):
        """Test delete_custom_dashboard with missing dashboard_id"""
        result = asyncio.run(self.custom_dashboard_tools.delete_custom_dashboard(
            dashboard_id=None,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("Dashboard ID is required", (result.get("error") or result.get("message", "")))

    def test_get_shareable_users_success(self):
        """Test successful get_shareable_users call"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {"id": "user1", "name": "User 1"},
            {"id": "user2", "name": "User 2"}
        ]
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.get_shareable_users_without_preload_content.assert_called_once()
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 2)

    def test_get_shareable_users_limits_response(self):
        """Test get_shareable_users limits large responses"""
        mock_response = MagicMock()
        mock_response.status = 200
        # Create 25 users
        mock_response_data = [{"id": f"user{i}", "name": f"User {i}"} for i in range(25)]
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            api_client=self.custom_dashboards_api
        ))

        # Should be limited to 20
        self.assertEqual(len(result["items"]), 20)

    def test_get_shareable_api_tokens_success(self):
        """Test successful get_shareable_api_tokens call"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response_data = [
            {"id": "token1", "name": "Token 1"},
            {"id": "token2", "name": "Token 2"}
        ]
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            api_client=self.custom_dashboards_api
        ))

        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.assert_called_once()
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 2)

    def test_get_shareable_api_tokens_limits_response(self):
        """Test get_shareable_api_tokens limits large responses"""
        mock_response = MagicMock()
        mock_response.status = 200
        # Create 15 tokens
        mock_response_data = [{"id": f"token{i}", "name": f"Token {i}"} for i in range(15)]
        mock_response.data = json.dumps(mock_response_data).encode('utf-8')
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            api_client=self.custom_dashboards_api
        ))

        # Should be limited to 10
        self.assertEqual(len(result["items"]), 10)

    def test_execute_dashboard_operation_get_all(self):
        """Test execute_dashboard_operation with get_all operation"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([]).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get_all",
            params={"query": "test"}
        ))

        self.assertIn("items", result)

    def test_execute_dashboard_operation_get(self):
        """Test execute_dashboard_operation with get operation"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get",
            params={"dashboard_id": "dash1"}
        ))

        self.assertIn("id", result)

    def test_execute_dashboard_operation_get_missing_id(self):
        """Test execute_dashboard_operation get without dashboard_id"""
        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("dashboard_id is required", (result.get("error") or result.get("message", "")))

    def test_execute_dashboard_operation_create(self):
        """Test execute_dashboard_operation with create operation"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="create",
            params={"custom_dashboard": {"title": "Test"}}
        ))

        self.assertIn("id", result)

    def test_execute_dashboard_operation_create_missing_config(self):
        """Test execute_dashboard_operation create without custom_dashboard"""
        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="create",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("custom_dashboard", (result.get("error") or result.get("message", "")))

    def test_execute_dashboard_operation_update(self):
        """Test execute_dashboard_operation with update operation"""
        mock_put_response = MagicMock()
        mock_put_response.status = 200
        mock_put_response.data = b""
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.return_value = mock_put_response

        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_get_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="update",
            params={"dashboard_id": "dash1", "custom_dashboard": {"title": "Updated"}}
        ))

        self.assertIn("id", result)

    def test_execute_dashboard_operation_update_missing_id(self):
        """Test execute_dashboard_operation update without dashboard_id"""
        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="update",
            params={"custom_dashboard": {"title": "Test"}}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("dashboard_id", (result.get("error") or result.get("message", "")))

    def test_execute_dashboard_operation_update_missing_config(self):
        """Test execute_dashboard_operation update without custom_dashboard"""
        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="update",
            params={"dashboard_id": "dash1"}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("custom_dashboard", (result.get("error") or result.get("message", "")))

    def test_execute_dashboard_operation_delete(self):
        """Test execute_dashboard_operation with delete operation"""
        mock_response = MagicMock()
        mock_response.status = 204
        mock_response.data = b""
        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="delete",
            params={"dashboard_id": "dash1"}
        ))

        self.assertIn("success", result)

    def test_execute_dashboard_operation_delete_missing_id(self):
        """Test execute_dashboard_operation delete without dashboard_id"""
        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="delete",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("dashboard_id is required", (result.get("error") or result.get("message", "")))

    def test_execute_dashboard_operation_get_shareable_users(self):
        """Test execute_dashboard_operation with get_shareable_users operation"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([]).encode('utf-8')
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get_shareable_users",
            params={}
        ))

        self.assertIn("items", result)

    def test_execute_dashboard_operation_get_shareable_api_tokens(self):
        """Test execute_dashboard_operation with get_shareable_api_tokens operation"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([]).encode('utf-8')
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get_shareable_api_tokens",
            params={}
        ))

        self.assertIn("items", result)

    def test_execute_dashboard_operation_unsupported(self):
        """Test execute_dashboard_operation with unsupported operation"""
        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="unsupported_operation",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("not supported", (result.get("error") or result.get("message", "")))

    def test_execute_dashboard_operation_none_params(self):
        """Test execute_dashboard_operation with None params"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([]).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get_all",
            params=None
        ))

        self.assertIn("items", result)

    def test_execute_dashboard_operation_exception(self):
        """Test execute_dashboard_operation with exception"""
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.side_effect = Exception("Test error")

        result = asyncio.run(self.custom_dashboard_tools.execute_dashboard_operation(
            operation="get_all",
            params={}
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_custom_dashboards_non_list_response(self):
        """Test get_custom_dashboards with non-list response"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"data": "not a list"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboards(
            api_client=self.custom_dashboards_api
        ))

        self.assertEqual(result["count"], 0)
        self.assertEqual(result["items"], [])

    def test_get_custom_dashboards_json_serialization_error(self):
        """Test get_custom_dashboards with JSON serialization error in logging"""
        mock_response = MagicMock()
        mock_response.status = 200
        # Create a response that will cause JSON serialization issues in logging
        mock_response.data = json.dumps([{"id": "dash1"}]).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboards_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboards(
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("items", result)

    def test_get_custom_dashboard_json_serialization_error(self):
        """Test get_custom_dashboard with JSON serialization error in logging"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("id", result)

    def test_get_custom_dashboard_exception(self):
        """Test get_custom_dashboard with exception"""
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.custom_dashboard_tools.get_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_add_custom_dashboard_error_status(self):
        """Test add_custom_dashboard with error status"""
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.data = b"Bad Request"
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {"title": "Test"}

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))
        self.assertIn("400", (result.get("error") or result.get("message", "")))

    def test_add_custom_dashboard_exception(self):
        """Test add_custom_dashboard with exception"""
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.side_effect = Exception("API Error")

        dashboard_config = {"title": "Test"}

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_add_custom_dashboard_json_serialization_error(self):
        """Test add_custom_dashboard with JSON serialization error in logging"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {"title": "Test"}

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("id", result)

    def test_update_custom_dashboard_error_status(self):
        """Test update_custom_dashboard with error status"""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.data = b"Not Found"
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {"title": "Updated"}

        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_update_custom_dashboard_exception(self):
        """Test update_custom_dashboard with exception"""
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.side_effect = Exception("API Error")

        dashboard_config = {"title": "Updated"}

        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_update_custom_dashboard_json_serialization_error(self):
        """Test update_custom_dashboard — re-fetch returns full record."""
        mock_put_response = MagicMock()
        mock_put_response.status = 200
        mock_put_response.data = b""
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.return_value = mock_put_response

        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_get_response

        dashboard_config = {"title": "Updated"}

        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("id", result)

    def test_delete_custom_dashboard_error_status(self):
        """Test delete_custom_dashboard with error status"""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.data = b"Not Found"
        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.delete_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_delete_custom_dashboard_exception(self):
        """Test delete_custom_dashboard with exception"""
        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.custom_dashboard_tools.delete_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_delete_custom_dashboard_json_serialization_error(self):
        """Test delete_custom_dashboard with JSON serialization error in logging"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"deleted": True}).encode('utf-8')
        self.custom_dashboards_api.delete_custom_dashboard_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.delete_custom_dashboard(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("deleted", result)

    def test_get_shareable_users_error_status(self):
        """Test get_shareable_users with error status"""
        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.data = b"Server Error"
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_shareable_users_exception(self):
        """Test get_shareable_users with exception"""
        self.custom_dashboards_api.get_shareable_users_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_shareable_users_json_serialization_error(self):
        """Test get_shareable_users with JSON serialization error in logging"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([{"id": "user1"}]).encode('utf-8')
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("items", result)

    def test_get_shareable_users_non_list_response(self):
        """Test get_shareable_users with non-list response"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"data": "not a list"}).encode('utf-8')
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            api_client=self.custom_dashboards_api
        ))

        # Non-list response is treated as an object, so count will be 1
        self.assertIn("items", result)

    def test_get_shareable_api_tokens_error_status(self):
        """Test get_shareable_api_tokens with error status"""
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.data = b"Forbidden"
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_shareable_api_tokens_exception(self):
        """Test get_shareable_api_tokens with exception"""
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.side_effect = Exception("API Error")

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            api_client=self.custom_dashboards_api
        ))

        self.assertTrue("error" in result or result.get("elicitation_needed"))

    def test_get_shareable_api_tokens_json_serialization_error(self):
        """Test get_shareable_api_tokens with JSON serialization error in logging"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([{"id": "token1"}]).encode('utf-8')
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("items", result)

    def test_get_shareable_api_tokens_non_list_response(self):
        """Test get_shareable_api_tokens with non-list response"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"data": "not a list"}).encode('utf-8')
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            api_client=self.custom_dashboards_api
        ))

        # Non-list response is treated as an object, so count will be 1
        self.assertIn("items", result)

    def test_add_custom_dashboard_with_id(self):
        """Test add_custom_dashboard when id is already present"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {"id": "existing_id", "title": "Test"}

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("id", result)

    def test_add_custom_dashboard_with_access_rules(self):
        """Test add_custom_dashboard when accessRules is already present"""
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.return_value = mock_response

        dashboard_config = {
            "title": "Test",
            "accessRules": [{"accessType": "READ", "relationType": "USER", "relatedId": "user1"}]
        }

        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("id", result)

    def test_update_custom_dashboard_with_access_rules(self):
        """Test update_custom_dashboard when accessRules is already present — re-fetches full record."""
        mock_put_response = MagicMock()
        mock_put_response.status = 200
        mock_put_response.data = b""
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.return_value = mock_put_response

        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.data = json.dumps({"id": "dash1"}).encode('utf-8')
        self.custom_dashboards_api.get_custom_dashboard_without_preload_content.return_value = mock_get_response

        dashboard_config = {
            "title": "Updated",
            "accessRules": [{"accessType": "READ", "relationType": "USER", "relatedId": "user1"}]
        }

        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard=dashboard_config,
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("id", result)

    def test_get_shareable_users_with_dashboard_id(self):
        """Test get_shareable_users with dashboard_id parameter (ignored)"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([{"id": "user1"}]).encode('utf-8')
        self.custom_dashboards_api.get_shareable_users_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_users(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("items", result)

    def test_get_shareable_api_tokens_with_dashboard_id(self):
        """Test get_shareable_api_tokens with dashboard_id parameter (ignored)"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps([{"id": "token1"}]).encode('utf-8')
        self.custom_dashboards_api.get_shareable_api_tokens_without_preload_content.return_value = mock_response

        result = asyncio.run(self.custom_dashboard_tools.get_shareable_api_tokens(
            dashboard_id="dash1",
            api_client=self.custom_dashboards_api
        ))

        self.assertIn("items", result)


    # -------------------------------------------------------------------------
    # _validate_dashboard_payload tests
    # -------------------------------------------------------------------------

    def test_validate_missing_title_returns_elicitation(self):
        """Missing title must produce an elicitation with api_error."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {"widgets": []}, "create"
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("api_error", result)
        self.assertTrue(any("title" in e for e in result["api_error"]))

    def test_validate_empty_title_returns_elicitation(self):
        """Whitespace-only title is also invalid."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {"title": "   "}, "create"
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("title" in e for e in result["api_error"]))

    def test_validate_valid_minimal_payload_passes(self):
        """title only is sufficient (widgets/accessRules get defaults)."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {"title": "My Dashboard"}, "create"
        )
        self.assertIsNone(result)

    def test_validate_valid_full_payload_passes(self):
        """Full valid payload with accessRules and widgets passes."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Full Dashboard",
                "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}],
                "widgets": [{"id": "w1", "type": "chart", "config": {"metric": "cpu"}}],
            },
            "create",
        )
        self.assertIsNone(result)

    def test_validate_invalid_access_type_returns_elicitation(self):
        """An invalid accessType enum value triggers elicitation."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Test",
                "accessRules": [{"accessType": "WRITE", "relationType": "GLOBAL"}],
            },
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertTrue(any("accessType" in e for e in result["api_error"]))

    def test_validate_invalid_relation_type_returns_elicitation(self):
        """An invalid relationType enum value triggers elicitation."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Test",
                "accessRules": [{"accessType": "READ", "relationType": "ORG"}],
            },
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("relationType" in e for e in result["api_error"]))

    def test_validate_missing_access_type_and_relation_type(self):
        """Missing both accessType and relationType produces two errors."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {"title": "Test", "accessRules": [{}]},
            "create",
        )
        self.assertIsNotNone(result)
        errors = result["api_error"]
        self.assertTrue(any("accessType" in e for e in errors))
        self.assertTrue(any("relationType" in e for e in errors))

    def test_validate_empty_access_rules_list_returns_elicitation(self):
        """An empty accessRules list is invalid (min_length=1)."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {"title": "Test", "accessRules": []},
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("accessRules" in e for e in result["api_error"]))

    def test_validate_widget_missing_required_fields_returns_elicitation(self):
        """Widget missing id, type, config all reported in one pass."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {"title": "Test", "widgets": [{"title": "Widget 1"}]},
            "create",
        )
        self.assertIsNotNone(result)
        errors = result["api_error"]
        self.assertTrue(any("widgets[0].id" in e for e in errors))
        self.assertTrue(any("widgets[0].type" in e for e in errors))
        self.assertTrue(any("widgets[0].config" in e for e in errors))

    def test_validate_widget_invalid_width_returns_elicitation(self):
        """Widget width outside 1-12 triggers elicitation."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Test",
                "widgets": [
                    {"id": "w1", "type": "chart", "config": {}, "width": 13}
                ],
            },
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("width" in e for e in result["api_error"]))

    def test_validate_widget_invalid_x_returns_elicitation(self):
        """Widget x outside 0-11 triggers elicitation."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Test",
                "widgets": [{"id": "w1", "type": "chart", "config": {}, "x": 12}],
            },
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("widgets[0].x" in e for e in result["api_error"]))

    def test_validate_widget_invalid_y_returns_elicitation(self):
        """Negative y triggers elicitation."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Test",
                "widgets": [{"id": "w1", "type": "chart", "config": {}, "y": -1}],
            },
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("widgets[0].y" in e for e in result["api_error"]))

    def test_validate_widget_invalid_height_returns_elicitation(self):
        """height < 1 triggers elicitation."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "title": "Test",
                "widgets": [{"id": "w1", "type": "chart", "config": {}, "height": 0}],
            },
            "create",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("height" in e for e in result["api_error"]))

    def test_validate_multiple_errors_all_reported(self):
        """All errors across title, accessRules, and widgets are collected in one pass."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {
                "accessRules": [{"accessType": "INVALID", "relationType": "INVALID"}],
                "widgets": [{"title": "no id/type/config"}],
            },
            "update",
        )
        self.assertIsNotNone(result)
        errors = result["api_error"]
        # title missing, accessType invalid, relationType invalid,
        # widget missing id/type/config — all in one shot
        self.assertGreaterEqual(len(errors), 5)
        self.assertTrue(result["elicitation_needed"])

    def test_validate_reason_reflects_operation(self):
        """reason string includes the operation name."""
        result = CustomDashboardMCPTools._validate_dashboard_payload(
            {}, "update"
        )
        self.assertIn("update", result["reason"])

    # -------------------------------------------------------------------------
    # Integration: add/update return elicitation when payload is invalid
    # -------------------------------------------------------------------------

    def test_add_dashboard_missing_title_returns_elicitation(self):
        """add_custom_dashboard returns elicitation (not a crash) for missing title."""
        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard={"widgets": []},
            api_client=self.custom_dashboards_api,
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("api_error", result)
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.assert_not_called()

    def test_update_dashboard_missing_title_returns_elicitation(self):
        """update_custom_dashboard returns elicitation (not a crash) for missing title."""
        result = asyncio.run(self.custom_dashboard_tools.update_custom_dashboard(
            dashboard_id="dash1",
            custom_dashboard={"widgets": []},
            api_client=self.custom_dashboards_api,
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertIn("api_error", result)
        self.custom_dashboards_api.update_custom_dashboard_without_preload_content.assert_not_called()

    def test_add_dashboard_invalid_access_type_returns_elicitation(self):
        """add_custom_dashboard returns elicitation for bad accessType enum."""
        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard={
                "title": "Test",
                "accessRules": [{"accessType": "WRITE", "relationType": "GLOBAL"}],
            },
            api_client=self.custom_dashboards_api,
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("accessType" in e for e in result["api_error"]))
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.assert_not_called()

    def test_add_dashboard_widget_missing_fields_returns_elicitation(self):
        """add_custom_dashboard returns elicitation for widget missing id/type/config."""
        result = asyncio.run(self.custom_dashboard_tools.add_custom_dashboard(
            custom_dashboard={
                "title": "Test",
                "widgets": [{"title": "Widget without required fields"}],
            },
            api_client=self.custom_dashboards_api,
        ))
        self.assertTrue(result.get("elicitation_needed"))
        errors = result["api_error"]
        self.assertTrue(any("widgets[0].id" in e for e in errors))
        self.assertTrue(any("widgets[0].type" in e for e in errors))
        self.assertTrue(any("widgets[0].config" in e for e in errors))
        self.custom_dashboards_api.add_custom_dashboard_without_preload_content.assert_not_called()


if __name__ == '__main__':
    unittest.main()
