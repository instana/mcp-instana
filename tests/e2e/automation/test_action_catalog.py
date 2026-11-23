"""
E2E tests for Automation Action Catalog MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def create_action_catalog_client(instana_credentials):
    """Dynamically import and create Action Catalog client"""
    module = importlib.import_module("src.automation.action_catalog")
    module = importlib.reload(module)
    return module.ActionCatalogMCPTools(
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


RAW_ACTION = {
    "id": "act-1",
    "name": "Restart",
    "description": "Restart service",
    "type": "SCRIPT",
    "tags": ["ops", "restart"],
    "fields": "base64==",
    "metadata": {"builtIn": True},
    "createdAt": 1,
    "inputParameters": [
        {
            "name": "svc",
            "label": "Service",
            "description": "Svc name",
            "type": "STRING",
            "value": "x",
            "hidden": False,
            "secured": False,
        }
    ],
}


class TestActionCatalogE2E:
    """End-to-end tests for Automation Action Catalog MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_action_catalog_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ---------------------------------------------------------------- get_actions
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_actions_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse([RAW_ACTION])
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_actions(api_client=mock_api)

        assert isinstance(result, list)
        assert result[0]["id"] == "act-1"
        assert "fields" not in result[0]
        assert "metadata" not in result[0]
        param = result[0]["inputParameters"][0]
        assert param["name"] == "svc"
        assert param["required"] is False
        assert "hidden" not in param

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_actions_dict_with_actions_key(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse(
            {"actions": [{"id": "a", "name": "n"}]}
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_actions(api_client=mock_api)

        assert result == [{"id": "a", "name": "n", "description": None, "type": None, "tags": []}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_actions_unexpected_format_returned_as_is(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse({"foo": "bar"})
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_actions(api_client=mock_api)

        assert result == {"foo": "bar"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_actions_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_actions(api_client=mock_api)

        assert "Failed to parse JSON response" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_actions_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.side_effect = Exception("Boom")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_actions(api_client=mock_api)

        assert "Failed to get actions" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- get_action_details
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_details_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_by_id_without_preload_content.return_value = _MockResponse(RAW_ACTION)
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_details(action_id="act-1", api_client=mock_api)

        assert result["id"] == "act-1"
        assert result["tags"] == ["ops", "restart"]
        assert "createdAt" not in result
        mock_api.get_action_by_id_without_preload_content.assert_called_once_with(id="act-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("bad_id", ["", "   ", None])
    async def test_get_action_details_missing_id_returns_elicitation(self, instana_credentials, bad_id):
        mock_api = MagicMock()
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_details(action_id=bad_id, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "action_id" in result["reason"]
        mock_api.get_action_by_id_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_details_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_by_id_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_details(action_id="act-1", api_client=mock_api)

        assert "Failed to parse JSON response" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_details_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_by_id_without_preload_content.side_effect = Exception("Boom")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_details(action_id="act-1", api_client=mock_api)

        assert "Failed to get action details" in result["error"]

    # ---------------------------------------------------------------- get_action_types
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_types_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse(
            [{"type": "SCRIPT"}, {"type": "HTTP"}, {"type": "SCRIPT"}, {"name": "no-type"}, "junk"]
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_types(api_client=mock_api)

        assert sorted(result["types"]) == ["HTTP", "SCRIPT"]
        assert result["total_types"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_types_non_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse({"a": 1})
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_types(api_client=mock_api)

        assert result == {"types": [], "total_types": 0}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_types_invalid_json_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_types(api_client=mock_api)
        assert "Failed to parse JSON response" in result["error"]

        mock_api.get_actions_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_action_types(api_client=mock_api)
        assert "Failed to get action types" in result["error"]

    # ---------------------------------------------------------------- get_action_tags
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_tags_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse(
            [{"tags": ["a", "b"]}, {"tags": ["b", "c"]}, {"tags": "not-a-list"}, {"id": "x"}, "junk"]
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_tags(api_client=mock_api)

        assert sorted(result["tags"]) == ["a", "b", "c"]
        assert result["total_tags"] == 3

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_tags_non_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse({"a": 1})
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_tags(api_client=mock_api)

        assert result == {"tags": [], "total_tags": 0}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_tags_invalid_json_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_actions_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_tags(api_client=mock_api)
        assert "Failed to parse JSON response" in result["error"]

        mock_api.get_actions_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_action_tags(api_client=mock_api)
        assert "Failed to get action tags" in result["error"]

    # ---------------------------------------------------------------- get_action_matches
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_without_preload_content.return_value = _MockResponse(
            [
                {"score": 0.9, "aiEngine": "x", "confidence": "HIGH", "action": RAW_ACTION},
                {"score": 0.1},
            ]
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(
            payload={"name": "CPU high", "description": "desc"},
            target_snapshot_id="snap-1",
            api_client=mock_api,
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert result["data"][0]["action"]["id"] == "act-1"
        assert "fields" not in result["data"][0]["action"]
        assert result["data"][1] == {"score": 0.1}
        assert mock_api.get_action_matches_without_preload_content.call_args.kwargs["target_snapshot_id"] == "snap-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("make_payload", [
        json.dumps,
        lambda p: json.dumps(p).replace('"', "'"),
        repr,
    ], ids=["json", "single-quoted", "python-literal"])
    async def test_get_action_matches_string_payload_formats(self, instana_credentials, make_payload):
        mock_api = MagicMock()
        mock_api.get_action_matches_without_preload_content.return_value = _MockResponse([])
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(
            payload=make_payload({"name": "CPU high"}), api_client=mock_api
        )

        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_non_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_without_preload_content.return_value = _MockResponse({"k": "v"})
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(payload={"name": "CPU"}, api_client=mock_api)

        assert result["success"] is True
        assert result["data"] == {"k": "v"}
        assert "count" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_missing_payload(self, instana_credentials):
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(payload={}, api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert "payload is required" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_unparseable_payload(self, instana_credentials):
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(payload="{not: valid", api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert "not valid JSON" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("payload", [{"description": "x"}, {"name": "   "}, "[1, 2]"])
    async def test_get_action_matches_missing_name(self, instana_credentials, payload):
        mock_api = MagicMock()
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "payload.name" in result["api_error"][0]
        mock_api.get_action_matches_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_invalid_search_space(self, instana_credentials):
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(
            payload={"name": "CPU", "description": ["not", "a", "string"]}, api_client=MagicMock()
        )

        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_build_action_search_space_import_error(self, instana_credentials):
        client = create_action_catalog_client(instana_credentials)

        with patch.dict("sys.modules", {"instana_client.models.action_search_space": None}):
            result = client._build_action_search_space({"name": "CPU"})

        assert "Failed to import ActionSearchSpace" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_invalid_json_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_without_preload_content.return_value = _MockResponse(b"nope")
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches(payload={"name": "CPU"}, api_client=mock_api)
        assert "Failed to parse JSON response" in result["error"]

        mock_api.get_action_matches_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_action_matches(payload={"name": "CPU"}, api_client=mock_api)
        assert "Failed to get action matches" in result["error"]

    # ---------------------------------------------------------------- matches by id / window
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_by_id_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = _MockResponse(
            [{"score": 1, "aiEngine": "e", "confidence": "HIGH", "action": RAW_ACTION}, {"other": 1}]
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches_by_id_and_time_window(
            application_id="app-1", to=1710658800000, window_size=3600000, api_client=mock_api
        )

        assert result["success"] is True
        assert result["count"] == 2
        assert result["data"][0]["action"]["name"] == "Restart"
        assert result["data"][1] == {"other": 1}
        assert result["filters"] == {
            "application_id": "app-1", "snapshot_id": None, "to": 1710658800000, "window_size": 3600000,
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_by_id_with_snapshot(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = _MockResponse(
            {"matched": True}
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches_by_id_and_time_window(
            snapshot_id="snap-1", api_client=mock_api
        )

        assert result == {
            "success": True, "message": "Action matches retrieved successfully", "data": {"matched": True},
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_by_id_api_reports_errors(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = _MockResponse(
            {"errors": ["bad"]}
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches_by_id_and_time_window(
            application_id="app-1", api_client=mock_api
        )

        assert "API returned error" in result["error"]
        assert result["details"] == {"errors": ["bad"]}
        assert result["filters"]["application_id"] == "app-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_by_id_preflight_missing_ids(self, instana_credentials):
        mock_api = MagicMock()
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches_by_id_and_time_window(api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "application_id" in result["api_error"][0]
        mock_api.get_action_matches_by_id_and_time_window_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_by_id_preflight_invalid_values(self, instana_credentials):
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches_by_id_and_time_window(
            application_id="app-1", to="yesterday", window_size="big", api_client=MagicMock()
        )
        assert len(result["api_error"]) == 2
        assert "to: must be an integer" in result["api_error"][0]
        assert "window_size: must be a positive integer" in result["api_error"][1]

        result = await client.get_action_matches_by_id_and_time_window(
            application_id="app-1", to=123, window_size=-5, api_client=MagicMock()
        )
        assert len(result["api_error"]) == 2
        assert "not a valid 13-digit" in result["api_error"][0]
        assert "must be ≥ 0" in result["api_error"][1]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_matches_by_id_invalid_json_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_matches_by_id_and_time_window_without_preload_content.return_value = _MockResponse(
            b"nope"
        )
        client = create_action_catalog_client(instana_credentials)

        result = await client.get_action_matches_by_id_and_time_window(
            application_id="app-1", api_client=mock_api
        )
        assert "Failed to parse JSON response" in result["error"]

        mock_api.get_action_matches_by_id_and_time_window_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_action_matches_by_id_and_time_window(
            application_id="app-1", api_client=mock_api
        )
        assert "Failed to get action matches by ID and time window" in result["error"]
