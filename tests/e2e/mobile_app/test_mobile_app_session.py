"""
E2E tests (mocked) for Mobile App Session and Session Replay MCP Tools
"""

import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def _load_module():
    module = importlib.import_module("src.mobile_app.mobile_app_session")
    return importlib.reload(module)


def create_mobile_app_session_client(instana_credentials):
    """Dynamically import and create Mobile App Session client"""
    return _load_module().MobileAppSessionMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


def create_mobile_app_session_replay_client(instana_credentials):
    """Dynamically import and create Mobile App Session Replay client"""
    return _load_module().MobileAppSessionReplayMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(body, status=200):
    return _MockResponse(json.dumps(body).encode("utf-8"), status=status)


class TestMobileAppSessionHelpersE2E:
    @pytest.mark.mocked
    def test_clean_nan_values_recurses(self):
        clean = _load_module().clean_nan_values
        data = {
            "a": "NaN",
            "b": ["NaN", 1, {"c": "NaN", "d": "ok"}],
            "e": 5,
            "f": None,
            "g": "nan",
        }
        assert clean(data) == {
            "a": None,
            "b": [None, 1, {"c": None, "d": "ok"}],
            "e": 5,
            "f": None,
            "g": "nan",
        }


class TestMobileAppSessionBeaconsE2E:
    """MobileAppSessionMCPTools.get_session_beacons"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_success(self, instana_credentials):
        beacons = [
            {"beaconId": "b1", "type": "SESSION_START", "duration": "NaN"},
            {"beaconId": "b2", "type": "VIEW_CHANGE", "nested": {"x": ["NaN"]}},
        ]
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _json_response(beacons)
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1785783898711, api_client=mock_api
        )

        assert [b["beaconId"] for b in result["beacons"]] == ["b1", "b2"]
        assert result["beacons"][0]["duration"] is None
        assert result["beacons"][1]["nested"] == {"x": [None]}
        mock_api.get_session_without_preload_content.assert_called_once_with(
            id="s-1", timestamp=1785783898711
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_empty_list(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _json_response([])
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1, api_client=mock_api
        )

        assert result == {"beacons": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_non_list_response_is_treated_as_empty(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _json_response({"unexpected": True})
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1, api_client=mock_api
        )

        assert result == {"beacons": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_with_ctx(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _json_response([{"beaconId": "b"}])
        ctx = MagicMock()
        ctx.log = AsyncMock()
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1",
            timestamp=1,
            ctx=ctx,
            api_client=mock_api,
            resource_type="mobile_app",
            tool_name="manage_mobile_apps",
        )

        assert result == {"beacons": [{"beaconId": "b"}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "kwargs,expected_missing",
        [
            ({}, ["session_id", "timestamp"]),
            ({"session_id": "s-1"}, ["timestamp"]),
            ({"timestamp": 123}, ["session_id"]),
        ],
    )
    async def test_get_session_beacons_missing_params(self, instana_credentials, kwargs, expected_missing):
        mock_api = MagicMock()
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(api_client=mock_api, **kwargs)

        assert result["elicitation_needed"] is True
        assert [p["name"] for p in result["missing_parameters"]] == expected_missing
        for name in expected_missing:
            assert f"- {name}:" in result["elicitation_prompt"]
        mock_api.get_session_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_timestamp_zero_is_allowed(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _json_response([])
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(session_id="s", timestamp=0, api_client=mock_api)

        assert result == {"beacons": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _MockResponse(b"not found", status=404)
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1, api_client=mock_api
        )

        assert result["status_code"] == 404
        assert "HTTP 404" in result["error"]
        assert result["details"] == "not found"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.return_value = _MockResponse(b"<html>")
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1, api_client=mock_api
        )

        assert result["error"].startswith("Failed to get mobile app beacons")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_sdk_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_session_without_preload_content.side_effect = RuntimeError("network")
        client = create_mobile_app_session_client(instana_credentials)

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1, api_client=mock_api
        )

        assert result == {"error": "Failed to get mobile app beacons: network"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_session_beacons_unexpected_exception_in_outer_handler(self, instana_credentials):
        client = create_mobile_app_session_client(instana_credentials)
        client._execute_beacons_call = AsyncMock(side_effect=RuntimeError("boom"))

        result = await client.get_session_beacons(
            session_id="s-1", timestamp=1, api_client=MagicMock()
        )

        assert result == {"error": "Failed to get mobile app session beacons: boom"}


class TestMobileAppSessionReplayE2E:
    """MobileAppSessionReplayMCPTools.get_session_replay_action_beacons"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_success_with_explicit_pagination(self, instana_credentials):
        body = {
            "beacons": [{"id": "a1", "value": "NaN"}, {"id": "a2"}],
            "nextCursor": 2,
            "hasMore": True,
        }
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.return_value = _json_response(body)
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1",
            session_id="s-1",
            cursor=10,
            page_size=2,
            api_client=mock_api,
        )

        assert result["beacons"][0] == {"id": "a1", "value": None}
        assert result["nextCursor"] == 2
        assert result["hasMore"] is True
        mock_api.get_action_beacons_without_preload_content.assert_called_once_with(
            mobile_app_id="app-1", session_id="s-1", cursor=10, page_size=2
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_defaults_applied_for_cursor_and_page_size(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.return_value = _json_response(
            {"beacons": [], "nextCursor": None, "hasMore": False}
        )
        ctx = MagicMock()
        ctx.log = AsyncMock()
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", ctx=ctx, api_client=mock_api
        )

        assert result == {"beacons": [], "nextCursor": None, "hasMore": False}
        mock_api.get_action_beacons_without_preload_content.assert_called_once_with(
            mobile_app_id="app-1", session_id="s-1", cursor=0, page_size=100
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_response_without_beacons_key(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.return_value = _json_response({"hasMore": False})
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", cursor=0, page_size=1, api_client=mock_api
        )

        assert result == {"hasMore": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "kwargs,expected_missing",
        [
            ({}, ["mobile_app_id", "session_id"]),
            ({"mobile_app_id": "app-1"}, ["session_id"]),
            ({"session_id": "s-1"}, ["mobile_app_id"]),
            ({"mobile_app_id": "", "session_id": ""}, ["mobile_app_id", "session_id"]),
        ],
    )
    async def test_missing_required_params(self, instana_credentials, kwargs, expected_missing):
        mock_api = MagicMock()
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(api_client=mock_api, **kwargs)

        assert result["elicitation_needed"] is True
        assert [p["name"] for p in result["missing_parameters"]] == expected_missing
        mock_api.get_action_beacons_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_negative_cursor_is_rejected(self, instana_credentials):
        mock_api = MagicMock()
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", cursor=-1, api_client=mock_api
        )

        assert result["validation_failed"] is True
        assert result["valid"] is False
        assert result["error_count"] == 1
        assert result["errors"][0]["field"] == "cursor"
        mock_api.get_action_beacons_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("page_size", [0, -5, 1001])
    async def test_out_of_range_page_size_is_rejected(self, instana_credentials, page_size):
        mock_api = MagicMock()
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", page_size=page_size, api_client=mock_api
        )

        assert result["validation_failed"] is True
        assert result["errors"][0]["field"] == "page_size"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_both_pagination_params_invalid_reports_both(self, instana_credentials):
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", cursor=-1, page_size=5000, api_client=MagicMock()
        )

        assert result["error_count"] == 2
        assert {e["field"] for e in result["errors"]} == {"cursor", "page_size"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("page_size", [1, 1000])
    async def test_page_size_boundaries_are_accepted(self, instana_credentials, page_size):
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.return_value = _json_response({"beacons": [{"id": 1}]})
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", page_size=page_size, api_client=mock_api
        )

        assert result == {"beacons": [{"id": 1}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.return_value = _MockResponse(b"denied", status=403)
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", api_client=mock_api
        )

        assert result["status_code"] == 403
        assert "HTTP 403" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_json_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.return_value = _MockResponse(b"garbage")
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", api_client=mock_api
        )

        assert result["error"].startswith("Failed to get mobile app action beacons")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_sdk_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_beacons_without_preload_content.side_effect = RuntimeError("down")
        client = create_mobile_app_session_replay_client(instana_credentials)

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", api_client=mock_api
        )

        assert result == {"error": "Failed to get mobile app action beacons: down"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unexpected_exception_in_outer_handler(self, instana_credentials):
        client = create_mobile_app_session_replay_client(instana_credentials)
        client._execute_action_beacons_call = AsyncMock(side_effect=RuntimeError("boom"))

        result = await client.get_session_replay_action_beacons(
            mobile_app_id="app-1", session_id="s-1", api_client=MagicMock()
        )

        assert result == {"error": "Failed to get mobile app session replay action beacons: boom"}
