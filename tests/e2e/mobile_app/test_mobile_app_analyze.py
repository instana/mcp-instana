"""
E2E tests for Mobile App Analyze MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest

DEFAULT_TIME_WINDOW_MS = 3600000  # 1 hour in milliseconds
DEFAULT_PAGE_SIZE = 20  # Matches Instana UI default


def create_mobile_app_analyze_client(instana_credentials):
    """Dynamically import and create Mobile App Analyze client"""
    module = importlib.import_module("src.mobile_app.mobile_app_analyze")
    module = importlib.reload(module)
    mobile_app_analyze_mcp_tools = module.MobileAppAnalyzeMCPTools
    return mobile_app_analyze_mcp_tools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


class TestMobileAppAnalyzeE2E:
    """End-to-end tests for Mobile App Analyze MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_mocked_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacons_without_preload_content.return_value = _MockResponse(
            json.dumps(
                {
                    "totalHits": 1,
                    "items": [{"beacon": {"mobileAppLabel": "Robot Shop", "timestamp": 123, "appVersion": "1.0"}}],
                }
            ).encode("utf-8")
        )

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            time_frame={"windowSize": DEFAULT_TIME_WINDOW_MS},
            pagination={"retrievalSize": DEFAULT_PAGE_SIZE},
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "summary" in result
        assert "beacons" in result
        assert result["summary"]["totalHits"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_requires_beacon_type(self, instana_credentials):
        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(api_client=MagicMock())

        assert isinstance(result, dict)
        assert result.get("elicitation_needed") is True
        assert result["missing_parameters"][0]["name"] == "beacon_type"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_error_handling(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacons_without_preload_content.side_effect = Exception("API Error")

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get mobile app beacons" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_initialization_error(self, instana_credentials):
        with patch(
            "src.mobile_app.mobile_app_analyze.MobileAppAnalyzeApi",
            side_effect=Exception("Initialization Error"),
        ):
            client = create_mobile_app_analyze_client(instana_credentials)
            assert client is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_default_params_and_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacons_without_preload_content.return_value = _MockResponse(
            json.dumps([
                {"beacon": {"mobileAppLabel": "App1", "timestamp": 1}}
            ]).encode("utf-8")
        )

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "summary" in result
        assert "beacons" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_pagination_bounds(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacons_without_preload_content.return_value = _MockResponse(
            json.dumps({"items": [], "totalHits": 0}).encode("utf-8")
        )

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            pagination={"retrievalSize": 500, "offset": 0},
            api_client=mock_api,
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_tag_filter_missing_fields(self, instana_credentials):
        mock_api = MagicMock()

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression={
                "type": "TAG_FILTER",
                "name": "mobileBeacon.view.name",
                # missing operator/value/entity
            },
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "elicitation_needed" in result
        assert "reason" in result
        assert "missing_entity_tags" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_expression_conversion(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacons_without_preload_content.return_value = _MockResponse(
            json.dumps({"items": [], "totalHits": 0}).encode("utf-8")
        )

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression={
                "type": "EXPRESSION",
                "elements": [
                    {
                        "type": "TAG_FILTER",
                        "name": "mobileBeacon.view.name",
                        "operator": "EQUALS",
                        "value": "test",
                        "entity": "NOT_APPLICABLE",
                    }
                ]
            },
            api_client=mock_api,
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_nan_cleanup_and_summary(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_mobile_app_beacons_without_preload_content.return_value = _MockResponse(
            json.dumps({
                "totalHits": 1,
                "items": [
                    {
                        "beacon": {
                            "mobileAppLabel": "App",
                            "timestamp": 123,
                            "errorCount": 0,
                            "errorMessage": "NaN"
                        }
                    }
                ]
            }).encode()
        )

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "beacons" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_app_beacons_missing_entity_field(self, instana_credentials):
        mock_api = MagicMock()

        client = create_mobile_app_analyze_client(instana_credentials)

        result = await client.get_all_mobile_app_beacons(
            beacon_type="SESSION_START",
            tag_filter_expression={
                "type": "TAG_FILTER",
                "name": "mobileBeacon.view.name",
                "operator": "EQUALS",
                "value": "Robot Shop",
                # entity missing → triggers elicitation
            },
            api_client=mock_api,
        )

        assert isinstance(result, dict)
        assert "elicitation_needed" in result
