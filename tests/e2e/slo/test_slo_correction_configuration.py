"""
E2E tests for SLO Correction Configuration MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_slo_correction_client(instana_credentials):
    """Dynamically import and create SLO Correction client"""
    module = importlib.import_module("src.slo.slo_correction_configuration")
    module = importlib.reload(module)
    return module.SLOCorrectionMCPTools(
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


CORRECTION = {
    "id": "corr-1",
    "name": "Maintenance",
    "description": "Planned",
    "sloIds": ["slo-1"],
    "scheduling": {"duration": 2, "durationUnit": "hour"},
    "tags": ["maint"],
    "createdDate": 1700000000000,
    "lastUpdated": 1700000001000,
    "internal": "dropped",
}


def _valid_payload():
    return {
        "name": "Maintenance",
        "description": "Planned",
        "sloIds": ["slo-1"],
        "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": 1700000000000},
        "tags": ["maint"],
        "active": True,
    }


class TestSLOCorrectionConfigurationE2E:
    """End-to-end tests for SLO Correction Configuration MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ------------------------------------------------------------------ get_all
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_corrections_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = _MockResponse(
            {"items": [CORRECTION], "totalHits": 1}
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_all_corrections(page_size=5, page=1, query="Maint", api_client=mock_api)

        assert result["totalHits"] == 1
        assert result["items"][0]["id"] == "corr-1"
        assert "internal" not in result["items"][0]
        kwargs = mock_api.get_all_slo_correction_window_configs_without_preload_content.call_args.kwargs
        assert kwargs["page_size"] == 5
        assert kwargs["query"] == "Maint"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_corrections_without_items(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = _MockResponse(
            {"totalHits": 0}
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_all_corrections(api_client=mock_api)

        assert result == {"totalHits": 0}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_corrections_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = _MockResponse(
            b"forbidden", status=403
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_all_corrections(api_client=mock_api)

        assert "API error (status 403)" in result["error"]
        assert "forbidden" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_corrections_api_error_no_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_correction_window_configs_without_preload_content.return_value = _MockResponse(
            b"", status=500
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_all_corrections(api_client=mock_api)

        assert "No error details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_corrections_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_slo_correction_window_configs_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_all_corrections(api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ get by id
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_correction_by_id_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_correction_window_config_by_id_without_preload_content.return_value = _MockResponse(
            CORRECTION
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_correction_by_id(id="corr-1", api_client=mock_api)

        assert result["id"] == "corr-1"
        assert result["name"] == "Maintenance"
        assert "internal" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_correction_by_id_missing_id(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_correction_by_id(id="", api_client=MagicMock())

        assert result == {"error": "ID is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_correction_by_id_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_correction_window_config_by_id_without_preload_content.return_value = _MockResponse(
            b"missing", status=404
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_correction_by_id(id="nope", api_client=mock_api)

        assert "API error (status 404)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_correction_by_id_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_slo_correction_window_config_by_id_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_correction_client(instana_credentials)

        result = await client.get_correction_by_id(id="corr-1", api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ create
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_success_dict_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            CORRECTION
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload=_valid_payload(), api_client=mock_api)

        assert result["success"] is True
        assert result["message"] == "Correction window created"
        assert result["data"]["id"] == "corr-1"
        mock_api.create_slo_correction_window_config_without_preload_content.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_success_json_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            CORRECTION
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload=json.dumps(_valid_payload()), api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_success_python_literal_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            CORRECTION
        )
        client = create_slo_correction_client(instana_credentials)

        # Single-quoted dict literal is not valid JSON -> falls back to ast.literal_eval
        result = await client.create_correction(payload=repr(_valid_payload()), api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_invalid_string_payload(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload="not a payload (", api_client=MagicMock())

        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_missing_payload(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload={}, api_client=MagicMock())

        assert result == {"error": "payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_elicitation_when_everything_missing(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload={"description": "x"}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert set(result["missing_parameters"]) == {"name", "sloIds", "scheduling"}
        assert "**Top-level fields:**" in result["message"]
        mock_api.create_slo_correction_window_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_elicitation_scheduling_fields(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)
        payload = {"name": "n", "sloIds": ["s"], "scheduling": {}}

        result = await client.create_correction(payload=payload, api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert result["missing_parameters"] == ["scheduling.duration", "scheduling.durationUnit"]
        assert "**Scheduling fields:**" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_elicitation_invalid_scheduling_values(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)
        payload = {
            "name": "n",
            "sloIds": ["s"],
            "scheduling": {"duration": -1, "durationUnit": "fortnight"},
        }

        result = await client.create_correction(payload=payload, api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert result["missing_parameters"] == ["scheduling.duration", "scheduling.durationUnit"]
        assert "Invalid duration: -1" in result["message"]
        assert "Invalid durationUnit: fortnight" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_non_dict_scheduling_passes_validation(self, instana_credentials):
        """A non-dict scheduling skips nested validation; later steps surface the error."""
        client = create_slo_correction_client(instana_credentials)
        payload = {"name": "n", "sloIds": ["s"], "scheduling": "weekly"}

        result = await client.create_correction(payload=payload, api_client=MagicMock())

        assert "error" in result
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            b"bad", status=400
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload=_valid_payload(), api_client=mock_api)

        assert "API error (status 400)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_api_error_no_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            b"", status=500
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload=_valid_payload(), api_client=mock_api)

        assert "No error details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_correction_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_slo_correction_window_config_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_correction_client(instana_credentials)

        result = await client.create_correction(payload=_valid_payload(), api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ update
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            CORRECTION
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="corr-1", payload=_valid_payload(), api_client=mock_api)

        assert result["success"] is True
        assert result["message"] == "Correction window updated"
        assert result["data"]["id"] == "corr-1"
        kwargs = mock_api.update_slo_correction_window_config_without_preload_content.call_args.kwargs
        assert kwargs["id"] == "corr-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            CORRECTION
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(
            id="corr-1", payload=json.dumps(_valid_payload()), api_client=mock_api
        )
        assert result["success"] is True

        result = await client.update_correction(
            id="corr-1", payload=repr(_valid_payload()), api_client=mock_api
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_missing_id(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="", payload=_valid_payload(), api_client=MagicMock())

        assert result == {"error": "Missing required parameter: id"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_missing_payload(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="corr-1", payload={}, api_client=MagicMock())

        assert result == {"error": "Missing required parameter: payload"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_elicitation_uses_update_wording(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="corr-1", payload={"name": "n"}, api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert "To update the SLO correction window" in result["message"]
        assert "To create an SLO correction window" not in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            b"conflict", status=409
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="corr-1", payload=_valid_payload(), api_client=mock_api)

        assert "API error (status 409)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_api_error_no_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_correction_window_config_without_preload_content.return_value = _MockResponse(
            b"", status=500
        )
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="corr-1", payload=_valid_payload(), api_client=mock_api)

        assert "No error details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_correction_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_slo_correction_window_config_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_correction_client(instana_credentials)

        result = await client.update_correction(id="corr-1", payload=_valid_payload(), api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ delete
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_correction_success(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_correction_client(instana_credentials)

        result = await client.delete_correction(id="corr-1", api_client=mock_api)

        assert result == {"success": True, "message": "Correction window 'corr-1' deleted"}
        mock_api.delete_slo_correction_window_config.assert_called_once_with(id="corr-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_correction_missing_id(self, instana_credentials):
        client = create_slo_correction_client(instana_credentials)

        result = await client.delete_correction(id="", api_client=MagicMock())

        assert result == {"error": "id is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_correction_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_slo_correction_window_config.side_effect = Exception("Boom")
        client = create_slo_correction_client(instana_credentials)

        result = await client.delete_correction(id="corr-1", api_client=mock_api)

        assert result == {"error": "Boom"}
