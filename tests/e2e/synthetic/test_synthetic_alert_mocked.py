"""
Mocked E2E tests for Synthetic Alert MCP Tools (no real Instana API required)
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def _load_module():
    module = importlib.import_module("src.synthetic.synthetic_alert")
    return importlib.reload(module)


def create_synthetic_alert_client(instana_credentials):
    """Dynamically import and create Synthetic Alert client"""
    module = _load_module()
    return module.SyntheticAlertMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload=None, status=200, headers=None):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


VALID_PAYLOAD = {
    "name": "My Synthetic Alert",
    "description": "Fires when test fails",
    "syntheticTestIds": ["test-abc"],
    "alertChannelIds": [],
    "customPayloadFields": [],
    "rule": {"alertType": "failure", "metricName": "synthetic.metricsStatus"},
    "timeThreshold": {"type": "violationsInSequence", "violationsCount": 2},
    "tagFilterExpression": None,
}


class TestSyntheticAlertE2E:
    """End-to-end (mocked) tests for Synthetic Alert MCP Tools"""

    # ------------------------------------------------------------------
    # find_active_synthetic_alert_configs
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_success_with_pagination(self, instana_credentials):
        configs = [{"id": f"a{i}", "name": f"Alert {i}"} for i in range(5)]
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(configs)
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(
            synthetic_test_id="t1", alert_ids=["a1"], page=2, page_size=2, api_client=mock_api
        )

        assert result["total"] == 5
        assert result["count"] == 2
        assert result["page"] == 2
        assert result["page_size"] == 2
        assert result["total_pages"] == 3
        assert result["has_next"] is True
        assert result["has_previous"] is True
        assert [c["id"] for c in result["configs"]] == ["a2", "a3"]
        assert "pagination" in result
        assert "Found 5" in result["message"]
        mock_api.find_active_synthetic_alert_configs_without_preload_content.assert_called_once_with(
            synthetic_test_id="t1", alert_ids=["a1"]
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_defaults_and_invalid_paging(self, instana_credentials):
        configs = [{"id": "a1"}, {"id": "a2"}]
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(configs)
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(page=0, page_size=-5, api_client=mock_api)

        assert result["page"] == 1
        assert result["page_size"] == 50
        assert result["count"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_empty_list(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse([])
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert result["configs"] == []
        assert result["total"] == 0
        assert "No active synthetic smart alert configurations found" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_single_dict_response_wrapped(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(
            {"id": "only"}
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert result["total"] == 1
        assert result["configs"] == [{"id": "only"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(
            b"boom", status=500, headers={"Content-Type": "text/plain"}
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert "error" in result
        assert "status 500" in result["error"]
        assert "boom" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_http_error_empty_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(
            b"", status=404
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert "No error details available" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(
            b"not json"
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert result == {"error": "Invalid JSON from API"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_empty_body_treated_as_no_configs(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.return_value = _MockResponse(b"")
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert result["total"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_timeout_error_dict_returned(self, instana_credentials):
        module = _load_module()
        client = module.SyntheticAlertMCPTools(
            read_token=instana_credentials["api_token"], base_url=instana_credentials["base_url"]
        )
        timeout_err = {"error": "Instana API call timed out after 1s"}

        async def _timeout(coro, **_kwargs):
            coro.close()  # avoid "coroutine was never awaited" warning
            return timeout_err

        with patch.object(module, "sdk_call_with_keepalive", _timeout):
            result = await client.find_active_synthetic_alert_configs(api_client=MagicMock())

        assert result == timeout_err

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_synthetic_alert_configs_without_preload_content.side_effect = Exception("API Error")
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_active_synthetic_alert_configs(api_client=mock_api)

        assert "Failed to get active synthetic alert configs" in result["error"]
        assert "API Error" in result["error"]

    # ------------------------------------------------------------------
    # find_synthetic_alert_config
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            {"id": "abc", "name": "A"}
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_synthetic_alert_config(id="abc", valid_on=123, api_client=mock_api)

        assert result == {"id": "abc", "name": "A"}
        mock_api.find_synthetic_alert_config_without_preload_content.assert_called_once_with(id="abc", valid_on=123)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_empty_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_synthetic_alert_config_without_preload_content.return_value = _MockResponse(b"")
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_synthetic_alert_config(id="abc", api_client=mock_api)

        assert "Empty response from API for config 'abc'" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            b"not found", status=404
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_synthetic_alert_config(id="abc", api_client=mock_api)

        assert "status 404" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_synthetic_alert_config_without_preload_content.side_effect = Exception("Network down")
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_synthetic_alert_config(id="abc", api_client=mock_api)

        assert "Failed to get synthetic alert config" in result["error"]
        assert "Network down" in result["error"]

    # ------------------------------------------------------------------
    # find_synthetic_alert_config_versions
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_synthetic_alert_config_versions_without_preload_content.return_value = _MockResponse(
            [{"created": 1}, {"created": 2}]
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.find_synthetic_alert_config_versions(id="abc", api_client=mock_api)

        assert result["count"] == 2
        assert result["versions"][0]["created"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_single_dict_and_empty(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        mock_api.find_synthetic_alert_config_versions_without_preload_content.return_value = _MockResponse(
            {"created": 1}
        )
        single = await client.find_synthetic_alert_config_versions(id="abc", api_client=mock_api)
        assert single == {"versions": [{"created": 1}], "count": 1}

        mock_api.find_synthetic_alert_config_versions_without_preload_content.return_value = _MockResponse(b"")
        empty = await client.find_synthetic_alert_config_versions(id="abc", api_client=mock_api)
        assert empty == {"versions": [], "count": 0}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        mock_api.find_synthetic_alert_config_versions_without_preload_content.return_value = _MockResponse(
            b"forbidden", status=403
        )
        err = await client.find_synthetic_alert_config_versions(id="abc", api_client=mock_api)
        assert "status 403" in err["error"]

        mock_api.find_synthetic_alert_config_versions_without_preload_content.side_effect = Exception("kaboom")
        exc = await client.find_synthetic_alert_config_versions(id="abc", api_client=mock_api)
        assert "Failed to get synthetic alert config versions" in exc["error"]

    # ------------------------------------------------------------------
    # create_synthetic_alert_config
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_success_dict_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            {**VALID_PAYLOAD, "id": "new-id"}
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=VALID_PAYLOAD, api_client=mock_api)

        assert result["id"] == "new-id"
        kwargs = mock_api.create_synthetic_alert_config_without_preload_content.call_args.kwargs
        assert kwargs["synthetic_alert_config"].name == "My Synthetic Alert"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_success_json_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            {"id": "json-id"}
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=json.dumps(VALID_PAYLOAD), api_client=mock_api)

        assert result["id"] == "json-id"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_with_tag_filter_and_custom_payload_fields(self, instana_credentials):
        payload = {
            **VALID_PAYLOAD,
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "synthetic.locationId",
                "operator": "EQUALS",
                "entity": "NOT_APPLICABLE",
                "stringValue": "loc1",
                "value": "loc1",
            },
            "customPayloadFields": [{"type": "staticString", "key": "env", "value": "prod"}],
        }
        mock_api = MagicMock()
        mock_api.create_synthetic_alert_config_without_preload_content.return_value = _MockResponse({"id": "x"})
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=payload, api_client=mock_api)

        assert result == {"id": "x"}
        cfg = mock_api.create_synthetic_alert_config_without_preload_content.call_args.kwargs["synthetic_alert_config"]
        assert cfg.tag_filter_expression is not None
        assert len(cfg.custom_payload_fields) == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_invalid_tag_filter_returns_elicitation(self, instana_credentials):
        payload = {
            **VALID_PAYLOAD,
            "tagFilterExpression": {"type": "TAG_FILTER", "name": "x", "operator": "BOGUS", "entity": "NOT_APPLICABLE"},
        }
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_payload"
        assert result["api_error"]
        mock_api.create_synthetic_alert_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_invalid_custom_payload_field_returns_elicitation(self, instana_credentials):
        payload = {**VALID_PAYLOAD, "customPayloadFields": [{"type": "unknownType", "key": "k"}]}
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert any("customPayloadFields[0]" in issue["field"] for issue in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_missing_required_fields_returns_elicitation(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload={"name": "only name"}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "Payload failed SyntheticAlertConfig validation" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_unparseable_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload="{{not valid", api_client=mock_api)

        assert "error" in result
        mock_api.create_synthetic_alert_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_missing_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=None, api_client=mock_api)

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_payload_not_object(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload="[1, 2, 3]", api_client=mock_api)

        assert result == {"error": "payload must be a JSON object"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_empty_body_returns_success_message(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_synthetic_alert_config_without_preload_content.return_value = _MockResponse(b"")
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.create_synthetic_alert_config(payload=VALID_PAYLOAD, api_client=mock_api)

        assert result["success"] is True
        assert "no body returned" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        mock_api.create_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            b"bad request", status=400
        )
        err = await client.create_synthetic_alert_config(payload=VALID_PAYLOAD, api_client=mock_api)
        assert "status 400" in err["error"]

        mock_api.create_synthetic_alert_config_without_preload_content.side_effect = Exception("explode")
        exc = await client.create_synthetic_alert_config(payload=VALID_PAYLOAD, api_client=mock_api)
        assert "Failed to create synthetic alert config" in exc["error"]

    # ------------------------------------------------------------------
    # update_synthetic_alert_config
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_success_with_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            {"id": "abc", "name": "Updated"}
        )
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.update_synthetic_alert_config(id="abc", payload=VALID_PAYLOAD, api_client=mock_api)

        assert result["name"] == "Updated"
        assert mock_api.update_synthetic_alert_config_without_preload_content.call_args.kwargs["id"] == "abc"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_success_without_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_synthetic_alert_config_without_preload_content.return_value = _MockResponse(b"")
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.update_synthetic_alert_config(id="abc", payload=VALID_PAYLOAD, api_client=mock_api)

        assert result["success"] is True
        assert "'abc' updated successfully" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_invalid_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        result = await client.update_synthetic_alert_config(id="abc", payload={"name": "x"}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        mock_api.update_synthetic_alert_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        mock_api.update_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            b"conflict", status=409
        )
        err = await client.update_synthetic_alert_config(id="abc", payload=VALID_PAYLOAD, api_client=mock_api)
        assert "status 409" in err["error"]

        mock_api.update_synthetic_alert_config_without_preload_content.side_effect = Exception("explode")
        exc = await client.update_synthetic_alert_config(id="abc", payload=VALID_PAYLOAD, api_client=mock_api)
        assert "Failed to update synthetic alert config" in exc["error"]

    # ------------------------------------------------------------------
    # delete / enable / disable / restore
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "method_name,sdk_name,verb",
        [
            ("delete_synthetic_alert_config", "delete_synthetic_alert_config_without_preload_content", "deleted"),
            ("enable_synthetic_alert_config", "enable_synthetic_alert_config_without_preload_content", "enabled"),
            ("disable_synthetic_alert_config", "disable_synthetic_alert_config_without_preload_content", "disabled"),
        ],
    )
    async def test_simple_state_operations(self, instana_credentials, method_name, sdk_name, verb):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        # Success - non-JSON body must not be reported as failure (parse_body=False)
        getattr(mock_api, sdk_name).return_value = _MockResponse(b"<html>ok</html>", status=204)
        ok = await getattr(client, method_name)(id="abc", api_client=mock_api)
        assert ok["success"] is True
        assert f"'abc' {verb} successfully" in ok["message"]

        # HTTP error
        getattr(mock_api, sdk_name).return_value = _MockResponse(b"nope", status=404)
        err = await getattr(client, method_name)(id="abc", api_client=mock_api)
        assert "status 404" in err["error"]

        # Exception
        getattr(mock_api, sdk_name).side_effect = Exception("boom")
        exc = await getattr(client, method_name)(id="abc", api_client=mock_api)
        assert "Failed to" in exc["error"]
        assert "boom" in exc["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_success_error_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_alert_client(instana_credentials)

        mock_api.restore_synthetic_alert_config_without_preload_content.return_value = _MockResponse(b"", status=204)
        ok = await client.restore_synthetic_alert_config(id="abc", created=1710658800000, api_client=mock_api)
        assert ok["success"] is True
        assert "1710658800000" in ok["message"]
        mock_api.restore_synthetic_alert_config_without_preload_content.assert_called_once_with(
            id="abc", created=1710658800000
        )

        mock_api.restore_synthetic_alert_config_without_preload_content.return_value = _MockResponse(
            b"gone", status=410
        )
        err = await client.restore_synthetic_alert_config(id="abc", created=1, api_client=mock_api)
        assert "status 410" in err["error"]

        mock_api.restore_synthetic_alert_config_without_preload_content.side_effect = Exception("boom")
        exc = await client.restore_synthetic_alert_config(id="abc", created=1, api_client=mock_api)
        assert "Failed to restore synthetic alert config" in exc["error"]

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_synthetic_alert_client(instana_credentials)

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
