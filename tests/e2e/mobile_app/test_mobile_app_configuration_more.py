"""
Additional E2E tests (mocked) for Mobile App Configuration MCP Tools.

Complements ``test_mobile_app_configuration.py`` with the dispatchers, name
resolution, geo mapping rules (CSV) and source map upload configuration branches.
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


class MobileAppConfigurationApi(MagicMock):
    """Stand-in SDK API class.

    The class name matches the real SDK class so ``with_header_auth`` re-uses an
    instance attached to the client (STDIO mode) instead of building a real one.
    """


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


def _json_response(body, status=200):
    return _MockResponse(json.dumps(body).encode("utf-8"), status=status)


def create_mobile_app_configuration_client(instana_credentials):
    """Dynamically import and create the Mobile App Configuration client with a mocked SDK API."""
    module = importlib.import_module("src.mobile_app.mobile_app_configuration")
    module = importlib.reload(module)
    client = module.MobileAppConfigurationMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )
    client.mobile_app_configuration_api = MobileAppConfigurationApi()
    return client


def _api(client):
    return client.mobile_app_configuration_api


class _AppObject:
    """Object-style mobile app (as returned by the SDK models)."""

    def __init__(self, name, app_id):
        self.name = name
        self.id = app_id


APPS = [
    {"id": "id-1", "name": "Robot Shop"},
    {"id": "id-2", "name": "Other App"},
]


class TestMobileAppConfigurationHelpersE2E:
    @pytest.mark.mocked
    def test_normalize_mobile_apps_response(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        assert client._normalize_mobile_apps_response({"results": [1, 2]}) == [1, 2]
        assert client._normalize_mobile_apps_response({"id": "x"}) == [{"id": "x"}]
        assert client._normalize_mobile_apps_response([{"id": "x"}]) == [{"id": "x"}]
        assert client._normalize_mobile_apps_response("raw") == "raw"

    @pytest.mark.mocked
    def test_extract_name_and_id_variants(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        assert client._extract_name_and_id({"name": "A", "id": "1"}) == ("A", "1")
        assert client._extract_name_and_id({"name": "A"}) == ("A", None)
        assert client._extract_name_and_id(_AppObject("B", "2")) == ("B", "2")
        assert client._extract_name_and_id(42) == (None, None)

    @pytest.mark.mocked
    def test_find_mobile_app_id_by_name_is_case_insensitive(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        apps = [{"name": "NoId"}, {"id": "no-name"}, _AppObject("Robot Shop", "id-1"), 5]

        assert client._find_mobile_app_id_by_name(apps, "robot SHOP") == "id-1"
        assert client._find_mobile_app_id_by_name(apps, "missing") is None

    @pytest.mark.mocked
    def test_extract_mobile_app_names(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        names = client._extract_mobile_app_names([{"name": "A"}, {"id": "no-name"}, _AppObject("B", "2"), 7])

        assert names == ["A", "unknown", "B"]

    @pytest.mark.mocked
    def test_parse_csv_to_dict_list_variants(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        assert client._parse_csv_to_dict_list("") == {
            "status": "empty",
            "data": [],
            "message": "Empty response from API",
        }
        assert client._parse_csv_to_dict_list("   \n")["status"] == "empty"

        success = client._parse_csv_to_dict_list("cidr,country\n10.0.0.0/8,DE\n192.168.0.0/16,US\n")
        assert success["status"] == "success"
        assert success["schema"] == ["cidr", "country"]
        assert success["data"][0] == {"cidr": "10.0.0.0/8", "country": "DE"}

        schema_only = client._parse_csv_to_dict_list("cidr,country\n")
        assert schema_only["status"] == "schema_only"
        assert schema_only["schema"] == ["cidr", "country"]
        assert "schema is available" in schema_only["message"]

        unexpected = client._parse_csv_to_dict_list("no-comma-here")
        assert unexpected["status"] == "error"
        assert "Unexpected response format" in unexpected["message"]


class TestMobileAppConfigurationDispatcherE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_operation(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_config.return_value = APPS

        result = await client.execute_mobile_app_operation(
            operation="get_all", resource_type="mobile_app", tool_name="manage_mobile_apps"
        )

        assert result == APPS

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_operation(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        model = MagicMock()
        model.to_dict.return_value = {"id": "id-1", "name": "Robot Shop"}
        _api(client).get_single_mobile_app_config.return_value = model

        result = await client.execute_mobile_app_operation(operation="get", mobile_app_id="id-1")

        assert result == {"id": "id-1", "name": "Robot Shop"}
        _api(client).get_single_mobile_app_config.assert_called_once_with(mobile_app_id="id-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_operation_resolves_id(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_config.return_value = APPS
        _api(client).get_single_mobile_app_config.return_value = {"id": "id-2", "name": "Other App"}

        result = await client.execute_mobile_app_operation(operation="get", mobile_app_name="other app")

        assert result == {"id": "id-2", "name": "Other App"}
        _api(client).get_single_mobile_app_config.assert_called_once_with(mobile_app_id="id-2")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_name_not_found(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_config.return_value = APPS

        result = await client.execute_mobile_app_operation(operation="get", mobile_app_name="ghost")

        assert result == {"error": "No mobile app found with name 'ghost'"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_requires_id_or_name(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        result = await client.execute_mobile_app_operation(operation="get")

        assert result == {"error": "mobile_app_id or mobile_app_name is required for get operation"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        result = await client.execute_mobile_app_operation(operation="delete")

        assert result == {"error": "Invalid operation: delete"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dispatcher_exception_is_wrapped(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        async def boom(*_a, **_k):
            raise RuntimeError("kaboom")

        client.get_all_mobile_apps = boom

        result = await client.execute_mobile_app_operation(operation="get_all")

        assert result == {"error": "Failed to execute operation 'get_all': kaboom"}


class TestMobileAppConfigurationReadsE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_mobile_apps_to_dict_and_error(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        model = MagicMock()
        model.to_dict.return_value = {"results": APPS}
        api = MagicMock()
        api.get_mobile_app_config.return_value = model

        result = await client.get_all_mobile_apps(api_client=api)
        assert result == {"results": APPS}

        failing = MagicMock()
        failing.get_mobile_app_config.side_effect = RuntimeError("down")
        error = await client.get_all_mobile_apps(api_client=failing)
        assert error == [{"error": "Failed to get mobile apps: down"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_mobile_app_by_id_variants(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()

        api.get_single_mobile_app_config.return_value = {"id": "id-1"}
        assert await client.get_mobile_app_by_id("id-1", api_client=api) == {"id": "id-1"}

        api.get_single_mobile_app_config.side_effect = RuntimeError("404")
        error = await client.get_mobile_app_by_id("id-1", api_client=api)
        assert error == {"error": "Failed to get mobile app with ID id-1: 404"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_geo_location_configuration(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        model = MagicMock()
        model.to_dict.return_value = {"geoDetailRemoval": "NONE"}

        api.get_mobile_app_geo_location_configuration.return_value = model
        assert await client.get_mobile_app_geo_location_configuration("id-1", api_client=api) == {
            "geoDetailRemoval": "NONE"
        }

        api.get_mobile_app_geo_location_configuration.return_value = {"geoDetailRemoval": "CITY"}
        assert await client.get_mobile_app_geo_location_configuration("id-1", api_client=api) == {
            "geoDetailRemoval": "CITY"
        }

        api.get_mobile_app_geo_location_configuration.side_effect = RuntimeError("x")
        error = await client.get_mobile_app_geo_location_configuration("id-1", api_client=api)
        assert "Failed to get geo location configuration for mobile app with ID id-1" in error["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_ip_masking_configuration(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        model = MagicMock()
        model.to_dict.return_value = {"ipMasking": "DEFAULT"}

        api.get_mobile_app_ip_masking_configuration.return_value = model
        assert await client.get_mobile_app_ip_masking_configuration("id-1", api_client=api) == {
            "ipMasking": "DEFAULT"
        }

        api.get_mobile_app_ip_masking_configuration.return_value = {"ipMasking": "STRICT"}
        assert await client.get_mobile_app_ip_masking_configuration("id-1", api_client=api) == {
            "ipMasking": "STRICT"
        }

        api.get_mobile_app_ip_masking_configuration.side_effect = RuntimeError("x")
        error = await client.get_mobile_app_ip_masking_configuration("id-1", api_client=api)
        assert "Failed to get IP masking configuration" in error["error"]


class TestMobileAppGeoMappingRulesE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_csv_result_from_high_level_call(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_geo_mapping_rules.return_value = "cidr,country\n10.0.0.0/8,DE\n"

        result = await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api)

        assert result["status"] == "success"
        assert result["data"] == [{"cidr": "10.0.0.0/8", "country": "DE"}]
        api.get_mobile_app_geo_mapping_rules_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_none_result_falls_back_to_raw_bytes(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_geo_mapping_rules.return_value = None
        api.get_mobile_app_geo_mapping_rules_without_preload_content.return_value = _MockResponse(
            b"cidr,country\n1.1.1.0/24,AU\n"
        )

        result = await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api)

        assert result["status"] == "success"
        assert result["data"][0]["country"] == "AU"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_exception_falls_back_to_raw_str_data(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_geo_mapping_rules.side_effect = RuntimeError("pydantic")
        api.get_mobile_app_geo_mapping_rules_without_preload_content.return_value = _MockResponse(
            "cidr,country\n"
        )

        result = await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api)

        assert result["status"] == "schema_only"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_raw_response_without_data_attribute(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_geo_mapping_rules.return_value = None
        api.get_mobile_app_geo_mapping_rules_without_preload_content.return_value = "plain,csv\n"

        result = await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api)

        assert result["status"] == "schema_only"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_and_unexpected_bodies(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()

        api.get_mobile_app_geo_mapping_rules.return_value = ""
        assert (await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api))["status"] == "empty"

        api.get_mobile_app_geo_mapping_rules.return_value = "oops"
        assert (await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api))["status"] == "error"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_both_calls_failing_returns_error_list(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_geo_mapping_rules.side_effect = RuntimeError("first")
        api.get_mobile_app_geo_mapping_rules_without_preload_content.side_effect = RuntimeError("second")

        result = await client.get_mobile_app_geo_mapping_rules("id-1", api_client=api)

        assert result == [{"error": "Failed to get mobile app geo mapping rules: second"}]


class TestMobileAppSourceMapConfigE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_success(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_files_without_preload_content.return_value = _json_response(
            [{"id": "sm-1"}]
        )

        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)

        assert result == [{"id": "sm-1"}]
        api.get_mobile_app_source_map_files_without_preload_content.assert_called_once_with(mobile_app_id="id-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_http_error_with_body(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_files_without_preload_content.return_value = _MockResponse(
            b"forbidden", status=403
        )

        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)

        assert result == {
            "error": "Failed to get source map configurations: HTTP 403",
            "details": "forbidden",
            "status_code": 403,
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_http_error_with_undecodable_body(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_files_without_preload_content.return_value = _MockResponse(
            object(), status=500
        )

        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)

        assert result == {"error": "Failed to get source map configurations: HTTP 500", "status_code": 500}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_falls_back_to_standard_method(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_files_without_preload_content.side_effect = RuntimeError("bad")
        model = MagicMock()
        model.to_dict.return_value = {"fallback": "model"}
        api.get_mobile_app_source_map_files.return_value = model

        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)
        assert result == {"fallback": "model"}

        api.get_mobile_app_source_map_files.return_value = [{"fallback": "list"}]
        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)
        assert result == [{"fallback": "list"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_invalid_json_triggers_fallback(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_files_without_preload_content.return_value = _MockResponse(b"<html>")
        api.get_mobile_app_source_map_files.return_value = {"ok": True}

        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)

        assert result == {"ok": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_both_calls_fail(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_files_without_preload_content.side_effect = RuntimeError("one")
        api.get_mobile_app_source_map_files.side_effect = RuntimeError("two")

        result = await client.get_all_mobile_app_source_map_upload_configurations("id-1", api_client=api)

        assert "Failed to get source map upload configurations for mobile app with ID id-1: two" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_success(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_file_without_preload_content.return_value = _json_response({"id": "sm-1"})

        result = await client.get_mobile_app_source_map_upload_configuration_by_id(
            "id-1", "sm-1", api_client=api
        )

        assert result == {"id": "sm-1"}
        api.get_mobile_app_source_map_file_without_preload_content.assert_called_once_with(
            mobile_app_id="id-1", source_map_config_id="sm-1"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_http_errors(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()

        api.get_mobile_app_source_map_file_without_preload_content.return_value = _MockResponse(
            b"missing", status=404
        )
        with_body = await client.get_mobile_app_source_map_upload_configuration_by_id("a", "b", api_client=api)
        assert with_body == {
            "error": "Failed to get source map configuration: HTTP 404",
            "details": "missing",
            "status_code": 404,
        }

        api.get_mobile_app_source_map_file_without_preload_content.return_value = _MockResponse(
            object(), status=500
        )
        without_body = await client.get_mobile_app_source_map_upload_configuration_by_id("a", "b", api_client=api)
        assert without_body == {"error": "Failed to get source map configuration: HTTP 500", "status_code": 500}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_by_id_fallbacks(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_source_map_file_without_preload_content.side_effect = RuntimeError("bad")
        model = MagicMock()
        model.to_dict.return_value = {"id": "model"}

        api.get_mobile_app_source_map_file.return_value = model
        assert await client.get_mobile_app_source_map_upload_configuration_by_id("a", "b", api_client=api) == {
            "id": "model"
        }

        api.get_mobile_app_source_map_file.return_value = {"id": "dict"}
        assert await client.get_mobile_app_source_map_upload_configuration_by_id("a", "b", api_client=api) == {
            "id": "dict"
        }

        api.get_mobile_app_source_map_file.side_effect = RuntimeError("worse")
        error = await client.get_mobile_app_source_map_upload_configuration_by_id("a", "b", api_client=api)
        assert "Failed to get mobile app source map upload configuration: worse" in error["error"]


class TestMobileAppAdvancedConfigDispatcherE2E:
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_requires_id_or_name(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        result = await client.execute_mobile_app_advanced_config_operation(operation="get_geo_config")

        assert result == {"error": "Either mobile_app_id or mobile_app_name must be provided"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_name_resolution_failure_is_returned(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_config.return_value = APPS

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_geo_config", mobile_app_name="ghost"
        )

        assert result == {"error": "No mobile app found with name 'ghost'"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_name_resolution_with_unusable_listing(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_config.return_value = "garbage"

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_geo_config", mobile_app_name="Robot Shop"
        )

        assert result == {"error": "Failed to retrieve mobile apps for name resolution"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resolve_with_explicit_api_client(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        api = MagicMock()
        api.get_mobile_app_config.return_value = {"results": APPS}

        resolved = await client._resolve_mobile_app_id(None, "robot shop", None, api_client=api)

        assert resolved == "id-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        "operation,sdk_method,sdk_return",
        [
            ("get_geo_config", "get_mobile_app_geo_location_configuration", {"geo": 1}),
            ("get_ip_masking", "get_mobile_app_ip_masking_configuration", {"ip": 1}),
        ],
    )
    async def test_routes_simple_operations(self, instana_credentials, operation, sdk_method, sdk_return):
        client = create_mobile_app_configuration_client(instana_credentials)
        getattr(_api(client), sdk_method).return_value = sdk_return

        result = await client.execute_mobile_app_advanced_config_operation(
            operation=operation, mobile_app_id="id-1", resource_type="mobile_app", tool_name="manage_mobile_apps"
        )

        assert result == sdk_return
        getattr(_api(client), sdk_method).assert_called_once_with(mobile_app_id="id-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_routes_geo_rules(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_geo_mapping_rules.return_value = "cidr,country\n1.0.0.0/8,FR\n"

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_geo_rules", mobile_app_id="id-1"
        )

        assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_routes_source_map_upload_config_by_name(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_config.return_value = APPS
        _api(client).get_mobile_app_source_map_files_without_preload_content.return_value = _json_response([])

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_source_map_upload_config", mobile_app_name="Robot Shop"
        )

        assert result == []
        _api(client).get_mobile_app_source_map_files_without_preload_content.assert_called_once_with(
            mobile_app_id="id-1"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_routes_source_map_config_by_id(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)
        _api(client).get_mobile_app_source_map_file_without_preload_content.return_value = _json_response(
            {"id": "sm-1"}
        )

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_mobile_app_source_map_upload_config_by_id", mobile_app_id="id-1", config_id="sm-1"
        )

        assert result == {"id": "sm-1"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_source_map_config_by_id_requires_config_id(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_mobile_app_source_map_upload_config_by_id", mobile_app_id="id-1"
        )

        assert result == {
            "error": "config_id is required for get_mobile_app_source_map_upload_config_by_id operation"
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="nope", mobile_app_id="id-1"
        )

        assert "Invalid advanced config operation: nope" in result["error"]
        assert "get_geo_config" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unexpected_exception_is_wrapped(self, instana_credentials):
        client = create_mobile_app_configuration_client(instana_credentials)

        async def boom(*_a, **_k):
            raise RuntimeError("kaboom")

        client._route_advanced_config_operation = boom

        result = await client.execute_mobile_app_advanced_config_operation(
            operation="get_geo_config", mobile_app_id="id-1"
        )

        assert result == {"error": "Failed to execute advanced config operation: kaboom"}
