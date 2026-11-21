"""
E2E tests for SLO Alert Configuration MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_slo_alert_client(instana_credentials):
    """Dynamically import and create SLO Alert Config client"""
    module = importlib.import_module("src.slo.slo_alert_config")
    module = importlib.reload(module)
    return module.SLOAlertConfigMCPTools(
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


ALERT_CONFIG = {
    "id": "alert-1",
    "name": "Burn Rate",
    "description": "High burn rate",
    "sloIds": ["slo-1"],
    "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE_V2"},
    "severity": 10,
    "alertChannelIds": ["ch-1"],
    "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
    "customPayloadFields": [],
    "internalField": "dropped",
}


def _valid_payload():
    return {
        "name": "Burn Rate",
        "description": "High burn rate",
        "sloIds": ["slo-1"],
        "severity": 10,
        "alertChannelIds": ["ch-1"],
        "customPayloadFields": [{"type": "staticString", "key": "env", "value": "prod"}],
        "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE_V2"},
        "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000},
    }


class TestSLOAlertConfigE2E:
    """End-to-end tests for SLO Alert Configuration MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ------------------------------------------------------------------ find_active
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_alert_configs_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = _MockResponse(
            [ALERT_CONFIG]
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_active_alert_configs(
            slo_id="slo-1", alert_ids=["alert-1"], api_client=mock_api
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["configs"][0]["id"] == "alert-1"
        assert "internalField" not in result["configs"][0]
        mock_api.find_active_service_levels_alert_configs_without_preload_content.assert_called_once_with(
            slo_id="slo-1", alert_ids=["alert-1"]
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_alert_configs_non_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = _MockResponse(
            {"unexpected": True}
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_active_alert_configs(api_client=mock_api)

        assert result == {"success": True, "configs": [], "count": 0}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_alert_configs_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = _MockResponse(
            b"denied", status=403
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_active_alert_configs(api_client=mock_api)

        assert "API error (status 403)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_alert_configs_api_error_no_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_service_levels_alert_configs_without_preload_content.return_value = _MockResponse(
            b"", status=500
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_active_alert_configs(api_client=mock_api)

        assert "No error details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_alert_configs_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_active_service_levels_alert_configs_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_active_alert_configs(api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ find
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_alert_config(id="alert-1", valid_on=1700000000000, api_client=mock_api)

        assert result["id"] == "alert-1"
        assert "internalField" not in result
        mock_api.find_service_levels_alert_config_without_preload_content.assert_called_once_with(
            id="alert-1", valid_on=1700000000000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_id_validation(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        assert await client.find_alert_config(id="", api_client=MagicMock()) == {"error": "id is required"}
        assert await client.find_alert_config(id=123, api_client=MagicMock()) == {"error": "id must be a string"}
        assert await client.find_alert_config(id="   ", api_client=MagicMock()) == {"error": "id cannot be empty"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_invalid_valid_on(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_alert_config(id="alert-1", valid_on="yesterday", api_client=MagicMock())

        assert result == {"error": "valid_on must be an integer timestamp"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            b"missing", status=404
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_alert_config(id="alert-1", api_client=mock_api)

        assert "API error (status 404)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_service_levels_alert_config_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_alert_config(id="alert-1", api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ versions
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_versions_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.find_service_levels_alert_config_versions_without_preload_content.return_value = _MockResponse(
            [{"created": 1}, {"created": 2}]
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.find_alert_config_versions(id="alert-1", api_client=mock_api)

        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_alert_config_versions_validation_and_errors(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        assert await client.find_alert_config_versions(id="", api_client=MagicMock()) == {
            "error": "id is required"
        }

        mock_api = MagicMock()
        mock_api.find_service_levels_alert_config_versions_without_preload_content.return_value = _MockResponse(
            b"bad", status=400
        )
        result = await client.find_alert_config_versions(id="alert-1", api_client=mock_api)
        assert "API error (status 400)" in result["error"]

        mock_api.find_service_levels_alert_config_versions_without_preload_content.side_effect = Exception("Boom")
        result = await client.find_alert_config_versions(id="alert-1", api_client=mock_api)
        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ create
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.create_alert_config(payload=_valid_payload(), api_client=mock_api)

        assert result["success"] is True
        assert result["message"] == "Alert config created"
        assert result["data"]["id"] == "alert-1"
        mock_api.create_service_levels_alert_config_without_preload_content.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_burn_rate_with_threshold_and_windows(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["rule"] = {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"}
        payload["threshold"] = {"type": "staticThreshold", "operator": ">=", "value": 2.0}
        payload["burnRateTimeWindows"] = {
            "longTimeWindow": {"duration": 1, "durationType": "hour"},
            "shortTimeWindow": {"duration": 5, "durationType": "minute"},
        }

        result = await client.create_alert_config(payload=payload, api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_service_levels_objective_rule(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["rule"] = {"alertType": "SERVICE_LEVELS_OBJECTIVE"}

        result = await client.create_alert_config(payload=payload, api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_json_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.create_alert_config(payload=json.dumps(_valid_payload()), api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_unparseable_payload(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        result = await client.create_alert_config(payload="{not: valid", api_client=MagicMock())

        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_elicitation_all_missing(self, instana_credentials):
        mock_api = MagicMock()
        client = create_slo_alert_client(instana_credentials)

        result = await client.create_alert_config(payload={"x": 1}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert set(result["missing_parameters"]) == {
            "name", "description", "sloIds", "severity", "alertChannelIds",
            "customPayloadFields", "rule", "timeThreshold",
        }
        assert "**Top-level fields:**" in result["message"]
        mock_api.create_service_levels_alert_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_elicitation_invalid_severity(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["severity"] = 7

        result = await client.create_alert_config(payload=payload, api_client=MagicMock())

        assert result["missing_parameters"] == ["severity"]
        assert "Invalid severity" in result["parameter_details"][0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_elicitation_rule_fields(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()

        payload["rule"] = {}
        result = await client.create_alert_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["rule.alertType"]
        assert "**Rule fields:**" in result["message"]

        payload["rule"] = {"alertType": "ERROR_BUDGET"}
        result = await client.create_alert_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["rule.metric"]

        payload["rule"] = {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"}
        result = await client.create_alert_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["burnRateTimeWindows"]
        assert "**Conditional fields" in result["message"]

        payload["rule"] = "ERROR_BUDGET"
        result = await client.create_alert_config(payload=payload, api_client=MagicMock())
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_elicitation_time_threshold_fields(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()

        payload["timeThreshold"] = {}
        result = await client.create_alert_config(payload=payload, api_client=MagicMock())
        assert result["missing_parameters"] == ["timeThreshold.expiry", "timeThreshold.timeWindow"]
        assert "**Time threshold fields:**" in result["message"]

        payload["timeThreshold"] = 5
        result = await client.create_alert_config(payload=payload, api_client=MagicMock())
        assert "elicitation_needed" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_invalid_alert_type(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["rule"] = {"alertType": "BOGUS"}

        result = await client.create_alert_config(payload=payload, api_client=MagicMock())

        assert "Invalid alertType: BOGUS" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_time_threshold_incomplete(self, instana_credentials):
        """Reach the builder's own check by bypassing the elicitation validator."""
        client = create_slo_alert_client(instana_credentials)
        body = _valid_payload()
        body["timeThreshold"] = {"expiry": 1}

        result = client._build_alert_config_object(body)

        assert "timeThreshold must include both" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_build_alert_config_object_guard_branches(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        body = _valid_payload()
        body["rule"] = {"alertType": "ERROR_BUDGET"}
        assert "rule.metric is required" in client._build_alert_config_object(body)["error"]

        body = _valid_payload()
        body["rule"] = {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"}
        assert "burnRateTimeWindows is required" in client._build_alert_config_object(body)["error"]

        body = _valid_payload()
        body["rule"] = {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"}
        body["burnRateTimeWindows"] = {"longTimeWindow": {"duration": 1, "durationType": "hour"}}
        built = client._build_alert_config_object(body)
        assert not isinstance(built, dict)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_non_static_custom_fields_skipped(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["customPayloadFields"] = [{"type": "dynamic", "key": "k"}]

        result = await client.create_alert_config(payload=payload, api_client=mock_api)

        assert result["success"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_model_failure(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["rule"] = {"alertType": "ERROR_BUDGET", "metric": "NOT_A_METRIC"}

        result = await client.create_alert_config(payload=payload, api_client=MagicMock())

        assert "Failed to build alert config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            b"bad", status=400
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.create_alert_config(payload=_valid_payload(), api_client=mock_api)

        assert "API error (status 400)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_alert_config_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_service_levels_alert_config_without_preload_content.side_effect = Exception("Boom")
        client = create_slo_alert_client(instana_credentials)

        result = await client.create_alert_config(payload=_valid_payload(), api_client=mock_api)

        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ update
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_alert_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            ALERT_CONFIG
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.update_alert_config(id="alert-1", payload=_valid_payload(), api_client=mock_api)

        assert result["success"] is True
        assert result["message"] == "Alert config updated"
        assert mock_api.update_service_levels_alert_config_without_preload_content.call_args.kwargs["id"] == "alert-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_alert_config_invalid_id(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        result = await client.update_alert_config(id="", payload=_valid_payload(), api_client=MagicMock())

        assert result == {"error": "id is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_alert_config_unparseable_payload(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        result = await client.update_alert_config(id="alert-1", payload="{not: valid", api_client=MagicMock())

        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_alert_config_elicitation_uses_update_wording(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        result = await client.update_alert_config(id="alert-1", payload={"name": "x"}, api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert "To update the SLO alert configuration" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_alert_config_builder_error(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)
        payload = _valid_payload()
        payload["rule"] = {"alertType": "BOGUS"}

        result = await client.update_alert_config(id="alert-1", payload=payload, api_client=MagicMock())

        assert "Invalid alertType" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_alert_config_api_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            b"conflict", status=409
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.update_alert_config(id="alert-1", payload=_valid_payload(), api_client=mock_api)
        assert "API error (status 409)" in result["error"]

        mock_api.update_service_levels_alert_config_without_preload_content.side_effect = Exception("Boom")
        result = await client.update_alert_config(id="alert-1", payload=_valid_payload(), api_client=mock_api)
        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ delete / enable / disable
    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("method,sdk_method,verb", [
        ("delete_alert_config", "delete_service_levels_alert_config", "deleted"),
        ("disable_alert_config", "disable_service_levels_alert_config", "disabled"),
        ("enable_alert_config", "enable_service_levels_alert_config", "enabled"),
    ])
    async def test_simple_alert_operations(self, instana_credentials, method, sdk_method, verb):
        client = create_slo_alert_client(instana_credentials)
        mock_api = MagicMock()

        result = await getattr(client, method)(id="alert-1", api_client=mock_api)
        assert result == {"success": True, "message": f"Alert config 'alert-1' {verb}"}
        getattr(mock_api, sdk_method).assert_called_once_with(id="alert-1")

        result = await getattr(client, method)(id="", api_client=MagicMock())
        assert result == {"error": "id is required"}

        failing_api = MagicMock()
        getattr(failing_api, sdk_method).side_effect = Exception("Boom")
        result = await getattr(client, method)(id="alert-1", api_client=failing_api)
        assert result == {"error": "Boom"}

    # ------------------------------------------------------------------ restore
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_alert_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.restore_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            b"", status=204
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.restore_alert_config(id="alert-1", created=1700000000000, api_client=mock_api)

        assert result["success"] is True
        assert "restored" in result["message"]
        mock_api.restore_service_levels_alert_config_without_preload_content.assert_called_once_with(
            id="alert-1", created=1700000000000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_alert_config_validation(self, instana_credentials):
        client = create_slo_alert_client(instana_credentials)

        assert await client.restore_alert_config(id="", created=1, api_client=MagicMock()) == {
            "error": "id is required"
        }
        assert await client.restore_alert_config(id="alert-1", created=0, api_client=MagicMock()) == {
            "error": "created is required"
        }
        assert await client.restore_alert_config(id="alert-1", created="soon", api_client=MagicMock()) == {
            "error": "created must be an integer timestamp"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_alert_config_api_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.restore_service_levels_alert_config_without_preload_content.return_value = _MockResponse(
            b"nope", status=404
        )
        client = create_slo_alert_client(instana_credentials)

        result = await client.restore_alert_config(id="alert-1", created=1, api_client=mock_api)
        assert "API error (status 404)" in result["error"]

        mock_api.restore_service_levels_alert_config_without_preload_content.side_effect = Exception("Boom")
        result = await client.restore_alert_config(id="alert-1", created=1, api_client=mock_api)
        assert result == {"error": "Boom"}
