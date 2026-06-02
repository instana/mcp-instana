"""
E2E tests for Mobile App Alert MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def create_mobile_app_alert_client(instana_credentials):
    """Dynamically import and create Mobile App Alert client"""
    module = importlib.import_module("src.mobile_app.mobile_app_alert")
    module = importlib.reload(module)
    mobile_app_alert_mcp_tools = module.MobileAppAlertMCPTools
    return mobile_app_alert_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


class TestMobileAppAlertE2E:
    """End-to-end tests for Mobile App Alert MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_single_config_success(self, instana_credentials):
        """Test retrieving a single alert configuration by ID"""
        mock_api = MagicMock()
        expected_config = {
            "id": "alert_12345",
            "name": "Mobile App Response Time Alert",
            "description": "Alert when response time exceeds threshold",
            "enabled": True,
            "severity": "CRITICAL",
            "validFrom": 1609459200,
            "validTo": None,
            "conditions": [
                {
                    "metric": "latency",
                    "operator": "GREATER_THAN",
                    "threshold": 1000
                }
            ],
            "actions": [
                {
                    "type": "EMAIL",
                    "recipients": ["team@example.com"]
                }
            ]
        }

        mock_response = _MockResponse(json.dumps(expected_config).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_12345", api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_12345"
        assert result["name"] == "Mobile App Response Time Alert"
        assert result["enabled"] is True
        assert result["severity"] == "CRITICAL"
        mock_api.find_mobile_app_alert_config_without_preload_content.assert_called_once_with(id="alert_12345", valid_on=None)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_list_response(self, instana_credentials):
        """Test retrieving multiple alert configurations"""
        mock_api = MagicMock()

        configs_list = [
            {
                "id": "alert_1",
                "name": "Alert 1",
                "enabled": True
            },
            {
                "id": "alert_2",
                "name": "Alert 2",
                "enabled": False
            }
        ]

        mock_response = _MockResponse(json.dumps(configs_list).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_1", api_client=mock_api)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "alert_1"
        assert result[1]["id"] == "alert_2"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_with_valid_on_timestamp(self, instana_credentials):
        """Test retrieving alert configuration at specific timestamp"""
        mock_api = MagicMock()
        timestamp = 1609459200

        config_data = {
            "id": "alert_1",
            "name": "Historical Alert",
            "validFrom": 1609459200,
            "validTo": 1609545600
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_1", valid_on=timestamp, api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_1"
        assert result["validFrom"] == 1609459200
        mock_api.find_mobile_app_alert_config_without_preload_content.assert_called_once_with(id="alert_1", valid_on=timestamp)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_empty_list(self, instana_credentials):
        """Test when no alert configurations exist"""
        mock_api = MagicMock()
        mock_response = _MockResponse(json.dumps([]).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_1", api_client=mock_api)

        assert isinstance(result, list)
        assert result == []

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_api_error(self, instana_credentials):
        """Test error handling when API call fails"""
        mock_api = MagicMock()
        mock_api.find_mobile_app_alert_config_without_preload_content.side_effect = Exception("API Connection Error")

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_1", api_client=mock_api)

        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get mobile app alert config" in result["error"]
        assert "API Connection Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_both_parameters(self, instana_credentials):
        """Test retrieving alert with both ID and timestamp"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_specific",
            "name": "Specific Alert at Time",
            "validFrom": 1609459200
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(
            id="alert_specific",
            valid_on=1609459200,
            api_client=mock_api
        )

        assert isinstance(result, dict)
        assert result["id"] == "alert_specific"
        mock_api.find_mobile_app_alert_config_without_preload_content.assert_called_once_with(
            id="alert_specific",
            valid_on=1609459200
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_no_to_dict_method(self, instana_credentials):
        """Test handling response object without to_dict method"""
        mock_api = MagicMock()

        # Return plain dict as JSON response
        config_data = {
            "id": "alert_plain",
            "name": "Plain Dict Alert"
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_plain", api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_plain"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_complex_conditions(self, instana_credentials):
        """Test alert configuration with complex conditions"""
        mock_api = MagicMock()

        complex_config = {
            "id": "alert_complex",
            "name": "Complex Alert",
            "conditions": [
                {
                    "metric": "latency",
                    "operator": "GREATER_THAN",
                    "threshold": 1000,
                    "windowSize": 300,
                    "violations": 2
                },
                {
                    "metric": "errorRate",
                    "operator": "GREATER_THAN",
                    "threshold": 0.05,
                    "windowSize": 300,
                    "violations": 1
                }
            ],
            "combinationOperator": "OR",
            "actions": [
                {"type": "EMAIL", "recipients": ["alert@example.com"]},
                {"type": "SLACK", "channel": "#alerts"},
                {"type": "WEBHOOK", "url": "https://example.com/webhook"}
            ]
        }

        mock_response = _MockResponse(json.dumps(complex_config).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_complex", api_client=mock_api)

        assert isinstance(result, dict)
        assert len(result["conditions"]) == 2
        assert result["combinationOperator"] == "OR"
        assert len(result["actions"]) == 3

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_timeout_error(self, instana_credentials):
        """Test handling timeout errors"""
        mock_api = MagicMock()
        mock_api.find_mobile_app_alert_config_without_preload_content.side_effect = TimeoutError("Request timeout")

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_1", api_client=mock_api)

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_initialization(self, instana_credentials):
        """Test proper initialization of the client"""
        client = create_mobile_app_alert_client(instana_credentials)

        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_response_format_validation(self, instana_credentials):
        """Test that response format is valid"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_validate",
            "name": "Validation Alert",
            "enabled": True,
            "severity": "CRITICAL"
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_validate", api_client=mock_api)

        assert isinstance(result, dict)
        assert all(key in result for key in ["id", "name", "enabled", "severity"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_large_list_response(self, instana_credentials):
        """Test handling large list of alert configurations"""
        mock_api = MagicMock()

        configs = []
        for i in range(100):
            configs.append({
                "id": f"alert_{i}",
                "name": f"Alert {i}"
            })

        mock_response = _MockResponse(json.dumps(configs).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_1", api_client=mock_api)

        assert isinstance(result, list)
        assert len(result) == 100
        assert result[0]["id"] == "alert_0"
        assert result[99]["id"] == "alert_99"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_mobile_app_alert_config_null_values_handling(self, instana_credentials):
        """Test handling of null/None values in response"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_null",
            "name": "Alert with Nulls",
            "description": None,
            "validTo": None,
            "conditions": None
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = mock_response

        client = create_mobile_app_alert_client(instana_credentials)
        result = await client.find_mobile_app_alert_config(id="alert_null", api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_null"
        assert result["description"] is None
        assert result["validTo"] is None


if __name__ == "__main__":
    pytest.main([__file__])
