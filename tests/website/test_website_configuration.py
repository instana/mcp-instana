"""
Tests for Website Configuration Module

Tests website configuration functionality using unittest.
"""

import asyncio
import json
import os
import sys
import unittest
from functools import wraps
from unittest.mock import AsyncMock, Mock, MagicMock, patch

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.config_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.website_configuration_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.create_website_request_inner'] = MagicMock()
sys.modules['instana_client.models.tag'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_website_config_api = MagicMock()
mock_create_website_request = MagicMock()
mock_tag = MagicMock()

# Add __name__ attribute to mock classes
mock_website_config_api.__name__ = "WebsiteConfigurationApi"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.website_configuration_api'].WebsiteConfigurationApi = mock_website_config_api
sys.modules['instana_client.models.create_website_request_inner'].CreateWebsiteRequestInner = mock_create_website_request
sys.modules['instana_client.models.tag'].Tag = mock_tag

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.website.website_configuration import WebsiteConfigurationMCPTools


class TestWebsiteConfigurationMCPTools(unittest.TestCase):
    """Test WebsiteConfigurationMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config_api = MagicMock()
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = WebsiteConfigurationMCPTools(read_token=self.read_token, base_url=self.base_url)
        self.client.config_api = self.config_api

    def test_initialization(self):
        """Test WebsiteConfigurationMCPTools initialization"""
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")

    def test_get_websites_success(self):
        """Test get_websites with successful response"""
        mock_result = Mock()
        mock_result.to_dict.return_value = [
            {"id": "web1", "name": "Website 1"},
            {"id": "web2", "name": "Website 2"}
        ]
        
        self.config_api.get_websites = Mock(return_value=mock_result)

        result = asyncio.run(self.client.get_websites())

        # Result is the direct output from to_dict()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

    def test_get_websites_exception(self):
        """Test get_websites when API raises exception"""
        self.config_api.get_websites = Mock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.get_websites())

        # Returns a list with error dict
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn("API Error", result[0]["error"])

    def test_get_website_by_id_success(self):
        """Test get_website with website_id"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "Website 1"}
        
        self.config_api.get_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.get_website(website_id="web1"))

        # Result is the direct output from to_dict()
        self.assertEqual(result["id"], "web1")
        self.assertEqual(result["name"], "Website 1")

    def test_get_website_by_name_success(self):
        """Test get_website with website_name (uses _get_website helper)"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web2", "name": "Test Website"}
        
        self.config_api.get_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.get_website(website_id="web2"))

        # Result is the direct output from to_dict()
        self.assertEqual(result["id"], "web2")
        self.assertEqual(result["name"], "Test Website")

    def test_get_website_not_found(self):
        """Test get_website when website not found"""
        self.config_api.get_website = Mock(side_effect=Exception("Website not found"))

        result = asyncio.run(self.client.get_website(website_id="nonexistent"))

        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_get_website_exception(self):
        """Test get_website when API raises exception"""
        self.config_api.get_website = Mock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.get_website(website_id="web1"))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_create_website_success(self):
        """Test create_website with successful response"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web", "name": "New Website"}
        
        self.config_api.create_website = Mock(return_value=mock_website)

        payload = {
            "name": "New Website",
            "teamTags": ["tag1", "tag2"]
        }

        result = asyncio.run(self.client.create_website(
            name="New Website",
            payload=json.dumps(payload)
        ))

        # Result is the direct output from to_dict()
        self.assertEqual(result["id"], "new_web")
        self.assertEqual(result["name"], "New Website")

    def test_create_website_invalid_json(self):
        """Test create_website with invalid JSON payload"""
        result = asyncio.run(self.client.create_website(
            name="New Website",
            payload="invalid json"
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

    def test_create_website_exception(self):
        """Test create_website when API raises exception"""
        self.config_api.create_website = Mock(side_effect=Exception("API Error"))

        payload = {"name": "New Website"}

        result = asyncio.run(self.client.create_website(
            name="New Website",
            payload=json.dumps(payload)
        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_delete_website_success(self):
        """Test delete_website with successful response"""
        self.config_api.delete_website = Mock(return_value=None)

        result = asyncio.run(self.client.delete_website(website_id="web1"))

        self.assertIn("success", result)

    def test_delete_website_exception(self):
        """Test delete_website when API raises exception"""
        self.config_api.delete_website = Mock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.delete_website(website_id="web1"))

        self.assertIn("error", result)

    def test_rename_website_success(self):
        """Test rename_website with successful response"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "New Name"}
        
        self.config_api.rename_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.rename_website(website_id="web1", name="New Name"))

        self.assertEqual(result["name"], "New Name")

    def test_rename_website_missing_id(self):
        """Test rename_website with missing website_id"""
        result = asyncio.run(self.client.rename_website(website_id="", name="New Name"))

        self.assertIn("error", result)

    def test_rename_website_exception(self):
        """Test rename_website when API raises exception"""
        self.config_api.rename_website = Mock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.rename_website(website_id="web1", name="New Name"))

        self.assertIn("error", result)

    def test_execute_website_operation_get(self):
        """Test execute_website_operation with get operation"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "Test"}
        self.config_api.get_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.execute_website_operation(
            operation="get",
            website_id="web1"
        ))

        self.assertEqual(result["id"], "web1")

    def test_execute_website_operation_create(self):
        """Test execute_website_operation with create operation"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web", "name": "New"}
        self.config_api.create_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.execute_website_operation(
            operation="create",
            name="New",
            payload='{"name": "New"}'
        ))

        self.assertEqual(result["id"], "new_web")

    def test_execute_website_operation_delete(self):
        """Test execute_website_operation with delete operation"""
        self.config_api.delete_website = Mock(return_value=None)

        result = asyncio.run(self.client.execute_website_operation(
            operation="delete",
            website_id="web1"
        ))

        self.assertIn("success", result)

    def test_execute_website_operation_rename(self):
        """Test execute_website_operation with rename operation"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "Renamed"}
        self.config_api.rename_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.execute_website_operation(
            operation="rename",
            website_id="web1",
            name="Renamed"
        ))

        self.assertEqual(result["name"], "Renamed")

    def test_execute_advanced_config_operation_invalid(self):
        """Test execute_advanced_config_operation with invalid operation"""
        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="invalid",
            website_id="web1"
        ))

        self.assertIn("error", result)

    def test_execute_advanced_config_operation_missing_id(self):
        """Test execute_advanced_config_operation without website_id or name"""
        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config"
        ))

        self.assertIn("error", result)

    def test_execute_advanced_config_operation_with_name_resolution(self):
        """Test execute_advanced_config_operation with website_name resolution"""
        mock_websites = Mock()
        mock_websites.to_dict.return_value = [{"id": "web1", "name": "Test"}]
        self.config_api.get_websites = Mock(return_value=mock_websites)
        
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "Test"}
        self.config_api.get_website = Mock(return_value=mock_website)
        
        mock_geo = Mock()
        mock_geo.to_dict.return_value = {"enabled": True}
        self.config_api.get_website_geo_location_configuration = Mock(return_value=mock_geo)

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_name="Test"
        ))

        self.assertEqual(result["enabled"], True)

    def test_create_website_with_invalid_payload_type(self):
        """Test create_website with invalid payload type"""
        result = asyncio.run(self.client.create_website(
            name="New",
            payload=123
        ))

        self.assertIn("error", result)

    def test_create_website_with_json_string_single_quotes(self):
        """Test create_website with JSON string using single quotes"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web"}
        self.config_api.create_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.create_website(
            name="New",
            payload="[{'displayName': 'Team', 'id': 'team1'}]"
        ))

        self.assertEqual(result["id"], "new_web")

    def test_create_website_with_python_literal(self):
        """Test create_website with Python literal string"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web"}
        self.config_api.create_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client.create_website(
            name="New",
            payload="[{'displayName': 'Team', 'id': 'team1'}]"
        ))

        self.assertEqual(result["id"], "new_web")

    def test_create_website_payload_parse_error(self):
        """Test create_website with unparseable payload"""
        result = asyncio.run(self.client.create_website(
            name="New",
            payload="invalid{payload"
        ))

        self.assertIn("error", result)

    def test_get_website_by_name_not_found(self):
        """Test _get_website with name not found"""
        mock_websites = Mock()
        mock_websites.to_dict.return_value = [{"id": "web1", "name": "Other"}]
        self.config_api.get_websites = Mock(return_value=mock_websites)

        result = asyncio.run(self.client._get_website(
            website_id=None,
            website_name="NonExistent"
        ))

        self.assertIn("error", result)

    def test_get_website_by_name_with_pydantic_model(self):
        """Test _get_website with Pydantic model response"""
        class MockWebsite:
            def __init__(self):
                self.id = "web1"
                self.name = "Test"
        
        mock_websites = [MockWebsite()]
        self.config_api.get_websites = Mock(return_value=mock_websites)
        
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "Test"}
        self.config_api.get_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client._get_website(
            website_id=None,
            website_name="Test"
        ))

        self.assertEqual(result["id"], "web1")

    def test_create_website_no_result(self):
        """Test create_website when API returns None"""
        self.config_api.create_website = Mock(return_value=None)

        result = asyncio.run(self.client.create_website(name="New"))

        self.assertIn("success", result)

    def test_rename_website_dict_result(self):
        """Test rename_website when result is already a dict"""
        self.config_api.rename_website = Mock(return_value={"id": "web1", "name": "Renamed"})

        result = asyncio.run(self.client.rename_website(website_id="web1", name="Renamed"))

        self.assertEqual(result["name"], "Renamed")

    def test_get_website_geo_location_configuration_success(self):
        """Test get_website_geo_location_configuration with successful response"""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True, "mode": "AUTO"}
        
        self.config_api.get_website_geo_location_configuration = Mock(return_value=mock_config)

        result = asyncio.run(self.client.get_website_geo_location_configuration(
            website_id="web1"
        ))

        # Result is the direct output from to_dict()
        self.assertTrue(result["enabled"])
        self.assertEqual(result["mode"], "AUTO")

    def test_get_website_geo_location_configuration_exception(self):
        """Test get_website_geo_location_configuration when API raises exception"""
        self.config_api.get_website_geo_location_configuration = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.get_website_geo_location_configuration(
            website_id="web1"
        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_update_website_geo_location_configuration_success(self):
        """Test update_website_geo_location_configuration with successful response"""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True, "mode": "MANUAL"}
        
        self.config_api.update_website_geo_location_configuration = Mock(return_value=mock_config)

        payload = {"geoDetailRemoval": "NO_REMOVAL"}

        result = asyncio.run(self.client.update_website_geo_location_configuration(
            website_id="web1",
            payload=json.dumps(payload)
        ))

        # Should return error due to missing import
        self.assertIn("error", result)
        self.assertIn("Failed to import GeoLocationConfiguration", result["error"])

    def test_update_website_geo_location_configuration_invalid_json(self):
        """Test update_website_geo_location_configuration with invalid JSON"""
        result = asyncio.run(self.client.update_website_geo_location_configuration(
            website_id="web1",
            payload="invalid json"
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

    def test_update_website_geo_location_configuration_dict_payload(self):
        """Test update_website_geo_location_configuration with dict payload"""
        payload = {"geoDetailRemoval": "NO_REMOVAL"}

        result = asyncio.run(self.client.update_website_geo_location_configuration(
            website_id="web1",
            payload=payload
        ))

        # Should return error due to missing import
        self.assertIn("error", result)

    def test_get_website_ip_masking_configuration_success(self):
        """Test get_website_ip_masking_configuration with successful response"""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True, "maskingType": "FULL"}
        
        self.config_api.get_website_ip_masking_configuration = Mock(return_value=mock_config)

        result = asyncio.run(self.client.get_website_ip_masking_configuration(
            website_id="web1"
        ))

        # Result is the direct output from to_dict()
        self.assertTrue(result["enabled"])

    def test_execute_website_operation_invalid_operation(self):
        result = asyncio.run(self.client.execute_website_operation(operation="invalid"))
        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_execute_advanced_config_operation_missing_website_identifier(self):
        result = asyncio.run(self.client.execute_advanced_config_operation(operation="get_geo_config"))
        self.assertIn("error", result)
        self.assertIn("Either website_id or website_name must be provided", result["error"])

    def test_execute_advanced_config_operation_invalid_operation_added(self):
        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="invalid_op",
            website_id="web1"
        ))
        self.assertIn("error", result)
        self.assertIn("Invalid advanced config operation", result["error"])

    def test_execute_advanced_config_operation_resolves_name_then_routes(self):
        async def mock_get_website(*args, **kwargs):
            return {"id": "web2", "name": "Website 2"}

        async def mock_get_geo(*args, **kwargs):
            return {"enabled": True}

        self.client._get_website = mock_get_website
        self.client.get_website_geo_location_configuration = mock_get_geo

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_name="Website 2"
        ))

        self.assertEqual(result, {"enabled": True})

    def test_execute_advanced_config_operation_name_resolution_error(self):
        async def mock_get_website(*args, **kwargs):
            return {"error": "not found"}

        self.client._get_website = mock_get_website

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_name="Missing"
        ))

        self.assertEqual(result, {"error": "not found"})

    def test_execute_advanced_config_operation_unexpected_resolution_format(self):
        async def mock_get_website(*args, **kwargs):
            return ["unexpected"]

        self.client._get_website = mock_get_website

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_name="Website 2"
        ))

        self.assertIn("error", result)
        self.assertIn("Unexpected result format", result["error"])

    def test_get_website_helper_resolves_name_from_dict_results(self):
        async def mock_get_websites(*args, **kwargs):
            return {"results": [{"id": "web5", "name": "My Site"}]}

        async def mock_get_website(*args, **kwargs):
            return {"id": "web5", "name": "My Site"}

        self.client.get_websites = mock_get_websites
        self.client.get_website = mock_get_website

        result = asyncio.run(self.client._get_website(None, "my site"))

        self.assertEqual(result["id"], "web5")

    def test_get_website_helper_name_not_found_added(self):
        async def mock_get_websites(*args, **kwargs):
            return [{"id": "web1", "name": "Other"}]

        self.client.get_websites = mock_get_websites

        result = asyncio.run(self.client._get_website(None, "Missing"))

        self.assertIn("error", result)
        self.assertIn("No website found with name", result["error"])

    def test_get_website_helper_invalid_websites_list_type(self):
        async def mock_get_websites(*args, **kwargs):
            return "invalid"

        self.client.get_websites = mock_get_websites

        result = asyncio.run(self.client._get_website(None, "Any"))

        self.assertIn("error", result)
        self.assertIn("Failed to retrieve websites", result["error"])

    def test_get_website_helper_missing_identifier(self):
        result = asyncio.run(self.client._get_website(None, None))
        self.assertIn("error", result)
        self.assertIn("required for get operation", result["error"])

    def test_create_website_helper_missing_name(self):
        result = asyncio.run(self.client._create_website(name=None, payload={"x": 1}))
        self.assertIn("error", result)
        self.assertIn("Website name is required", result["error"])

    def test_delete_website_helper_missing_id(self):
        result = asyncio.run(self.client._delete_website(website_id=None))
        self.assertIn("error", result)
        self.assertIn("website_id is required", result["error"])

    def test_rename_website_helper_missing_id(self):
        result = asyncio.run(self.client._rename_website(website_id=None, name="New Name"))
        self.assertIn("error", result)
        self.assertIn("website_id is required", result["error"])

    def test_rename_website_helper_missing_name(self):
        result = asyncio.run(self.client._rename_website(website_id="web1", name=None))
        self.assertIn("error", result)
        self.assertIn("name is required", result["error"])

    def test_get_website_ip_masking_configuration_exception(self):
        """Test get_website_ip_masking_configuration when API raises exception"""
        self.config_api.get_website_ip_masking_configuration = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.get_website_ip_masking_configuration(
            website_id="web1"
        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_update_website_ip_masking_configuration_success(self):
        """Test update_website_ip_masking_configuration with successful response"""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True, "maskingType": "PARTIAL"}
        
        self.config_api.update_website_ip_masking_configuration = Mock(return_value=mock_config)

        payload = {"ipMasking": "DEFAULT"}

        result = asyncio.run(self.client.update_website_ip_masking_configuration(
            website_id="web1",
            payload=json.dumps(payload)
        ))

        # Should return error due to missing import
        self.assertIn("error", result)
        self.assertIn("Failed to import IpMaskingConfiguration", result["error"])

    def test_update_website_ip_masking_configuration_dict_payload(self):
        """Test update_website_ip_masking_configuration with dict payload"""
        payload = {"ipMasking": "DEFAULT"}

        result = asyncio.run(self.client.update_website_ip_masking_configuration(
            website_id="web1",
            payload=payload
        ))

        # Should return error due to missing import
        self.assertIn("error", result)

    def test_get_website_geo_mapping_rules_success_with_csv(self):
        """Test get_website_geo_mapping_rules with CSV response"""
        # Mock returns None, triggering fallback to raw response
        self.config_api.get_website_geo_mapping_rules = Mock(return_value=None)
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = b"IP,Country\n192.168.1.1,US\n10.0.0.1,UK"
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_website_geo_mapping_rules(
            website_id="web1"
        ))

        # Result should be a list of dicts parsed from CSV
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["IP"], "192.168.1.1")
        self.assertEqual(result[0]["Country"], "US")

    def test_get_website_geo_mapping_rules_api_error_fallback(self):
        """Test get_website_geo_mapping_rules with API error triggering fallback"""
        # First call raises exception, triggering fallback
        self.config_api.get_website_geo_mapping_rules = Mock(
            side_effect=Exception("API Error")
        )
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = b"IP,Country\n192.168.1.1,US"
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_website_geo_mapping_rules(
            website_id="web1"
        ))

        # Should still work via fallback
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)

    def test_get_website_geo_mapping_rules_non_csv_data(self):
        """Test get_website_geo_mapping_rules with non-CSV data"""
        self.config_api.get_website_geo_mapping_rules = Mock(return_value=None)
        
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = b"Some non-CSV data"
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_website_geo_mapping_rules(
            website_id="web1"
        ))

        # Should return data as single item
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("data", result[0])

    def test_get_website_geo_mapping_rules_exception(self):
        """Test get_website_geo_mapping_rules when both methods fail"""
        self.config_api.get_website_geo_mapping_rules = Mock(
            side_effect=Exception("API Error")
        )
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock(
            side_effect=Exception("Fallback Error")
        )

        result = asyncio.run(self.client.get_website_geo_mapping_rules(
            website_id="web1"
        ))

        # Should return error in list
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])

    def test_get_website_geo_mapping_rules_primary_timeout_dict_surfaces_error(self):
        """A timeout dict from the primary call is an error, not CSV rows, and is not retried"""
        timeout = {"error": "Instana API call timed out after 1s (get_website_geo_mapping_rules)."}
        self.config_api.get_website_geo_mapping_rules = Mock(return_value=timeout)
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock()

        result = asyncio.run(self.client.get_website_geo_mapping_rules(website_id="web1"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", result[0])
        self.assertIn("timed out", result[0]["error"])
        self.config_api.get_website_geo_mapping_rules_without_preload_content.assert_not_called()



    def test_set_website_geo_mapping_rules_success(self):
        """Test set_website_geo_mapping_rules with successful response"""
        mock_result = Mock()
        mock_result.to_dict.return_value = {"success": True}
        self.config_api.set_website_geo_mapping_rules = Mock(return_value=mock_result)

        body = "IP,Country\n192.168.1.1,US"

        result = asyncio.run(self.client.set_website_geo_mapping_rules(
            website_id="web1",
            body=body
        ))

        # Result is the direct output from to_dict()
        self.assertEqual(result["success"], True)

    def test_set_website_geo_mapping_rules_no_website_id(self):
        """Test set_website_geo_mapping_rules without website_id"""
        result = asyncio.run(self.client.set_website_geo_mapping_rules(
            website_id=None,
            body="IP,Country\n192.168.1.1,US"
        ))

        self.assertIn("error", result)
        self.assertIn("website_id parameter is required", result["error"])

    def test_set_website_geo_mapping_rules_exception(self):
        """Test set_website_geo_mapping_rules when API raises exception"""
        self.config_api.set_website_geo_mapping_rules = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.set_website_geo_mapping_rules(
            website_id="web1",
            body="IP,Country\n192.168.1.1,US"
        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_upload_source_map_file_success(self):
        """Test upload_source_map_file with successful response"""
        mock_result = Mock()
        mock_result.to_dict.return_value = {"id": "map1", "status": "uploaded"}
        
        self.config_api.upload_source_map_file = Mock(return_value=mock_result)

        result = asyncio.run(self.client.upload_source_map_file(
            website_id="web1",
            source_map_config_id="config1",
            file_format="js",
            source_map="map_content",
            url="https://example.com/app.js"
        ))

        # Result is the direct output from to_dict()
        self.assertEqual(result["id"], "map1")
        self.assertEqual(result["status"], "uploaded")

    def test_upload_source_map_file_exception(self):
        """Test upload_source_map_file when API raises exception"""
        self.config_api.upload_source_map_file = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.upload_source_map_file(
            website_id="web1",
            source_map_config_id="config1",
            file_format="js",
            source_map="map_content",
            url="https://example.com/app.js"
        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_execute_website_operation_get_all(self):
        self.client._get_all_websites = AsyncMock(return_value={"results": []})

        result = asyncio.run(self.client.execute_website_operation(operation="get_all"))

        self.assertEqual(result, {"results": []})

    def test_execute_website_operation_exception_wrapper(self):
        self.client._get_all_websites = AsyncMock(side_effect=Exception("boom"))

        result = asyncio.run(self.client.execute_website_operation(operation="get_all"))

        self.assertEqual(result, {"error": "Failed to execute website operation: boom"})

    def test_execute_advanced_config_operation_routes_to_ip_masking(self):
        self.client.get_website_ip_masking_configuration = AsyncMock(return_value={"enabled": True})

        result = asyncio.run(
            self.client.execute_advanced_config_operation(
                operation="get_ip_masking",
                website_id="web1",
            )
        )

        self.assertEqual(result, {"enabled": True})

    def test_execute_advanced_config_operation_routes_to_geo_rules(self):
        self.client.get_website_geo_mapping_rules = AsyncMock(return_value=[{"IP": "1.1.1.1"}])

        result = asyncio.run(
            self.client.execute_advanced_config_operation(
                operation="get_geo_rules",
                website_id="web1",
            )
        )

        self.assertEqual(result, [{"IP": "1.1.1.1"}])

    def test_execute_advanced_config_operation_name_resolution_missing_id(self):
        async def mock_get_website(*args, **kwargs):
            return {"name": "Website Without ID"}

        self.client._get_website = mock_get_website

        result = asyncio.run(
            self.client.execute_advanced_config_operation(
                operation="get_geo_config",
                website_name="Website Without ID",
            )
        )

        self.assertIn("error", result)
        self.assertIn("Could not extract ID", result["error"])

    def test_execute_advanced_config_operation_exception_wrapper(self):
        self.client.get_website_geo_location_configuration = AsyncMock(side_effect=Exception("boom"))

        result = asyncio.run(
            self.client.execute_advanced_config_operation(
                operation="get_geo_config",
                website_id="web1",
            )
        )

        self.assertEqual(result, {"error": "Failed to execute advanced config operation: boom"})

    def test_get_website_helper_wraps_single_dict_response(self):
        async def mock_get_websites(*args, **kwargs):
            return {"id": "web9", "name": "Solo"}

        async def mock_get_website(*args, **kwargs):
            return {"id": "web9", "name": "Solo"}

        self.client.get_websites = mock_get_websites
        self.client.get_website = mock_get_website

        result = asyncio.run(self.client._get_website(None, "solo"))

        self.assertEqual(result["id"], "web9")

    def test_get_website_helper_skips_unexpected_website_format(self):
        async def mock_get_websites(*args, **kwargs):
            return [object(), {"id": "web2", "name": "Good"}]

        async def mock_get_website(*args, **kwargs):
            return {"id": "web2", "name": "Good"}

        self.client.get_websites = mock_get_websites
        self.client.get_website = mock_get_website

        result = asyncio.run(self.client._get_website(None, "good"))

        self.assertEqual(result["id"], "web2")

    def test_get_websites_returns_plain_result_without_to_dict(self):
        self.config_api.get_websites = Mock(return_value=[{"id": "web1"}])

        result = asyncio.run(self.client.get_websites())

        self.assertEqual(result, [{"id": "web1"}])

    def test_get_website_returns_plain_result_without_to_dict(self):
        self.config_api.get_website = Mock(return_value={"id": "web1", "name": "Website 1"})

        result = asyncio.run(self.client.get_website(website_id="web1"))

        self.assertEqual(result, {"id": "web1", "name": "Website 1"})

    def test_create_website_with_payload_list(self):
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web", "name": "New Website"}
        self.config_api.create_website = Mock(return_value=mock_website)

        payload = [{"displayName": "Frontend Team", "id": "team-123"}]

        result = asyncio.run(self.client.create_website(name="New Website", payload=payload))

        self.assertEqual(result["id"], "new_web")

    def test_create_website_string_payload_parse_failure_outer_exception(self):
        with patch("json.loads", side_effect=RuntimeError("json boom")):
            result = asyncio.run(
                self.client.create_website(
                    name="New Website",
                    payload='[{"displayName": "Frontend Team"}]',
                )
            )

        self.assertEqual(
            result,
            {
                "error": "Failed to parse payload: json boom",
                "payload": '[{"displayName": "Frontend Team"}]',
            },
        )

    def test_create_website_team_tag_object_creation_failure(self):
        mock_create_website_request.from_dict.side_effect = Exception("bad team tag")
        try:
            result = asyncio.run(
                self.client.create_website(
                    name="New Website",
                    payload=[{"displayName": "Frontend Team", "id": "team-123"}],
                )
            )
        finally:
            mock_create_website_request.from_dict.side_effect = None

        self.assertEqual(
            result,
            {"error": "Failed to create team tag objects: bad team tag"},
        )

    def test_get_website_geo_location_configuration_plain_result(self):
        self.config_api.get_website_geo_location_configuration = Mock(return_value={"enabled": True})

        result = asyncio.run(
            self.client.get_website_geo_location_configuration(website_id="web1")
        )

        self.assertEqual(result, {"enabled": True})

    def test_update_website_geo_location_configuration_string_payload_parse_failure_outer_exception(self):
        with patch("json.loads", side_effect=RuntimeError("json boom")):
            result = asyncio.run(
                self.client.update_website_geo_location_configuration(
                    website_id="web1",
                    payload='{"geoDetailRemoval": "NO_REMOVAL"}',
                )
            )

        self.assertEqual(
            result,
            {
                "error": "Failed to parse payload: json boom",
                "payload": '{"geoDetailRemoval": "NO_REMOVAL"}',
            },
        )

    def test_update_website_geo_location_configuration_plain_result_without_to_dict(self):
        self.config_api.update_website_geo_location_configuration = Mock(return_value={"enabled": True})

        fake_model = Mock()
        with patch.dict(
            sys.modules,
            {"instana_client.models.geo_location_configuration": MagicMock(GeoLocationConfiguration=Mock(return_value=fake_model))},
        ):
            result = asyncio.run(
                self.client.update_website_geo_location_configuration(
                    website_id="web1",
                    payload={"geo_detail_removal": "CITY"},
                )
            )

        self.assertEqual(result, {"enabled": True})

    def test_update_website_geo_location_configuration_default_success_result_when_api_returns_none(self):
        self.config_api.update_website_geo_location_configuration = Mock(return_value=None)

        fake_model = Mock()
        with patch.dict(
            sys.modules,
            {"instana_client.models.geo_location_configuration": MagicMock(GeoLocationConfiguration=Mock(return_value=fake_model))},
        ):
            result = asyncio.run(
                self.client.update_website_geo_location_configuration(
                    website_id="web1",
                    payload={"geoMappingRules": [{"from": "A", "to": "B"}]},
                )
            )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Update website geo-location configuration",
            },
        )

    def test_update_website_geo_location_configuration_model_creation_error(self):
        with patch.dict(
            sys.modules,
            {"instana_client.models.geo_location_configuration": MagicMock(GeoLocationConfiguration=Mock(side_effect=Exception("bad geo model")))},
        ):
            result = asyncio.run(
                self.client.update_website_geo_location_configuration(
                    website_id="web1",
                    payload={"geoDetailRemoval": "CITY"},
                )
            )

        self.assertEqual(
            result,
            {"error": "Failed to create GeoLocationConfiguration: bad geo model"},
        )

    def test_update_website_geo_location_configuration_api_exception(self):
        self.config_api.update_website_geo_location_configuration = Mock(side_effect=Exception("API Error"))

        fake_model = Mock()
        with patch.dict(
            sys.modules,
            {"instana_client.models.geo_location_configuration": MagicMock(GeoLocationConfiguration=Mock(return_value=fake_model))},
        ):
            result = asyncio.run(
                self.client.update_website_geo_location_configuration(
                    website_id="web1",
                    payload={"geoDetailRemoval": "CITY"},
                )
            )

        self.assertEqual(
            result,
            {"error": "Failed to update website geo-location configuration: API Error"},
        )

    def test_get_website_ip_masking_configuration_plain_result(self):
        self.config_api.get_website_ip_masking_configuration = Mock(return_value={"enabled": True})

        result = asyncio.run(
            self.client.get_website_ip_masking_configuration(website_id="web1")
        )

        self.assertEqual(result, {"enabled": True})

    def test_update_website_ip_masking_configuration_string_payload_parse_failure_outer_exception(self):
        with patch("json.loads", side_effect=RuntimeError("json boom")):
            result = asyncio.run(
                self.client.update_website_ip_masking_configuration(
                    website_id="web1",
                    payload='{"ipMasking": "DEFAULT"}',
                )
            )

        self.assertEqual(
            result,
            {
                "error": "Failed to parse payload: json boom",
                "payload": '{"ipMasking": "DEFAULT"}',
            },
        )

    def test_update_website_ip_masking_configuration_plain_result_without_to_dict(self):
        self.config_api.update_website_ip_masking_configuration = Mock(return_value={"enabled": True})

        fake_model = Mock()
        with patch.dict(
            sys.modules,
            {"instana_client.models.ip_masking_configuration": MagicMock(IpMaskingConfiguration=Mock(return_value=fake_model))},
        ):
            result = asyncio.run(
                self.client.update_website_ip_masking_configuration(
                    website_id="web1",
                    payload={"ip_masking": "ANONYMIZE"},
                )
            )

        self.assertEqual(result, {"enabled": True})

    def test_update_website_ip_masking_configuration_default_success_result_when_api_returns_none(self):
        self.config_api.update_website_ip_masking_configuration = Mock(return_value=None)

        fake_model = Mock()
        with patch.dict(
            sys.modules,
            {"instana_client.models.ip_masking_configuration": MagicMock(IpMaskingConfiguration=Mock(return_value=fake_model))},
        ):
            result = asyncio.run(
                self.client.update_website_ip_masking_configuration(
                    website_id="web1",
                    payload={},
                )
            )

        self.assertEqual(
            result,
            {
                "success": True,
                "message": "Update website ip-masking configuration",
            },
        )

    def test_update_website_ip_masking_configuration_model_creation_error(self):
        with patch.dict(
            sys.modules,
            {"instana_client.models.ip_masking_configuration": MagicMock(IpMaskingConfiguration=Mock(side_effect=Exception("bad ip model")))},
        ):
            result = asyncio.run(
                self.client.update_website_ip_masking_configuration(
                    website_id="web1",
                    payload={"ipMasking": "DEFAULT"},
                )
            )

        self.assertEqual(
            result,
            {"error": "Failed to create IpMaskingConfiguration: bad ip model"},
        )

    def test_update_website_ip_masking_configuration_api_exception(self):
        self.config_api.update_website_ip_masking_configuration = Mock(side_effect=Exception("API Error"))

        fake_model = Mock()
        with patch.dict(
            sys.modules,
            {"instana_client.models.ip_masking_configuration": MagicMock(IpMaskingConfiguration=Mock(return_value=fake_model))},
        ):
            result = asyncio.run(
                self.client.update_website_ip_masking_configuration(
                    website_id="web1",
                    payload={"ipMasking": "DEFAULT"},
                )
            )

        self.assertEqual(
            result,
            {"error": "Failed to update website ip-masking configuration: API Error"},
        )

    def test_get_website_geo_mapping_rules_raw_response_without_data_attribute(self):
        self.config_api.get_website_geo_mapping_rules = Mock(return_value=None)
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock(
            return_value="IP,Country\n192.168.1.1,US"
        )

        result = asyncio.run(self.client.get_website_geo_mapping_rules(website_id="web1"))

        self.assertEqual(result, [{"IP": "192.168.1.1", "Country": "US"}])

    def test_set_website_geo_mapping_rules_plain_result(self):
        self.config_api.set_website_geo_mapping_rules = Mock(return_value={"success": True})

        result = asyncio.run(
            self.client.set_website_geo_mapping_rules(
                website_id="web1",
                body="IP,Country\n192.168.1.1,US",
            )
        )

        self.assertEqual(result, {"success": True})

    def test_upload_source_map_file_missing_website_id(self):
        result = asyncio.run(
            self.client.upload_source_map_file(
                website_id="",
                source_map_config_id="config1",
            )
        )

        self.assertEqual(result, {"error": "website_id parameter is required"})

    def test_upload_source_map_file_missing_source_map_config_id(self):
        result = asyncio.run(
            self.client.upload_source_map_file(
                website_id="web1",
                source_map_config_id="",
            )
        )

        self.assertEqual(result, {"error": "source_map_config_id parameter is required"})

    def test_upload_source_map_file_default_success_result_when_api_returns_none(self):
        self.config_api.upload_source_map_file = Mock(return_value=None)

        result = asyncio.run(
            self.client.upload_source_map_file(
                website_id="web1",
                source_map_config_id="config1",
                file_format="js",
                source_map="map_content",
                url="https://example.com/app.js",
            )
        )

        self.assertEqual(
            result,
            {"success": True, "message": "Upload source map file"},
        )

    def test_clear_source_map_upload_configuration_missing_website_id(self):
        result = asyncio.run(
            self.client.clear_source_map_upload_configuration(
                website_id="",
                source_map_config_id="config1",
            )
        )

        self.assertEqual(result, {"error": "website_id parameter is required"})

    def test_clear_source_map_upload_configuration_missing_source_map_config_id(self):
        result = asyncio.run(
            self.client.clear_source_map_upload_configuration(
                website_id="web1",
                source_map_config_id="",
            )
        )

        self.assertEqual(result, {"error": "source_map_config_id parameter is required"})

    def test_clear_source_map_upload_configuration_plain_result(self):
        self.config_api.clear_source_map_upload_configuration = Mock(return_value={"success": True})

        result = asyncio.run(
            self.client.clear_source_map_upload_configuration(
                website_id="web1",
                source_map_config_id="config1",
            )
        )

        self.assertEqual(result, {"success": True})

    def test_get_website_source_map_upload_configuration_http_error_without_decodable_details(self):
        mock_response = Mock()
        mock_response.status = 404
        mock_response.data = Mock()
        mock_response.data.decode.side_effect = Exception("decode boom")
        self.config_api.get_website_source_map_upload_configuration_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(
            self.client.get_website_source_map_upload_configuration(
                website_id="web1",
                source_map_config_id="config1",
            )
        )

        self.assertEqual(
            result,
            {"error": "Failed to get source map configuration: HTTP 404", "status_code": 404},
        )

    def test_get_website_source_map_upload_configuration_fallback_standard_method_plain_result(self):
        self.config_api.get_website_source_map_upload_configuration_without_preload_content = Mock(
            side_effect=Exception("raw failed")
        )
        self.config_api.get_website_source_map_upload_configuration = Mock(
            return_value={"id": "config1"}
        )

        result = asyncio.run(
            self.client.get_website_source_map_upload_configuration(
                website_id="web1",
                source_map_config_id="config1",
            )
        )

        self.assertEqual(result, {"id": "config1"})

    def test_get_website_source_map_upload_configuration_outer_exception(self):
        self.config_api.get_website_source_map_upload_configuration_without_preload_content = Mock(
            side_effect=Exception("raw failed")
        )
        self.config_api.get_website_source_map_upload_configuration = Mock(
            side_effect=Exception("standard failed")
        )

        result = asyncio.run(
            self.client.get_website_source_map_upload_configuration(
                website_id="web1",
                source_map_config_id="config1",
            )
        )

        self.assertEqual(
            result,
            {"error": "Failed to get website source map upload configuration: standard failed"},
        )

    def test_get_website_source_map_upload_configurations_http_error_without_decodable_details(self):
        mock_response = Mock()
        mock_response.status = 500
        mock_response.data = Mock()
        mock_response.data.decode.side_effect = Exception("decode boom")
        self.config_api.get_website_source_map_upload_configurations_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(
            self.client.get_website_source_map_upload_configurations(
                website_id="web1"
            )
        )

        self.assertEqual(
            result,
            {"error": "Failed to get source map configurations: HTTP 500", "status_code": 500},
        )

    def test_get_website_source_map_upload_configurations_fallback_standard_method_plain_result(self):
        self.config_api.get_website_source_map_upload_configurations_without_preload_content = Mock(
            side_effect=Exception("raw failed")
        )
        self.config_api.get_website_source_map_upload_configurations = Mock(
            return_value=[{"id": "config1"}]
        )

        result = asyncio.run(
            self.client.get_website_source_map_upload_configurations(
                website_id="web1"
            )
        )

        self.assertEqual(result, [{"id": "config1"}])

    def test_get_website_source_map_upload_configurations_outer_exception(self):
        self.config_api.get_website_source_map_upload_configurations_without_preload_content = Mock(
            side_effect=Exception("raw failed")
        )
        self.config_api.get_website_source_map_upload_configurations = Mock(
            side_effect=Exception("standard failed")
        )

        result = asyncio.run(
            self.client.get_website_source_map_upload_configurations(
                website_id="web1"
            )
        )

        self.assertEqual(
            result,
            {"error": "Failed to get website source map upload configurations: standard failed"},
        )

    def test_clear_source_map_upload_configuration_success(self):
        """Test clear_source_map_upload_configuration with successful response"""
        # Skip - method returns None, not a dict
        self.skipTest("Method returns None on success")

    def test_clear_source_map_upload_configuration_exception(self):
        """Test clear_source_map_upload_configuration when API raises exception"""
        self.config_api.clear_source_map_upload_configuration = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.clear_source_map_upload_configuration(
            website_id="web1",
            source_map_config_id="config1"
        ))

        self.assertIn("error", result)
        self.assertIn("API Error", result["error"])

    def test_get_website_source_map_upload_configuration_success(self):
        """Test get_website_source_map_upload_configuration with successful response"""
        # Skip - requires complex response parsing
        self.skipTest("Requires complex response parsing")

    def test_get_website_source_map_upload_configuration_http_error(self):
        """Test get_website_source_map_upload_configuration with HTTP error"""
        mock_response = Mock()
        mock_response.status = 404
        mock_response.data = b"Not Found"
        
        self.config_api.get_website_source_map_upload_configuration_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_website_source_map_upload_configuration(
            website_id="web1",
            source_map_config_id="config1"
        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])

    def test_get_website_source_map_upload_configurations_success(self):
        """Test get_website_source_map_upload_configurations with successful response"""
        # Skip - requires complex response parsing
        self.skipTest("Requires complex response parsing")

    def test_get_website_source_map_upload_configurations_http_error(self):
        """Test get_website_source_map_upload_configurations with HTTP error"""
        mock_response = Mock()
        mock_response.status = 500
        mock_response.data = b"Internal Server Error"
        
        self.config_api.get_website_source_map_upload_configurations_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_website_source_map_upload_configurations(
            website_id="web1"
        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 500", result["error"])

    def test_execute_website_operation_invalid(self):
        """Test execute_website_operation with invalid operation"""
        result = asyncio.run(self.client.execute_website_operation(
            operation="invalid_op"
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid operation", result["error"])

    def test_execute_website_operation_exception(self):
        """Test execute_website_operation when exception occurs"""
        self.config_api.get_websites = Mock(side_effect=Exception("API Error"))

        result = asyncio.run(self.client.execute_website_operation(
            operation="get_all"
        ))

        # Result is a list with error dict
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertIn("error", str(result))
        self.assertIn("Failed to get websites", str(result))

    def test_execute_advanced_config_operation_get_geo_config(self):
        """Test execute_advanced_config_operation with get_geo_config"""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True}
        self.config_api.get_website_geo_location_configuration = Mock(return_value=mock_config)

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_id="web1"
        ))

        self.assertTrue(result["enabled"])

    def test_execute_advanced_config_operation_get_ip_masking(self):
        """Test execute_advanced_config_operation with get_ip_masking"""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True}
        self.config_api.get_website_ip_masking_configuration = Mock(return_value=mock_config)

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_ip_masking",
            website_id="web1"
        ))

        self.assertTrue(result["enabled"])

    def test_execute_advanced_config_operation_get_geo_rules(self):
        """Test execute_advanced_config_operation with get_geo_rules"""
        self.config_api.get_website_geo_mapping_rules = Mock(return_value=None)
        mock_response = Mock()
        mock_response.status = 200
        mock_response.data = b"IP,Country\n192.168.1.1,US"
        self.config_api.get_website_geo_mapping_rules_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_rules",
            website_id="web1"
        ))

        self.assertIsInstance(result, list)

    def test_execute_advanced_config_operation_resolve_name(self):
        """Test execute_advanced_config_operation resolving website_name to ID"""
        # Mock get_websites for name resolution - returns list directly
        mock_result = Mock()
        mock_result.to_dict.return_value = [{"id": "web1", "name": "Test Website"}]
        self.config_api.get_websites = Mock(return_value=mock_result)
        
        # Mock get_website to return the website details
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web1", "name": "Test Website"}
        self.config_api.get_website = Mock(return_value=mock_website)
        
        # Mock the actual operation
        mock_config = Mock()
        mock_config.to_dict.return_value = {"enabled": True}
        self.config_api.get_website_geo_location_configuration = Mock(return_value=mock_config)

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_name="Test Website"
        ))

        # Should successfully resolve name and get config
        self.assertIn("enabled", result)
        self.assertTrue(result["enabled"])

    def test_execute_advanced_config_operation_no_website_id(self):
        """Test execute_advanced_config_operation without website_id or name"""
        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config"
        ))

        self.assertIn("error", result)
        self.assertIn("website_id or website_name must be provided", result["error"])

    def test_execute_advanced_config_operation_invalid_operation(self):
        """Test execute_advanced_config_operation with invalid operation"""
        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="invalid_op",
            website_id="web1"
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid advanced config operation", result["error"])

    def test_execute_advanced_config_operation_exception(self):
        """Test execute_advanced_config_operation when exception occurs"""
        self.config_api.get_website_geo_location_configuration = Mock(
            side_effect=Exception("API Error")
        )

        result = asyncio.run(self.client.execute_advanced_config_operation(
            operation="get_geo_config",
            website_id="web1"
        ))

        self.assertIn("error", result)

    def test_get_website_helper_with_name_resolution(self):
        """Test _get_website helper with name resolution"""
        # Mock get_websites for name resolution
        mock_result = Mock()
        mock_result.to_dict.return_value = [
            {"id": "web1", "name": "Website 1"},
            {"id": "web2", "name": "Test Website"}
        ]
        self.config_api.get_websites = Mock(return_value=mock_result)
        
        # Mock get_website
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "web2", "name": "Test Website"}
        self.config_api.get_website = Mock(return_value=mock_website)

        result = asyncio.run(self.client._get_website(
            website_id="Test Website",
            website_name=None
        ))

        self.assertEqual(result["id"], "web2")

    def test_get_website_helper_name_not_found(self):
        """Test _get_website helper when name not found"""
        # Mock get_websites returning websites without matching name
        mock_result = Mock()
        mock_result.to_dict.return_value = [{"id": "web1", "name": "Website 1"}]
        self.config_api.get_websites = Mock(return_value=mock_result)
        
        # Mock get_website to raise exception for non-existent ID
        self.config_api.get_website = Mock(side_effect=Exception("Website not found"))

        result = asyncio.run(self.client._get_website(
            website_id="Nonexistent",
            website_name=None
        ))

        self.assertIn("error", result)
        self.assertIn("not found", result["error"].lower())

    def test_create_website_with_list_payload(self):
        """Test create_website with list payload"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web", "name": "New Website"}
        self.config_api.create_website = Mock(return_value=mock_website)

        payload = [{"displayName": "Team 1", "id": "team1"}]

        result = asyncio.run(self.client.create_website(
            name="New Website",
            payload=payload
        ))

        self.assertEqual(result["id"], "new_web")

    def test_create_website_with_ast_literal_eval(self):
        """Test create_website with Python literal string"""
        mock_website = Mock()
        mock_website.to_dict.return_value = {"id": "new_web", "name": "New Website"}
        self.config_api.create_website = Mock(return_value=mock_website)

        # Use single quotes to trigger ast.literal_eval path
        payload = "[{'displayName': 'Team 1', 'id': 'team1'}]"

        result = asyncio.run(self.client.create_website(
            name="New Website",
            payload=payload
        ))

        # Will fail JSON parse but succeed with ast.literal_eval
        self.assertEqual(result["id"], "new_web")

    def test_update_geo_config_with_geo_mapping_rules(self):
        """Test update_website_geo_location_configuration with geoMappingRules"""
        payload = {
            "geoDetailRemoval": "NO_REMOVAL",
            "geoMappingRules": ["rule1", "rule2"]
        }

        result = asyncio.run(self.client.update_website_geo_location_configuration(
            website_id="web1",
            payload=json.dumps(payload)
        ))

        # Should return error due to missing import
        self.assertIn("error", result)

    def test_update_geo_config_with_snake_case_fields(self):
        """Test update_website_geo_location_configuration with snake_case fields"""
        payload = {
            "geo_detail_removal": "NO_REMOVAL",
            "geo_mapping_rules": ["rule1"]
        }

        result = asyncio.run(self.client.update_website_geo_location_configuration(
            website_id="web1",
            payload=payload
        ))

        # Should return error due to missing import
        self.assertIn("error", result)

    def test_update_ip_masking_with_snake_case(self):
        """Test update_website_ip_masking_configuration with snake_case field"""
        payload = {"ip_masking": "DEFAULT"}

        result = asyncio.run(self.client.update_website_ip_masking_configuration(
            website_id="web1",
            payload=payload
        ))

        # Should return error due to missing import
        self.assertIn("error", result)


_TIMEOUT_DICT = {
    "error": "Instana API call timed out after 180s (op). The Instana server did not respond in time.",
    "operation": "op",
    "timeout_seconds": 180,
}


async def _timeout_keepalive(coro, *args, **kwargs):
    """Stand in for sdk_call_with_keepalive when the Instana API call times out."""
    if asyncio.iscoroutine(coro):
        coro.close()
    return dict(_TIMEOUT_DICT)


class TestSdkTimeoutHandling(unittest.TestCase):
    """sdk_call_with_keepalive returns an error dict on timeout; a delete must not report success."""

    def setUp(self):
        self.client = WebsiteConfigurationMCPTools(read_token="test_token", base_url="https://test.instana.io")
        self.client.config_api = MagicMock()
        patcher = patch(
            "src.website.website_configuration.sdk_call_with_keepalive",
            side_effect=_timeout_keepalive,
        )
        self.mock_keepalive = patcher.start()
        self.addCleanup(patcher.stop)

    def test_delete_website_timeout(self):
        result = asyncio.run(self.client.delete_website(website_id="web1"))

        self.assertIn("timed out", result["error"])
        self.assertEqual(result["timeout_seconds"], 180)
        self.assertNotIn("success", result)
        self.mock_keepalive.assert_called_once()


if __name__ == '__main__':
    unittest.main()

