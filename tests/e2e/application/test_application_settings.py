"""
E2E tests for Application Settings MCP Tools
"""

import importlib
import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _require_real_sdk():
    """Skip when another test module has replaced the SDK with mocks (mixed test runs)."""
    for name in ("instana_client.api", "instana_client.models"):
        if not isinstance(sys.modules.get(name), types.ModuleType):
            pytest.skip(f"{name} is mocked in this session")


def create_application_settings_client(instana_credentials):
    """Dynamically import and create Application Settings client"""
    module = importlib.import_module("src.application.application_settings")
    module = importlib.reload(module)
    return module.ApplicationSettingsMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(body):
    return _MockResponse(json.dumps(body).encode("utf-8"))


def _write_api(response_body):
    """Mock api_client whose low-level add/put serialize+call_api path returns response_body."""
    mock_api = MagicMock()
    rest_response = MagicMock()
    rest_response.status = 200
    rest_response.data = json.dumps(response_body).encode("utf-8")
    mock_api.api_client.call_api.return_value = rest_response
    mock_api._add_application_config_serialize.return_value = ("serialized",)
    mock_api._put_application_config_serialize.return_value = ("serialized",)
    return mock_api, rest_response


_TAG_FILTER = {
    "type": "TAG_FILTER",
    "name": "service.name",
    "operator": "EQUALS",
    "entity": "DESTINATION",
    "value": "svc",
}


class TestApplicationSettingsInitE2E:
    @pytest.mark.mocked
    def test_initialization(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
        assert client.settings_api is not None

    @pytest.mark.mocked
    def test_initialization_error(self, instana_credentials):
        from src.application.application_settings import ApplicationSettingsMCPTools

        with patch(
            "src.application.application_settings.ApplicationSettingsApi",
            side_effect=Exception("Initialization Error"),
        ), pytest.raises(Exception, match="Initialization Error"):
            ApplicationSettingsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"],
            )

    @pytest.mark.mocked
    def test_debug_print(self, capsys):
        from src.application.application_settings import debug_print

        debug_print("hello", "world")
        assert "hello world" in capsys.readouterr().err


class TestApplicationSettingsDispatcherE2E:
    """execute_settings_operation routing and pre-flight validation"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_missing_id_and_payload(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client.execute_settings_operation(operation="update", resource_subtype="application")

        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) == 2
        assert any(e.startswith("id:") for e in result["api_error"])
        assert any(e.startswith("payload:") for e in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation", ["get", "delete"])
    async def test_missing_id_only(self, instana_credentials, operation):
        client = create_application_settings_client(instana_credentials)

        result = await client.execute_settings_operation(operation=operation, resource_subtype="endpoint")

        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_missing_payload(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client.execute_settings_operation(operation="create", resource_subtype="service")

        assert result["elicitation_needed"] is True
        assert result["api_error"][0].startswith("payload:")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("subtype", "operation", "handler", "needs_id", "needs_payload"),
        [
            ("application", "get_all", "_get_all_applications_configs", False, False),
            ("application", "get", "_get_application_config", True, False),
            ("application", "create", "_add_application_config", False, True),
            ("application", "update", "_update_application_config", True, True),
            ("application", "delete", "_delete_application_config", True, False),
            ("endpoint", "get_all", "_get_all_endpoint_configs", False, False),
            ("endpoint", "get", "_get_endpoint_config", True, False),
            ("endpoint", "create", "_create_endpoint_config", False, True),
            ("endpoint", "update", "_update_endpoint_config", True, True),
            ("endpoint", "delete", "_delete_endpoint_config", True, False),
            ("service", "get_all", "_get_all_service_configs", False, False),
            ("service", "get", "_get_service_config", True, False),
            ("service", "create", "_add_service_config", False, True),
            ("service", "update", "_update_service_config", True, True),
            ("service", "delete", "_delete_service_config", True, False),
            ("manual_service", "get_all", "_get_all_manual_service_configs", False, False),
            ("manual_service", "create", "_add_manual_service_config", False, True),
            ("manual_service", "update", "_update_manual_service_config", True, True),
            ("manual_service", "delete", "_delete_manual_service_config", True, False),
        ],
    )
    async def test_routing(
        self, instana_credentials, subtype, operation, handler, needs_id, needs_payload
    ):
        from unittest.mock import AsyncMock

        client = create_application_settings_client(instana_credentials)
        mock_handler = AsyncMock(return_value={"routed": handler})
        setattr(client, handler, mock_handler)

        result = await client.execute_settings_operation(
            operation=operation,
            resource_subtype=subtype,
            id="cfg-1" if needs_id else None,
            payload={"label": "x"} if needs_payload else None,
        )

        assert result == {"routed": handler}
        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("subtype", "operation"),
        [
            ("manual_service", "get"),
            ("unknown", "get_all"),
            ("application", "order"),
        ],
    )
    async def test_unsupported_combination(self, instana_credentials, subtype, operation):
        client = create_application_settings_client(instana_credentials)

        result = await client.execute_settings_operation(
            operation=operation, resource_subtype=subtype, id="x", payload={"a": 1}
        )

        assert "not supported" in result["error"]
        assert operation in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatcher_exception(self, instana_credentials):
        from unittest.mock import AsyncMock

        client = create_application_settings_client(instana_credentials)
        client._get_all_applications_configs = AsyncMock(side_effect=Exception("kaboom"))

        result = await client.execute_settings_operation(operation="get_all", resource_subtype="application")

        assert result["error"] == "Error executing get_all on application: kaboom"


class TestApplicationSettingsApplicationE2E:
    """Application perspective CRUD"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_success_list(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_configs_without_preload_content.return_value = _json_response(
            [{"id": "a1", "label": "App 1"}, "not-a-dict"]
        )
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_applications_configs(api_client=mock_api)

        assert result[0]["id"] == "a1"
        assert "link" in result[0]
        assert result[1] == "not-a-dict"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_single_object_is_wrapped(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_configs_without_preload_content.return_value = _json_response(
            {"id": "a1", "label": "App 1"}
        )
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_applications_configs(api_client=mock_api)

        assert len(result) == 1
        assert result[0]["id"] == "a1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_empty_object(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_configs_without_preload_content.return_value = _json_response({})
        client = create_application_settings_client(instana_credentials)

        assert await client._get_all_applications_configs(api_client=mock_api) == []

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_invalid_json(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_configs_without_preload_content.return_value = _MockResponse(b"not-json")
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_applications_configs(api_client=mock_api)

        assert "Failed to parse JSON response" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_configs_without_preload_content.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_applications_configs(api_client=mock_api)

        assert "Failed to get all applications" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_config_without_preload_content.return_value = _json_response(
            {"id": "a1", "label": "App 1"}
        )
        client = create_application_settings_client(instana_credentials)

        result = await client._get_application_config(id="a1", api_client=mock_api)

        assert result["id"] == "a1"
        assert "link" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_non_dict_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_config_without_preload_content.return_value = _json_response([1])
        client = create_application_settings_client(instana_credentials)

        assert await client._get_application_config(id="a1", api_client=mock_api) == [1]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_requires_id(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client._get_application_config(id="", api_client=MagicMock())

        assert result == {"error": "id is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_config_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_config_without_preload_content.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._get_application_config(id="a1", api_client=mock_api)

        assert "Failed to get application config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_minimal_applies_defaults(self, instana_credentials):
        mock_api, _ = _write_api({"id": "new-1", "label": "My App"})
        client = create_application_settings_client(instana_credentials)

        result = await client._add_application_config(payload={"label": "My App"}, api_client=mock_api)

        assert result["id"] == "new-1"
        assert result["message"] == "Application perspective 'My App' created successfully"
        assert result["applied_defaults"] == {
            "scope": "INCLUDE_ALL_DOWNSTREAM",
            "boundaryScope": "ALL",
            "accessRules": "READ_WRITE GLOBAL",
        }
        sent = mock_api._add_application_config_serialize.call_args.kwargs["new_application_config"]
        assert sent["label"] == "My App"
        assert sent["scope"] == "INCLUDE_ALL_DOWNSTREAM"
        assert sent["tagFilterExpression"]["type"] == "EXPRESSION"
        assert sent["accessRules"][0]["relationType"] == "GLOBAL"
        mock_api.api_client.call_api.assert_called_once_with("serialized")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_full_payload_json_string(self, instana_credentials):
        mock_api, _ = _write_api({"id": "new-2"})
        client = create_application_settings_client(instana_credentials)
        payload = {
            "label": "Full App",
            "scope": "INCLUDE_NO_DOWNSTREAM",
            "boundaryScope": "INBOUND",
            "accessRules": [{"accessType": "READ", "relationType": "GLOBAL"}],
            "businessCriticality": "NOT_DEFINED",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [
                    _TAG_FILTER,
                    {**_TAG_FILTER, "value": None, "stringValue": "svc2", "key": "k"},
                ],
            },
        }

        result = await client._add_application_config(payload=json.dumps(payload), api_client=mock_api)

        assert result["applied_defaults"]["accessRules"] == "Custom"  # string payload parsed up front
        assert result["applied_defaults"]["scope"] == "INCLUDE_NO_DOWNSTREAM"
        sent = mock_api._add_application_config_serialize.call_args.kwargs["new_application_config"]
        assert "businessCriticality" not in sent
        assert sent["boundaryScope"] == "INBOUND"
        assert sent["tagFilterExpression"]["type"] == "EXPRESSION"
        assert len(sent["tagFilterExpression"]["elements"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_custom_access_rules_reported(self, instana_credentials):
        mock_api, _ = _write_api({"id": "new-3"})
        client = create_application_settings_client(instana_credentials)

        result = await client._add_application_config(
            payload={
                "label": "App",
                "accessRules": [{"accessType": "READ", "relationType": "GLOBAL"}],
                "matchSpecification": {"dummy": True},
            },
            api_client=mock_api,
        )

        assert result["applied_defaults"]["accessRules"] == "Custom"
        sent = mock_api._add_application_config_serialize.call_args.kwargs["new_application_config"]
        assert "tagFilterExpression" not in sent

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("payload", "expected_fragment"),
        [
            ({"scope": "INCLUDE_NO_DOWNSTREAM"}, "'label'"),
            ({"label": "x", "scope": "BAD"}, "'scope' value 'BAD'"),
            ({"label": "x", "boundaryScope": "BAD"}, "'boundaryScope' value 'BAD'"),
            ({"label": "x", "accessRules": "nope"}, "'accessRules' must be a list"),
        ],
    )
    async def test_add_application_config_validation_errors(
        self, instana_credentials, payload, expected_fragment
    ):
        mock_api, _ = _write_api({})
        client = create_application_settings_client(instana_credentials)

        result = await client._add_application_config(payload=payload, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert any(expected_fragment in e for e in result["api_error"])
        mock_api.api_client.call_api.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_non_dict_payload(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client._add_application_config(payload="not json at all", api_client=MagicMock())

        assert result["elicitation_needed"] is True
        assert "payload" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_invalid_tag_filter(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client._add_application_config(
            payload={
                "label": "x",
                "tagFilterExpression": {
                    "type": "TAG_FILTER",
                    "name": "a",
                    "operator": "BAD_OPERATOR",
                    "entity": "DESTINATION",
                },
            },
            api_client=MagicMock(),
        )

        assert "Invalid tagFilterExpression structure" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_config_api_error(self, instana_credentials):
        mock_api, _ = _write_api({})
        mock_api.api_client.call_api.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._add_application_config(payload={"label": "x"}, api_client=mock_api)

        assert "Failed to add application config" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_success_injects_id(self, instana_credentials):
        mock_api, _ = _write_api({"id": "a1", "label": "Renamed"})
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="a1",
            payload={
                "label": "Renamed",
                "link": "[x](y)",
                "url": "https://u",
                "businessCriticality": 2,
                "accessRules": [{"accessType": "READ", "relationType": "GLOBAL"}],
                "tagFilterExpression": _TAG_FILTER,
            },
            api_client=mock_api,
        )

        assert result == {"id": "a1", "label": "Renamed"}
        kwargs = mock_api._put_application_config_serialize.call_args.kwargs
        assert kwargs["id"] == "a1"
        body = kwargs["application_config"]
        assert body["id"] == "a1"
        assert "link" not in body
        assert "url" not in body
        assert body["businessCriticality"] == 2
        assert body["tagFilterExpression"]["name"] == "service.name"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_empty_response_returns_success(self, instana_credentials):
        mock_api, rest_response = _write_api({})
        rest_response.data = b""
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="a1", payload=json.dumps({"label": "x", "id": "a1"}), api_client=mock_api
        )

        assert result == {"success": True, "message": "Application config 'a1' updated"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_python_literal_string(self, instana_credentials):
        mock_api, _ = _write_api({"id": "a1"})
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="a1", payload="{'label': 'x'}", api_client=mock_api
        )

        assert result == {"id": "a1"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_invalid_string_payload(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="a1", payload="{{definitely not valid", api_client=MagicMock()
        )

        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_validation_error(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="a1", payload={"label": " "}, api_client=MagicMock()
        )

        assert result["elicitation_needed"] is True
        assert "label" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_missing_id(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="  ", payload={"label": "x"}, api_client=MagicMock()
        )

        assert result["elicitation_needed"] is True
        assert "'id' is required" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_application_config_api_error(self, instana_credentials):
        mock_api, _ = _write_api({})
        mock_api.api_client.call_api.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._update_application_config(
            id="a1", payload={"label": "x"}, api_client=mock_api
        )

        assert "Failed to update application config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_config(self, instana_credentials):
        mock_api = MagicMock()
        client = create_application_settings_client(instana_credentials)

        result = await client._delete_application_config(id="a1", api_client=mock_api)

        assert result == {"success": True, "message": "Application config 'a1' deleted successfully"}
        mock_api.delete_application_config.assert_called_once_with(id="a1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_config_requires_id(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        assert await client._delete_application_config(id="", api_client=MagicMock()) == {
            "error": "id is required"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_application_config_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_application_config.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._delete_application_config(id="a1", api_client=mock_api)

        assert "Failed to delete application config" in result["error"]


class TestApplicationSettingsHelpersE2E:
    @pytest.mark.mocked
    def test_convert_tag_filter_expression_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        assert client._convert_tag_filter_expression("raw") == "raw"
        unknown = {"type": "OTHER"}
        assert client._convert_tag_filter_expression(unknown) is unknown

        by_string_value = client._convert_tag_filter_expression(
            {**{k: v for k, v in _TAG_FILTER.items() if k != "value"}, "stringValue": "abc"}
        )
        assert by_string_value.string_value == "abc"
        assert by_string_value.value.actual_instance == "abc"

        by_value = client._convert_tag_filter_expression(_TAG_FILTER)
        assert by_value.string_value == "svc"

        expression = client._convert_tag_filter_expression(
            {
                "type": "EXPRESSION",
                "logicalOperator": "OR",
                "elements": [_TAG_FILTER, "ignored-non-dict"],
            }
        )
        assert expression.logical_operator == "OR"
        assert len(expression.elements) == 1

    @pytest.mark.mocked
    def test_parse_payload_string(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        assert client._parse_payload_string({"a": 1}) == {"a": 1}
        assert client._parse_payload_string('{"a": 1}') == {"a": 1}
        assert client._parse_payload_string("{'a': 1}") == {"a": 1}
        assert "Invalid payload format" in client._parse_payload_string("{{bad")["error"]

    @pytest.mark.mocked
    def test_validate_and_prepare_payload_string_paths(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        ok = client._validate_and_prepare_application_payload('{"label": "x"}')
        assert ok["payload"]["label"] == "x"

        assert "error" in client._validate_and_prepare_application_payload("{{bad")
        missing = client._validate_and_prepare_application_payload({"scope": "INCLUDE_NO_DOWNSTREAM"})
        assert missing["missing_fields"] == ["label"]

    @pytest.mark.mocked
    def test_validate_does_not_mutate_input(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)
        payload = {"label": "x"}

        client._validate_and_prepare_application_payload(payload)

        assert payload == {"label": "x"}

    @pytest.mark.mocked
    def test_build_serializable_body_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)
        model = MagicMock()
        model.to_dict.return_value = {"m": 1}
        item = MagicMock()
        item.to_dict.return_value = {"i": 1}

        body = client._build_serializable_body(
            {
                "url": "u",
                "link": "l",
                "businessCriticality": "STR",
                "model": model,
                "items": [item, "plain"],
                "plain": 5,
            }
        )

        assert body == {"model": {"m": 1}, "items": [{"i": 1}, "plain"], "plain": 5}
        assert client._build_serializable_body({"businessCriticality": 0}) == {"businessCriticality": 0}

    @pytest.mark.mocked
    def test_validate_settings_payload_non_dict(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        for bad in (None, "str", [1]):
            result = client._validate_settings_payload("application", "create", bad)
            assert result["elicitation_needed"] is True
            assert "payload is missing or invalid" in result["reason"]

    @pytest.mark.mocked
    def test_validate_settings_payload_unknown_subtype_is_valid(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        assert client._validate_settings_payload("mystery", "create", {"a": 1}) is None

    @pytest.mark.mocked
    def test_validate_endpoint_fields(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        missing = client._validate_settings_payload("endpoint", "create", {})
        assert len(missing["api_error"]) == 2
        assert "'endpointCase' is required" in missing["api_error"][0]
        assert "'serviceId' is required" in missing["api_error"][1]

        invalid = client._validate_settings_payload(
            "endpoint", "create", {"endpointCase": "WEIRD", "serviceId": "s"}
        )
        assert "'endpointCase' value 'WEIRD' is invalid" in invalid["api_error"][0]

        assert client._validate_settings_payload(
            "endpoint", "create", {"endpointCase": "LOWER", "serviceId": "s"}
        ) is None

    @pytest.mark.mocked
    def test_validate_service_fields(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        missing = client._validate_settings_payload("service", "create", {})
        assert len(missing["api_error"]) == 4

        wrong_enabled = client._validate_settings_payload(
            "service",
            "create",
            {"label": "l", "name": "n", "enabled": "yes", "matchSpecification": []},
        )
        assert wrong_enabled["api_error"] == ["'enabled' must be a boolean (true/false)"]

        assert client._validate_settings_payload(
            "service",
            "create",
            {"label": "l", "name": "n", "enabled": True, "matchSpecification": []},
        ) is None

    @pytest.mark.mocked
    def test_validate_manual_service_fields(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        missing = client._validate_settings_payload("manual_service", "create", {})
        assert "'tagFilterExpression' is required" in missing["api_error"][0]

        not_dict = client._validate_settings_payload(
            "manual_service", "create", {"tagFilterExpression": "x"}
        )
        assert "must be a dictionary" in not_dict["api_error"][0]

        assert client._validate_settings_payload(
            "manual_service", "create", {"tagFilterExpression": _TAG_FILTER}
        ) is None


class TestApplicationSettingsEndpointE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("body", "expected"),
        [([{"id": "e1"}], [{"id": "e1"}]), ({"id": "e1"}, [{"id": "e1"}]), ({}, [])],
    )
    async def test_get_all(self, instana_credentials, body, expected):
        mock_api = MagicMock()
        mock_api.get_endpoint_configs_without_preload_content.return_value = _json_response(body)
        client = create_application_settings_client(instana_credentials)

        assert await client._get_all_endpoint_configs(api_client=mock_api) == expected

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_endpoint_configs_without_preload_content.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_endpoint_configs(api_client=mock_api)

        assert "Failed to get endpoint configs" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "e1"}
        model_api.get_endpoint_config.return_value = model_response
        assert await client._get_endpoint_config(id="e1", api_client=model_api) == {"id": "e1"}

        dict_api = MagicMock()
        dict_api.get_endpoint_config.return_value = {"id": "e2"}
        assert await client._get_endpoint_config(id="e2", api_client=dict_api) == {"id": "e2"}

        assert await client._get_endpoint_config(id="", api_client=MagicMock()) == {"error": "id is required"}

        error_api = MagicMock()
        error_api.get_endpoint_config.side_effect = Exception("API Error")
        result = await client._get_endpoint_config(id="e1", api_client=error_api)
        assert "Failed to get endpoint config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)
        payload = {"endpointCase": "LOWER", "serviceId": "svc-1"}

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "e1"}
        model_api.create_endpoint_config.return_value = model_response
        assert await client._create_endpoint_config(payload=payload, api_client=model_api) == {"id": "e1"}
        assert model_api.create_endpoint_config.call_args.kwargs["endpoint_config"].service_id == "svc-1"

        empty_api = MagicMock()
        empty_api.create_endpoint_config.return_value = None
        result = await client._create_endpoint_config(payload=json.dumps(payload), api_client=empty_api)
        assert result == {"success": True, "message": "Endpoint config created"}

        literal_api = MagicMock()
        literal_api.create_endpoint_config.return_value = {"id": "e3"}
        result = await client._create_endpoint_config(payload=str(payload), api_client=literal_api)
        assert result == {"id": "e3"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_validation_and_error(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        invalid = await client._create_endpoint_config(payload={"endpointCase": "X"}, api_client=MagicMock())
        assert invalid["elicitation_needed"] is True

        error_api = MagicMock()
        error_api.create_endpoint_config.side_effect = Exception("API Error")
        result = await client._create_endpoint_config(
            payload={"endpointCase": "LOWER", "serviceId": "s"}, api_client=error_api
        )
        assert "Failed to create endpoint config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)
        payload = {"endpointCase": "UPPER", "serviceId": "svc-1"}

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "e1"}
        model_api.update_endpoint_config.return_value = model_response
        assert await client._update_endpoint_config(id="e1", payload=payload, api_client=model_api) == {"id": "e1"}

        empty_api = MagicMock()
        empty_api.update_endpoint_config.return_value = None
        result = await client._update_endpoint_config(
            id="e1", payload=json.dumps(payload), api_client=empty_api
        )
        assert result == {"success": True, "message": "Endpoint config 'e1' updated"}

        literal_api = MagicMock()
        literal_api.update_endpoint_config.return_value = {"id": "e1"}
        assert await client._update_endpoint_config(id="e1", payload=str(payload), api_client=literal_api) == {
            "id": "e1"
        }

        invalid = await client._update_endpoint_config(id="e1", payload={}, api_client=MagicMock())
        assert invalid["elicitation_needed"] is True

        error_api = MagicMock()
        error_api.update_endpoint_config.side_effect = Exception("API Error")
        result = await client._update_endpoint_config(id="e1", payload=payload, api_client=error_api)
        assert "Failed to update endpoint config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        ok_api = MagicMock()
        result = await client._delete_endpoint_config(id="e1", api_client=ok_api)
        assert result["success"] is True
        ok_api.delete_endpoint_config.assert_called_once_with(id="e1")

        assert await client._delete_endpoint_config(id="", api_client=MagicMock()) == {"error": "id is required"}

        error_api = MagicMock()
        error_api.delete_endpoint_config.side_effect = Exception("API Error")
        result = await client._delete_endpoint_config(id="e1", api_client=error_api)
        assert "Failed to delete endpoint config" in result["error"]


class TestApplicationSettingsServiceE2E:
    _PAYLOAD = {
        "id": "svc-1",
        "label": "Service",
        "name": "svc",
        "enabled": True,
        "matchSpecification": [{"key": "k", "value": "v"}],
    }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("body", "expected"),
        [([{"id": "s1"}], [{"id": "s1"}]), ({"id": "s1"}, [{"id": "s1"}]), ({}, [])],
    )
    async def test_get_all(self, instana_credentials, body, expected):
        mock_api = MagicMock()
        mock_api.get_service_configs_without_preload_content.return_value = _json_response(body)
        client = create_application_settings_client(instana_credentials)

        assert await client._get_all_service_configs(api_client=mock_api) == expected

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_service_configs_without_preload_content.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_service_configs(api_client=mock_api)

        assert "Failed to get service configs" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "s1"}
        model_api.get_service_config.return_value = model_response
        assert await client._get_service_config(id="s1", api_client=model_api) == {"id": "s1"}

        dict_api = MagicMock()
        dict_api.get_service_config.return_value = {"id": "s2"}
        assert await client._get_service_config(id="s2", api_client=dict_api) == {"id": "s2"}

        assert await client._get_service_config(id="", api_client=MagicMock()) == {"error": "id is required"}

        error_api = MagicMock()
        error_api.get_service_config.side_effect = Exception("API Error")
        assert "Failed to get service config" in (
            await client._get_service_config(id="s1", api_client=error_api)
        )["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "svc-1"}
        model_api.add_service_config.return_value = model_response
        assert await client._add_service_config(payload=self._PAYLOAD, api_client=model_api) == {"id": "svc-1"}

        empty_api = MagicMock()
        empty_api.add_service_config.return_value = None
        result = await client._add_service_config(payload=json.dumps(self._PAYLOAD), api_client=empty_api)
        assert result == {"success": True, "message": "Service config created"}

        literal_api = MagicMock()
        literal_api.add_service_config.return_value = {"id": "x"}
        assert await client._add_service_config(payload=str(self._PAYLOAD), api_client=literal_api) == {"id": "x"}

        invalid = await client._add_service_config(payload={"label": "l"}, api_client=MagicMock())
        assert invalid["elicitation_needed"] is True

        error_api = MagicMock()
        error_api.add_service_config.side_effect = Exception("API Error")
        assert "Failed to add service config" in (
            await client._add_service_config(payload=self._PAYLOAD, api_client=error_api)
        )["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "svc-1"}
        model_api.update_service_config.return_value = model_response
        assert await client._update_service_config(
            id="svc-1", payload=self._PAYLOAD, api_client=model_api
        ) == {"id": "svc-1"}

        empty_api = MagicMock()
        empty_api.update_service_config.return_value = None
        result = await client._update_service_config(
            id="svc-1", payload=json.dumps(self._PAYLOAD), api_client=empty_api
        )
        assert result == {"success": True, "message": "Service config 'svc-1' updated"}

        literal_api = MagicMock()
        literal_api.update_service_config.return_value = {"id": "x"}
        assert await client._update_service_config(
            id="svc-1", payload=str(self._PAYLOAD), api_client=literal_api
        ) == {"id": "x"}

        invalid = await client._update_service_config(id="svc-1", payload={}, api_client=MagicMock())
        assert invalid["elicitation_needed"] is True

        error_api = MagicMock()
        error_api.update_service_config.side_effect = Exception("API Error")
        assert "Failed to update service config" in (
            await client._update_service_config(id="svc-1", payload=self._PAYLOAD, api_client=error_api)
        )["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        ok_api = MagicMock()
        assert (await client._delete_service_config(id="s1", api_client=ok_api))["success"] is True
        ok_api.delete_service_config.assert_called_once_with(id="s1")

        assert await client._delete_service_config(id="", api_client=MagicMock()) == {"error": "id is required"}

        error_api = MagicMock()
        error_api.delete_service_config.side_effect = Exception("API Error")
        assert "Failed to delete service config" in (
            await client._delete_service_config(id="s1", api_client=error_api)
        )["error"]


class TestApplicationSettingsManualServiceE2E:
    _PAYLOAD = {"tagFilterExpression": _TAG_FILTER}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("body", "expected"),
        [([{"id": "m1"}], [{"id": "m1"}]), ({"id": "m1"}, [{"id": "m1"}]), ({}, [])],
    )
    async def test_get_all(self, instana_credentials, body, expected):
        mock_api = MagicMock()
        mock_api.get_all_manual_service_configs_without_preload_content.return_value = _json_response(body)
        client = create_application_settings_client(instana_credentials)

        assert await client._get_all_manual_service_configs(api_client=mock_api) == expected

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_all_manual_service_configs_without_preload_content.side_effect = Exception("API Error")
        client = create_application_settings_client(instana_credentials)

        result = await client._get_all_manual_service_configs(api_client=mock_api)

        assert "Failed to get manual service configs" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "m1"}
        model_api.add_manual_service_config.return_value = model_response
        assert await client._add_manual_service_config(payload=self._PAYLOAD, api_client=model_api) == {
            "id": "m1"
        }

        empty_api = MagicMock()
        empty_api.add_manual_service_config.return_value = None
        result = await client._add_manual_service_config(
            payload=json.dumps(self._PAYLOAD), api_client=empty_api
        )
        assert result == {"success": True, "message": "Manual service config created"}

        literal_api = MagicMock()
        literal_api.add_manual_service_config.return_value = {"id": "x"}
        assert await client._add_manual_service_config(
            payload=str(self._PAYLOAD), api_client=literal_api
        ) == {"id": "x"}

        invalid = await client._add_manual_service_config(payload={}, api_client=MagicMock())
        assert invalid["elicitation_needed"] is True

        error_api = MagicMock()
        error_api.add_manual_service_config.side_effect = Exception("API Error")
        assert "Failed to add manual service config" in (
            await client._add_manual_service_config(payload=self._PAYLOAD, api_client=error_api)
        )["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)
        payload = {"id": "m1", **self._PAYLOAD}

        model_api = MagicMock()
        model_response = MagicMock()
        model_response.to_dict.return_value = {"id": "m1"}
        model_api.update_manual_service_config.return_value = model_response
        assert await client._update_manual_service_config(
            id="m1", payload=payload, api_client=model_api
        ) == {"id": "m1"}

        empty_api = MagicMock()
        empty_api.update_manual_service_config.return_value = None
        result = await client._update_manual_service_config(
            id="m1", payload=json.dumps(payload), api_client=empty_api
        )
        assert result == {"success": True, "message": "Manual service config 'm1' updated"}

        literal_api = MagicMock()
        literal_api.update_manual_service_config.return_value = {"id": "x"}
        assert await client._update_manual_service_config(
            id="m1", payload=str(payload), api_client=literal_api
        ) == {"id": "x"}

        invalid = await client._update_manual_service_config(id="m1", payload={}, api_client=MagicMock())
        assert invalid["elicitation_needed"] is True

        error_api = MagicMock()
        error_api.update_manual_service_config.side_effect = Exception("API Error")
        assert "Failed to update manual service config" in (
            await client._update_manual_service_config(id="m1", payload=payload, api_client=error_api)
        )["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_variants(self, instana_credentials):
        client = create_application_settings_client(instana_credentials)

        ok_api = MagicMock()
        assert (await client._delete_manual_service_config(id="m1", api_client=ok_api))["success"] is True
        ok_api.delete_manual_service_config.assert_called_once_with(id="m1")

        assert await client._delete_manual_service_config(id="", api_client=MagicMock()) == {
            "error": "id is required"
        }

        error_api = MagicMock()
        error_api.delete_manual_service_config.side_effect = Exception("API Error")
        assert "Failed to delete manual service config" in (
            await client._delete_manual_service_config(id="m1", api_client=error_api)
        )["error"]
