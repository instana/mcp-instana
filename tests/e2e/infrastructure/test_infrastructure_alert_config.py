"""
E2E tests (mocked) for Infrastructure Smart Alert Configuration MCP Tools
"""

import copy
import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


class InfrastructureAlertConfigurationApi(MagicMock):
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


def _make_streaming_response(body: bytes, status=200):
    """Mock urllib3-style response whose .read(n) yields chunks (used by stream_json_array_page)."""
    pos = [0]

    def _read(n=-1):
        if pos[0] >= len(body):
            return b""
        end = len(body) if n < 0 else pos[0] + n
        chunk = body[pos[0]:end]
        pos[0] += len(chunk)
        return chunk

    response = MagicMock()
    response.status = status
    response.headers = {}
    response.read = _read
    response.data = body
    return response


def _skip_unless_real_sdk_model(module_path, attr):
    """Skip when another test module has replaced the SDK model with a mock (mixed test runs)."""
    module = importlib.import_module(module_path)
    if not isinstance(getattr(module, attr, None), type):
        pytest.skip(f"{module_path}.{attr} is mocked in this session")


@pytest.fixture
def real_infra_alert_model():
    _skip_unless_real_sdk_model("instana_client.models.infra_alert_config", "InfraAlertConfig")


def create_infra_alert_client(instana_credentials):
    """Dynamically import and create the Infrastructure Alert Config client with a mocked SDK API."""
    module = importlib.import_module("src.infrastructure.infrastructure_alert_config")
    module = importlib.reload(module)
    client = module.InfrastructureAlertConfigMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )
    client.infrastructure_alert_configuration_api = InfrastructureAlertConfigurationApi()
    return client


def _api(client):
    return client.infrastructure_alert_configuration_api


def _payload(**overrides):
    payload = {
        "name": "High CPU",
        "description": "CPU is high",
        "granularity": 600000,
        "groupBy": [],
        "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
        "timeThreshold": {"type": "violationsInSequence", "timeWindow": 600000},
        "severity": 10,
        "rule": {
            "alertType": "genericRule",
            "metricName": "cpu.used",
            "entityType": "host",
            "aggregation": "MEAN",
            "crossSeriesAggregation": "MEAN",
        },
        "threshold": {"type": "staticThreshold", "operator": ">=", "value": 0.9},
    }
    payload.update(overrides)
    return copy.deepcopy(payload)


def _multi_rule_payload():
    payload = _payload()
    del payload["rule"]
    del payload["threshold"]
    payload["rules"] = [
        {
            "thresholdOperator": ">=",
            "rule": {
                "alertType": "genericRule",
                "metricName": "cpu.used",
                "entityType": "host",
                "aggregation": "MEAN",
                "crossSeriesAggregation": "MEAN",
            },
            "thresholds": {"WARNING": {"type": "staticThreshold", "value": 0.8}},
        },
    ]
    return payload


def _configs_body(count):
    return ("[" + ",".join(f'{{"id": "c{i}"}}' for i in range(count)) + "]").encode()


class TestInfrastructureAlertConfigValidatorsE2E:
    """Static validators and helpers"""

    @pytest.fixture
    def tools(self, instana_credentials):
        module = importlib.reload(importlib.import_module("src.infrastructure.infrastructure_alert_config"))
        return module.InfrastructureAlertConfigMCPTools

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({}, "name: required"),
            ({"name": 5}, "name: must be a string"),
            ({"name": "x" * 257}, "exceeds maximum length"),
            ({"name": "ok"}, None),
        ],
    )
    def test_validate_name(self, tools, payload, expected):
        result = tools._validate_name(payload)
        if expected is None:
            assert result is None
        else:
            assert expected in result

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({}, "description: required"),
            ({"description": 1}, "description: must be a string"),
            ({"description": "d"}, None),
        ],
    )
    def test_validate_description(self, tools, payload, expected):
        result = tools._validate_description(payload)
        if expected is None:
            assert result is None
        else:
            assert expected in result

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({}, "granularity: required"),
            ({"granularity": "600000"}, "must be an integer"),
            ({"granularity": 1234}, "is not valid"),
            ({"granularity": 60000}, None),
        ],
    )
    def test_validate_granularity(self, tools, payload, expected):
        result = tools._validate_granularity(payload)
        if expected is None:
            assert result is None
        else:
            assert expected in result

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "payload,expected",
        [
            ({}, "groupBy: required"),
            ({"groupBy": "host"}, "must be a list"),
            ({"groupBy": []}, None),
        ],
    )
    def test_validate_group_by(self, tools, payload, expected):
        result = tools._validate_group_by(payload)
        if expected is None:
            assert result is None
        else:
            assert expected in result

    @pytest.mark.mocked
    @pytest.mark.parametrize("payload", [None, {}])
    def test_validate_alert_payload_missing(self, tools, payload):
        result = tools._validate_alert_payload(payload, "create")
        assert result["elicitation_needed"] is True
        assert "payload is missing" in result["reason"]

    @pytest.mark.mocked
    def test_validate_alert_payload_not_a_dict(self, tools):
        result = tools._validate_alert_payload(["x"], "update")
        assert "payload must be a dict" in result["reason"]
        assert "list" in result["api_error"][0]

    @pytest.mark.mocked
    def test_validate_alert_payload_collects_all_errors(self, tools):
        result = tools._validate_alert_payload(
            {"severity": 7, "evaluationType": "BOGUS", "name": 1}, "create"
        )
        errors = " | ".join(result["api_error"])
        assert "name: must be a string" in errors
        assert "description: required" in errors
        assert "granularity: required" in errors
        assert "groupBy: required" in errors
        assert "tagFilterExpression: required" in errors
        assert "timeThreshold: required" in errors
        assert "severity: 7" in errors
        assert "evaluationType: 'BOGUS'" in errors
        assert "8 validation problem(s)" in result["reason"]

    @pytest.mark.mocked
    def test_validate_alert_payload_valid(self, tools):
        assert tools._validate_alert_payload(_payload(evaluationType="PER_ENTITY"), "create") is None

    @pytest.mark.mocked
    def test_preflight_requires_id(self, tools):
        for op in ("find", "find_versions", "update", "delete", "enable", "disable", "restore"):
            result = tools._preflight(op, None, 1)
            assert result["elicitation_needed"] is True
            assert f"id: required for '{op}'" in result["api_error"][0]

    @pytest.mark.mocked
    def test_preflight_restore_created_checks(self, tools):
        missing = tools._preflight("restore", "id-1", None)
        assert "created: required for 'restore'" in missing["api_error"][0]
        negative = tools._preflight("restore", "id-1", -5)
        assert "must be a positive integer" in negative["api_error"][0]
        non_int = tools._preflight("restore", "id-1", "yesterday")
        assert "must be a positive integer" in non_int["api_error"][0]
        assert tools._preflight("restore", "id-1", 1710658800000) is None

    @pytest.mark.mocked
    def test_preflight_ok_for_other_ops(self, tools):
        assert tools._preflight("find_active", None, None) is None
        assert tools._preflight("create", None, None) is None
        assert tools._preflight("find", "id-1", None) is None

    @pytest.mark.mocked
    def test_parse_payload_variants(self, tools):
        assert tools._parse_payload({"a": 1}) == {"a": 1}
        assert tools._parse_payload(None) is None
        assert tools._parse_payload('{"a": 1}') == {"a": 1}
        assert tools._parse_payload("{'a': 1}") == {"a": 1}
        with pytest.raises(ValueError, match="payload could not be parsed"):
            tools._parse_payload("{definitely not parseable")

    @pytest.mark.mocked
    def test_normalize_metric_group_by(self, instana_credentials):
        module = importlib.reload(importlib.import_module("src.infrastructure.infrastructure_alert_config"))
        payload = {
            "rule": {"metricName": "m"},
            "rules": [{"rule": {"metricName": "n"}}, {"rule": {"metricGroupBy": ["x"]}}, "skip", {"rule": "bad"}],
        }
        module._normalize_metric_group_by(payload)
        assert payload["rule"]["metricGroupBy"] == []
        assert payload["rules"][0]["rule"]["metricGroupBy"] == []
        assert payload["rules"][1]["rule"]["metricGroupBy"] == ["x"]

        untouched = {"rule": "not-a-dict", "rules": "not-a-list"}
        module._normalize_metric_group_by(untouched)
        assert untouched == {"rule": "not-a-dict", "rules": "not-a-list"}


class TestInfrastructureAlertConfigDispatcherE2E:
    """execute_alert_config_operation routing + validation"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_preflight_short_circuits(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(operation="delete")

        assert result["elicitation_needed"] is True
        assert "id: required for 'delete'" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["create", "update"])
    async def test_unparseable_payload(self, instana_credentials, operation):
        client = create_infra_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(
            operation=operation, id="id-1", payload="{nope"
        )

        assert result["elicitation_needed"] is True
        assert "payload could not be parsed" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["create", "update"])
    async def test_invalid_payload_returns_elicitation(self, instana_credentials, operation):
        client = create_infra_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(
            operation=operation, id="id-1", payload={"name": "only-name"}
        )

        assert result["elicitation_needed"] is True
        assert f"'{operation}' payload has" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unsupported_operation(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(operation="explode")

        assert result == {"error": "Operation 'explode' not supported"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatcher_catches_unexpected_exception(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)

        async def boom(*_args, **_kwargs):
            raise RuntimeError("kaboom")

        client._find = boom

        result = await client.execute_alert_config_operation(operation="find", id="id-1")

        assert result == {"error": "Error executing 'find': kaboom"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatch_forwards_resource_type_and_tool_name(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        client._delete = AsyncMock(return_value={"success": True})

        result = await client.execute_alert_config_operation(
            operation="delete", id="id-1", resource_type="alert_config", tool_name="manage_infrastructure"
        )

        assert result == {"success": True}
        client._delete.assert_awaited_once_with(
            "id-1", None, resource_type="alert_config", tool_name="manage_infrastructure"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_string_payload_is_parsed_before_create(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).create_infra_alert_config_without_preload_content.return_value = _MockResponse({"id": "new"})

        result = await client.execute_alert_config_operation(
            operation="create", payload=json.dumps(_payload())
        )

        assert result == {"id": "new"}


class TestInfrastructureAlertConfigFindActiveE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_default_pagination(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        api = _api(client)
        api.find_active_infra_alert_configs_without_preload_content.return_value = _make_streaming_response(
            _configs_body(60)
        )

        result = await client.execute_alert_config_operation(operation="find_active", alert_ids=["c1"])

        assert result["count"] == 50
        assert result["total"] == 60
        assert result["page"] == 1
        assert result["page_size"] == 50
        assert result["total_pages"] == 2
        assert result["has_next"] is True
        assert result["has_previous"] is False
        assert "Showing page 1 of 2" in result["message"]
        api.find_active_infra_alert_configs_without_preload_content.assert_called_once_with(alert_ids=["c1"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_second_page(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_active_infra_alert_configs_without_preload_content.return_value = (
            _make_streaming_response(_configs_body(25))
        )

        result = await client.execute_alert_config_operation(
            operation="find_active", page=2, page_size=10
        )

        assert [c["id"] for c in result["configs"]] == [f"c{i}" for i in range(10, 20)]
        assert result["has_next"] is True
        assert result["has_previous"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_clamps_out_of_range_pagination(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_active_infra_alert_configs_without_preload_content.return_value = (
            _make_streaming_response(_configs_body(3))
        )

        result = await client.execute_alert_config_operation(
            operation="find_active", page=-4, page_size=99999
        )

        assert result["page"] == 1
        assert result["page_size"] == 1000
        assert result["count"] == 3

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_clamps_zero_page_size(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_active_infra_alert_configs_without_preload_content.return_value = (
            _make_streaming_response(_configs_body(3))
        )

        result = await client.execute_alert_config_operation(operation="find_active", page_size=0)

        assert result["page_size"] == 1
        assert result["count"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_array(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_active_infra_alert_configs_without_preload_content.return_value = (
            _make_streaming_response(b"[]")
        )

        result = await client.execute_alert_config_operation(operation="find_active")

        assert result["configs"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 0
        assert result["message"] == "No active Infra Smart Alert configurations found."

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_http_error(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_active_infra_alert_configs_without_preload_content.return_value = _MockResponse(
            raw=b"nope", status=401
        )

        result = await client.execute_alert_config_operation(operation="find_active")

        assert result["status_code"] == 401
        assert "find_active_infra_alert_configs" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_sdk_exception(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_active_infra_alert_configs_without_preload_content.side_effect = RuntimeError("down")

        result = await client.execute_alert_config_operation(operation="find_active")

        assert "Failed to list active infra alert configs" in result["error"]


class TestInfrastructureAlertConfigReadE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_with_to_dict(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        model = MagicMock()
        model.to_dict.return_value = {"id": "id-1"}
        _api(client).find_infra_alert_config.return_value = model

        result = await client.execute_alert_config_operation(operation="find", id="id-1", valid_on=123)

        assert result == {"id": "id-1"}
        _api(client).find_infra_alert_config.assert_called_once_with(id="id-1", valid_on=123)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_dict_and_other(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_infra_alert_config.return_value = {"id": "id-1"}
        assert await client.execute_alert_config_operation(operation="find", id="id-1") == {"id": "id-1"}

        _api(client).find_infra_alert_config.return_value = "raw"
        assert await client.execute_alert_config_operation(operation="find", id="id-1") == {"data": "raw"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_exception(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_infra_alert_config.side_effect = RuntimeError("404")

        result = await client.execute_alert_config_operation(operation="find", id="id-1")

        assert "Failed to find infra alert config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_list(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        item = MagicMock()
        item.to_dict.return_value = {"created": 1}
        _api(client).find_infra_alert_config_versions.return_value = [item, {"created": 2}]

        result = await client.execute_alert_config_operation(operation="find_versions", id="id-1")

        assert result == {"versions": [{"created": 1}, {"created": 2}]}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_other_shapes(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        model = MagicMock()
        model.to_dict.return_value = {"x": 1}
        _api(client).find_infra_alert_config_versions.return_value = model
        assert await client.execute_alert_config_operation(operation="find_versions", id="i") == {"x": 1}

        _api(client).find_infra_alert_config_versions.return_value = {"y": 2}
        assert await client.execute_alert_config_operation(operation="find_versions", id="i") == {"y": 2}

        _api(client).find_infra_alert_config_versions.return_value = 42
        assert await client.execute_alert_config_operation(operation="find_versions", id="i") == {"data": 42}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_exception(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).find_infra_alert_config_versions.side_effect = RuntimeError("bad")

        result = await client.execute_alert_config_operation(operation="find_versions", id="i")

        assert "Failed to find infra alert config versions" in result["error"]


class TestInfrastructureAlertConfigWriteE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("status", [200, 201])
    async def test_create_success(self, instana_credentials, real_infra_alert_model, status):
        client = create_infra_alert_client(instana_credentials)
        _api(client).create_infra_alert_config_without_preload_content.return_value = _MockResponse(
            {"id": "new-1"}, status=status
        )

        result = await client.execute_alert_config_operation(operation="create", payload=_payload())

        assert result == {"id": "new-1"}
        kwargs = _api(client).create_infra_alert_config_without_preload_content.call_args.kwargs
        assert kwargs["infra_alert_config"] is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_multi_rule_with_defaults_applied(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).create_infra_alert_config_without_preload_content.return_value = _MockResponse({"id": "m"})

        result = await client.execute_alert_config_operation(
            operation="create", payload=_multi_rule_payload()
        )

        assert result == {"id": "m"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_model_build_error(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        # Passes pre-flight but the SDK model rejects the unknown rule type
        payload = _payload(rule={"alertType": "unknownRuleType"})

        result = await client.execute_alert_config_operation(operation="create", payload=payload)

        assert "Failed to build InfraAlertConfig model" in result["error"]
        _api(client).create_infra_alert_config_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_http_error(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).create_infra_alert_config_without_preload_content.return_value = _MockResponse(
            raw=b"bad request", status=400
        )

        result = await client.execute_alert_config_operation(operation="create", payload=_payload())

        assert result["status_code"] == 400
        assert "create_infra_alert_config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_sdk_exception(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).create_infra_alert_config_without_preload_content.side_effect = RuntimeError("down")

        result = await client.execute_alert_config_operation(operation="create", payload=_payload())

        assert "Failed to create infra alert config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_success_with_body(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).update_infra_alert_config_without_preload_content.return_value = _MockResponse({"id": "id-1"})

        result = await client.execute_alert_config_operation(
            operation="update", id="id-1", payload=_payload()
        )

        assert result == {"id": "id-1"}
        assert _api(client).update_infra_alert_config_without_preload_content.call_args.kwargs["id"] == "id-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_success_empty_body(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).update_infra_alert_config_without_preload_content.return_value = _MockResponse(
            raw=b"  ", status=204
        )

        result = await client.execute_alert_config_operation(
            operation="update", id="id-1", payload=_multi_rule_payload()
        )

        assert result["success"] is True
        assert "id-1" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_model_build_error(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(
            operation="update", id="id-1", payload=_payload(rule={"alertType": "unknownRuleType"})
        )

        assert "Failed to build InfraAlertConfig model" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_http_error(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).update_infra_alert_config_without_preload_content.return_value = _MockResponse(
            raw=b"conflict", status=409
        )

        result = await client.execute_alert_config_operation(
            operation="update", id="id-1", payload=_payload()
        )

        assert result["status_code"] == 409

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_sdk_exception(self, instana_credentials, real_infra_alert_model):
        client = create_infra_alert_client(instana_credentials)
        _api(client).update_infra_alert_config_without_preload_content.side_effect = RuntimeError("x")

        result = await client.execute_alert_config_operation(
            operation="update", id="id-1", payload=_payload()
        )

        assert "Failed to update infra alert config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("response", [None, _MockResponse(raw=b"", status=200), _MockResponse(raw=b"", status=204)])
    async def test_delete_success(self, instana_credentials, response):
        client = create_infra_alert_client(instana_credentials)
        _api(client).delete_infra_alert_config.return_value = response

        result = await client.execute_alert_config_operation(operation="delete", id="id-1")

        assert result["success"] is True
        assert "'id-1' deleted successfully" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_http_error(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).delete_infra_alert_config.return_value = _MockResponse(raw=b"missing", status=404)

        result = await client.execute_alert_config_operation(operation="delete", id="id-1")

        assert result["status_code"] == 404

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_exception(self, instana_credentials):
        client = create_infra_alert_client(instana_credentials)
        _api(client).delete_infra_alert_config.side_effect = RuntimeError("x")

        result = await client.execute_alert_config_operation(operation="delete", id="id-1")

        assert "Failed to delete infra alert config" in result["error"]


class TestInfrastructureAlertConfigStateOpsE2E:
    """enable / disable / restore share the same result handling"""

    CASES = [
        ("enable", "enable_infra_alert_config", {}, "enabled."),
        ("disable", "disable_infra_alert_config", {}, "disabled."),
        ("restore", "restore_infra_alert_config", {"created": 1710658800000}, "restored successfully."),
    ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,sdk_method,extra,message_tail", CASES)
    async def test_to_dict_result(self, instana_credentials, operation, sdk_method, extra, message_tail):
        client = create_infra_alert_client(instana_credentials)
        model = MagicMock()
        model.to_dict.return_value = {"id": "id-1", "enabled": True}
        getattr(_api(client), sdk_method).return_value = model

        result = await client.execute_alert_config_operation(operation=operation, id="id-1", **extra)

        assert result == {"id": "id-1", "enabled": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,sdk_method,extra,message_tail", CASES)
    async def test_dict_result(self, instana_credentials, operation, sdk_method, extra, message_tail):
        client = create_infra_alert_client(instana_credentials)
        getattr(_api(client), sdk_method).return_value = {"ok": True}

        result = await client.execute_alert_config_operation(operation=operation, id="id-1", **extra)

        assert result == {"ok": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,sdk_method,extra,message_tail", CASES)
    async def test_empty_result_gives_success_message(
        self, instana_credentials, operation, sdk_method, extra, message_tail
    ):
        client = create_infra_alert_client(instana_credentials)
        getattr(_api(client), sdk_method).return_value = None

        result = await client.execute_alert_config_operation(operation=operation, id="id-1", **extra)

        assert result["success"] is True
        assert "'id-1'" in result["message"]
        assert result["message"].endswith(message_tail)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,sdk_method,extra,message_tail", CASES)
    async def test_exception(self, instana_credentials, operation, sdk_method, extra, message_tail):
        client = create_infra_alert_client(instana_credentials)
        getattr(_api(client), sdk_method).side_effect = RuntimeError("boom")

        result = await client.execute_alert_config_operation(operation=operation, id="id-1", **extra)

        assert f"Failed to {operation} infra alert config" in result["error"]
        assert "boom" in result["error"]
