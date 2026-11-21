"""
Mocked E2E tests for Website Configuration MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_website_configuration_client(instana_credentials):
    """Dynamically import and create Website Configuration client"""
    module = importlib.import_module("src.website.website_configuration")
    module = importlib.reload(module)
    return module.WebsiteConfigurationMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


def attach_stdio_mock_api(client, mock_api_methods=None):
    """
    Attach a mock SDK API object to the client so that ``with_header_auth`` discovers it
    (STDIO mode, ``*_api`` attribute whose class name matches) instead of building a real one.
    Used for the ``execute_*`` router methods that do not accept ``api_client``.
    """
    module = importlib.import_module("src.website.website_configuration")
    mock_api = MagicMock(spec=module.WebsiteConfigurationApi)
    for name, value in (mock_api_methods or {}).items():
        setattr(mock_api, name, value)
    client.website_configuration_api = mock_api
    return mock_api


class _ToDict:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class _MockResponse:
    def __init__(self, payload, status=200):
        self.data = payload
        self.status = status
        self.headers = {"Content-Type": "application/json"}


class _Named:
    """Object (non-dict) website with attributes."""

    def __init__(self, name, id):
        self.name = name
        self.id = id


class TestWebsiteConfigurationE2E:
    """Mocked end-to-end tests for Website Configuration MCP Tools"""

    # ---------------- get_websites / get_website ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_websites_list_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_websites.return_value = [{"id": "w1", "name": "shop"}]
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_websites(api_client=mock_api)

        assert result == [{"id": "w1", "name": "shop"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_websites_to_dict_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_websites.return_value = _ToDict({"results": []})
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_websites(api_client=mock_api)

        assert result == {"results": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_websites_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_websites.side_effect = Exception("API Error")
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_websites(api_client=mock_api)

        assert isinstance(result, list)
        assert "Failed to get websites" in result[0]["error"]
        assert "API Error" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_website_success_to_dict(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website.return_value = _ToDict({"id": "w1"})
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website(website_id="w1", api_client=mock_api)

        assert result == {"id": "w1"}
        mock_api.get_website.assert_called_once_with(website_id="w1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_website_plain_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website.return_value = {"id": "w2"}
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website(website_id="w2", api_client=mock_api)

        assert result == {"id": "w2"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_website_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website.side_effect = Exception("nope")
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website(website_id="w1", api_client=mock_api)

        assert "Failed to get website" in result["error"]

    # ---------------- create_website ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_no_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.return_value = _ToDict({"id": "new"})
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(name="n", api_client=mock_api)

        assert result == {"id": "new"}
        mock_api.create_website.assert_called_once_with(name="n", create_website_request_inner=None)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_with_list_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.return_value = {"id": "new"}
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(
            name="n",
            payload=[{"displayName": "Team", "id": "t1"}, "ignored-non-dict"],
            api_client=mock_api,
        )

        assert result == {"id": "new"}
        tags = mock_api.create_website.call_args.kwargs["create_website_request_inner"]
        assert len(tags) == 1
        assert tags[0].display_name == "Team"
        assert tags[0].id == "t1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_with_json_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.return_value = None
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(
            name="n",
            payload=json.dumps([{"displayName": "Team", "id": "t1"}]),
            api_client=mock_api,
        )

        assert result == {"success": True, "message": "Website created successfully"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_with_single_quote_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.return_value = {"id": "x"}
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(
            name="n",
            payload="[{'displayName': 'Team', 'id': 't1'}]",
            api_client=mock_api,
        )

        assert result == {"id": "x"}
        assert len(mock_api.create_website.call_args.kwargs["create_website_request_inner"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_with_python_literal_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.return_value = {"id": "y"}
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(
            name="n",
            payload="[{'displayName': \"Dev's Team\", 'id': 't1'}]",
            api_client=mock_api,
        )

        assert result == {"id": "y"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_invalid_string_payload(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(name="n", payload="not [valid", api_client=mock_api)

        assert "Invalid payload format" in result["error"]
        mock_api.create_website.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_invalid_payload_type(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(name="n", payload={"a": 1}, api_client=mock_api)

        assert result == {"error": "Payload must be a list of team tags or a JSON string"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_invalid_team_tag(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(
            name="n", payload=[{"displayName": 123}], api_client=mock_api
        )

        assert "Failed to create team tag objects" in result["error"]
        mock_api.create_website.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_website_api_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.side_effect = Exception("denied")
        client = create_website_configuration_client(instana_credentials)

        result = await client.create_website(name="n", api_client=mock_api)

        assert "Failed to create website" in result["error"]
        assert "denied" in result["error"]

    # ---------------- delete / rename ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_website_success(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.delete_website(website_id="w1", api_client=mock_api)

        assert result["success"] is True
        assert "w1" in result["message"]
        mock_api.delete_website.assert_called_once_with(website_id="w1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_website_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_website.side_effect = Exception("cannot")
        client = create_website_configuration_client(instana_credentials)

        result = await client.delete_website(website_id="w1", api_client=mock_api)

        assert "Failed to delete website" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rename_website_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.rename_website.return_value = _ToDict({"id": "w1", "name": "new"})
        client = create_website_configuration_client(instana_credentials)

        result = await client.rename_website(website_id="w1", name="new", api_client=mock_api)

        assert result == {"id": "w1", "name": "new"}
        mock_api.rename_website.assert_called_once_with(website_id="w1", name="new")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rename_website_plain_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.rename_website.return_value = {"ok": True}
        client = create_website_configuration_client(instana_credentials)

        result = await client.rename_website(website_id="w1", name="new", api_client=mock_api)

        assert result == {"ok": True}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rename_website_missing_id(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.rename_website(website_id="", name="x", api_client=mock_api)

        assert result == {"error": "website_id parameter is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rename_website_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.rename_website.side_effect = Exception("fail")
        client = create_website_configuration_client(instana_credentials)

        result = await client.rename_website(website_id="w1", name="x", api_client=mock_api)

        assert "Failed to rename website" in result["error"]

    # ---------------- geo location ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_location_configuration(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_location_configuration.return_value = _ToDict(
            {"geoDetailRemoval": "NO_REMOVAL"}
        )
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_location_configuration(
            website_id="w1", api_client=mock_api
        )

        assert result == {"geoDetailRemoval": "NO_REMOVAL"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_location_configuration_plain_and_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_location_configuration.return_value = {"a": 1}
        client = create_website_configuration_client(instana_credentials)

        assert await client.get_website_geo_location_configuration(
            website_id="w1", api_client=mock_api
        ) == {"a": 1}

        mock_api.get_website_geo_location_configuration.side_effect = Exception("bad")
        result = await client.get_website_geo_location_configuration(
            website_id="w1", api_client=mock_api
        )
        assert "Failed to get website geo-location configuration" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_dict_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_geo_location_configuration.return_value = _ToDict({"updated": True})
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_geo_location_configuration(
            website_id="w1",
            payload={"geoDetailRemoval": "REMOVE_CITY", "geoMappingRules": [{"cidr": "10.0.0.0/8", "subdivisions": []}]},
            api_client=mock_api,
        )

        assert result == {"updated": True}
        kwargs = mock_api.update_website_geo_location_configuration.call_args.kwargs
        assert kwargs["website_id"] == "w1"
        assert kwargs["geo_location_configuration"].geo_detail_removal == "REMOVE_CITY"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_snake_case_payload(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_geo_location_configuration.return_value = None
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_geo_location_configuration(
            website_id="w1",
            payload={"geo_detail_removal": "REMOVE_ALL", "geo_mapping_rules": []},
            api_client=mock_api,
        )

        assert result == {"success": True, "message": "Update website geo-location configuration"}
        config = mock_api.update_website_geo_location_configuration.call_args.kwargs[
            "geo_location_configuration"
        ]
        assert config.geo_detail_removal == "REMOVE_ALL"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_default_and_json_string(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_geo_location_configuration.return_value = {"ok": 1}
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_geo_location_configuration(
            website_id="w1", payload="{}", api_client=mock_api
        )

        assert result == {"ok": 1}
        config = mock_api.update_website_geo_location_configuration.call_args.kwargs[
            "geo_location_configuration"
        ]
        assert config.geo_detail_removal == "NO_REMOVAL"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_single_quote_and_literal_strings(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_geo_location_configuration.return_value = {"ok": 1}
        client = create_website_configuration_client(instana_credentials)

        assert await client.update_website_geo_location_configuration(
            website_id="w1", payload="{'geoDetailRemoval': 'REMOVE_CITY'}", api_client=mock_api
        ) == {"ok": 1}
        assert await client.update_website_geo_location_configuration(
            website_id="w1",
            payload="{'geoDetailRemoval': 'REMOVE_CITY', 'note': \"it's\"}",
            api_client=mock_api,
        ) == {"ok": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_invalid_string(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_geo_location_configuration(
            website_id="w1", payload="not {valid", api_client=mock_api
        )

        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_invalid_enum(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_geo_location_configuration(
            website_id="w1", payload={"geoDetailRemoval": "BOGUS"}, api_client=mock_api
        )

        assert "Failed to create GeoLocationConfiguration" in result["error"]
        mock_api.update_website_geo_location_configuration.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_geo_location_api_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_geo_location_configuration.side_effect = Exception("fail")
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_geo_location_configuration(
            website_id="w1", payload={"geoDetailRemoval": "NO_REMOVAL"}, api_client=mock_api
        )

        assert "Failed to update website geo-location configuration" in result["error"]

    # ---------------- ip masking ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_ip_masking_configuration(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_ip_masking_configuration.return_value = _ToDict({"ipMasking": "DEFAULT"})
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_ip_masking_configuration(
            website_id="w1", api_client=mock_api
        )
        assert result == {"ipMasking": "DEFAULT"}

        mock_api.get_website_ip_masking_configuration.return_value = {"raw": 1}
        assert await client.get_website_ip_masking_configuration(
            website_id="w1", api_client=mock_api
        ) == {"raw": 1}

        mock_api.get_website_ip_masking_configuration.side_effect = Exception("bad")
        error = await client.get_website_ip_masking_configuration(website_id="w1", api_client=mock_api)
        assert "Failed to get website IP masking configuration" in error["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_ip_masking_variants(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_ip_masking_configuration.return_value = _ToDict({"ipMasking": "STRICT"})
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_ip_masking_configuration(
            website_id="w1", payload={"ipMasking": "STRICT"}, api_client=mock_api
        )
        assert result == {"ipMasking": "STRICT"}
        config = mock_api.update_website_ip_masking_configuration.call_args.kwargs[
            "ip_masking_configuration"
        ]
        assert config.ip_masking == "STRICT"

        mock_api.update_website_ip_masking_configuration.return_value = None
        result = await client.update_website_ip_masking_configuration(
            website_id="w1", payload={"ip_masking": "REMOVE_ALL_DETAILS"}, api_client=mock_api
        )
        assert result == {"success": True, "message": "Update website ip-masking configuration"}

        # None payload -> default value DEFAULT
        mock_api.update_website_ip_masking_configuration.return_value = {"ok": 1}
        result = await client.update_website_ip_masking_configuration(
            website_id="w1", payload=None, api_client=mock_api
        )
        assert result == {"ok": 1}
        config = mock_api.update_website_ip_masking_configuration.call_args.kwargs[
            "ip_masking_configuration"
        ]
        assert config.ip_masking == "DEFAULT"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_ip_masking_string_payloads(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_website_ip_masking_configuration.return_value = {"ok": 1}
        client = create_website_configuration_client(instana_credentials)

        for payload in (
            '{"ipMasking": "STRICT"}',
            "{'ipMasking': 'STRICT'}",
            "{'ipMasking': 'STRICT', 'note': \"it's\"}",
        ):
            assert await client.update_website_ip_masking_configuration(
                website_id="w1", payload=payload, api_client=mock_api
            ) == {"ok": 1}

        error = await client.update_website_ip_masking_configuration(
            website_id="w1", payload="not {valid", api_client=mock_api
        )
        assert "Invalid payload format" in error["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_ip_masking_invalid_enum_and_api_error(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        result = await client.update_website_ip_masking_configuration(
            website_id="w1", payload={"ipMasking": "BOGUS"}, api_client=mock_api
        )
        assert "Failed to create IpMaskingConfiguration" in result["error"]

        mock_api.update_website_ip_masking_configuration.side_effect = Exception("fail")
        result = await client.update_website_ip_masking_configuration(
            website_id="w1", payload={"ipMasking": "DEFAULT"}, api_client=mock_api
        )
        assert "Failed to update website ip-masking configuration" in result["error"]

    # ---------------- geo mapping rules ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_mapping_rules_csv(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_mapping_rules.return_value = "cidr,country\n10.0.0.0/8,DE\n"
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_mapping_rules(website_id="w1", api_client=mock_api)

        assert result == [{"cidr": "10.0.0.0/8", "country": "DE"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_mapping_rules_plain_text(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_mapping_rules.return_value = "no-delimiter"
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_mapping_rules(website_id="w1", api_client=mock_api)

        assert result == [{"data": "no-delimiter"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_mapping_rules_fallback_on_none_bytes(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_mapping_rules.return_value = None
        mock_api.get_website_geo_mapping_rules_without_preload_content.return_value = _MockResponse(
            b"cidr,country\n1.1.1.0/24,US\n"
        )
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_mapping_rules(website_id="w1", api_client=mock_api)

        assert result == [{"cidr": "1.1.1.0/24", "country": "US"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_mapping_rules_fallback_on_exception_str_data(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_mapping_rules.side_effect = Exception("high-level failed")
        mock_api.get_website_geo_mapping_rules_without_preload_content.return_value = _MockResponse("")
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_mapping_rules(website_id="w1", api_client=mock_api)

        assert result == []

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_mapping_rules_fallback_without_data_attr(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_mapping_rules.return_value = None
        mock_api.get_website_geo_mapping_rules_without_preload_content.return_value = "a,b\n1,2\n"
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_mapping_rules(website_id="w1", api_client=mock_api)

        assert result == [{"a": "1", "b": "2"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_geo_mapping_rules_both_fail(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_geo_mapping_rules.side_effect = Exception("one")
        mock_api.get_website_geo_mapping_rules_without_preload_content.side_effect = Exception("two")
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_geo_mapping_rules(website_id="w1", api_client=mock_api)

        assert "Failed to get website geo mapping rules" in result[0]["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_set_geo_mapping_rules(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.set_website_geo_mapping_rules.return_value = _ToDict({"ok": True})
        client = create_website_configuration_client(instana_credentials)

        assert await client.set_website_geo_mapping_rules(
            website_id="w1", body="cidr,country", api_client=mock_api
        ) == {"ok": True}
        mock_api.set_website_geo_mapping_rules.assert_called_once_with(
            website_id="w1", body="cidr,country"
        )

        mock_api.set_website_geo_mapping_rules.return_value = {"plain": 1}
        assert await client.set_website_geo_mapping_rules(
            website_id="w1", body="x", api_client=mock_api
        ) == {"plain": 1}

        assert await client.set_website_geo_mapping_rules(
            website_id="", body="x", api_client=mock_api
        ) == {"error": "website_id parameter is required"}

        mock_api.set_website_geo_mapping_rules.side_effect = Exception("fail")
        error = await client.set_website_geo_mapping_rules(
            website_id="w1", body="x", api_client=mock_api
        )
        assert "Failed to set website geo mapping rules" in error["error"]

    # ---------------- source maps ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_upload_source_map_file(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.upload_source_map_file.return_value = _ToDict({"uploaded": True})
        client = create_website_configuration_client(instana_credentials)

        assert await client.upload_source_map_file(
            website_id="w1", source_map_config_id="c1", file_format="js", source_map="m",
            url="http://x/a.js", api_client=mock_api,
        ) == {"uploaded": True}

        mock_api.upload_source_map_file.return_value = None
        assert await client.upload_source_map_file(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        ) == {"success": True, "message": "Upload source map file"}

        assert await client.upload_source_map_file(
            website_id="", source_map_config_id="c1", api_client=mock_api
        ) == {"error": "website_id parameter is required"}
        assert await client.upload_source_map_file(
            website_id="w1", source_map_config_id="", api_client=mock_api
        ) == {"error": "source_map_config_id parameter is required"}

        mock_api.upload_source_map_file.side_effect = Exception("fail")
        error = await client.upload_source_map_file(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        )
        assert "Failed to upload source map file" in error["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_clear_source_map_upload_configuration(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.clear_source_map_upload_configuration.return_value = _ToDict({"cleared": True})
        client = create_website_configuration_client(instana_credentials)

        assert await client.clear_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        ) == {"cleared": True}

        mock_api.clear_source_map_upload_configuration.return_value = {"plain": 1}
        assert await client.clear_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        ) == {"plain": 1}

        assert await client.clear_source_map_upload_configuration(
            website_id="", source_map_config_id="c1", api_client=mock_api
        ) == {"error": "website_id parameter is required"}
        assert await client.clear_source_map_upload_configuration(
            website_id="w1", source_map_config_id="", api_client=mock_api
        ) == {"error": "source_map_config_id parameter is required"}

        mock_api.clear_source_map_upload_configuration.side_effect = Exception("fail")
        error = await client.clear_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        )
        assert "Failed to clear source map upload configuration" in error["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_source_map_upload_configuration_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_source_map_upload_configuration_without_preload_content.return_value = (
            _MockResponse(json.dumps({"id": "c1"}).encode("utf-8"))
        )
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        )

        assert result == {"id": "c1"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_source_map_upload_configuration_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_source_map_upload_configuration_without_preload_content.return_value = (
            _MockResponse(b"nope", status=404)
        )
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        )

        assert result["status_code"] == 404
        assert result["details"] == "nope"
        assert "HTTP 404" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_source_map_upload_configuration_http_error_undecodable(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_source_map_upload_configuration_without_preload_content.return_value = (
            _MockResponse(object(), status=500)
        )
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        )

        assert result == {
            "error": "Failed to get source map configuration: HTTP 500",
            "status_code": 500,
        }

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_source_map_upload_configuration_fallback(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_source_map_upload_configuration_without_preload_content.side_effect = (
            Exception("raw failed")
        )
        mock_api.get_website_source_map_upload_configuration.return_value = _ToDict({"id": "c2"})
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c2", api_client=mock_api
        )
        assert result == {"id": "c2"}

        mock_api.get_website_source_map_upload_configuration.return_value = {"plain": 1}
        result = await client.get_website_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c2", api_client=mock_api
        )
        assert result == {"plain": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_source_map_upload_configuration_both_fail(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website_source_map_upload_configuration_without_preload_content.side_effect = (
            Exception("one")
        )
        mock_api.get_website_source_map_upload_configuration.side_effect = Exception("two")
        client = create_website_configuration_client(instana_credentials)

        result = await client.get_website_source_map_upload_configuration(
            website_id="w1", source_map_config_id="c1", api_client=mock_api
        )

        assert "Failed to get website source map upload configuration" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_source_map_upload_configurations_variants(self, instana_credentials):
        mock_api = MagicMock()
        raw = mock_api.get_website_source_map_upload_configurations_without_preload_content
        raw.return_value = _MockResponse(json.dumps([{"id": "c1"}]).encode("utf-8"))
        client = create_website_configuration_client(instana_credentials)

        assert await client.get_website_source_map_upload_configurations(
            website_id="w1", api_client=mock_api
        ) == [{"id": "c1"}]

        raw.return_value = _MockResponse(b"err", status=500)
        result = await client.get_website_source_map_upload_configurations(
            website_id="w1", api_client=mock_api
        )
        assert result["status_code"] == 500
        assert result["details"] == "err"

        raw.return_value = _MockResponse(object(), status=503)
        result = await client.get_website_source_map_upload_configurations(
            website_id="w1", api_client=mock_api
        )
        assert result == {
            "error": "Failed to get source map configurations: HTTP 503",
            "status_code": 503,
        }

        raw.side_effect = Exception("raw failed")
        mock_api.get_website_source_map_upload_configurations.return_value = _ToDict({"configs": []})
        assert await client.get_website_source_map_upload_configurations(
            website_id="w1", api_client=mock_api
        ) == {"configs": []}

        mock_api.get_website_source_map_upload_configurations.return_value = [{"p": 1}]
        assert await client.get_website_source_map_upload_configurations(
            website_id="w1", api_client=mock_api
        ) == [{"p": 1}]

        mock_api.get_website_source_map_upload_configurations.side_effect = Exception("two")
        error = await client.get_website_source_map_upload_configurations(
            website_id="w1", api_client=mock_api
        )
        assert "Failed to get website source map upload configurations" in error["error"]

    # ---------------- internal helpers (api_client forwarded) ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_internal_create_delete_rename_validation(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.create_website.return_value = {"id": "n"}
        mock_api.rename_website.return_value = {"id": "w1"}
        client = create_website_configuration_client(instana_credentials)

        assert await client._create_website(None, None, api_client=mock_api) == {
            "error": "Website name is required for create operation"
        }
        assert await client._create_website("n", None, api_client=mock_api) == {"id": "n"}
        assert await client._delete_website(None, api_client=mock_api) == {
            "error": "website_id is required for delete operation"
        }
        assert (await client._delete_website("w1", api_client=mock_api))["success"] is True
        assert await client._rename_website(None, "x", api_client=mock_api) == {
            "error": "website_id is required for rename operation"
        }
        assert await client._rename_website("w1", None, api_client=mock_api) == {
            "error": "name is required for rename operation"
        }
        assert await client._rename_website("w1", "x", api_client=mock_api) == {"id": "w1"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_internal_get_website_name_resolution(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_website.return_value = _ToDict({"id": "w2", "name": "Shop"})
        client = create_website_configuration_client(instana_credentials)

        # list of dicts
        mock_api.get_websites.return_value = [{"id": "w1", "name": "other"}, {"id": "w2", "name": "Shop"}]
        result = await client._get_website(None, "shop", api_client=mock_api)
        assert result == {"id": "w2", "name": "Shop"}
        mock_api.get_website.assert_called_with(website_id="w2")

        # list of objects, with an unsupported entry in the mix
        mock_api.get_websites.return_value = [42, _Named("Blog", "w3")]
        result = await client._get_website(None, "BLOG", api_client=mock_api)
        assert result == {"id": "w2", "name": "Shop"}
        mock_api.get_website.assert_called_with(website_id="w3")

        # dict containing 'results'
        mock_api.get_websites.return_value = {"results": [{"id": "w9", "name": "Wiki"}]}
        await client._get_website(None, "wiki", api_client=mock_api)
        mock_api.get_website.assert_called_with(website_id="w9")

        # single dict website
        mock_api.get_websites.return_value = {"id": "w7", "name": "Solo"}
        await client._get_website(None, "solo", api_client=mock_api)
        mock_api.get_website.assert_called_with(website_id="w7")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_internal_get_website_name_resolution_failures(self, instana_credentials):
        mock_api = MagicMock()
        client = create_website_configuration_client(instana_credentials)

        mock_api.get_websites.return_value = [{"id": "w1", "name": "a"}, _Named("b", "w2"), 5]
        assert await client._get_website(None, "missing", api_client=mock_api) == {
            "error": "No website found with name 'missing'"
        }

        # get_websites raises -> returns list of error dicts, which is a list without a match
        mock_api.get_websites.side_effect = Exception("down")
        result = await client._get_website(None, "x", api_client=mock_api)
        assert result == {"error": "No website found with name 'x'"}

        # non-list/non-dict value from get_websites
        mock_api.get_websites.side_effect = None
        mock_api.get_websites.return_value = "weird"
        assert await client._get_website(None, "x", api_client=mock_api) == {
            "error": "Failed to retrieve websites for name resolution"
        }

        assert await client._get_website(None, None, api_client=mock_api) == {
            "error": "website_id or website_name is required for get operation"
        }

    # ---------------- execute_website_operation (router) ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_website_operation_get_all_and_get(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.get_websites.return_value = [{"id": "w1", "name": "shop"}]
        mock_api.get_website.return_value = _ToDict({"id": "w1"})

        assert await client.execute_website_operation(operation="get_all") == [
            {"id": "w1", "name": "shop"}
        ]
        assert await client.execute_website_operation(operation="get", website_id="w1") == {"id": "w1"}
        assert await client.execute_website_operation(operation="get", website_name="SHOP") == {"id": "w1"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_website_operation_create_delete_rename(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.create_website.return_value = {"id": "n"}
        mock_api.rename_website.return_value = {"id": "w1", "name": "new"}

        assert await client.execute_website_operation(operation="create", name="n") == {"id": "n"}
        assert (await client.execute_website_operation(operation="delete", website_id="w1"))[
            "success"
        ] is True
        assert await client.execute_website_operation(
            operation="rename", website_id="w1", name="new"
        ) == {"id": "w1", "name": "new"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_website_operation_invalid_operation(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        attach_stdio_mock_api(client)

        result = await client.execute_website_operation(operation="explode")

        assert result == {"error": "Invalid operation: explode"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_website_operation_exception(self, instana_credentials, monkeypatch):
        client = create_website_configuration_client(instana_credentials)

        async def _boom(*args, **kwargs):
            raise RuntimeError("router failure")

        monkeypatch.setattr(client, "_get_all_websites", _boom)

        result = await client.execute_website_operation(operation="get_all")

        assert "Failed to execute website operation" in result["error"]
        assert "router failure" in result["error"]

    # ---------------- execute_advanced_config_operation (router) ----------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_by_id(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.get_website_geo_location_configuration.return_value = {"geo": 1}
        mock_api.get_website_ip_masking_configuration.return_value = {"ip": 1}
        mock_api.get_website_geo_mapping_rules.return_value = "a,b\n1,2\n"

        assert await client.execute_advanced_config_operation(
            operation="get_geo_config", website_id="w1"
        ) == {"geo": 1}
        assert await client.execute_advanced_config_operation(
            operation="get_ip_masking", website_id="w1"
        ) == {"ip": 1}
        assert await client.execute_advanced_config_operation(
            operation="get_geo_rules", website_id="w1"
        ) == [{"a": "1", "b": "2"}]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_name_resolution(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.get_websites.return_value = [{"id": "w1", "name": "shop"}]
        mock_api.get_website.return_value = _ToDict({"id": "w1", "name": "shop"})
        mock_api.get_website_geo_location_configuration.return_value = {"geo": 1}

        result = await client.execute_advanced_config_operation(
            operation="get_geo_config", website_name="shop"
        )

        assert result == {"geo": 1}
        mock_api.get_website_geo_location_configuration.assert_called_once_with(website_id="w1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_name_not_found(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.get_websites.return_value = [{"id": "w1", "name": "shop"}]

        result = await client.execute_advanced_config_operation(
            operation="get_geo_config", website_name="ghost"
        )

        assert result == {"error": "No website found with name 'ghost'"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_resolved_without_id(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.get_websites.return_value = [{"id": "w1", "name": "shop"}]
        mock_api.get_website.return_value = {"name": "shop"}  # no id key

        result = await client.execute_advanced_config_operation(
            operation="get_geo_config", website_name="shop"
        )

        assert result == {"error": "Could not extract ID for website 'shop'"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_unexpected_resolution_format(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        mock_api = attach_stdio_mock_api(client)
        mock_api.get_websites.return_value = [{"id": "w1", "name": "shop"}]
        mock_api.get_website.return_value = ["not", "a", "dict"]

        result = await client.execute_advanced_config_operation(
            operation="get_geo_config", website_name="shop"
        )

        assert "Unexpected result format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_missing_identifiers(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        attach_stdio_mock_api(client)

        result = await client.execute_advanced_config_operation(operation="get_geo_config")

        assert result == {"error": "Either website_id or website_name must be provided"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_invalid_operation(self, instana_credentials):
        client = create_website_configuration_client(instana_credentials)
        attach_stdio_mock_api(client)

        result = await client.execute_advanced_config_operation(
            operation="bogus", website_id="w1"
        )

        assert "Invalid advanced config operation: bogus" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_advanced_config_exception(self, instana_credentials, monkeypatch):
        client = create_website_configuration_client(instana_credentials)

        async def _boom(*args, **kwargs):
            raise RuntimeError("adv failure")

        monkeypatch.setattr(client, "get_website_geo_location_configuration", _boom)

        result = await client.execute_advanced_config_operation(
            operation="get_geo_config", website_id="w1"
        )

        assert "Failed to execute advanced config operation" in result["error"]
        assert "adv failure" in result["error"]
