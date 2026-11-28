"""
E2E tests for SLO Configuration MCP Tools
"""

import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def create_slo_configuration_client(instana_credentials):
    """Dynamically import and create SLO Configuration client"""
    module = importlib.import_module("src.slo.slo_configuration")
    module = importlib.reload(module)
    return module.SLOConfigurationMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        self.data = payload
        self.status = status
        self.headers = {"Content-Type": "application/json"}


SLO_CONFIG = {
    "id": "slo-1",
    "name": "API Latency",
    "tags": ["api"],
    "target": 0.95,
    "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
    "indicator": {"type": "timeBased", "blueprint": "latency", "threshold": 100, "aggregation": "P90"},
    "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"},
    "createdDate": 1,
    "rbacTags": [],
}


def _valid_payload():
    return {
        "name": "API Latency",
        "tags": ["api"],
        "target": 0.95,
        "entity": {"type": "application", "applicationId": "app-1", "boundaryScope": "ALL"},
        "indicator": {"type": "timeBased", "blueprint": "latency", "threshold": 100, "aggregation": "P90"},
        "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"},
    }


class TestSLOConfigurationE2E:
    """End-to-end tests for SLO Configuration MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ---------------------------------------------------------------- get_all
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_configs_with_items(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_configs_without_preload_content.return_value = _MockResponse(
            {"items": [SLO_CONFIG], "page": 1, "pageSize": 10, "totalHits": 1}
        )
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_configs(
            filters={"page_size": 10, "page": 1, "query": "API", "tag": ["api"]},
            api_client=mock_api,
        )

        assert result["success"] is True
        assert result["totalHits"] == 1
        assert result["page"] == 1
        assert result["items"][0]["id"] == "slo-1"
        assert "createdDate" not in result["items"][0]
        assert "rbacTags" not in result["items"][0]
        kwargs = mock_api.get_all_slo_configs_without_preload_content.call_args.kwargs
        assert kwargs["page_size"] == 10
        assert kwargs["query"] == "API"
        assert kwargs["tag"] == ["api"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_configs_no_filters_non_paged_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_configs_without_preload_content.return_value = _MockResponse({"other": 1})
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_configs(api_client=mock_api)

        assert result == {"other": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_configs_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_configs_without_preload_content.return_value = _MockResponse(b"<html>")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_configs(api_client=mock_api)

        assert "Failed to parse" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_configs_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_configs_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_configs(api_client=mock_api)

        assert "Failed to get SLO configs" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- get by id
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_config_by_id_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_config_by_id_without_preload_content.return_value = _MockResponse(SLO_CONFIG)
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_slo_config_by_id(id="slo-1", refresh=True, api_client=mock_api)

        assert result["id"] == "slo-1"
        assert result["target"] == 0.95
        assert "createdDate" not in result
        mock_api.get_slo_config_by_id_without_preload_content.assert_called_once_with(id="slo-1", refresh=True)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_config_by_id_missing_id(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_slo_config_by_id(id="", api_client=MagicMock())

        assert result == {"error": "id is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_config_by_id_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_config_by_id_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_slo_config_by_id(id="slo-1", api_client=mock_api)

        assert "Failed to parse JSON response" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_config_by_id_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_config_by_id_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_slo_config_by_id(id="slo-1", api_client=mock_api)

        assert result == {"error": "Boom"}

    # ---------------------------------------------------------------- create
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(SLO_CONFIG, status=201)
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=_valid_payload(), api_client=mock_api)

        assert result["success"] is True
        assert result["message"] == "SLO config created successfully"
        assert result["data"]["id"] == "slo-1"
        assert result["status_code"] == 201
        mock_api.create_slo_config_without_preload_content.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("make_payload", [
        json.dumps,
        lambda p: json.dumps(p).replace('"', "'"),
        repr,
    ], ids=["json", "single-quoted", "python-literal"])
    async def test_create_slo_config_string_payload_formats(self, instana_credentials, make_payload):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(SLO_CONFIG)
        client = create_slo_configuration_client(instana_credentials)

        payload = make_payload(_valid_payload())
        # repr() output contains Python literals (False/None) that are not JSON; the payload
        # here is purely JSON-compatible so every format must parse.
        result = await client.create_slo_config(payload=payload, api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_unparseable_string_payload(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload="{not: valid", api_client=MagicMock())

        assert "Invalid payload format" in result["error"]
        assert result["payload"] == "{not: valid"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_missing_payload(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=None, api_client=MagicMock())

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_elicitation_all_missing(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload={"unrelated": 1}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert set(result["missing_parameters"]) == {
            "name", "tags", "target", "entity", "indicator", "timeWindow",
        }
        assert "**Top-level fields:**" in result["message"]
        mock_api.create_slo_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_elicitation_invalid_target(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        for bad in (1.5, -0.1, "high"):
            payload = _valid_payload()
            payload["target"] = bad
            result = await client.create_slo_config(payload=payload, api_client=MagicMock())
            assert result["elicitation_needed"] is True
            assert result["missing_parameters"] == ["target"]
            assert "Invalid target value" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_elicitation_entity_fields(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        payload = _valid_payload()
        payload["entity"] = {"type": "application"}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["entity.applicationId", "entity.boundaryScope"]
        assert "**Entity fields:**" in result["message"]

        payload["entity"] = {"type": "application", "applicationId": "a", "boundaryScope": "NOPE"}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["entity.boundaryScope"]
        assert "Invalid boundaryScope: NOPE" in result["message"]

        payload["entity"] = {"applicationId": "a"}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["entity.type"]

        # Non-dict entity skips nested validation
        payload["entity"] = "application"
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_entity_defaults_are_injected(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(SLO_CONFIG)
        client = create_slo_configuration_client(instana_credentials)

        payload = _valid_payload()
        result = await client.create_slo_config(payload=payload, api_client=mock_api)

        assert result["success"] is True
        assert payload["entity"]["includeInternal"] is False
        assert payload["entity"]["includeSynthetic"] is False

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_elicitation_indicator_fields(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()

        payload["indicator"] = {}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["indicator.type", "indicator.blueprint"]
        assert "**Indicator fields:**" in result["message"]

        payload["indicator"] = {"type": "weird", "blueprint": "odd", "aggregation": "P12"}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == [
            "indicator.type", "indicator.blueprint", "indicator.aggregation",
        ]
        assert "Invalid indicator type: weird" in result["message"]
        assert "Invalid blueprint: odd" in result["message"]
        assert "Invalid aggregation: P12" in result["message"]

        payload["indicator"] = "latency"
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_elicitation_time_window_fields(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()

        payload["timeWindow"] = {}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == [
            "timeWindow.type", "timeWindow.duration", "timeWindow.durationUnit",
        ]
        assert "**Time window fields:**" in result["message"]

        payload["timeWindow"] = {"type": "sliding", "duration": 0, "durationUnit": "decade"}
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == [
            "timeWindow.type", "timeWindow.duration", "timeWindow.durationUnit",
        ]
        assert "Invalid timeWindow type: sliding" in result["message"]
        assert "Invalid duration: 0" in result["message"]
        assert "Invalid durationUnit: decade" in result["message"]

        payload["timeWindow"] = "1w"
        result = await client.create_slo_config(payload=payload, api_client=MagicMock())
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_unsupported_entity_type(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()
        payload["entity"] = {"type": "website"}

        result = await client.create_slo_config(payload=payload, api_client=MagicMock())

        assert "Unsupported entity type: website" in result["error"] or "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_empty_name(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()
        payload["name"] = ""

        result = await client.create_slo_config(payload=payload, api_client=MagicMock())

        assert result == {"error": "name and target are required fields"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_model_construction_failure(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()
        payload["indicator"] = {"type": "timeBased", "blueprint": "latency", "threshold": "not-a-number"}

        result = await client.create_slo_config(payload=payload, api_client=MagicMock())

        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(b"bad", status=400)
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=_valid_payload(), api_client=mock_api)

        assert "API error (status 400)" in result["error"]
        assert result["status_code"] == 400

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_api_error_no_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(b"", status=500)
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=_valid_payload(), api_client=mock_api)

        assert "No error details provided" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_empty_success_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(b"  ", status=200)
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=_valid_payload(), api_client=mock_api)

        assert result["success"] is True
        assert "empty response" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_invalid_json_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.return_value = _MockResponse(b"{oops")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=_valid_payload(), api_client=mock_api)

        assert "Failed to parse JSON response" in result["error"]
        assert result["raw_response"] == "{oops"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_slo_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_config_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.create_slo_config(payload=_valid_payload(), api_client=mock_api)

        assert "Failed to create SLO config" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- update
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_success_refetches(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_config_without_preload_content.return_value.status = 200
        client = create_slo_configuration_client(instana_credentials)
        # The re-fetch goes through the auth decorator without the injected mock client,
        # so stub it on this instance only.
        client.get_slo_config_by_id = AsyncMock(return_value={"id": "slo-1"})

        result = await client.update_slo_config(id="slo-1", payload=_valid_payload(), api_client=mock_api)

        assert result["id"] == "slo-1"
        client.get_slo_config_by_id.assert_awaited_once()
        mock_api.update_slo_config_without_preload_content.assert_called_once()
        assert mock_api.update_slo_config_without_preload_content.call_args.kwargs["id"] == "slo-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("make_payload", [
        json.dumps,
        lambda p: json.dumps(p).replace('"', "'"),
        repr,
    ], ids=["json", "single-quoted", "python-literal"])
    async def test_update_slo_config_string_payload_formats(self, instana_credentials, make_payload):
        mock_api = MagicMock()
        mock_api.update_slo_config_without_preload_content.return_value.status = 200
        client = create_slo_configuration_client(instana_credentials)
        client.get_slo_config_by_id = AsyncMock(return_value={"id": "slo-1"})

        result = await client.update_slo_config(
            id="slo-1", payload=make_payload(_valid_payload()), api_client=mock_api
        )

        assert result["id"] == "slo-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_unparseable_string_payload(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        result = await client.update_slo_config(id="slo-1", payload="{not: valid", api_client=MagicMock())

        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_missing_id_and_payload(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        assert await client.update_slo_config(id="", payload=_valid_payload(), api_client=MagicMock()) == {
            "error": "id is required"
        }
        assert await client.update_slo_config(id="slo-1", payload=None, api_client=MagicMock()) == {
            "error": "payload is required"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_elicitation_uses_update_wording(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_configuration_client(instana_credentials)

        result = await client.update_slo_config(id="slo-1", payload={"name": "x"}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "To update the SLO configuration" in result["message"]
        mock_api.update_slo_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_empty_name(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()
        payload["name"] = ""

        result = await client.update_slo_config(id="slo-1", payload=payload, api_client=MagicMock())

        assert result == {"error": "name and target are required fields"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_model_construction_failure(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)
        payload = _valid_payload()
        payload["indicator"] = {"type": "timeBased", "blueprint": "latency", "threshold": "not-a-number"}

        result = await client.update_slo_config(id="slo-1", payload=payload, api_client=MagicMock())

        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_slo_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_config_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.update_slo_config(id="slo-1", payload=_valid_payload(), api_client=mock_api)

        assert "Failed to update SLO config" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- delete
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_slo_config_success(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_configuration_client(instana_credentials)

        result = await client.delete_slo_config(id="slo-1", api_client=mock_api)

        assert result == {"success": True, "message": "SLO config slo-1 deleted successfully"}
        mock_api.delete_slo_config.assert_called_once_with(id="slo-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_slo_config_missing_id(self, instana_credentials):
        client = create_slo_configuration_client(instana_credentials)

        result = await client.delete_slo_config(id="", api_client=MagicMock())

        assert result == {"error": "id is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_slo_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_slo_config.side_effect = Exception("Boom")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.delete_slo_config(id="slo-1", api_client=mock_api)

        assert "Failed to delete SLO config" in result["error"]

    # ---------------------------------------------------------------- tags
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_config_tags_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_config_tags_without_preload_content.return_value = _MockResponse(["a", "b"])
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_config_tags(
            query="a", tag=["a"], entity_type="APPLICATION", api_client=mock_api
        )

        assert result == {"success": True, "tags": ["a", "b"], "count": 2}
        mock_api.get_all_slo_config_tags_without_preload_content.assert_called_once_with(
            query="a", tag=["a"], entity_type="APPLICATION"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_config_tags_dict_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_config_tags_without_preload_content.return_value = _MockResponse({"tags": ["x"]})
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_config_tags(api_client=mock_api)

        assert result == {"success": True, "tags": ["x"], "count": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_config_tags_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_config_tags_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_config_tags(api_client=mock_api)

        assert "Failed to parse JSON response" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_slo_config_tags_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_config_tags_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_configuration_client(instana_credentials)

        result = await client.get_all_slo_config_tags(api_client=mock_api)

        assert "Failed to get SLO config tags" in result["error"]
