"""
E2E tests for Application Global Alert Configuration MCP Tools
"""

import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def create_global_alert_client(instana_credentials):
    """Dynamically import and create Application Global Alert client"""
    module = importlib.import_module("src.application.application_global_alert_config")
    module = importlib.reload(module)
    return module.ApplicationGlobalAlertMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _StreamResponse:
    """Minimal streaming HTTP response: ``read(n)`` returns successive byte chunks."""

    def __init__(self, payload, chunk=64):
        self._buf = json.dumps(payload).encode("utf-8")
        self._pos = 0
        self._chunk = chunk
        self.status = 200
        self.headers = {"Content-Type": "application/json"}

    def read(self, n=None):
        size = min(n or self._chunk, self._chunk)
        piece = self._buf[self._pos:self._pos + size]
        self._pos += size
        return piece


def _valid_payload(**overrides):
    payload = {
        "name": "Slow calls",
        "description": "Calls are slow",
        "boundaryScope": "INBOUND",
        "applications": {"app-1": {"applicationId": "app-1", "inclusive": True}},
        "severity": 5,
        "triggering": False,
        "tagFilterExpression": {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
        "includeInternal": False,
        "includeSynthetic": False,
        "rule": {"alertType": "slowness", "aggregation": "P90", "metricName": "latency"},
        "threshold": {"type": "staticThreshold", "operator": ">=", "value": 2, "lastUpdated": 0},
        "granularity": 600000,
        "timeThreshold": {"type": "violationsInSequence", "timeWindow": 600000},
        "evaluationType": "PER_AP",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def real_global_alert_sdk_model():
    """Skip when another test module has replaced the SDK model with a mock (mixed test runs)."""
    module = importlib.import_module("instana_client.models.global_applications_alert_config")
    if not isinstance(getattr(module, "GlobalApplicationsAlertConfig", None), type):
        pytest.skip("GlobalApplicationsAlertConfig is mocked in this session")


class TestApplicationGlobalAlertInitE2E:
    @pytest.mark.mocked
    def test_initialization(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]


class TestApplicationGlobalAlertValidationE2E:
    """Static validators and parsers"""

    @pytest.mark.mocked
    def test_validate_payload_missing(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        for empty in (None, {}):
            result = client._validate_alert_payload(empty, "create")
            assert result["elicitation_needed"] is True
            assert "payload is missing" in result["reason"]

    @pytest.mark.mocked
    def test_validate_payload_not_a_dict(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = client._validate_alert_payload(["x"], "update", "my_label")

        assert "must be a dict" in result["reason"]
        assert result["reason"].startswith("my_label 'update'")
        assert "'list'" in result["api_error"][0]

    @pytest.mark.mocked
    def test_validate_payload_all_fields_missing(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = client._validate_alert_payload({"x": 1}, "create")

        fields = [e.split(":")[0] for e in result["api_error"]]
        assert fields == [
            "name",
            "description",
            "boundaryScope",
            "evaluationType",
            "granularity",
            "applications",
            "tagFilterExpression",
            "timeThreshold",
        ]
        assert "8 validation problem(s)" in result["reason"]

    @pytest.mark.mocked
    def test_validate_payload_invalid_values(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = client._validate_alert_payload(
            _valid_payload(
                name=5,
                description="d" * 65537,
                boundaryScope="BAD",
                evaluationType="BAD",
                granularity="x",
                applications=[],
                severity=7,
            ),
            "create",
        )

        errors = result["api_error"]
        assert any("name: must be a string" in e for e in errors)
        assert any("description: exceeds maximum length of 65536" in e for e in errors)
        assert any("boundaryScope: 'BAD'" in e for e in errors)
        assert any("evaluationType: 'BAD'" in e for e in errors)
        assert any("granularity: must be an integer" in e for e in errors)
        assert any("applications: must be a dict" in e for e in errors)
        assert any("severity: 7 is not valid" in e for e in errors)

    @pytest.mark.mocked
    def test_validate_payload_invalid_granularity_value_and_long_name(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = client._validate_alert_payload(
            _valid_payload(name="n" * 257, granularity=123), "create"
        )

        assert any("name: exceeds maximum length of 256" in e for e in result["api_error"])
        assert any("granularity: 123 is not valid" in e for e in result["api_error"])

    @pytest.mark.mocked
    def test_validate_payload_valid(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        assert client._validate_alert_payload(_valid_payload(), "create") is None

    @pytest.mark.mocked
    def test_preflight_find_active_requires_application_id(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = client._preflight_global_alert_config("find_active", None, None, None)

        assert result["elicitation_needed"] is True
        assert result["api_error"][0].startswith("application_id:")

    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "operation", ["find", "find_versions", "update", "delete", "enable", "disable", "restore"]
    )
    def test_preflight_requires_id(self, instana_credentials, operation):
        client = create_global_alert_client(instana_credentials)

        result = client._preflight_global_alert_config(operation, None, None, 1700000000000)

        assert result["api_error"][0].startswith("id:")

    @pytest.mark.mocked
    def test_preflight_restore_created_validation(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        missing = client._preflight_global_alert_config("restore", None, "id-1", None)
        assert missing["api_error"][0].startswith("created: required")

        negative = client._preflight_global_alert_config("restore", None, "id-1", -5)
        assert "positive integer" in negative["api_error"][0]

        not_int = client._preflight_global_alert_config("restore", None, "id-1", "abc")
        assert "positive integer" in not_int["api_error"][0]

        both = client._preflight_global_alert_config("restore", None, None, None)
        assert len(both["api_error"]) == 2

        assert client._preflight_global_alert_config("restore", None, "id-1", 1700000000000) is None

    @pytest.mark.mocked
    def test_preflight_valid_cases(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        assert client._preflight_global_alert_config("find_active", "app-1", None, None) is None
        assert client._preflight_global_alert_config("create", None, None, None) is None

    @pytest.mark.mocked
    def test_parse_payload(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        assert client._parse_payload(None) is None
        assert client._parse_payload({"a": 1}) == {"a": 1}
        assert client._parse_payload('{"a": 1}') == {"a": 1}
        assert client._parse_payload("{'a': 1}") == {"a": 1}
        assert client._parse_payload("{{bad") is None


class TestApplicationGlobalAlertDispatcherE2E:
    """execute_alert_config_operation and _dispatch_global_alert_config"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_preflight_failure_short_circuits(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        client._dispatch_global_alert_config = AsyncMock()

        result = await client.execute_alert_config_operation(operation="delete")

        assert result["elicitation_needed"] is True
        client._dispatch_global_alert_config.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["create", "update"])
    async def test_payload_validation_failure_short_circuits(self, instana_credentials, operation):
        client = create_global_alert_client(instana_credentials)
        client._dispatch_global_alert_config = AsyncMock()

        result = await client.execute_alert_config_operation(
            operation=operation, id="cfg-1", payload="{'name': 'only-name'}"
        )

        assert result["elicitation_needed"] is True
        assert any("description" in e for e in result["api_error"])
        client._dispatch_global_alert_config.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unparseable_payload_is_reported_missing(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(operation="create", payload="{{bad")

        assert result["elicitation_needed"] is True
        assert "payload is missing" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unsupported_operation(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = await client.execute_alert_config_operation(operation="explode")

        assert result == {"error": "Operation 'explode' not supported"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatch_exception_is_wrapped(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        client._dispatch_global_alert_config = AsyncMock(side_effect=Exception("kaboom"))

        result = await client.execute_alert_config_operation(operation="find", id="cfg-1")

        assert result == {"error": "Error executing find: kaboom"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("operation", "handler", "kwargs"),
        [
            ("find_active", "_find_active_configs", {"application_id": "app-1", "alert_ids": ["a"], "page": 2, "page_size": 5}),
            ("find_versions", "_find_config_versions", {"id": "cfg-1"}),
            ("find", "_find_config", {"id": "cfg-1", "valid_on": 1700000000000}),
            ("create", "_create_config", {"payload": _valid_payload()}),
            ("update", "_update_config", {"id": "cfg-1", "payload": _valid_payload()}),
            ("delete", "_delete_config", {"id": "cfg-1"}),
            ("enable", "_enable_config", {"id": "cfg-1"}),
            ("disable", "_disable_config", {"id": "cfg-1"}),
            ("restore", "_restore_config", {"id": "cfg-1", "created": 1700000000000}),
        ],
    )
    async def test_dispatch_routes_each_operation(self, instana_credentials, operation, handler, kwargs):
        client = create_global_alert_client(instana_credentials)
        mock_handler = AsyncMock(return_value={"routed": handler})
        setattr(client, handler, mock_handler)

        result = await client.execute_alert_config_operation(
            operation=operation, resource_type="global_alert_config", tool_name="manage_applications", **kwargs
        )

        assert result == {"routed": handler}
        mock_handler.assert_awaited_once()
        call_kwargs = mock_handler.await_args.kwargs
        assert call_kwargs["resource_type"] == "global_alert_config"
        assert call_kwargs["tool_name"] == "manage_applications"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatch_forwards_paging_only_when_set(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        handler = AsyncMock(return_value={})
        client._find_active_configs = handler

        await client.execute_alert_config_operation(operation="find_active", application_id="app-1")
        assert "page" not in handler.await_args.kwargs
        assert "page_size" not in handler.await_args.kwargs

        await client.execute_alert_config_operation(
            operation="find_active", application_id="app-1", page=3, page_size=7
        )
        assert handler.await_args.kwargs["page"] == 3
        assert handler.await_args.kwargs["page_size"] == 7


class TestApplicationGlobalAlertWrappersE2E:
    """Private _xxx_config wrappers: guards + delegation to the public SDK-facing methods"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_wrapper(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_active_global_application_alert_configs_without_preload_content.return_value = (
            _StreamResponse([{"id": "c1"}])
        )

        result = await client._find_active_configs(
            application_id="app-1", alert_ids=["c1"], page=1, page_size=10, api_client=mock_api
        )

        assert result["configs"] == [{"id": "c1"}]
        call = mock_api.find_active_global_application_alert_configs_without_preload_content.call_args
        assert call.kwargs == {"application_id": "app-1", "alert_ids": ["c1"]}

        assert await client._find_active_configs(
            application_id=None, alert_ids=None, api_client=mock_api
        ) == {"error": "application_id is required for find_active operation"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_wrapper(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_global_application_alert_config_versions.return_value = [{"id": "v1"}]

        result = await client._find_config_versions(id="cfg-1", api_client=mock_api)
        assert result == {"versions": [{"id": "v1"}]}

        assert await client._find_config_versions(id=None, api_client=mock_api) == {
            "error": "id is required for find_versions operation"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_wrapper(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_global_application_alert_config.return_value = {"id": "cfg-1"}

        result = await client._find_config(id="cfg-1", valid_on=123, api_client=mock_api)

        assert result == {"id": "cfg-1"}
        mock_api.find_global_application_alert_config.assert_called_once_with(id="cfg-1", valid_on=123)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_wrapper(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.create_global_application_alert_config.return_value = {"id": "new"}

        assert await client._create_config(payload=_valid_payload(), api_client=mock_api) == {"id": "new"}
        assert await client._create_config(payload=None, api_client=mock_api) == {
            "error": "payload is required for create operation"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_wrapper(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.update_global_application_alert_config.return_value = {"id": "cfg-1"}

        assert await client._update_config(id="cfg-1", payload=_valid_payload(), api_client=mock_api) == {
            "id": "cfg-1"
        }
        assert await client._update_config(id=None, payload=_valid_payload(), api_client=mock_api) == {
            "error": "id is required for update operation"
        }
        assert await client._update_config(id="cfg-1", payload=None, api_client=mock_api) == {
            "error": "payload is required for update operation"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("method", "sdk_method", "missing_message"),
        [
            ("_delete_config", "delete_global_application_alert_config", "id is required for delete operation"),
            ("_enable_config", "enable_global_application_alert_config", "id is required for enable operation"),
            ("_disable_config", "disable_global_application_alert_config", "id is required for disable operation"),
        ],
    )
    async def test_id_only_wrappers(self, instana_credentials, method, sdk_method, missing_message):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        getattr(mock_api, sdk_method).return_value = {"done": True}

        result = await getattr(client, method)(id="cfg-1", api_client=mock_api)
        getattr(mock_api, sdk_method).assert_called_once_with(id="cfg-1")
        assert result  # delete synthesises success, enable/disable passes the result through

        assert await getattr(client, method)(id=None, api_client=mock_api) == {"error": missing_message}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_wrapper(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.restore_global_application_alert_config.return_value = {"id": "cfg-1"}

        result = await client._restore_config(id="cfg-1", created=1700000000000, api_client=mock_api)
        assert result == {"id": "cfg-1"}
        mock_api.restore_global_application_alert_config.assert_called_once_with(
            id="cfg-1", created=1700000000000
        )

        assert await client._restore_config(id=None, created=1, api_client=mock_api) == {
            "error": "id is required for restore operation"
        }
        assert await client._restore_config(id="cfg-1", created=None, api_client=mock_api) == {
            "error": "created timestamp is required for restore operation"
        }


class TestApplicationGlobalAlertFindActiveE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_first_page(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_active_global_application_alert_configs_without_preload_content.return_value = (
            _StreamResponse([{"id": f"c{i}", "name": "x" * 20} for i in range(25)])
        )

        result = await client.find_active_global_application_alert_configs(
            application_id="app-1", api_client=mock_api
        )

        assert result["count"] == 10
        assert result["total"] == 25
        assert result["showing"] == 10
        assert result["pagination"]["page"] == 1
        assert "Found 25 active" in result["message"]
        assert "Showing first 10." in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_later_page(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_active_global_application_alert_configs_without_preload_content.return_value = (
            _StreamResponse([{"id": f"c{i}"} for i in range(25)])
        )

        result = await client.find_active_global_application_alert_configs(
            application_id="app-1", page=3, page_size=10, api_client=mock_api
        )

        assert [c["id"] for c in result["configs"]] == [f"c{i}" for i in range(20, 25)]
        assert "Showing page 3 of 3 (5 item(s))." in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_empty(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_active_global_application_alert_configs_without_preload_content.return_value = (
            _StreamResponse([])
        )

        result = await client.find_active_global_application_alert_configs(
            application_id="app-1", api_client=mock_api
        )

        assert result["configs"] == []
        assert result["total"] == 0
        assert "No active global alert configurations found for application ID: app-1" in result["message"]
        assert "suggestion" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_requires_application_id(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = await client.find_active_global_application_alert_configs(
            application_id="", api_client=MagicMock()
        )

        assert result == {"error": "application_id is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_active_api_error(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.find_active_global_application_alert_configs_without_preload_content.side_effect = Exception(
            "API Error"
        )

        result = await client.find_active_global_application_alert_configs(
            application_id="app-1", api_client=mock_api
        )

        assert "Failed to get active global application alert config" in result["error"]
        assert "API Error" in result["error"]


class TestApplicationGlobalAlertReadWriteE2E:
    """Public SDK-facing methods"""

    # find_versions ------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_variants(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        item = MagicMock()
        item.to_dict.return_value = {"id": "v1"}
        list_api = MagicMock()
        list_api.find_global_application_alert_config_versions.return_value = [item, {"id": "v2"}]
        assert await client.find_global_application_alert_config_versions(id="c", api_client=list_api) == {
            "versions": [{"id": "v1"}, {"id": "v2"}]
        }

        model = MagicMock()
        model.to_dict.return_value = {"id": "single"}
        model_api = MagicMock()
        model_api.find_global_application_alert_config_versions.return_value = model
        assert await client.find_global_application_alert_config_versions(id="c", api_client=model_api) == {
            "id": "single"
        }

        dict_api = MagicMock()
        dict_api.find_global_application_alert_config_versions.return_value = {"raw": 1}
        assert await client.find_global_application_alert_config_versions(id="c", api_client=dict_api) == {
            "raw": 1
        }

        other_api = MagicMock()
        other_api.find_global_application_alert_config_versions.return_value = "text"
        assert await client.find_global_application_alert_config_versions(id="c", api_client=other_api) == {
            "data": "text"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_versions_missing_id_and_error(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        assert await client.find_global_application_alert_config_versions(
            id="", api_client=MagicMock()
        ) == {"error": "id is required"}

        error_api = MagicMock()
        error_api.find_global_application_alert_config_versions.side_effect = Exception("API Error")
        result = await client.find_global_application_alert_config_versions(id="c", api_client=error_api)
        assert "Failed to get global application alert config versions" in result["error"]

    # find ---------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_variants(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        item = MagicMock()
        item.to_dict.return_value = {"id": "c1"}
        list_api = MagicMock()
        list_api.find_global_application_alert_config.return_value = [item, {"id": "c2"}]
        assert await client.find_global_application_alert_config(id="c", api_client=list_api) == {
            "configs": [{"id": "c1"}, {"id": "c2"}]
        }

        model = MagicMock()
        model.to_dict.return_value = {"id": "single"}
        model_api = MagicMock()
        model_api.find_global_application_alert_config.return_value = model
        assert await client.find_global_application_alert_config(id="c", api_client=model_api) == {
            "id": "single"
        }

        dict_api = MagicMock()
        dict_api.find_global_application_alert_config.return_value = {"raw": 1}
        assert await client.find_global_application_alert_config(id="c", api_client=dict_api) == {"raw": 1}

        other_api = MagicMock()
        other_api.find_global_application_alert_config.return_value = 5
        assert await client.find_global_application_alert_config(id="c", api_client=other_api) == {"data": 5}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_find_error(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)
        error_api = MagicMock()
        error_api.find_global_application_alert_config.side_effect = Exception("API Error")

        result = await client.find_global_application_alert_config(id="c", api_client=error_api)

        assert "Failed to get global application alert configs" in result["error"]

    # delete -------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_variants(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        ok_api = MagicMock()
        result = await client.delete_global_application_alert_config(id="c1", api_client=ok_api)
        assert result["success"] is True
        assert "'c1'" in result["message"]
        ok_api.delete_global_application_alert_config.assert_called_once_with(id="c1")

        assert await client.delete_global_application_alert_config(id="", api_client=ok_api) == {
            "error": "id is required"
        }

        error_api = MagicMock()
        error_api.delete_global_application_alert_config.side_effect = Exception("API Error")
        result = await client.delete_global_application_alert_config(id="c1", api_client=error_api)
        assert "Failed to delete global application alert config" in result["error"]

    # enable / disable / restore ----------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("method", "sdk_method", "success_fragment"),
        [
            ("enable_global_application_alert_config", "enable_global_application_alert_config", "successfully enabled"),
            ("disable_global_application_alert_config", "disable_global_application_alert_config", "successfully disabled"),
        ],
    )
    async def test_enable_disable_variants(self, instana_credentials, method, sdk_method, success_fragment):
        client = create_global_alert_client(instana_credentials)
        action = getattr(client, method)

        model = MagicMock()
        model.to_dict.return_value = {"id": "c1", "enabled": True}
        model_api = MagicMock()
        getattr(model_api, sdk_method).return_value = model
        assert await action(id="c1", api_client=model_api) == {"id": "c1", "enabled": True}

        none_api = MagicMock()
        getattr(none_api, sdk_method).return_value = None
        result = await action(id="c1", api_client=none_api)
        assert result["success"] is True
        assert success_fragment in result["message"]

        dict_api = MagicMock()
        getattr(dict_api, sdk_method).return_value = {"raw": 1}
        assert await action(id="c1", api_client=dict_api) == {"raw": 1}

        assert await action(id="", api_client=MagicMock()) == {"error": "id is required"}

        error_api = MagicMock()
        getattr(error_api, sdk_method).side_effect = Exception("API Error")
        result = await action(id="c1", api_client=error_api)
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_restore_variants(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        model = MagicMock()
        model.to_dict.return_value = {"id": "c1"}
        model_api = MagicMock()
        model_api.restore_global_application_alert_config.return_value = model
        assert await client.restore_global_application_alert_config(
            id="c1", created=1700000000000, api_client=model_api
        ) == {"id": "c1"}

        none_api = MagicMock()
        none_api.restore_global_application_alert_config.return_value = None
        result = await client.restore_global_application_alert_config(
            id="c1", created=1700000000000, api_client=none_api
        )
        assert result["success"] is True
        assert "successfully restored" in result["message"]

        dict_api = MagicMock()
        dict_api.restore_global_application_alert_config.return_value = {"raw": 1}
        assert await client.restore_global_application_alert_config(
            id="c1", created=1, api_client=dict_api
        ) == {"raw": 1}

        assert await client.restore_global_application_alert_config(
            id="", created=1, api_client=MagicMock()
        ) == {"error": "id is required"}
        assert await client.restore_global_application_alert_config(
            id="c1", created=0, api_client=MagicMock()
        ) == {"error": "created timestamp is required"}

        error_api = MagicMock()
        error_api.restore_global_application_alert_config.side_effect = Exception("API Error")
        result = await client.restore_global_application_alert_config(
            id="c1", created=1, api_client=error_api
        )
        assert "Failed to restore global application alert config" in result["error"]


class TestApplicationGlobalAlertCreateUpdateE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_success_applies_defaults(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        response = MagicMock()
        response.to_dict.return_value = {"id": "new-1"}
        mock_api.create_global_application_alert_config.return_value = response
        payload = _valid_payload()

        result = await client.create_global_application_alert_config(payload=payload, api_client=mock_api)

        assert result == {"id": "new-1"}
        sent = mock_api.create_global_application_alert_config.call_args.kwargs[
            "global_applications_alert_config"
        ]
        assert sent.name == "Slow calls"
        assert payload["alertChannelIds"] == []
        assert payload["customPayloadFields"] == []
        assert payload["applications"]["app-1"]["services"] == {}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "make_payload",
        [
            lambda p: json.dumps(p),
            lambda p: str(p),
            lambda p: json.dumps(p).replace('"', "'").replace("true", "True").replace("false", "False"),
        ],
        ids=["json", "python-literal", "single-quoted"],
    )
    async def test_create_string_payload_formats(
        self, instana_credentials, real_global_alert_sdk_model, make_payload
    ):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.create_global_application_alert_config.return_value = {"id": "new-2"}

        result = await client.create_global_application_alert_config(
            payload=make_payload(_valid_payload()), api_client=mock_api
        )

        assert result == {"id": "new-2"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_unparseable_string(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        result = await client.create_global_application_alert_config(
            payload="{{definitely not valid", api_client=MagicMock()
        )

        assert "Invalid payload format" in result["error"]
        assert result["payload"] == "{{definitely not valid"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_empty_payload(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        assert await client.create_global_application_alert_config(
            payload={}, api_client=MagicMock()
        ) == {"error": "Payload is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_invalid_model(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)

        result = await client.create_global_application_alert_config(
            payload={"name": "only-name"}, api_client=MagicMock()
        )

        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_api_error(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.create_global_application_alert_config.side_effect = Exception("API Error")

        result = await client.create_global_application_alert_config(
            payload=_valid_payload(), api_client=mock_api
        )

        assert "Failed to create global application alert config" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_plain_dict_result(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)
        mock_api = MagicMock()
        mock_api.create_global_application_alert_config.return_value = {"id": "plain"}

        result = await client.create_global_application_alert_config(
            payload=_valid_payload(), api_client=mock_api
        )

        assert result == {"id": "plain"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_success_variants(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)

        model = MagicMock()
        model.to_dict.return_value = {"id": "c1"}
        model_api = MagicMock()
        model_api.update_global_application_alert_config.return_value = model
        assert await client.update_global_application_alert_config(
            id="c1", payload=_valid_payload(), api_client=model_api
        ) == {"id": "c1"}
        kwargs = model_api.update_global_application_alert_config.call_args.kwargs
        assert kwargs["id"] == "c1"
        assert kwargs["global_applications_alert_config"].name == "Slow calls"

        none_api = MagicMock()
        none_api.update_global_application_alert_config.return_value = None
        result = await client.update_global_application_alert_config(
            id="c1", payload=json.dumps(_valid_payload()), api_client=none_api
        )
        assert result["success"] is True
        assert "successfully updated" in result["message"]

        dict_api = MagicMock()
        dict_api.update_global_application_alert_config.return_value = {"raw": 1}
        assert await client.update_global_application_alert_config(
            id="c1", payload=str(_valid_payload()), api_client=dict_api
        ) == {"raw": 1}

        single_quoted = json.dumps(_valid_payload()).replace('"', "'").replace("true", "True").replace(
            "false", "False"
        )
        assert await client.update_global_application_alert_config(
            id="c1", payload=single_quoted, api_client=dict_api
        ) == {"raw": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_guards(self, instana_credentials):
        client = create_global_alert_client(instana_credentials)

        assert await client.update_global_application_alert_config(
            id="", payload={"a": 1}, api_client=MagicMock()
        ) == {"error": "id is required"}
        assert await client.update_global_application_alert_config(
            id="c1", payload={}, api_client=MagicMock()
        ) == {"error": "payload is required"}

        result = await client.update_global_application_alert_config(
            id="c1", payload="{{definitely not valid", api_client=MagicMock()
        )
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_invalid_model_and_api_error(self, instana_credentials, real_global_alert_sdk_model):
        client = create_global_alert_client(instana_credentials)

        invalid = await client.update_global_application_alert_config(
            id="c1", payload={"name": "only-name"}, api_client=MagicMock()
        )
        assert "Failed to create config object" in invalid["error"]

        error_api = MagicMock()
        error_api.update_global_application_alert_config.side_effect = Exception("API Error")
        result = await client.update_global_application_alert_config(
            id="c1", payload=_valid_payload(), api_client=error_api
        )
        assert "Failed to update global application alert config" in result["error"]
