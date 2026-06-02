"""
E2E tests for Website Alert MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def create_website_alert_client(instana_credentials):
    """Dynamically import and create Website Alert client"""
    module = importlib.import_module("src.website.website_alert")
    module = importlib.reload(module)
    website_alert_mcp_tools = module.WebsiteAlertMCPTools
    return website_alert_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


class TestWebsiteAlertE2E:
    """End-to-end tests for Website Alert MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_single_config_success(self, instana_credentials):
        """Test retrieving a single alert configuration by ID"""
        mock_api = MagicMock()
        expected_config = {
            "id": "alert_web_12345",
            "name": "Website Availability Alert",
            "description": "Alert when website is down",
            "enabled": True,
            "severity": "CRITICAL",
            "validFrom": 1609459200,
            "validTo": None,
            "conditions": [
                {
                    "metric": "availability",
                    "operator": "LESS_THAN",
                    "threshold": 99.5
                }
            ],
            "actions": [
                {
                    "type": "EMAIL",
                    "recipients": ["ops@example.com"]
                }
            ]
        }

        mock_response = _MockResponse(json.dumps(expected_config).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_12345", api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_web_12345"
        assert result["name"] == "Website Availability Alert"
        assert result["enabled"] is True
        assert result["severity"] == "CRITICAL"
        mock_api.find_website_alert_config_without_preload_content.assert_called_once_with(id="alert_web_12345", valid_on=None)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_list_response(self, instana_credentials):
        """Test retrieving multiple alert configurations"""
        mock_api = MagicMock()

        configs_list = [
            {
                "id": "alert_web_1",
                "name": "Production Alert",
                "enabled": True
            },
            {
                "id": "alert_web_2",
                "name": "Staging Alert",
                "enabled": False
            }
        ]

        mock_response = _MockResponse(json.dumps(configs_list).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_1", api_client=mock_api)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "alert_web_1"
        assert result[1]["id"] == "alert_web_2"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_with_valid_on_timestamp(self, instana_credentials):
        """Test retrieving alert configuration at specific timestamp"""
        mock_api = MagicMock()
        timestamp = 1609459200

        config_data = {
            "id": "alert_web_hist",
            "name": "Historical Website Alert",
            "validFrom": 1609459200,
            "validTo": 1609545600
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_hist", valid_on=timestamp, api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_web_hist"
        assert result["validFrom"] == 1609459200
        mock_api.find_website_alert_config_without_preload_content.assert_called_once_with(id="alert_web_hist", valid_on=timestamp)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_empty_list(self, instana_credentials):
        """Test when no alert configurations exist"""
        mock_api = MagicMock()
        mock_response = _MockResponse(json.dumps([]).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_1", api_client=mock_api)

        assert isinstance(result, list)
        assert result == []

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_api_error(self, instana_credentials):
        """Test error handling when API call fails"""
        mock_api = MagicMock()
        mock_api.find_website_alert_config_without_preload_content.side_effect = Exception("API Connection Error")

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_1", api_client=mock_api)

        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get website alert config" in result["error"]
        assert "API Connection Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_both_parameters(self, instana_credentials):
        """Test retrieving alert with both ID and timestamp"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_web_specific",
            "name": "Specific Website Alert at Time",
            "validFrom": 1609459200
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(
            id="alert_web_specific",
            valid_on=1609459200,
            api_client=mock_api
        )

        assert isinstance(result, dict)
        assert result["id"] == "alert_web_specific"
        mock_api.find_website_alert_config_without_preload_content.assert_called_once_with(
            id="alert_web_specific",
            valid_on=1609459200
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_no_to_dict_method(self, instana_credentials):
        """Test handling response object without to_dict method"""
        mock_api = MagicMock()

        # Return plain dict as JSON response
        config_data = {
            "id": "alert_web_plain",
            "name": "Plain Dict Website Alert"
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_plain", api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_web_plain"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_complex_conditions(self, instana_credentials):
        """Test alert configuration with complex conditions"""
        mock_api = MagicMock()

        complex_config = {
            "id": "alert_web_complex",
            "name": "Complex Website Alert",
            "conditions": [
                {
                    "metric": "responseTime",
                    "operator": "GREATER_THAN",
                    "threshold": 2000,
                    "windowSize": 300,
                    "violations": 3
                },
                {
                    "metric": "errorRate",
                    "operator": "GREATER_THAN",
                    "threshold": 0.01,
                    "windowSize": 300,
                    "violations": 2
                },
                {
                    "metric": "throughput",
                    "operator": "LESS_THAN",
                    "threshold": 100,
                    "windowSize": 600,
                    "violations": 1
                }
            ],
            "combinationOperator": "AND",
            "actions": [
                {"type": "EMAIL", "recipients": ["alerts@example.com"]},
                {"type": "SLACK", "channel": "#website-alerts"},
                {"type": "PAGERDUTY", "escalation": "high"},
                {"type": "WEBHOOK", "url": "https://example.com/webhooks/alerts"}
            ]
        }

        mock_response = _MockResponse(json.dumps(complex_config).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_complex", api_client=mock_api)

        assert isinstance(result, dict)
        assert len(result["conditions"]) == 3
        assert result["combinationOperator"] == "AND"
        assert len(result["actions"]) == 4

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_timeout_error(self, instana_credentials):
        """Test handling timeout errors"""
        mock_api = MagicMock()
        mock_api.find_website_alert_config_without_preload_content.side_effect = TimeoutError("Request timeout")

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_1", api_client=mock_api)

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_initialization(self, instana_credentials):
        """Test proper initialization of the client"""
        client = create_website_alert_client(instana_credentials)

        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_response_format_validation(self, instana_credentials):
        """Test that response format is valid"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_web_validate",
            "name": "Validation Website Alert",
            "enabled": True,
            "severity": "CRITICAL"
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_validate", api_client=mock_api)

        assert isinstance(result, dict)
        assert all(key in result for key in ["id", "name", "enabled", "severity"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_large_list_response(self, instana_credentials):
        """Test handling large list of alert configurations"""
        mock_api = MagicMock()

        configs = []
        for i in range(100):
            configs.append({
                "id": f"alert_web_{i}",
                "name": f"Website Alert {i}"
            })

        mock_response = _MockResponse(json.dumps(configs).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_1", api_client=mock_api)

        assert isinstance(result, list)
        assert len(result) == 100
        assert result[0]["id"] == "alert_web_0"
        assert result[99]["id"] == "alert_web_99"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_null_values_handling(self, instana_credentials):
        """Test handling of null/None values in response"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_web_null",
            "name": "Website Alert with Nulls",
            "description": None,
            "validTo": None,
            "conditions": None
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_null", api_client=mock_api)

        assert isinstance(result, dict)
        assert result["id"] == "alert_web_null"
        assert result["description"] is None
        assert result["validTo"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_with_tags(self, instana_credentials):
        """Test alert configuration with tags and annotations"""
        mock_api = MagicMock()

        config_data = {
            "id": "alert_web_tagged",
            "name": "Tagged Website Alert",
            "enabled": True,
            "tags": ["production", "critical", "monitoring"],
            "annotations": {
                "team": "platform",
                "service": "website"
            }
        }
        mock_response = _MockResponse(json.dumps(config_data).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_web_tagged", api_client=mock_api)

        assert isinstance(result, dict)
        assert "tags" in result
        assert len(result["tags"]) == 3
        assert "annotations" in result
        assert result["annotations"]["team"] == "platform"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_website_alert_config_multiple_severity_levels(self, instana_credentials):
        """Test alert configurations with different severity levels"""
        mock_api = MagicMock()

        configs = []
        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

        for severity in severities:
            configs.append({
                "id": f"alert_{severity.lower()}",
                "name": f"{severity} Website Alert",
                "severity": severity
            })

        mock_response = _MockResponse(json.dumps(configs).encode('utf-8'))
        mock_api.find_website_alert_config_without_preload_content.return_value = mock_response

        client = create_website_alert_client(instana_credentials)
        result = await client.find_website_alert_config(id="alert_critical", api_client=mock_api)

        assert isinstance(result, list)
        assert len(result) == 5
        for i, severity in enumerate(severities):
            assert result[i]["severity"] == severity


if __name__ == "__main__":
    pytest.main([__file__])
