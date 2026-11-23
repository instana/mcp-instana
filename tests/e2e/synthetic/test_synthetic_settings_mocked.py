"""
Mocked E2E tests for Synthetic Settings MCP Tools (no real Instana API required)
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_synthetic_settings_client(instana_credentials):
    """Dynamically import and create Synthetic Settings client"""
    module = importlib.import_module("src.synthetic.synthetic_settings")
    module = importlib.reload(module)
    return module.SyntheticSettingsMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class _MockResponse:
    def __init__(self, payload, status=200, headers=None):
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        self.data = payload
        self.status = status
        self.headers = headers or {"Content-Type": "application/json"}


TESTS = [
    {"id": "t-b", "label": "Beta Test", "description": "b"},
    {"id": "t-a", "label": "Alpha Test", "description": "a"},
    {"id": "t-c", "label": "Gamma Test", "description": "c"},
]

LOCATIONS = [
    {"id": "loc1", "label": "aws-ap-south-1-Mumbai", "displayLabel": "ap-south-1(Mumbai)",
     "locationType": "Managed", "status": "Online"},
    {"id": "loc2", "label": "aws-us-east-1-Virginia", "displayLabel": "us-east-1(Virginia)",
     "locationType": "Managed", "status": "Offline"},
    {"id": "loc3", "label": "private-pop", "displayLabel": "My PoP",
     "locationType": "Private", "status": "Online"},
]


class TestSyntheticSettingsE2E:
    """End-to-end (mocked) tests for Synthetic Settings MCP Tools"""

    # ------------------------------------------------------------------
    # get_synthetic_test
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_by_id(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_test_without_preload_content.return_value = _MockResponse(
            {"id": "t-a", "label": "Alpha Test", "description": "a"}
        )
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_id="t-a", api_client=mock_api)

        assert result["id"] == "t-a"
        assert result["label"] == "Alpha Test"
        assert "link" in result
        mock_api.get_synthetic_test_without_preload_content.assert_called_once_with(id="t-a")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_non_dict_response_returned_as_is(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_test_without_preload_content.return_value = _MockResponse(b'["x"]')
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_id="t-a", api_client=mock_api)

        assert result == ["x"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_by_name_case_insensitive(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(TESTS)
        mock_api.get_synthetic_test_without_preload_content.return_value = _MockResponse(
            {"id": "t-a", "label": "Alpha Test"}
        )
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_name="alpha TEST", api_client=mock_api)

        assert result["id"] == "t-a"
        mock_api.get_synthetic_test_without_preload_content.assert_called_once_with(id="t-a")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_requires_id_or_name(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(api_client=mock_api)

        assert result == {"error": "Either test_id or test_name is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_name_not_found(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(TESTS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_name="nope", api_client=mock_api)

        assert "No synthetic test found with name 'nope'" in result["error"]
        assert "Alpha Test" in result["available_test_names"]
        mock_api.get_synthetic_test_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_name_resolution_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(b"denied", status=403)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_name="Alpha Test", api_client=mock_api)

        assert "name resolution: HTTP 403" in result["error"]
        assert result["details"] == "denied"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_test_without_preload_content.return_value = _MockResponse(b"missing", status=404)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_id="zzz", api_client=mock_api)

        assert "HTTP 404" in result["error"]
        assert result["test_id"] == "zzz"
        assert result["details"] == "missing"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_test_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_test_without_preload_content.side_effect = Exception("API Error")
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_test(test_id="t-a", api_client=mock_api)

        assert "Failed to get synthetic test" in result["error"]
        assert "API Error" in result["error"]

    # ------------------------------------------------------------------
    # get_synthetic_tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_all(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(TESTS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(api_client=mock_api)

        assert result["count"] == 3
        assert all("link" in t for t in result["items"])
        assert "pagination" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_filter_is_normalized_and_params_forwarded(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(TESTS[:1])
        client = create_synthetic_settings_client(instana_credentials)

        await client.get_synthetic_tests(
            application_id="app1", location_id="loc1", credential_name="cred", sort="+label",
            offset=0, limit=10, filter_param="label=Alpha", api_client=mock_api,
        )

        mock_api.get_synthetic_tests_without_preload_content.assert_called_once_with(
            application_id="app1", location_id="loc1", credential_name="cred", sort="+label",
            offset=0, limit=10, filter="{label=Alpha}",
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_filter_already_braced_untouched(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse([])
        client = create_synthetic_settings_client(instana_credentials)

        await client.get_synthetic_tests(filter_param="{label=X}", api_client=mock_api)

        assert mock_api.get_synthetic_tests_without_preload_content.call_args.kwargs["filter"] == "{label=X}"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_client_side_paging(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(TESTS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(page=1, page_size=2, api_client=mock_api)

        assert result["count"] == 2
        assert result["total"] == 3
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 2
        assert result["pagination"]["has_more"] is True
        # no explicit sort => stable sort applied by the paginator, so order is deterministic
        assert [t["id"] for t in result["items"]] == ["t-a", "t-b"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_client_side_paging_with_explicit_sort_keeps_api_order(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(TESTS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(sort="+label", page=1, page_size=3, api_client=mock_api)

        assert [t["id"] for t in result["items"]] == ["t-b", "t-a", "t-c"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_paging_conflicts_with_offset_limit(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(page=1, limit=5, api_client=mock_api)

        assert "cannot be combined" in result["error"]
        mock_api.get_synthetic_tests_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse(b"err", status=500)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(api_client=mock_api)

        assert "HTTP 500" in result["error"]
        assert result["status_code"] == 500

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.side_effect = Exception("API Error")
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(api_client=mock_api)

        assert "Failed to list synthetic tests" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_synthetic_tests_non_list_response(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_tests_without_preload_content.return_value = _MockResponse({"a": 1})
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_synthetic_tests(api_client=mock_api)

        assert result["items"] == {"a": 1}

    # ------------------------------------------------------------------
    # get_locations
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_locations_no_filters_forwards_paging(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_locations(sort="+label", offset=1, limit=5, filter="x", api_client=mock_api)

        assert result["count"] == 3
        assert result["filters_applied"] == {"location_type": None, "status": None}
        mock_api.get_synthetic_locations_without_preload_content.assert_called_once_with(
            sort="+label", offset=1, limit=5, filter="x"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_locations_post_fetch_filters_drop_paging(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_locations(
            location_type="managed", status="ONLINE", offset=1, limit=5, api_client=mock_api
        )

        assert [loc["id"] for loc in result["items"]] == ["loc1"]
        assert result["filters_applied"] == {"location_type": "managed", "status": "ONLINE"}
        kwargs = mock_api.get_synthetic_locations_without_preload_content.call_args.kwargs
        assert kwargs["offset"] is None
        assert kwargs["limit"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_locations_filter_private_only(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_locations(location_type="Private", api_client=mock_api)

        assert [loc["id"] for loc in result["items"]] == ["loc3"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_locations_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_settings_client(instana_credentials)

        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(b"err", status=502)
        err = await client.get_locations(api_client=mock_api)
        assert "HTTP 502" in err["error"]

        mock_api.get_synthetic_locations_without_preload_content.side_effect = Exception("API Error")
        exc = await client.get_locations(api_client=mock_api)
        assert "Failed to list synthetic locations" in exc["error"]

    # ------------------------------------------------------------------
    # get_location_by_id
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_location_by_id_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_location_without_preload_content.return_value = _MockResponse(LOCATIONS[0])
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_location_by_id(location_id="loc1", api_client=mock_api)

        assert result["id"] == "loc1"
        mock_api.get_synthetic_location_without_preload_content.assert_called_once_with(id="loc1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("name", ["aws-ap-south-1-Mumbai", "AP-SOUTH-1(MUMBAI)"])
    async def test_get_location_by_name_matches_label_or_display_label(self, instana_credentials, name):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        mock_api.get_synthetic_location_without_preload_content.return_value = _MockResponse(LOCATIONS[0])
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_location_by_id(location_name=name, api_client=mock_api)

        assert result["id"] == "loc1"
        mock_api.get_synthetic_location_without_preload_content.assert_called_once_with(id="loc1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_location_requires_id_or_name(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_location_by_id(api_client=mock_api)

        assert result == {"error": "Either location_id or location_name is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_location_name_not_found(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_location_by_id(location_name="Atlantis", api_client=mock_api)

        assert "No synthetic location found with name 'Atlantis'" in result["error"]
        available = result["available_location_names"]
        assert {"id": "loc1", "label": "aws-ap-south-1-Mumbai", "displayLabel": "ap-south-1(Mumbai)"} in available
        mock_api.get_synthetic_location_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_location_name_resolution_http_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(b"err", status=500)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_location_by_id(location_name="x", api_client=mock_api)

        assert "HTTP 500" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_location_by_id_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_settings_client(instana_credentials)

        mock_api.get_synthetic_location_without_preload_content.return_value = _MockResponse(b"nf", status=404)
        err = await client.get_location_by_id(location_id="zzz", api_client=mock_api)
        assert "HTTP 404" in err["error"]
        assert err["location_id"] == "zzz"
        assert err["details"] == "nf"

        mock_api.get_synthetic_location_without_preload_content.side_effect = Exception("API Error")
        exc = await client.get_location_by_id(location_id="zzz", api_client=mock_api)
        assert "Failed to get synthetic location" in exc["error"]

    # ------------------------------------------------------------------
    # get_all_datacenters
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_datacenters_returns_only_managed(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_all_datacenters(api_client=mock_api)

        assert [dc["id"] for dc in result["items"]] == ["loc1", "loc2"]
        assert result["count"] == 2
        assert result["total_online"] == 1
        assert result["filters_applied"] == {"location_type": "Managed", "status": None}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_datacenters_status_filter_keeps_fleet_total_online(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(LOCATIONS)
        client = create_synthetic_settings_client(instana_credentials)

        result = await client.get_all_datacenters(status="Offline", api_client=mock_api)

        assert [dc["id"] for dc in result["items"]] == ["loc2"]
        assert result["total_online"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_datacenters_http_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        client = create_synthetic_settings_client(instana_credentials)

        mock_api.get_synthetic_locations_without_preload_content.return_value = _MockResponse(b"err", status=500)
        err = await client.get_all_datacenters(api_client=mock_api)
        assert "HTTP 500" in err["error"]

        mock_api.get_synthetic_locations_without_preload_content.side_effect = Exception("API Error")
        exc = await client.get_all_datacenters(api_client=mock_api)
        assert "Failed to get datacenter locations" in exc["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_synthetic_settings_client(instana_credentials)

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
