"""
E2E tests for Alert Channels MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_alert_channels_client(instana_credentials):
    """Dynamically import and create Alert Channels client"""
    module = importlib.import_module("src.alert_channel.alert_channels_tools")
    module = importlib.reload(module)
    return module.AlertChannelsMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


def _alert_channels_module():
    return importlib.import_module("src.alert_channel.alert_channels_tools")


class _MockResponse:
    def __init__(self, payload, status=200):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        self.data = payload
        self.status = status
        self.headers = {"Content-Type": "application/json"}


CHANNELS = [
    {"id": "c2", "name": "Ops Webhook", "kind": "WEB_HOOK", "webhookUrl": "https://hooks.example.com/secret/abc"},
    {"id": "c1", "name": "Ops Email", "kind": "EMAIL", "emails": ["ops@example.com"]},
    {"id": "c3", "name": "Dev Slack", "kind": "SLACK"},
    "not-a-dict",
]


def _overview_api(payload=CHANNELS, status=200):
    mock_api = MagicMock()
    mock_api.get_alerting_channels_overview_without_preload_content.return_value = _MockResponse(payload, status)
    return mock_api


class TestAlertChannelsE2E:
    """End-to-end tests for Alert Channels MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ---------------------------------------------------------------- get_overview
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_success_sorted_and_masked(self, instana_credentials):
        mock_api = _overview_api()
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(api_client=mock_api)

        assert result["total"] == 3
        assert result["count"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total_pages"] == 1
        assert result["has_next"] is False
        assert result["has_previous"] is False
        # sorted by lower-cased name: Dev Slack, Ops Email, Ops Webhook
        assert [c["id"] for c in result["items"]] == ["c3", "c1", "c2"]
        webhook = result["items"][2]
        assert "secret" not in json.dumps(webhook)
        assert "hooks.example.com/secret" not in json.dumps(webhook)
        mock_api.get_alerting_channels_overview_without_preload_content.assert_called_once_with(ids=None)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_filters_by_kind_and_name(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(kind="web_hook", api_client=_overview_api())
        assert [c["id"] for c in result["items"]] == ["c2"]

        result = await client.get_overview(name_filter="  OPS ", api_client=_overview_api())
        assert [c["id"] for c in result["items"]] == ["c1", "c2"]

        result = await client.get_overview(kind="EMAIL", name_filter="webhook", api_client=_overview_api())
        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_pagination(self, instana_credentials):
        many = [{"id": f"id{i:02d}", "name": f"chan-{i:02d}", "kind": "SLACK"} for i in range(5)]
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(page=2, page_size=2, api_client=_overview_api(many))

        assert [c["id"] for c in result["items"]] == ["id02", "id03"]
        assert result["total"] == 5
        assert result["total_pages"] == 3
        assert result["has_next"] is True
        assert result["has_previous"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_page_size_clamped_and_coerced(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(page="abc", page_size=10_000, api_client=_overview_api())
        assert result["page"] == 1
        assert result["page_size"] == 100

        result = await client.get_overview(page=1, page_size=None, api_client=_overview_api())
        assert result["page_size"] == 20

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("ids,expected", [
        ("a, b ,,c", ["a", "b", "c"]),
        (["a", " b ", None, ""], ["a", "b"]),
        ([], None),
        (" , ", None),
    ])
    async def test_get_overview_ids_normalization(self, instana_credentials, ids, expected):
        mock_api = _overview_api()
        client = create_alert_channels_client(instana_credentials)

        await client.get_overview(ids=ids, api_client=mock_api)

        mock_api.get_alerting_channels_overview_without_preload_content.assert_called_once_with(ids=expected)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_invalid_ids_type(self, instana_credentials):
        mock_api = _overview_api()
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(ids=123, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "ids"
        mock_api.get_alerting_channels_overview_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_invalid_pagination(self, instana_credentials):
        mock_api = _overview_api()
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(page=0, api_client=mock_api)
        assert result["api_error"][0]["field"] == "page"

        result = await client.get_overview(page_size=0, api_client=mock_api)
        assert result["api_error"][0]["field"] == "page_size"

        mock_api.get_alerting_channels_overview_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_unknown_kind(self, instana_credentials):
        mock_api = _overview_api()
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(kind="CARRIER_PIGEON", api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "WEB_HOOK" in result["valid_kinds"]
        assert result["api_error"][0]["field"] == "kind"
        mock_api.get_alerting_channels_overview_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("status", [401, 403])
    async def test_get_overview_access_denied(self, instana_credentials, status):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(api_client=_overview_api(b"{}", status=status))

        assert result["error"] == _alert_channels_module().ACCESS_DENIED_ERROR
        assert result["status_code"] == status

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_other_http_error_redacts_body(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)
        body = {"message": "bad", "password": "hunter2", "token": "tok-123"}

        result = await client.get_overview(api_client=_overview_api(body, status=500))

        assert result["status_code"] == 500
        assert "Failed to retrieve alert channels overview" in result["error"]
        assert "hunter2" not in result["error"]
        assert "tok-123" not in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_error_body_variants(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(api_client=_overview_api(b"", status=500))
        assert result["error"] == "Failed to retrieve alert channels overview: "

        result = await client.get_overview(api_client=_overview_api(b"<html>oops</html>", status=500))
        assert "<non-JSON error body omitted>" in result["error"]
        assert "oops" not in result["error"]

        long_body = {"message": "x" * 2000}
        result = await client.get_overview(api_client=_overview_api(long_body, status=500))
        assert "...(truncated)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_unexpected_body(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(api_client=_overview_api({"not": "a list"}))
        assert "non-JSON or unexpected response body" in result["error"]
        assert result["status_code"] == 200

        result = await client.get_overview(api_client=_overview_api(b"<html>"))
        assert "non-JSON or unexpected response body" in result["error"]

        result = await client.get_overview(api_client=_overview_api(b"\xff\xfe"))
        assert "non-JSON or unexpected response body" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_error_dict_from_sdk_wrapper_is_returned(self, instana_credentials):
        mock_api = MagicMock()
        client = create_alert_channels_client(instana_credentials)
        timeout_error = {"error": "timed out", "operation": "x"}
        mock_api.get_alerting_channels_overview_without_preload_content.return_value = timeout_error

        result = await client.get_overview(api_client=mock_api)

        assert result == timeout_error

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_overview_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_alerting_channels_overview_without_preload_content.side_effect = Exception("Boom")
        client = create_alert_channels_client(instana_credentials)

        result = await client.get_overview(api_client=mock_api)

        assert "Failed to get alert channels overview" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- get by id
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_success_masked(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_alerting_channel_without_preload_content.return_value = _MockResponse(CHANNELS[0])
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(channel_id="c2", api_client=mock_api)

        assert result["id"] == "c2"
        assert result["webhookUrl"] == "***"
        assert "name_resolution" not in result
        mock_api.get_alerting_channel_without_preload_content.assert_called_once_with(id="c2")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_requires_id_or_name(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("status,expected_error", [
        (404, "Alert channel 'c2' not found"),
        (401, None),
        (403, None),
        (500, "Failed to get alert channel 'c2'"),
    ])
    async def test_get_by_id_http_errors(self, instana_credentials, status, expected_error):
        mock_api = MagicMock()
        mock_api.get_alerting_channel_without_preload_content.return_value = _MockResponse(
            {"message": "x"}, status=status
        )
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(channel_id="c2", api_client=mock_api)

        assert result["status_code"] == status
        if expected_error is None:
            assert result["error"] == _alert_channels_module().ACCESS_DENIED_ERROR
        else:
            assert expected_error in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_unexpected_body_and_error_dict(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_alerting_channel_without_preload_content.return_value = _MockResponse([1, 2])
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(channel_id="c2", api_client=mock_api)
        assert "non-JSON or unexpected response body" in result["error"]

        mock_api.get_alerting_channel_without_preload_content.return_value = {"error": "timed out"}
        result = await client.get(channel_id="c2", api_client=mock_api)
        assert result == {"error": "timed out"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_alerting_channel_without_preload_content.side_effect = Exception("Boom")
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(channel_id="c2", api_client=mock_api)

        assert "Failed to get alert channel" in result["error"]

    # ---------------------------------------------------------------- get by name
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_exact_name(self, instana_credentials):
        mock_api = _overview_api()
        mock_api.get_alerting_channel_without_preload_content.return_value = _MockResponse(CHANNELS[1])
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="ops email", api_client=mock_api)

        assert result["id"] == "c1"
        assert "name_resolution" not in result
        mock_api.get_alerting_channel_without_preload_content.assert_called_once_with(id="c1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_unique_substring_name_reports_resolution(self, instana_credentials):
        mock_api = _overview_api()
        mock_api.get_alerting_channel_without_preload_content.return_value = _MockResponse(CHANNELS[2])
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="slack", api_client=mock_api)

        assert result["id"] == "c3"
        assert result["name_resolution"]["match_type"] == "substring"
        assert result["name_resolution"]["resolved_id"] == "c3"
        assert result["name_resolution"]["requested_name"] == "slack"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_ambiguous_exact(self, instana_credentials):
        dupes = [
            {"id": "a", "name": "Same", "kind": "EMAIL"},
            {"id": "b", "name": "same", "kind": "SLACK"},
        ]
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="Same", api_client=_overview_api(dupes))

        assert result["elicitation_needed"] is True
        assert result["reason"] == "ambiguous_name"
        assert {c["id"] for c in result["candidates"]} == {"a", "b"}
        assert "Multiple alert channels match name" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_ambiguous_substring(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="ops", api_client=_overview_api())

        assert result["elicitation_needed"] is True
        assert result["reason"] == "ambiguous_name"
        assert {c["id"] for c in result["candidates"]} == {"c1", "c2"}
        assert "substring" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_not_found(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="missing", api_client=_overview_api())

        assert result["status_code"] == 404
        assert "No alert channel found with name 'missing'" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_blank_name(self, instana_credentials):
        mock_api = _overview_api()
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="   ", api_client=mock_api)

        assert result["status_code"] == 400
        assert "must not be empty" in result["error"]
        mock_api.get_alerting_channels_overview_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("status", [401, 403])
    async def test_get_by_name_lookup_access_denied(self, instana_credentials, status):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="Ops Email", api_client=_overview_api(b"{}", status=status))

        assert result["error"] == _alert_channels_module().ACCESS_DENIED_ERROR
        assert result["status_code"] == status

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_lookup_other_http_error(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="Ops Email", api_client=_overview_api(b"{}", status=502))

        assert result["error"] == "Failed to resolve channel name: HTTP 502"
        assert result["status_code"] == 502

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_lookup_unexpected_body_and_error_dict(self, instana_credentials):
        client = create_alert_channels_client(instana_credentials)

        result = await client.get(name="Ops Email", api_client=_overview_api({"not": "a list"}))
        assert "non-JSON or unexpected response body" in result["error"]

        mock_api = MagicMock()
        mock_api.get_alerting_channels_overview_without_preload_content.return_value = {"error": "timed out"}
        result = await client.get(name="Ops Email", api_client=mock_api)
        assert result == {"error": "timed out"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_unresolved_id_without_lookup_error(self, instana_credentials):
        """A resolved channel with a missing id falls through to the 'could not resolve' guard."""
        client = create_alert_channels_client(instana_credentials)
        nameless_id = [{"name": "Only One", "kind": "EMAIL"}]

        result = await client.get(name="Only One", api_client=_overview_api(nameless_id))

        assert result["status_code"] == 404
        assert "Could not resolve alert channel ID" in result["error"]
