"""
Additional E2E tests for Mobile App Alert MCP Tools (validation and error branches)
"""

import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def create_mobile_app_alert_client(instana_credentials):
    """Dynamically import and create Mobile App Alert client"""
    module = importlib.import_module("src.mobile_app.mobile_app_alert")
    module = importlib.reload(module)
    return module.MobileAppAlertMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _ctx():
    ctx = MagicMock()
    ctx.log = AsyncMock()
    return ctx


class TestMobileAppAlertMoreE2E:
    """Additional end-to-end tests for Mobile App Alert MCP Tools"""

    # ---------------- find_active_mobile_app_alert_configs ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("missing", ["", None])
    async def test_find_active_missing_mobile_app_id(self, instana_credentials, missing):
        mock_api = MagicMock()
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id=missing, api_client=mock_api
        )

        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        assert result["api_error"][0]["field"] == "mobile_app_id"
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_success_list(self, instana_credentials):
        mock_api = MagicMock()
        configs = [{"id": "a1", "name": "One"}, {"id": "a2", "name": "Two"}]
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.return_value = (
            _MockResponse(json.dumps(configs).encode("utf-8"))
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", alert_ids=["a1", "a2"], ctx=_ctx(), api_client=mock_api
        )

        assert result["configs"] == configs
        assert result["count"] == 2
        assert result["total"] == 2
        assert result["showing"] == 2
        assert "app-1" in result["message"]
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.assert_called_once_with(
            mobile_app_id="app-1", alert_ids=["a1", "a2"]
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_truncates_to_ten(self, instana_credentials):
        mock_api = MagicMock()
        configs = [{"id": f"a{i}"} for i in range(15)]
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.return_value = (
            _MockResponse(json.dumps(configs).encode("utf-8"))
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert result["count"] == 10
        assert result["showing"] == 10
        assert result["total"] == 15
        assert len(result["configs"]) == 10

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_single_dict_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.return_value = (
            _MockResponse(json.dumps({"id": "only"}).encode("utf-8"))
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert result["configs"] == [{"id": "only"}]
        assert result["total"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("payload", [b"[]", b"{}", b"null"])
    async def test_find_active_empty_configs(self, instana_credentials, payload):
        mock_api = MagicMock()
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.return_value = (
            _MockResponse(payload)
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert result["configs"] == []
        assert result["count"] == 0
        assert result["total"] == 0
        assert "No active alert configurations" in result["message"]
        assert "suggestion" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.return_value = (
            _MockResponse(b"<html>not json</html>")
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert "error" in result
        assert "Failed to parse response JSON" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.side_effect = (
            Exception("API down")
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert "error" in result
        assert "Failed to get active mobile app alert configs" in result["error"]
        assert "API down" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_non_utf8_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_mobile_app_alert_configs_without_preload_content.return_value = (
            _MockResponse(b"\xff\xfe\xfa")
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert "error" in result
        assert "Failed to get active mobile app alert configs" in result["error"]

    # ---------------- find_mobile_app_alert_config ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("missing", ["", None])
    async def test_find_config_missing_id(self, instana_credentials, missing):
        mock_api = MagicMock()
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_mobile_app_alert_config(id=missing, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        assert result["api_error"][0]["field"] == "id"
        mock_api.find_mobile_app_alert_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_with_valid_on(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = (
            _MockResponse(json.dumps({"id": "cfg-1", "name": "N"}).encode("utf-8"))
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_mobile_app_alert_config(
            id="cfg-1", valid_on=1700000000000, ctx=_ctx(), api_client=mock_api
        )

        assert result == {"id": "cfg-1", "name": "N"}
        mock_api.find_mobile_app_alert_config_without_preload_content.assert_called_once_with(
            id="cfg-1", valid_on=1700000000000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_mobile_app_alert_config_without_preload_content.return_value = (
            _MockResponse(b"garbage")
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_mobile_app_alert_config(id="cfg-1", api_client=mock_api)

        assert "error" in result
        assert "Failed to parse response JSON" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_mobile_app_alert_config_without_preload_content.side_effect = (
            RuntimeError("boom")
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_mobile_app_alert_config(id="cfg-1", api_client=mock_api)

        assert "error" in result
        assert "Failed to get mobile app alert config" in result["error"]
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_async_sdk_function(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_mobile_app_alert_config_without_preload_content = AsyncMock(
            return_value=_MockResponse(json.dumps({"id": "cfg-async"}).encode("utf-8"))
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_mobile_app_alert_config(id="cfg-async", api_client=mock_api)

        assert result == {"id": "cfg-async"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_async_sdk_function(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_mobile_app_alert_configs_without_preload_content = AsyncMock(
            return_value=_MockResponse(json.dumps([{"id": "x"}]).encode("utf-8"))
        )
        client = create_mobile_app_alert_client(instana_credentials)

        result = await client.find_active_mobile_app_alert_configs(
            mobile_app_id="app-1", api_client=mock_api
        )

        assert result["configs"] == [{"id": "x"}]
