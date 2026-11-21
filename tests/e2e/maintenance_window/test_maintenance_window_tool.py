"""
E2E tests for Maintenance Window MCP Tools

The tests drive the public dispatcher (``execute_maintenance_operation``) and the
decorated operation methods using a mocked Instana SDK API client.
"""

import importlib
import json
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _require_real_sdk():
    """Skip when another test module replaced the SDK with MagicMocks (mixed test runs)."""
    mocked = [
        name for name, mod in sys.modules.items()
        if name.startswith("instana_client") and isinstance(mod, MagicMock)
    ]
    if mocked:
        pytest.skip(f"instana_client is mocked in this session: {mocked[0]}")

HOUR_MS = 60 * 60 * 1000
DAY_MS = 24 * HOUR_MS


class MaintenanceConfigurationApi(MagicMock):
    """Stand-in SDK API class.

    The class name matches the real SDK class so ``with_header_auth`` re-uses an
    instance attached to the client (STDIO mode) instead of building a real one.
    """


class _MockResponse:
    def __init__(self, payload=None, status=200, raw=None):
        if raw is not None:
            self.data = raw
        elif payload is None:
            self.data = b""
        else:
            self.data = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers = {"Content-Type": "application/json"}


def _future(hours=24):
    return int(time.time() * 1000) + hours * HOUR_MS


def create_maintenance_window_client(instana_credentials, **kwargs):
    """Dynamically import and create the Maintenance Window client with a mocked SDK API."""
    module = importlib.import_module("src.maintenance_window.maintenance_window_tool")
    module = importlib.reload(module)
    client = module.MaintenanceWindowMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
        **kwargs,
    )
    client.maintenance_configuration_api = MaintenanceConfigurationApi()
    return client


def _api(client):
    return client.maintenance_configuration_api


def _window(state="ACTIVE", query="entity.tag:imap=EAL-1", **extra):
    base = {"id": f"w-{state.lower()}", "name": f"win_{state}", "query": query, "state": state}
    base.update(extra)
    return base


def _existing_window(start=None, rrule=None, **extra):
    scheduling = {
        "start": start or _future(),
        "duration": {"amount": 2, "unit": "HOURS"},
        "type": "RECURRENT" if rrule else "ONE_TIME",
    }
    if rrule:
        scheduling["rrule"] = rrule
        scheduling["timezoneId"] = "UTC"
    window = {
        "id": "mw-1",
        "name": "EAL-1_Deploy_2026_01_01",
        "query": "entity.tag:imap=EAL-1",
        "paused": False,
        "scheduling": scheduling,
        "tagFilterExpressionEnabled": False,
        "retriggerOpenAlertsEnabled": False,
    }
    window.update(extra)
    return window


class TestMaintenanceWindowDispatcherE2E:
    """Dispatcher, validation and helper behaviour."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_maintenance_window_client(
            instana_credentials, servicenow_token="snow", servicenow_url="https://snow.example.com"
        )
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
        assert client.servicenow_token == "snow"
        assert client.servicenow_url == "https://snow.example.com"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_templates(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(operation="get_templates")

        assert result["status"] == "success"
        assert set(result["templates"]) == {
            "deployment", "database_migration", "infrastructure_upgrade", "emergency", "routine"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation_returns_elicitation(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(operation="explode")

        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        assert "explode" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_numeric_string_parameter_returns_elicitation(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="create", params={"imap_code": "EAL-1", "start_time": "tomorrow"}
        )

        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_param_type"
        assert result["api_error"][0]["field"] == "start_time"
        assert "e.g., 1745020800000" in result["api_error"][0]["expected"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_numeric_end_time_has_no_example(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="create",
            params={"imap_code": "EAL-1", "start_time": _future(), "end_time": "later"},
        )

        assert result["reason"] == "invalid_param_type"
        assert result["api_error"][0]["field"] == "end_time"
        assert "e.g." not in result["api_error"][0]["expected"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_string_integers_are_converted_and_kwargs_style_supported(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        # kwargs style (old call convention) with numeric strings
        result = await client.execute_maintenance_operation(
            operation="validate",
            imap_code="EAL-1",
            start_time=str(_future()),
            duration_minutes="60",
        )

        assert result["status"] == "valid"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatcher_exception_is_returned_as_error(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        with patch.object(client, "_extract_maintenance_params", side_effect=RuntimeError("boom")):
            result = await client.execute_maintenance_operation(operation="get_templates")

        assert result["operation"] == "get_templates"
        assert "Maintenance operation failed: boom" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_route_operation_unknown_operation(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client._route_operation(operation="bogus", params={}, ctx=None)

        assert result == {"error": "Operation 'bogus' not implemented"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_log_operation_start_branches(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        # modify / close (window id) and rrule logging branches must not raise
        client._log_operation_start("modify", "mw-1", None, None, 30, None, None, 1, "why", "FREQ=DAILY", "2030-01-01")
        client._log_operation_start("close", "mw-1", None, None, None, None, None, None, None, None, None)
        client._log_operation_start("create", None, "EAL-1", None, None, None, None, None, None, None, None)

    # ----------------------------- validate -----------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_validate_success(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="validate", params={"imap_code": "EAL-1", "start_time": _future()}
        )

        assert result == {"operation": "validate", "status": "valid", "message": "All parameters are valid"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_validate_accepts_application_id(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="validate", params={"application_id": "app-1", "start_time": _future()}
        )

        assert result["status"] == "valid"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_validate_missing_params(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(operation="validate", params={})

        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert "imap_code / application_id" in fields
        assert "start_time" in fields

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_validate_start_time_in_past(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="validate", params={"imap_code": "EAL-1", "start_time": 1000}
        )

        assert result["elicitation_needed"] is True
        assert "cannot be in the past" in result["api_error"][0]["issue"]


class TestMaintenanceWindowCreateE2E:
    """Create and bulk_create operations."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_success_with_template(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        start = _future()
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        result = await client.execute_maintenance_operation(
            operation="create",
            params={
                "imap_code": "EAL-012471",
                "template": "deployment",
                "start_time": start,
                "reason": "v2 rollout",
            },
        )

        assert result["status"] == "success"
        details = result["details"]
        assert details["application"] == "EAL-012471"
        assert details["template_used"] == "deployment"
        assert details["reason"] == "v2 rollout"
        assert details["window_name"].startswith("EAL-012471_v2_rollout_")
        assert details["schedule"]["duration"] == "1 hours"
        assert result["raw_data"]["end_time"] == start + HOUR_MS
        put = _api(client).put_maintenance_config_v2_without_preload_content
        assert put.call_args.kwargs["id"] == details["window_id"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_with_keepalive_context(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        ctx = MagicMock()
        ctx.log = AsyncMock()
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        result = await client.execute_maintenance_operation(
            operation="create",
            params={"application_id": "app-1", "start_time": _future(), "duration_minutes": 90},
            ctx=ctx,
            resource_type="window",
            tool_name="manage_maintenance_windows",
        )

        assert result["status"] == "success"
        # 90 minutes => HOURS with amount 1 (integer division)
        assert result["details"]["schedule"]["duration"] == "1 hours"
        assert result["details"]["template_used"] == "none"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_with_tag_filter_expression(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        result = await client.execute_maintenance_operation(
            operation="create",
            params={
                "imap_code": "EAL-1",
                "start_time": _future(),
                "duration_days": 2,
                "use_tag_filter_expression": True,
                "tag_name": "custom.tag",
            },
        )

        assert result["status"] == "success"
        assert result["raw_data"]["duration_unit"] == "DAYS"
        assert result["raw_data"]["duration_amount"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_with_duration_hours(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        start = _future()
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        result = await client.execute_maintenance_operation(
            operation="create",
            params={"imap_code": "EAL-1", "start_time": start, "duration_hours": 3},
        )

        assert result["raw_data"]["duration_unit"] == "HOURS"
        assert result["raw_data"]["end_time"] == start + 3 * HOUR_MS

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_with_end_time_in_days_and_hours(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        start = _future()
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        days = await client.execute_maintenance_operation(
            operation="create",
            params={"imap_code": "EAL-1", "start_time": start, "end_time": start + 3 * DAY_MS},
        )
        hours = await client.execute_maintenance_operation(
            operation="create",
            params={"imap_code": "EAL-1", "start_time": start, "end_time": start + 5 * HOUR_MS},
        )

        assert days["raw_data"]["duration_unit"] == "DAYS"
        assert days["raw_data"]["duration_amount"] == 3
        assert hours["raw_data"]["duration_unit"] == "HOURS"
        assert hours["raw_data"]["duration_amount"] == 5

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_recurring_with_until_date(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse(
                {"id": kw["id"], "scheduling": {"type": "RECURRENT", "rrule": "FREQ=DAILY;UNTIL=20991231T235959Z"}}
            )
        )

        result = await client.execute_maintenance_operation(
            operation="create",
            params={
                "imap_code": "EAL-1",
                "start_time": _future(),
                "duration_minutes": 30,
                "rrule": "FREQ=DAILY;INTERVAL=1",
                "until_date": "2099-12-31T23:59:59Z",
            },
        )

        assert result["status"] == "success"
        # recurring windows are rounded up to whole hours (30min -> 1h)
        assert result["raw_data"]["duration_amount"] == 1
        assert result["raw_data"]["duration_unit"] == "HOURS"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_recurring_rrule_rejected_by_api_logs_warning(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        result = await client.execute_maintenance_operation(
            operation="create",
            params={
                "imap_code": "EAL-1",
                "start_time": _future(),
                "duration_minutes": 90,
                "rrule": "FREQ=WEEKLY",
            },
        )

        assert result["status"] == "success"
        # 90 minutes rounds up to 2 hours for recurring windows
        assert result["raw_data"]["duration_amount"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_calls_servicenow_when_change_request_given(self, instana_credentials):
        client = create_maintenance_window_client(
            instana_credentials, servicenow_token="snow", servicenow_url="https://snow.example.com"
        )
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        with patch.object(client, "_update_servicenow_change", new=AsyncMock(return_value={})) as snow:
            result = await client.execute_maintenance_operation(
                operation="create",
                params={
                    "imap_code": "EAL-1",
                    "start_time": _future(),
                    "change_request_id": "CHG0012345",
                },
            )

        assert result["status"] == "success"
        snow.assert_awaited_once()
        assert snow.call_args.kwargs["change_request_id"] == "CHG0012345"
        assert snow.call_args.kwargs["status"] == "maintenance_scheduled"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_missing_and_invalid_params(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="create", params={"template": "nonexistent"}
        )

        assert result["elicitation_needed"] is True
        fields = {e["field"] for e in result["api_error"]}
        assert fields == {"imap_code / application_id", "start_time", "template"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_start_time_in_past(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(
            operation="create", params={"imap_code": "EAL-1", "start_time": 1000}
        )

        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"
        assert result["api_error"][0]["field"] == "start_time"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_end_time_before_start_time(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        start = _future()

        result = await client.execute_maintenance_operation(
            operation="create",
            params={"imap_code": "EAL-1", "start_time": start, "end_time": start - HOUR_MS},
        )

        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "end_time"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_http_error_status(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.return_value = _MockResponse(
            {"errors": ["bad"]}, status=400
        )

        result = await client.execute_maintenance_operation(
            operation="create", params={"imap_code": "EAL-1", "start_time": _future()}
        )

        assert result["status_code"] == 400
        assert "HTTP 400 error during create maintenance window" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_empty_response(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.return_value = _MockResponse(raw=b"")

        result = await client.execute_maintenance_operation(
            operation="create", params={"imap_code": "EAL-1", "start_time": _future()}
        )

        assert result == {"error": "Empty response from API"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_api_exception(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = Exception("API Error")

        result = await client.execute_maintenance_operation(
            operation="create", params={"imap_code": "EAL-1", "start_time": _future()}
        )

        assert "Failed to create maintenance window" in result["error"]
        assert "API Error" in result["error"]

    # ----------------------------- bulk_create -----------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_bulk_create_success(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = (
            lambda **kw: _MockResponse({"id": kw["id"], "scheduling": {"type": "ONE_TIME"}})
        )

        result = await client.execute_maintenance_operation(
            operation="bulk_create",
            params={
                "imap_codes": ["EAL-1", "ORZ-2"],
                "start_time": _future(),
                "duration_hours": 2,
                "reason": "Bulk upgrade",
            },
        )

        assert result["status"] == "success"
        assert result["total"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert [r["imap_code"] for r in result["results"]] == ["EAL-1", "ORZ-2"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_bulk_create_with_application_ids_and_partial_failure(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        responses = [
            _MockResponse({"id": "a", "scheduling": {"type": "ONE_TIME"}}),
            _MockResponse({"errors": ["nope"]}, status=500),
        ]
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = responses

        result = await client.execute_maintenance_operation(
            operation="bulk_create",
            params={"application_ids": ["app-1", "app-2"], "start_time": _future()},
        )

        assert result["successful"] == 1
        assert result["failed"] == 1
        assert result["results"][1]["result"]["status_code"] == 500

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_bulk_create_missing_params(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(operation="bulk_create", params={})

        assert result["elicitation_needed"] is True
        fields = {e["field"] for e in result["api_error"]}
        assert fields == {"imap_codes / application_ids", "start_time"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_bulk_create_unexpected_exception(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        with patch.object(client, "_create_maintenance_window", side_effect=RuntimeError("kaput")):
            result = await client.execute_maintenance_operation(
                operation="bulk_create",
                params={"imap_codes": ["EAL-1"], "start_time": _future()},
            )

        assert "Bulk create failed: kaput" in result["error"]


class TestMaintenanceWindowCreateHelpersE2E:
    """Pure helper methods used while creating windows."""

    @pytest.mark.mocked
    def test_calculate_duration_and_end_time_requires_start(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        with pytest.raises(ValueError, match="start_time is required"):
            client._calculate_duration_and_end_time(None, None, 60, None, None, None, {})

    @pytest.mark.mocked
    def test_calculate_duration_from_inputs_priority(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        assert client._calculate_duration_from_inputs(10, 2, 1, None, {})["duration_unit"] == "DAYS"
        assert client._calculate_duration_from_inputs(10, 2, None, None, {})["duration_unit"] == "HOURS"
        minutes = client._calculate_duration_from_inputs(None, None, None, None, {"default_duration": 180})
        assert minutes["duration_ms"] == 180 * 60 * 1000
        assert minutes["duration_amount"] == 3

    @pytest.mark.mocked
    def test_calculate_duration_from_minutes_sub_hour_non_recurring(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = client._calculate_duration_from_minutes(15, None, {})

        assert result["duration_amount"] == 1
        assert result["duration_ms"] == 15 * 60 * 1000

    @pytest.mark.mocked
    def test_adjust_duration_for_recurring(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        assert client._adjust_duration_for_recurring(30) == 60
        assert client._adjust_duration_for_recurring(61) == 120
        assert client._adjust_duration_for_recurring(120) == 120

    @pytest.mark.mocked
    def test_process_rrule_with_until_variants(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        added = client._process_rrule_with_until("FREQ=DAILY", "2030-05-06T07:08:09Z")
        assert added == "FREQ=DAILY;UNTIL=20300506T070809Z"

        kept = client._process_rrule_with_until("FREQ=DAILY;UNTIL=20290101T000000Z", "2030-05-06T07:08:09Z")
        assert kept == "FREQ=DAILY;UNTIL=20290101T000000Z"

        invalid = client._process_rrule_with_until("FREQ=DAILY", "not-a-date")
        assert invalid == "FREQ=DAILY"

        no_until = client._process_rrule_with_until("FREQ=DAILY", None)
        assert no_until == "FREQ=DAILY"

    @pytest.mark.mocked
    def test_build_scheduling_object(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        one_time = client._build_scheduling_object(1000, 2, "HOURS", None, None)
        assert one_time == {"start": 1000, "duration": {"amount": 2, "unit": "HOURS"}, "type": "ONE_TIME"}

        recurring = client._build_scheduling_object(1000, 2, "HOURS", "FREQ=DAILY", "2030-01-01T00:00:00Z")
        assert recurring["type"] == "RECURRENT"
        assert recurring["timezoneId"] == "UTC"
        assert recurring["rrule"].endswith("UNTIL=20300101T000000Z")

    @pytest.mark.mocked
    def test_build_window_payload_formats(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        scheduling = {"start": 1}

        query_format = client._build_window_payload("n", "EAL-1", scheduling, False, None)
        assert query_format["query"] == "entity.tag:imap=EAL-1"
        assert query_format["tagFilterExpressionEnabled"] is False

        tag_format = client._build_window_payload("n", "EAL-1", scheduling, True, None)
        assert tag_format["tagFilterExpression"]["name"] == "synthetic.tags"
        assert tag_format["tagFilterExpression"]["stringValue"] == "imap=EAL-1"
        assert tag_format["tagFilterExpressionEnabled"] is True

        custom = client._build_window_payload("n", "EAL-1", scheduling, True, "my.tag")
        assert custom["tagFilterExpression"]["name"] == "my.tag"

    @pytest.mark.mocked
    def test_check_response_status(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        assert client._check_response_status(_MockResponse(status=204), "op") is None
        assert client._check_response_status(object(), "op") is None
        error = client._check_response_status(_MockResponse(status=503), "op")
        assert error == {"error": "HTTP 503 error during op", "status_code": 503, "operation": "op"}


class TestMaintenanceWindowModifyE2E:
    """Modify operation."""

    def _prime(self, client, existing, put_response=None, verify=None):
        api = _api(client)
        api.get_maintenance_config_v2_without_preload_content.side_effect = [
            _MockResponse(existing),
            _MockResponse(verify if verify is not None else existing),
        ]
        api.put_maintenance_config_v2_without_preload_content.return_value = (
            put_response if put_response is not None else _MockResponse(existing)
        )
        return api

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_duration_hours_and_reason(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        existing = _existing_window()
        api = self._prime(client, existing)

        result = await client.execute_maintenance_operation(
            operation="modify",
            params={"window_id": "mw-1", "duration_hours": 4, "reason": "extended by team"},
        )

        assert result["status"] == "success"
        assert result["new_duration"] == "4 HOURS"
        assert result["window_name"] == "EAL-1_Deploy_2026_01_01_modified_extended_by_team"
        assert result["modifications"] == "duration changed to 4 HOURS, name updated with reason: extended by team"
        assert result["new_end_time"] == existing["scheduling"]["start"] + 4 * HOUR_MS
        assert result["verification"]["current_rrule"] == "N/A (ONE_TIME window)"
        assert api.put_maintenance_config_v2_without_preload_content.call_args.kwargs["id"] == "mw-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_duration_days_and_minutes(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        existing = _existing_window()
        self._prime(client, existing)

        days = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1", "duration_days": 2}
        )
        assert days["new_duration"] == "2 DAYS"

        self._prime(client, existing)
        minutes = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1", "duration_minutes": 45}
        )
        assert minutes["new_duration"] == "45 MINUTES"
        assert minutes["new_end_time"] == existing["scheduling"]["start"] + 45 * 60 * 1000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_rrule_and_until_date(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        existing = _existing_window(rrule="FREQ=DAILY;INTERVAL=1;UNTIL=20250101T000000Z")
        verify = _existing_window(rrule="FREQ=DAILY;INTERVAL=1;UNTIL=20300101T000000Z")
        api = self._prime(client, existing, verify=verify)

        result = await client.execute_maintenance_operation(
            operation="modify",
            params={"window_id": "mw-1", "until_date": "2030-01-01"},
        )

        assert result["modifications"] == "recurrence rule updated"
        assert result["new_duration"] == "unchanged"
        assert result["new_end_time"] == "unchanged"
        assert result["verification"]["recurrence_type"] == "RECURRENT"
        assert result["verification"]["current_rrule"].endswith("UNTIL=20300101T000000Z")
        assert api.put_maintenance_config_v2_without_preload_content.called

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_explicit_rrule_overrides_until(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        existing = _existing_window()
        self._prime(client, existing)

        result = await client.execute_maintenance_operation(
            operation="modify",
            params={"window_id": "mw-1", "rrule": "FREQ=WEEKLY", "until_date": "2030-01-01T10:00:00Z"},
        )

        assert result["status"] == "success"
        assert result["modifications"] == "recurrence rule updated"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_without_changes_reports_window_updated(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, _existing_window(description="d"))

        result = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1"}
        )

        assert result["modifications"] == "window updated"
        assert result["modification_reason"] == "Window modified"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_invalid_until_date(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, _existing_window())

        result = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1", "until_date": "garbage"}
        )

        assert "Invalid until_date format: garbage" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_missing_window_id(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(operation="modify", params={})

        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "window_id"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_fetch_failures(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        api = _api(client)

        api.get_maintenance_config_v2_without_preload_content.return_value = _MockResponse({}, status=404)
        http_error = await client.execute_maintenance_operation(operation="modify", params={"window_id": "mw-1"})
        assert http_error["status_code"] == 404

        api.get_maintenance_config_v2_without_preload_content.return_value = _MockResponse(raw=b"")
        not_found = await client.execute_maintenance_operation(operation="modify", params={"window_id": "mw-1"})
        assert not_found == {"error": "Maintenance window not found: mw-1"}

        api.get_maintenance_config_v2_without_preload_content.side_effect = Exception("down")
        failed = await client.execute_maintenance_operation(operation="modify", params={"window_id": "mw-1"})
        assert "Failed to fetch window: down" in failed["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_modify_update_failures(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        existing = _existing_window()

        self._prime(client, existing, put_response=_MockResponse({"x": 1}, status=500))
        http_error = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1", "duration_hours": 1}
        )
        assert http_error["status_code"] == 500

        self._prime(client, existing, put_response=_MockResponse(raw=b""))
        empty = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1", "duration_hours": 1}
        )
        assert empty == {"error": "Empty response from API"}

        self._prime(client, existing)
        _api(client).put_maintenance_config_v2_without_preload_content.side_effect = Exception("put failed")
        raised = await client.execute_maintenance_operation(
            operation="modify", params={"window_id": "mw-1", "duration_hours": 1}
        )
        assert "Failed to modify maintenance window: put failed" in raised["error"]

    @pytest.mark.mocked
    def test_modify_helpers(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        # duration units
        payload = {}
        client._update_duration_in_payload(payload, 2880)
        assert payload["scheduling"]["duration"] == {"amount": 2, "unit": "DAYS"}
        client._update_duration_in_payload(payload, 120)
        assert payload["scheduling"]["duration"] == {"amount": 2, "unit": "HOURS"}

        # until_date parsing
        assert client._parse_until_date("2030-01-02")[0] == "20300102T235959Z"
        assert client._parse_until_date("2030-01-02T03:04:05Z")[0] == "20300102T030405Z"
        assert client._parse_until_date(1893456000000)[1] is None
        value, error = client._parse_until_date("nope")
        assert value is None
        assert "Invalid until_date format" in error

        # rrule/until merging
        assert client._update_rrule_with_until("FREQ=DAILY;UNTIL=1", "2") == "FREQ=DAILY;UNTIL=2"
        assert client._update_rrule_with_until("UNTIL=1;FREQ=DAILY", "2") == "FREQ=DAILY;UNTIL=2"
        assert client._update_rrule_with_until("", "2") == "FREQ=DAILY;INTERVAL=1;UNTIL=2"

        # _update_rrule_in_payload without scheduling / nothing to do
        assert client._update_rrule_in_payload({}, None, None) is None
        bare = {}
        assert client._update_rrule_in_payload(bare, "FREQ=HOURLY", None) is None
        assert bare["scheduling"]["rrule"] == "FREQ=HOURLY"
        assert "Invalid until_date" in client._update_rrule_in_payload({}, None, "bad")

        # name handling strips a prior suffix
        renamed = {}
        client._update_window_name_with_reason(renamed, "new reason", {"name": "base_modified_old"})
        assert renamed["name"] == "base_modified_new_reason"

        # end time for each unit
        base = {"scheduling": {"start": 0, "duration": {"amount": 1, "unit": "DAYS"}}}
        assert client._calculate_new_end_time(base) == DAY_MS
        base["scheduling"]["duration"] = {"amount": 2, "unit": "HOURS"}
        assert client._calculate_new_end_time(base) == 2 * HOUR_MS
        base["scheduling"]["duration"] = {"amount": 5, "unit": "MINUTES"}
        assert client._calculate_new_end_time(base) == 5 * 60 * 1000

        # summary variants
        assert client._build_modification_summary(None, 0, "HOURS", None, None, None) == "window updated"
        assert "recurrence rule updated" in client._build_modification_summary(None, 0, "HOURS", "R", None, None)

    @pytest.mark.mocked
    def test_build_base_modify_payload_preserves_optional_fields(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        existing = {
            "name": "n",
            "applicationNames": ["a"],
            "validVersion": 3,
            "description": "d",
            "tagFilterExpression": {"type": "TAG_FILTER"},
        }

        payload = client._build_base_modify_payload("id-1", existing)

        assert payload["id"] == "id-1"
        assert payload["scheduling"] == {}
        assert payload["applicationNames"] == ["a"]
        assert payload["validVersion"] == 3
        assert payload["description"] == "d"
        assert payload["tagFilterExpression"] == {"type": "TAG_FILTER"}


class TestMaintenanceWindowCloseE2E:
    """Close operation."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_close_success(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        api = _api(client)
        api.delete_maintenance_config_v2_without_preload_content.return_value = _MockResponse(status=204)

        result = await client.execute_maintenance_operation(
            operation="close", params={"window_id": "mw-1", "completion_notes": "all good"}
        )

        assert result["status"] == "success"
        assert result["window_id"] == "mw-1"
        assert result["completion_notes"] == "all good"
        assert isinstance(result["closed_at"], int)
        api.delete_maintenance_config_v2_without_preload_content.assert_called_once_with(id="mw-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_close_default_notes(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).delete_maintenance_config_v2_without_preload_content.return_value = _MockResponse(status=200)

        result = await client.execute_maintenance_operation(operation="close", params={"window_id": "mw-1"})

        assert result["completion_notes"] == "Maintenance completed"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_close_missing_window_id(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client.execute_maintenance_operation(operation="close", params={})

        assert result["elicitation_needed"] is True
        assert result["api_error"][0]["field"] == "window_id"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_close_http_error_and_exception(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        api = _api(client)

        api.delete_maintenance_config_v2_without_preload_content.return_value = _MockResponse(status=404)
        http_error = await client.execute_maintenance_operation(operation="close", params={"window_id": "mw-1"})
        assert http_error["status_code"] == 404

        api.delete_maintenance_config_v2_without_preload_content.side_effect = Exception("delete failed")
        raised = await client.execute_maintenance_operation(operation="close", params={"window_id": "mw-1"})
        assert "Failed to close maintenance window: delete failed" in raised["error"]


class TestMaintenanceWindowListE2E:
    """list_active / list_scheduled / list_all / list_expired operations."""

    def _windows(self):
        now = int(time.time() * 1000)
        return [
            _window("ACTIVE", "entity.tag:imap=EAL-1"),
            _window("SCHEDULED", "entity.tag:imap=ORZ-2"),
            _window("EXPIRED", "entity.tag:imap=EAL-1"),
            _window("EXPIRED", "", tagFilterExpression={"value": "TAGGED-3"}),
            # no state, active by occurrence time
            {"id": "w-time", "name": "time", "query": "entity.tag:imap=TIME-1",
             "occurrence": {"start": now - HOUR_MS, "end": now + HOUR_MS}},
            # no state, not currently active
            {"id": "w-old", "name": "old", "query": "entity.tag:imap=OLD-1",
             "occurrence": {"start": 1, "end": 2}},
        ]

    def _prime(self, client, payload, status=200):
        _api(client).get_maintenance_configs_v2_without_preload_content.return_value = _MockResponse(
            payload, status=status
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_active(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, self._windows())

        result = await client.execute_maintenance_operation(operation="list_active", params={})

        assert result["status"] == "success"
        assert result["count"] == 2
        assert {w["id"] for w in result["windows"]} == {"w-active", "w-time"}
        assert result["application_id"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_active_with_application_filter(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, self._windows())

        by_imap = await client.execute_maintenance_operation(
            operation="list_active", params={"imap_code": "EAL-1"}
        )
        by_time = await client.execute_maintenance_operation(
            operation="list_active", params={"application_id": "TIME-1"}
        )

        assert [w["id"] for w in by_imap["windows"]] == ["w-active"]
        assert [w["id"] for w in by_time["windows"]] == ["w-time"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_active_none_found_returns_helpful_summary(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, [_window("EXPIRED"), _window("SCHEDULED"), _window("SCHEDULED")])

        unfiltered = await client.execute_maintenance_operation(operation="list_active", params={})
        filtered = await client.execute_maintenance_operation(
            operation="list_active", params={"imap_code": "EAL-1"}
        )

        assert unfiltered["count"] == 0
        assert unfiltered["expired_count"] == 1
        assert unfiltered["scheduled_count"] == 2
        assert "No active maintenance windows found." in unfiltered["message"]
        assert filtered["application_id"] == "EAL-1"
        assert "for 'EAL-1'" in filtered["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_active_non_list_and_empty_payload(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        self._prime(client, {"unexpected": "dict"})
        non_list = await client.execute_maintenance_operation(operation="list_active", params={})
        assert non_list["count"] == 0

        _api(client).get_maintenance_configs_v2_without_preload_content.return_value = _MockResponse(raw=b"")
        empty = await client.execute_maintenance_operation(operation="list_active", params={})
        assert empty["count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_scheduled(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, self._windows())

        result = await client.execute_maintenance_operation(operation="list_scheduled", params={})
        filtered = await client.execute_maintenance_operation(
            operation="list_scheduled", params={"imap_code": "NOPE"}
        )
        matching = await client.execute_maintenance_operation(
            operation="list_scheduled", params={"imap_code": "ORZ-2"}
        )

        assert result["count"] == 1
        assert result["windows"][0]["state"] == "SCHEDULED"
        assert filtered["count"] == 0
        assert matching["count"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_all_groups_by_state(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, self._windows())

        result = await client.execute_maintenance_operation(operation="list_all", params={})

        assert result["total_count"] == 6
        assert result["active_count"] == 1
        assert result["scheduled_count"] == 1
        assert result["expired_count"] == 2
        assert result["summary"] == "Found 6 total maintenance window(s): 1 active, 1 scheduled, 2 expired"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_all_filtered_and_empty(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, self._windows())

        filtered = await client.execute_maintenance_operation(
            operation="list_all", params={"imap_code": "EAL-1"}
        )
        assert filtered["total_count"] == 2
        assert filtered["application_id"] == "EAL-1"

        self._prime(client, [])
        empty = await client.execute_maintenance_operation(operation="list_all", params={})
        assert empty["summary"] == "Found 0 total maintenance window(s): none"

        self._prime(client, "not-a-list")
        non_list = await client.execute_maintenance_operation(operation="list_all", params={})
        assert non_list["total_count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_expired(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, self._windows())

        result = await client.execute_maintenance_operation(operation="list_expired", params={})
        by_tag = await client.execute_maintenance_operation(
            operation="list_expired", params={"imap_code": "TAGGED-3"}
        )

        assert result["count"] == 2
        assert by_tag["count"] == 1
        assert by_tag["windows"][0]["tagFilterExpression"] == {"value": "TAGGED-3"}

        self._prime(client, "not-a-list")
        non_list = await client.execute_maintenance_operation(operation="list_expired", params={})
        assert non_list["count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "operation,label",
        [
            ("list_active", "list active windows"),
            ("list_scheduled", "list scheduled windows"),
            ("list_all", "list all windows"),
            ("list_expired", "list expired windows"),
        ],
    )
    async def test_list_operations_http_error(self, instana_credentials, operation, label):
        client = create_maintenance_window_client(instana_credentials)
        self._prime(client, {"error": "x"}, status=500)

        result = await client.execute_maintenance_operation(operation=operation, params={})

        assert result["status_code"] == 500
        assert result["operation"] == label

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "operation,label",
        [
            ("list_active", "active"),
            ("list_scheduled", "scheduled"),
            ("list_all", "all"),
            ("list_expired", "expired"),
        ],
    )
    async def test_list_operations_exception(self, instana_credentials, operation, label):
        client = create_maintenance_window_client(instana_credentials)
        _api(client).get_maintenance_configs_v2_without_preload_content.side_effect = Exception("list boom")

        result = await client.execute_maintenance_operation(operation=operation, params={})

        assert f"Failed to list {label} windows: list boom" in result["error"]

    @pytest.mark.mocked
    def test_matches_application_filter_and_state_helpers(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        window = {"query": "entity.tag:imap=ABC", "tagFilterExpression": None}
        assert client._matches_application_filter(window, "ABC") is True
        assert client._matches_application_filter(window, "XYZ") is False
        assert client._matches_application_filter({"tagFilterExpression": {"value": "XYZ"}}, "XYZ") is True

        assert client._is_window_active_by_state({"state": "ACTIVE"}) is True
        assert client._is_window_active_by_time({"occurrence": {"start": 1, "end": 10}}, 5) is True
        assert client._is_window_active_by_time({}, 5) is False
        assert client._should_include_window({"state": "SCHEDULED"}, None, 5) is False
        assert client._is_window_scheduled({"state": "SCHEDULED"}) is True
        assert client._is_window_expired({"state": "EXPIRED"}) is True
        grouped = client._group_windows_by_state([{"state": "active"}, {"state": "unknown"}, {}])
        assert len(grouped["active"]) == 1
        assert grouped["scheduled"] == [] and grouped["expired"] == []


class TestMaintenanceWindowServiceNowE2E:
    """ServiceNow integration helper."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_servicenow_change_not_configured(self, instana_credentials):
        client = create_maintenance_window_client(instana_credentials)

        result = await client._update_servicenow_change("CHG1", "w-1", "scheduled")

        assert result == {"status": "skipped", "reason": "ServiceNow not configured"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_servicenow_change_success(self, instana_credentials):
        client = create_maintenance_window_client(
            instana_credentials, servicenow_token="snow", servicenow_url="https://snow.example.com"
        )

        result = await client._update_servicenow_change("CHG1", "w-1", "scheduled")

        assert result == {
            "status": "success",
            "change_request_id": "CHG1",
            "window_id": "w-1",
            "updated_status": "scheduled",
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_servicenow_change_error(self, instana_credentials):
        client = create_maintenance_window_client(
            instana_credentials, servicenow_token="snow", servicenow_url="https://snow.example.com"
        )

        with patch("src.maintenance_window.maintenance_window_tool.logger.info", side_effect=RuntimeError("log fail")):
            result = await client._update_servicenow_change("CHG1", "w-1", "scheduled")

        assert result == {"status": "error", "error": "log fail"}
