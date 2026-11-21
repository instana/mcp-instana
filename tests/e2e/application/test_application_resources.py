"""
E2E tests for Application Resources MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock

import pytest


def create_application_resources_client(instana_credentials):
    """Dynamically import and create Application Resources client"""
    module = importlib.import_module("src.application.application_resources")
    module = importlib.reload(module)
    return module.ApplicationResourcesMCPTools(
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


class TestApplicationResourcesE2E:
    """End-to-end tests for Application Resources MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_application_resources_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ------------------------------------------------------------------
    # get_applications
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_success_adds_links(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_applications_without_preload_content.return_value = _json_response(
            {"items": [{"id": "app-1", "label": "My App"}, "not-a-dict", {"label": "no-id"}]}
        )
        client = create_application_resources_client(instana_credentials)

        result = await client.get_applications(
            name_filter="My", application_boundary_scope="ALL", api_client=mock_api
        )

        assert result["items"][0]["link"].startswith("[My App](")
        assert "app-1" in result["items"][0]["link"]
        assert "link" not in result["items"][2]
        mock_api.get_applications_without_preload_content.assert_called_once_with(
            name_filter="My", application_boundary_scope="ALL"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_list_payload_is_returned(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_applications_without_preload_content.return_value = _json_response([1, 2])
        client = create_application_resources_client(instana_credentials)

        result = await client.get_applications(api_client=mock_api)

        assert result == [1, 2]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_applications_without_preload_content.side_effect = Exception("API Error")
        client = create_application_resources_client(instana_credentials)

        result = await client.get_applications(api_client=mock_api)

        assert "Failed to get applications" in result["error"]
        assert "API Error" in result["error"]

    # ------------------------------------------------------------------
    # _get_applications_internal
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_internal_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_applications_without_preload_content.return_value = _json_response(
            {"items": [{"id": "a", "label": "A"}]}
        )
        client = create_application_resources_client(instana_credentials)

        result = await client._get_applications_internal(
            name_filter="A",
            window_size=1000,
            to_time=2000,
            page=1,
            page_size=5,
            application_boundary_scope="INBOUND",
            api_client=mock_api,
        )

        assert result == {"items": [{"id": "a", "label": "A"}]}
        mock_api.get_applications_without_preload_content.assert_called_once_with(
            name_filter="A",
            window_size=1000,
            to=2000,
            page=1,
            page_size=5,
            application_boundary_scope="INBOUND",
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_applications_internal_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_applications_without_preload_content.side_effect = Exception("API Error")
        client = create_application_resources_client(instana_credentials)

        result = await client._get_applications_internal(api_client=mock_api)

        assert "Failed to get applications" in result["error"]

    # ------------------------------------------------------------------
    # get_services
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services_success_sanitizes_and_links(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_services_without_preload_content.return_value = _json_response(
            {
                "items": [
                    {"id": "svc-1", "label": "Svc", "technologies": None},
                    {"id": "svc-2", "label": "Svc2", "technologies": ["java"]},
                    "not-a-dict",
                ]
            }
        )
        client = create_application_resources_client(instana_credentials)

        result = await client.get_services(
            name_filter="Svc", include_snapshot_ids=True, api_client=mock_api
        )

        assert result["items"][0]["technologies"] == []
        assert result["items"][1]["technologies"] == ["java"]
        assert "link" in result["items"][0]
        mock_api.get_services_without_preload_content.assert_called_once_with(
            name_filter="Svc", include_snapshot_ids=True
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_services_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_services_without_preload_content.side_effect = Exception("API Error")
        client = create_application_resources_client(instana_credentials)

        result = await client.get_services(api_client=mock_api)

        assert "Failed to get services" in result["error"]

    # ------------------------------------------------------------------
    # get_application_services
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_services_without_preload_content.return_value = _json_response(
            {"items": [{"id": "svc-1", "label": "Svc", "technologies": None}, "not-a-dict"]}
        )
        client = create_application_resources_client(instana_credentials)

        result = await client.get_application_services(
            application_id="app-1",
            name_filter="Svc",
            application_boundary_scope="INBOUND",
            include_snapshot_ids=False,
            api_client=mock_api,
        )

        assert result["items"][0]["technologies"] == []
        assert "link" in result["items"][0]
        mock_api.get_application_services_without_preload_content.assert_called_once_with(
            application_id="app-1",
            service_id="",
            name_filter="Svc",
            application_boundary_scope="INBOUND",
            include_snapshot_ids=False,
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_null_items(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_services_without_preload_content.return_value = _json_response(
            {"items": None}
        )
        client = create_application_resources_client(instana_credentials)

        result = await client.get_application_services(
            application_id="app-1", service_id="svc-1", api_client=mock_api
        )

        assert result == {"items": None}
        call_kwargs = mock_api.get_application_services_without_preload_content.call_args.kwargs
        assert call_kwargs["service_id"] == "svc-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_services_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_services_without_preload_content.side_effect = Exception("API Error")
        client = create_application_resources_client(instana_credentials)

        result = await client.get_application_services(application_id="app-1", api_client=mock_api)

        assert "Failed to get application services" in result["error"]

    @pytest.mark.mocked
    def test_sanitize_items_technologies_edge_cases(self, instana_credentials):
        client = create_application_resources_client(instana_credentials)

        # None of these should raise
        client._sanitize_items_technologies([])
        client._sanitize_items_technologies({"other": 1})
        client._sanitize_items_technologies({"items": "not-a-list"})

        data = {"items": [{"technologies": None}, {"technologies": ["x"]}, "str", {"id": "no-tech"}]}
        client._sanitize_items_technologies(data)
        assert data["items"][0]["technologies"] == []
        assert data["items"][1]["technologies"] == ["x"]
        # a missing 'technologies' key is treated like None and normalised to []
        assert data["items"][3]["technologies"] == []

    # ------------------------------------------------------------------
    # get_application_endpoints
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_endpoints_defaults_empty_ids(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_endpoints_without_preload_content.return_value = _json_response(
            {"items": [{"id": "ep-1"}]}
        )
        client = create_application_resources_client(instana_credentials)

        result = await client.get_application_endpoints(api_client=mock_api)

        assert result == {"items": [{"id": "ep-1"}]}
        mock_api.get_application_endpoints_without_preload_content.assert_called_once_with(
            application_id="",
            service_id="",
            endpoint_id="",
            name_filter=None,
            types=None,
            technologies=None,
            application_boundary_scope=None,
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_endpoints_with_filters(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_endpoints_without_preload_content.return_value = _json_response({"items": []})
        client = create_application_resources_client(instana_credentials)

        await client.get_application_endpoints(
            application_id="a",
            service_id="s",
            endpoint_id="e",
            name_filter="/api",
            types=["HTTP"],
            technologies=["java"],
            application_boundary_scope="ALL",
            api_client=mock_api,
        )

        mock_api.get_application_endpoints_without_preload_content.assert_called_once_with(
            application_id="a",
            service_id="s",
            endpoint_id="e",
            name_filter="/api",
            types=["HTTP"],
            technologies=["java"],
            application_boundary_scope="ALL",
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_endpoints_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_application_endpoints_without_preload_content.side_effect = Exception("API Error")
        client = create_application_resources_client(instana_credentials)

        result = await client.get_application_endpoints(api_client=mock_api)

        assert "Failed to get application endpoints" in result["error"]

    # ------------------------------------------------------------------
    # execute_resources_operation dispatcher
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_invalid_boundary_scope(self, instana_credentials):
        client = create_application_resources_client(instana_credentials)

        result = await client.execute_resources_operation(
            operation="get_applications", application_boundary_scope="BOGUS"
        )

        assert result["elicitation_needed"] is True
        assert "BOGUS" in result["reason"]
        assert "BOGUS" in result["api_error"][0]
        assert "['ALL', 'DEFAULT', 'INBOUND']" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_unsupported_operation(self, instana_credentials):
        client = create_application_resources_client(instana_credentials)

        result = await client.execute_resources_operation(operation="nope")

        assert result == {"error": "Operation 'nope' not supported"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize(
        ("operation", "kwargs", "target", "expected"),
        [
            (
                "get_applications",
                {"name_filter": "n", "application_boundary_scope": "ALL"},
                "get_applications",
                {"name_filter": "n", "application_boundary_scope": "ALL"},
            ),
            (
                "get_services",
                {"name_filter": "n", "include_snapshot_ids": True},
                "get_services",
                {"name_filter": "n", "include_snapshot_ids": True},
            ),
            (
                "get_application_services",
                {
                    "application_id": "a",
                    "service_id": "s",
                    "name_filter": "n",
                    "application_boundary_scope": "INBOUND",
                    "include_snapshot_ids": False,
                },
                "get_application_services",
                {
                    "application_id": "a",
                    "service_id": "s",
                    "name_filter": "n",
                    "application_boundary_scope": "INBOUND",
                    "include_snapshot_ids": False,
                },
            ),
            (
                "get_application_endpoints",
                {
                    "application_id": "a",
                    "service_id": "s",
                    "endpoint_id": "e",
                    "name_filter": "n",
                    "types": ["HTTP"],
                    "technologies": ["java"],
                    "application_boundary_scope": "DEFAULT",
                },
                "get_application_endpoints",
                {
                    "application_id": "a",
                    "service_id": "s",
                    "endpoint_id": "e",
                    "name_filter": "n",
                    "types": ["HTTP"],
                    "technologies": ["java"],
                    "application_boundary_scope": "DEFAULT",
                },
            ),
        ],
    )
    async def test_execute_dispatches_operations(
        self, instana_credentials, operation, kwargs, target, expected
    ):
        from unittest.mock import AsyncMock

        client = create_application_resources_client(instana_credentials)
        handler = AsyncMock(return_value={"ok": operation})
        setattr(client, target, handler)

        result = await client.execute_resources_operation(
            operation=operation, resource_type="resources", tool_name="manage_applications", **kwargs
        )

        assert result == {"ok": operation}
        handler.assert_awaited_once_with(
            ctx=None, resource_type="resources", tool_name="manage_applications", **expected
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_wraps_handler_exception(self, instana_credentials):
        from unittest.mock import AsyncMock

        client = create_application_resources_client(instana_credentials)
        client.get_services = AsyncMock(side_effect=Exception("kaboom"))

        result = await client.execute_resources_operation(operation="get_services")

        assert result["error"] == "Error executing get_services: kaboom"
