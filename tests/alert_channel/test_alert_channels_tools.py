"""
Unit tests for AlertChannelsMCPTools.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock the Instana SDK while importing the module under test (same approach as the other
# tool tests) so these tests never load the real instana_client package, and restore
# sys.modules afterwards so other test modules are unaffected.
_SDK_MODULES = [
    "instana_client",
    "instana_client.api",
    "instana_client.api.event_settings_api",
    "instana_client.configuration",
    "instana_client.api_client",
]
_original_sdk_modules = {name: sys.modules.get(name) for name in _SDK_MODULES}
for _name in _SDK_MODULES:
    sys.modules[_name] = MagicMock()
sys.modules["instana_client.api.event_settings_api"].EventSettingsApi = MagicMock(__name__="EventSettingsApi")

try:
    from src.alert_channel.alert_channels_tools import AlertChannelsMCPTools
finally:
    for _name, _original in _original_sdk_modules.items():
        if _original is not None:
            sys.modules[_name] = _original
        else:
            sys.modules.pop(_name, None)


class MockHTTPResponse:
    def __init__(self, data: bytes, status: int = 200):
        self.data = data
        self.status = status


@pytest.fixture
def tools():
    return AlertChannelsMCPTools(read_token="test-token", base_url="https://unit-test.instana.io")


async def _fake_sdk_call(coro, **kwargs):
    if hasattr(coro, "close"):
        coro.close()
    return _fake_sdk_call.return_val


@pytest.mark.asyncio
async def test_get_overview_success(tools):
    mock_data = [
        {"id": "chan-1", "kind": "WEB_HOOK", "name": "Slack Hook", "properties": {}},
        {"id": "chan-2", "kind": "EMAIL", "name": "Team Email", "properties": {}},
        {"id": "chan-3", "kind": "SLACK", "name": "Ops Channel", "properties": {}},
    ]
    mock_resp = MockHTTPResponse(json.dumps(mock_data).encode("utf-8"), status=200)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get_overview(api_client=mock_api, page=1, page_size=2)

        assert res["total"] == 3
        assert res["count"] == 2
        assert len(res["items"]) == 2
        assert res["has_next"] is True
        assert res["has_previous"] is False


@pytest.mark.asyncio
async def test_get_overview_string_pagination(tools):
    mock_data = [
        {"id": "chan-1", "kind": "WEB_HOOK", "name": "Slack Hook", "properties": {}},
        {"id": "chan-2", "kind": "EMAIL", "name": "Team Email", "properties": {}},
    ]
    mock_resp = MockHTTPResponse(json.dumps(mock_data).encode("utf-8"), status=200)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        # Pass page and page_size as strings and verify they cast successfully
        res = await tools.get_overview(api_client=mock_api, page="1", page_size="1")

        assert res["total"] == 2
        assert res["count"] == 1
        assert len(res["items"]) == 1
        assert res["page"] == 1
        assert res["page_size"] == 1


@pytest.mark.asyncio
async def test_get_overview_sorts_before_pagination_and_caps_page_size(tools):
    mock_data = [{"id": f"c{i}", "kind": "EMAIL", "name": f"chan-{i:03d}"} for i in range(150, 0, -1)]
    mock_resp = MockHTTPResponse(json.dumps(mock_data).encode("utf-8"), status=200)

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get_overview(api_client=MagicMock(), page=1, page_size=1000)

    assert res["page_size"] == 100
    assert res["count"] == 100
    assert res["total_pages"] == 2
    names = [item["name"] for item in res["items"]]
    assert names == sorted(names)
    assert names[0] == "chan-001"


@pytest.mark.asyncio
async def test_get_overview_string_ids(tools):
    mock_data = [
        {"id": "chan-1", "kind": "WEB_HOOK", "name": "Slack Hook"},
    ]
    mock_resp = MockHTTPResponse(json.dumps(mock_data).encode("utf-8"), status=200)
    mock_api = MagicMock()

    async def fake_sdk_call_run_coro(coro, **kwargs):
        await coro
        return mock_resp

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=fake_sdk_call_run_coro):
        await tools.get_overview(api_client=mock_api, ids="chan-1, chan-2")
        mock_api.get_alerting_channels_overview_without_preload_content.assert_called_once_with(ids=["chan-1", "chan-2"])


@pytest.mark.asyncio
async def test_get_overview_filters(tools):
    mock_data = [
        {"id": "chan-1", "kind": "WEB_HOOK", "name": "Production Webhook"},
        {"id": "chan-2", "kind": "EMAIL", "name": "Production Email"},
        {"id": "chan-3", "kind": "WEB_HOOK", "name": "Staging Webhook"},
    ]
    mock_resp = MockHTTPResponse(json.dumps(mock_data).encode("utf-8"), status=200)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp

        # Filter by kind
        res_kind = await tools.get_overview(kind="WEB_HOOK", api_client=mock_api)
        assert res_kind["total"] == 2
        assert all(item["kind"] == "WEB_HOOK" for item in res_kind["items"])

        # Filter by name substring
        res_name = await tools.get_overview(name_filter="staging", api_client=mock_api)
        assert res_name["total"] == 1
        assert res_name["items"][0]["id"] == "chan-3"


@pytest.mark.asyncio
async def test_get_overview_permission_error(tools):
    mock_resp = MockHTTPResponse(b'{"errors": ["Forbidden"]}', status=403)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get_overview(api_client=mock_api)

        assert "error" in res
        assert "canConfigureIntegrations" in res["error"]
        assert res["status_code"] == 403


@pytest.mark.asyncio
async def test_get_by_id_success(tools):
    channel_payload = {
        "id": "chan-webhook-1",
        "kind": "WEB_HOOK",
        "name": "Prod Alerts",
        "webhookUrls": ["https://hooks.example.com/services/SECRET_TOKEN_123"],
        "headers": ["Authorization: Bearer SECRET_AUTH"],
    }
    mock_resp = MockHTTPResponse(json.dumps(channel_payload).encode("utf-8"), status=200)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get(channel_id="chan-webhook-1", api_client=mock_api)

        assert res["id"] == "chan-webhook-1"
        assert res["name"] == "Prod Alerts"
        assert res["webhookUrls"] == ["***"]
        assert res["headers"] == ["Authorization: ***"]
        assert "SECRET_TOKEN_123" not in json.dumps(res)


@pytest.mark.asyncio
async def test_get_by_name_resolution(tools):
    overview_data = [
        {"id": "chan-1", "name": "Prod Alerts", "kind": "WEB_HOOK"},
        {"id": "chan-2", "name": "Dev Alerts", "kind": "EMAIL"},
    ]
    overview_resp = MockHTTPResponse(json.dumps(overview_data).encode("utf-8"), status=200)

    channel_payload = {
        "id": "chan-1",
        "kind": "WEB_HOOK",
        "name": "Prod Alerts",
        "webhookUrls": ["https://hooks.example.com/services/abc"],
    }
    channel_resp = MockHTTPResponse(json.dumps(channel_payload).encode("utf-8"), status=200)

    mock_api = MagicMock()
    responses = [overview_resp, channel_resp]

    async def side_effect(coro, **kwargs):
        if hasattr(coro, "close"):
            coro.close()
        return responses.pop(0)

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=side_effect):
        res = await tools.get(name="Prod Alerts", api_client=mock_api)
        assert res["id"] == "chan-1"
        assert res["name"] == "Prod Alerts"


@pytest.mark.asyncio
async def test_get_by_name_substring_fallback_is_surfaced(tools):
    overview_data = [
        {"id": "chan-1", "name": "Prod Alerts Primary", "kind": "WEB_HOOK"},
        {"id": "chan-2", "name": "Dev Email", "kind": "EMAIL"},
    ]
    channel_payload = {"id": "chan-1", "kind": "WEB_HOOK", "name": "Prod Alerts Primary"}
    responses = [
        MockHTTPResponse(json.dumps(overview_data).encode("utf-8"), status=200),
        MockHTTPResponse(json.dumps(channel_payload).encode("utf-8"), status=200),
    ]

    async def side_effect(coro, **kwargs):
        if hasattr(coro, "close"):
            coro.close()
        return responses.pop(0)

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=side_effect):
        res = await tools.get(name="prod alerts", api_client=MagicMock())

    assert res["id"] == "chan-1"
    assert res["name_resolution"]["match_type"] == "substring"
    assert res["name_resolution"]["requested_name"] == "prod alerts"
    assert res["name_resolution"]["resolved_name"] == "Prod Alerts Primary"


@pytest.mark.asyncio
async def test_get_by_name_exact_match_has_no_resolution_note(tools):
    overview_data = [{"id": "chan-1", "name": "Prod Alerts", "kind": "WEB_HOOK"}]
    channel_payload = {"id": "chan-1", "kind": "WEB_HOOK", "name": "Prod Alerts"}
    responses = [
        MockHTTPResponse(json.dumps(overview_data).encode("utf-8"), status=200),
        MockHTTPResponse(json.dumps(channel_payload).encode("utf-8"), status=200),
    ]

    async def side_effect(coro, **kwargs):
        if hasattr(coro, "close"):
            coro.close()
        return responses.pop(0)

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=side_effect):
        res = await tools.get(name="Prod Alerts", api_client=MagicMock())

    assert "name_resolution" not in res


@pytest.mark.asyncio
async def test_get_by_name_ambiguous(tools):
    overview_data = [
        {"id": "chan-1", "name": "Prod Alerts Primary", "kind": "WEB_HOOK"},
        {"id": "chan-2", "name": "Prod Alerts Secondary", "kind": "EMAIL"},
    ]
    overview_resp = MockHTTPResponse(json.dumps(overview_data).encode("utf-8"), status=200)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = overview_resp

        res = await tools.get(name="Prod Alerts", api_client=mock_api)
        assert res.get("elicitation_needed") is True
        assert res.get("reason") == "ambiguous_name"
        assert len(res.get("candidates", [])) == 2


@pytest.mark.asyncio
async def test_get_not_found(tools):
    mock_resp = MockHTTPResponse(b'{"errors": ["Not found"]}', status=404)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get(channel_id="nonexistent-id", api_client=mock_api)

        assert "error" in res
        assert "not found" in res["error"].lower()
        assert res["status_code"] == 404


@pytest.mark.asyncio
async def test_get_overview_already_parsed_list(tools):
    mock_data = [
        {"id": "chan-1", "kind": "WEB_HOOK", "name": "Slack Hook", "properties": {}},
    ]
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.data = mock_data
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get_overview(api_client=mock_api)
        assert res["total"] == 1
        assert res["items"][0]["id"] == "chan-1"


@pytest.mark.asyncio
async def test_get_by_id_already_parsed_dict(tools):
    channel_payload = {
        "id": "chan-webhook-1",
        "kind": "WEB_HOOK",
        "name": "Prod Alerts",
        "webhookUrls": ["https://hooks.example.com/services/SECRET_TOKEN_123"],
    }
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.data = channel_payload
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = mock_resp
        res = await tools.get(channel_id="chan-webhook-1", api_client=mock_api)
        assert res["id"] == "chan-webhook-1"
        assert res["webhookUrls"] == ["***"]


@pytest.mark.asyncio
async def test_get_by_name_malformed_overview(tools):
    # Simulate the case where get_overview returns a dictionary instead of a list during name resolution
    overview_data = {"status": "error", "message": "An error occurred"}
    overview_resp = MockHTTPResponse(json.dumps(overview_data).encode("utf-8"), status=200)
    mock_api = MagicMock()

    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = overview_resp

        # A non-list overview body is reported explicitly rather than treated as "no channels"
        res = await tools.get(name="Prod Alerts", api_client=mock_api)
        assert "error" in res
        assert "unexpected response body" in res["error"].lower()
        assert res["status_code"] == 200


@pytest.mark.asyncio
async def test_get_by_name_empty_or_whitespace(tools):
    mock_api = MagicMock()
    # Query with whitespace-only name
    res = await tools.get(name="   ", api_client=mock_api)

    assert "error" in res
    assert "empty or whitespace-only" in res["error"].lower()
    assert res["status_code"] == 400
    # Verify that get_alerting_channels_overview_without_preload_content was NEVER called
    mock_api.get_alerting_channels_overview_without_preload_content.assert_not_called()


@pytest.mark.asyncio
async def test_error_body_is_redacted_and_non_json_omitted(tools):
    mock_api = MagicMock()
    secret = "ERR-SECRET-999"

    json_err = MockHTTPResponse(
        json.dumps({"apiKey": secret, "webhookUrl": f"https://h.example.com/{secret}"}).encode("utf-8"),
        status=500,
    )
    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = json_err
        res = await tools.get(channel_id="x", api_client=mock_api)
        assert res["status_code"] == 500
        assert secret not in res["error"]

        _fake_sdk_call.return_val = MockHTTPResponse(f"upstream echoed {secret}".encode("utf-8"), status=500)
        res = await tools.get(channel_id="x", api_client=mock_api)
        assert secret not in res["error"]
        assert "omitted" in res["error"]

        res = await tools.get_overview(api_client=mock_api)
        assert secret not in res["error"]


@pytest.mark.asyncio
async def test_invalid_json_success_body_returns_explicit_error_without_leaking(tools):
    mock_api = MagicMock()
    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        for body in (b"not-json-SECRET", b"", b"\xff\xfeSECRET"):
            _fake_sdk_call.return_val = MockHTTPResponse(body, status=200)

            res = await tools.get_overview(api_client=mock_api)
            assert "unexpected response body" in res["error"]
            assert "total" not in res
            assert "SECRET" not in json.dumps(res)

            res = await tools.get(channel_id="x", api_client=mock_api)
            assert "unexpected response body" in res["error"]
            assert "SECRET" not in json.dumps(res)

            res = await tools.get(name="anything", api_client=mock_api)
            assert "unexpected response body" in res["error"]
            assert "SECRET" not in json.dumps(res)


@pytest.mark.asyncio
async def test_wrong_json_type_success_body_returns_explicit_error(tools):
    mock_api = MagicMock()
    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = MockHTTPResponse(b'{"not": "a list"}', status=200)
        res = await tools.get_overview(api_client=mock_api)
        assert "unexpected response body" in res["error"]

        _fake_sdk_call.return_val = MockHTTPResponse(b'["not", "a dict"]', status=200)
        res = await tools.get(channel_id="x", api_client=mock_api)
        assert "unexpected response body" in res["error"]


@pytest.mark.asyncio
async def test_unknown_kind_filter_logs_warning_and_lists_valid_kinds(tools, caplog):
    mock_api = MagicMock()
    with caplog.at_level("WARNING", logger="src.alert_channel.alert_channels_tools"):
        res = await tools.get_overview(kind="slak", api_client=mock_api)

    assert res["reason"] == "invalid_parameters"
    assert res["api_error"][0]["field"] == "kind"
    assert "SLACK" in res["valid_kinds"] and "WEB_HOOK" in res["valid_kinds"]
    assert res["valid_kinds"] == sorted(res["valid_kinds"])
    assert "SLACK" in res["message"]
    assert any("Unknown alert channel kind filter" in r.message for r in caplog.records)
    mock_api.get_alerting_channels_overview_without_preload_content.assert_not_called()


@pytest.mark.asyncio
async def test_known_kind_filter_is_case_insensitive_and_not_rejected(tools, caplog):
    mock_api = MagicMock()
    with patch("src.alert_channel.alert_channels_tools.sdk_call_with_keepalive", side_effect=_fake_sdk_call):
        _fake_sdk_call.return_val = MockHTTPResponse(b"[]", status=200)
        with caplog.at_level("WARNING", logger="src.alert_channel.alert_channels_tools"):
            res = await tools.get_overview(kind=" slack ", api_client=mock_api)

    assert res["total"] == 0
    assert "error" not in res and "reason" not in res
    assert not any("Unknown alert channel kind filter" in r.message for r in caplog.records)


