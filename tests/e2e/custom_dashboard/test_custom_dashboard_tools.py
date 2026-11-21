"""
E2E tests for Custom Dashboard MCP Tools
"""

import importlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest


def create_custom_dashboard_client(instana_credentials):
    """Dynamically import and create Custom Dashboard client"""
    module = importlib.import_module("src.custom_dashboard.custom_dashboard_tools")
    module = importlib.reload(module)
    return module.CustomDashboardMCPTools(
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


DASHBOARD = {"id": "dash-1", "title": "My Dashboard", "widgets": [], "accessRules": []}


def _valid_dashboard():
    return {
        "title": "My Dashboard",
        "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}],
        "widgets": [
            {"id": "w1", "type": "chart", "config": {"metric": "latency"}, "x": 0, "y": 0, "width": 6, "height": 4}
        ],
    }


class TestCustomDashboardE2E:
    """End-to-end tests for Custom Dashboard MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ---------------------------------------------------------------- get_custom_dashboards
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboards_flat_list(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboards_without_preload_content.return_value = _MockResponse([DASHBOARD])
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboards(query="My", api_client=mock_api)

        assert result == {"items": [DASHBOARD], "count": 1}
        mock_api.get_custom_dashboards_without_preload_content.assert_called_once_with(
            query="My", page_size=None, page=None, with_total_hits=None
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboards_paged_with_total_hits(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboards_without_preload_content.return_value = _MockResponse(
            {"items": [DASHBOARD], "totalHits": 25}
        )
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboards(page=2, page_size=10, api_client=mock_api)

        assert result["items"] == [DASHBOARD]
        assert result["total_hits"] == 25
        assert result["page"] == 2
        assert result["page_size"] == 10
        assert result["pagination"]["total_items"] == 25
        assert result["pagination"]["has_more"] is True
        kwargs = mock_api.get_custom_dashboards_without_preload_content.call_args.kwargs
        assert kwargs["with_total_hits"] is True
        assert kwargs["page"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboards_page_size_only_is_clamped(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboards_without_preload_content.return_value = _MockResponse(
            {"items": [], "totalHits": 0}
        )
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboards(page_size=1000, with_total_hits=False, api_client=mock_api)

        assert result["page"] == 1
        assert result["page_size"] == 100
        kwargs = mock_api.get_custom_dashboards_without_preload_content.call_args.kwargs
        assert kwargs["with_total_hits"] is False
        assert kwargs["page_size"] == 100

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboards_api_error(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboards_without_preload_content.return_value = _MockResponse(b"nope", status=403)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboards(api_client=mock_api)

        assert "API error (status 403)" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboards_api_error_no_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboards_without_preload_content.return_value = _MockResponse(b"", status=500)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboards(api_client=mock_api)

        assert "No error details" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboards_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboards_without_preload_content.side_effect = Exception("Boom")
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboards(api_client=mock_api)

        assert "Failed to get custom dashboards" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- get_custom_dashboard
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboard_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboard_without_preload_content.return_value = _MockResponse(DASHBOARD)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)

        assert result == DASHBOARD
        mock_api.get_custom_dashboard_without_preload_content.assert_called_once_with(custom_dashboard_id="dash-1")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboard_missing_id(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboard(dashboard_id="", api_client=MagicMock())

        assert result == {"error": "Dashboard ID is required for this operation"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_custom_dashboard_api_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_custom_dashboard_without_preload_content.return_value = _MockResponse(b"gone", status=404)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)
        assert "API error (status 404)" in result["error"]

        mock_api.get_custom_dashboard_without_preload_content.return_value = _MockResponse(b"", status=500)
        result = await client.get_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)
        assert "No error details" in result["error"]

        mock_api.get_custom_dashboard_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)
        assert "Failed to get custom dashboard" in result["error"]

    # ---------------------------------------------------------------- add_custom_dashboard
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_custom_dashboard_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.add_custom_dashboard_without_preload_content.return_value = _MockResponse(DASHBOARD)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.add_custom_dashboard(custom_dashboard=_valid_dashboard(), api_client=mock_api)

        assert result == DASHBOARD
        sent = mock_api.add_custom_dashboard_without_preload_content.call_args.kwargs["custom_dashboard"]
        assert sent.title == "My Dashboard"
        assert len(sent.widgets) == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_custom_dashboard_applies_defaults(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.add_custom_dashboard_without_preload_content.return_value = _MockResponse(DASHBOARD)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.add_custom_dashboard(custom_dashboard={"title": "Bare"}, api_client=mock_api)

        assert result == DASHBOARD
        sent = mock_api.add_custom_dashboard_without_preload_content.call_args.kwargs["custom_dashboard"]
        assert sent.widgets == []
        assert len(sent.access_rules) == 1
        assert sent.access_rules[0].relation_type == "GLOBAL"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_custom_dashboard_none_payload(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.add_custom_dashboard(custom_dashboard=None, api_client=MagicMock())

        assert result == {"error": "Custom dashboard configuration is required for this operation"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_custom_dashboard_validation_elicitation(self, instana_credentials):
        mock_api = MagicMock()
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.add_custom_dashboard(custom_dashboard={"title": " "}, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert result["reason"].startswith("create custom dashboard has 1")
        mock_api.add_custom_dashboard_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_custom_dashboard_api_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.add_custom_dashboard_without_preload_content.return_value = _MockResponse(b"bad", status=400)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.add_custom_dashboard(custom_dashboard=_valid_dashboard(), api_client=mock_api)
        assert "API error (status 400)" in result["error"]

        mock_api.add_custom_dashboard_without_preload_content.return_value = _MockResponse(b"", status=500)
        result = await client.add_custom_dashboard(custom_dashboard=_valid_dashboard(), api_client=mock_api)
        assert "No error details" in result["error"]

        mock_api.add_custom_dashboard_without_preload_content.side_effect = Exception("Boom")
        result = await client.add_custom_dashboard(custom_dashboard=_valid_dashboard(), api_client=mock_api)
        assert "Failed to add custom dashboard" in result["error"]

    # ---------------------------------------------------------------- update_custom_dashboard
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_custom_dashboard_success_refetches(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_custom_dashboard_without_preload_content.return_value = _MockResponse(b"")
        client = create_custom_dashboard_client(instana_credentials)
        # The re-fetch goes through the auth decorator without the injected mock client,
        # so stub it on this instance only.
        client.get_custom_dashboard = AsyncMock(return_value=DASHBOARD)

        result = await client.update_custom_dashboard(
            dashboard_id="dash-1", custom_dashboard={"title": "Renamed"}, api_client=mock_api
        )

        assert result == DASHBOARD
        kwargs = mock_api.update_custom_dashboard_without_preload_content.call_args.kwargs
        assert kwargs["custom_dashboard_id"] == "dash-1"
        assert kwargs["custom_dashboard"].id == "dash-1"
        assert kwargs["custom_dashboard"].widgets == []
        client.get_custom_dashboard.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_custom_dashboard_missing_params(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        assert await client.update_custom_dashboard(
            dashboard_id="", custom_dashboard={"title": "t"}, api_client=MagicMock()
        ) == {"error": "Dashboard ID is required for this operation"}
        assert await client.update_custom_dashboard(
            dashboard_id="dash-1", custom_dashboard=None, api_client=MagicMock()
        ) == {"error": "Custom dashboard configuration is required for this operation"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_custom_dashboard_validation_elicitation(self, instana_credentials):
        mock_api = MagicMock()
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.update_custom_dashboard(
            dashboard_id="dash-1", custom_dashboard={"title": ""}, api_client=mock_api
        )

        assert result["elicitation_needed"] is True
        assert result["reason"].startswith("update custom dashboard has")
        mock_api.update_custom_dashboard_without_preload_content.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_custom_dashboard_api_error_and_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.update_custom_dashboard_without_preload_content.return_value = _MockResponse(b"bad", status=400)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.update_custom_dashboard(
            dashboard_id="dash-1", custom_dashboard=_valid_dashboard(), api_client=mock_api
        )
        assert "API error (status 400)" in result["error"]

        mock_api.update_custom_dashboard_without_preload_content.return_value = _MockResponse(b"", status=500)
        result = await client.update_custom_dashboard(
            dashboard_id="dash-1", custom_dashboard=_valid_dashboard(), api_client=mock_api
        )
        assert "No error details" in result["error"]

        mock_api.update_custom_dashboard_without_preload_content.side_effect = Exception("Boom")
        result = await client.update_custom_dashboard(
            dashboard_id="dash-1", custom_dashboard=_valid_dashboard(), api_client=mock_api
        )
        assert "Failed to update custom dashboard" in result["error"]

    # ---------------------------------------------------------------- delete_custom_dashboard
    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("body,expected", [
        (b"", {"success": True, "message": "Dashboard dash-1 deleted"}),
        (b"   ", {"success": True, "message": "Dashboard dash-1 deleted"}),
        (b'{"deleted": true}', {"deleted": True}),
    ])
    async def test_delete_custom_dashboard_success(self, instana_credentials, body, expected):
        mock_api = MagicMock()
        mock_api.delete_custom_dashboard_without_preload_content.return_value = _MockResponse(body, status=200)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.delete_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)

        assert result == expected
        mock_api.delete_custom_dashboard_without_preload_content.assert_called_once_with(
            custom_dashboard_id="dash-1"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_custom_dashboard_no_data_attribute(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_custom_dashboard_without_preload_content.return_value = _MockResponse(None, status=204)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.delete_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)

        assert result == {"success": True, "message": "Dashboard dash-1 deleted"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_custom_dashboard_missing_id_error_and_exception(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        assert await client.delete_custom_dashboard(dashboard_id="", api_client=MagicMock()) == {
            "error": "Dashboard ID is required for this operation"
        }

        mock_api = MagicMock()
        mock_api.delete_custom_dashboard_without_preload_content.return_value = _MockResponse(b"nope", status=404)
        result = await client.delete_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)
        assert "API error (status 404)" in result["error"]

        mock_api.delete_custom_dashboard_without_preload_content.return_value = _MockResponse(b"", status=500)
        result = await client.delete_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)
        assert "No error details" in result["error"]

        mock_api.delete_custom_dashboard_without_preload_content.side_effect = Exception("Boom")
        result = await client.delete_custom_dashboard(dashboard_id="dash-1", api_client=mock_api)
        assert "Failed to delete custom dashboard" in result["error"]

    # ---------------------------------------------------------------- shareable users / tokens
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_shareable_users_success_and_limit(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_shareable_users_without_preload_content.return_value = _MockResponse(
            [{"id": f"u{i}"} for i in range(30)]
        )
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_shareable_users(api_client=mock_api)

        assert result["count"] == 20
        assert len(result["items"]) == 20

        mock_api.get_shareable_users_without_preload_content.return_value = _MockResponse([{"id": "u1"}])
        result = await client.get_shareable_users(api_client=mock_api)
        assert result == {"items": [{"id": "u1"}], "count": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_shareable_users_errors(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_shareable_users_without_preload_content.return_value = _MockResponse(b"no", status=403)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_shareable_users(api_client=mock_api)
        assert "API error (status 403)" in result["error"]

        mock_api.get_shareable_users_without_preload_content.return_value = _MockResponse(b"", status=500)
        result = await client.get_shareable_users(api_client=mock_api)
        assert "No error details" in result["error"]

        mock_api.get_shareable_users_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_shareable_users(api_client=mock_api)
        assert "Failed to get shareable users" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_shareable_users_non_list_body(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_shareable_users_without_preload_content.return_value = _MockResponse({"users": []})
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_shareable_users(api_client=mock_api)

        assert result == {"items": {"users": []}, "count": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_shareable_api_tokens_success_and_limit(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_shareable_api_tokens_without_preload_content.return_value = _MockResponse(
            [{"id": f"t{i}"} for i in range(15)]
        )
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_shareable_api_tokens(api_client=mock_api)

        assert result["count"] == 10
        assert len(result["items"]) == 10

        mock_api.get_shareable_api_tokens_without_preload_content.return_value = _MockResponse([{"id": "t1"}])
        result = await client.get_shareable_api_tokens(api_client=mock_api)
        assert result == {"items": [{"id": "t1"}], "count": 1}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_shareable_api_tokens_errors(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_shareable_api_tokens_without_preload_content.return_value = _MockResponse(b"no", status=403)
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.get_shareable_api_tokens(api_client=mock_api)
        assert "API error (status 403)" in result["error"]

        mock_api.get_shareable_api_tokens_without_preload_content.return_value = _MockResponse(b"", status=500)
        result = await client.get_shareable_api_tokens(api_client=mock_api)
        assert "No error details" in result["error"]

        mock_api.get_shareable_api_tokens_without_preload_content.side_effect = Exception("Boom")
        result = await client.get_shareable_api_tokens(api_client=mock_api)
        assert "Failed to get shareable API tokens" in result["error"]

    # ---------------------------------------------------------------- payload validation
    @pytest.mark.mocked
    def test_validate_dashboard_payload_valid(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        assert client._validate_dashboard_payload(_valid_dashboard(), "create") is None
        assert client._validate_dashboard_payload({"title": "Only title"}, "update") is None

    @pytest.mark.mocked
    def test_validate_dashboard_payload_access_rule_problems(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        result = client._validate_dashboard_payload({"title": "t", "accessRules": []}, "create")
        assert "must be a non-empty list" in result["api_error"][0]

        result = client._validate_dashboard_payload({"title": "t", "accessRules": "all"}, "create")
        assert "must be a non-empty list" in result["api_error"][0]

        result = client._validate_dashboard_payload({"title": "t", "accessRules": ["x"]}, "create")
        assert "accessRules[0]' must be an object" in result["api_error"][0]

        result = client._validate_dashboard_payload({"title": "t", "accessRules": [{}]}, "create")
        assert len(result["api_error"]) == 2
        assert "accessType' is required" in result["api_error"][0]
        assert "relationType' is required" in result["api_error"][1]

        result = client._validate_dashboard_payload(
            {"title": "t", "accessRules": [{"accessType": "WRITE", "relationType": "EVERYONE"}]}, "create"
        )
        assert "accessType' is invalid" in result["api_error"][0]
        assert "relationType' is invalid" in result["api_error"][1]

        too_many = [{"accessType": "READ", "relationType": "GLOBAL"}] * 65
        result = client._validate_dashboard_payload({"title": "t", "accessRules": too_many}, "create")
        assert "exceeds maximum of 64" in result["api_error"][0]

    @pytest.mark.mocked
    def test_validate_dashboard_payload_widget_problems(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        result = client._validate_dashboard_payload({"title": "t", "widgets": "w"}, "create")
        assert "'widgets' must be a list" in result["api_error"][0]

        result = client._validate_dashboard_payload({"title": "t", "widgets": ["w"]}, "create")
        assert "widgets[0]' must be an object" in result["api_error"][0]

        result = client._validate_dashboard_payload({"title": "t", "widgets": [{}]}, "create")
        errors = result["api_error"]
        assert any("id' is required" in e for e in errors)
        assert any("type' is required" in e for e in errors)
        assert any("config' is required" in e for e in errors)

        result = client._validate_dashboard_payload(
            {"title": "t", "widgets": [{"id": "x" * 65, "type": "chart", "config": "bad"}]}, "create"
        )
        assert any("exceeds max length" in e for e in result["api_error"])
        assert any("config' must be an object" in e for e in result["api_error"])

        result = client._validate_dashboard_payload(
            {
                "title": "t",
                "widgets": [
                    {"id": "w", "type": "c", "config": {}, "width": 13, "x": 12, "y": -1, "height": 0}
                ],
            },
            "create",
        )
        errors = result["api_error"]
        assert any("width' must be an integer 1-12" in e for e in errors)
        assert any(".x' must be an integer 0-11" in e for e in errors)
        assert any(".y' must be a non-negative integer" in e for e in errors)
        assert any("height' must be an integer" in e for e in errors)

        too_many = [{"id": str(i), "type": "c", "config": {}} for i in range(129)]
        result = client._validate_dashboard_payload({"title": "t", "widgets": too_many}, "create")
        assert "exceeds maximum of 128" in result["api_error"][0]

    # ---------------------------------------------------------------- execute_dashboard_operation
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_operation_invalid_operation(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.execute_dashboard_operation("explode")

        assert result["elicitation_needed"] is True
        assert "explode" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,params,expected_fragments", [
        ("get", {}, ["dashboard_id is required"]),
        ("delete", {}, ["dashboard_id is required"]),
        ("update", {}, ["dashboard_id is required", "custom_dashboard: required"]),
        ("create", {}, ["custom_dashboard: required"]),
    ])
    async def test_execute_operation_preflight_missing_params(
        self, instana_credentials, operation, params, expected_fragments
    ):
        client = create_custom_dashboard_client(instana_credentials)

        result = await client.execute_dashboard_operation(operation, params)

        assert result["elicitation_needed"] is True
        for fragment in expected_fragments:
            assert any(fragment in e for e in result["api_error"])

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("operation,params,method,expected_kwargs", [
        ("get_all", {"query": "q", "page_size": 5, "page": 2, "with_total_hits": True}, "get_custom_dashboards",
         {"query": "q", "page_size": 5, "page": 2, "with_total_hits": True}),
        ("get", {"dashboard_id": "d1"}, "get_custom_dashboard", {"dashboard_id": "d1"}),
        ("create", {"custom_dashboard": {"title": "t"}}, "add_custom_dashboard",
         {"custom_dashboard": {"title": "t"}}),
        ("update", {"dashboard_id": "d1", "custom_dashboard": {"title": "t"}}, "update_custom_dashboard",
         {"dashboard_id": "d1", "custom_dashboard": {"title": "t"}}),
        ("delete", {"dashboard_id": "d1"}, "delete_custom_dashboard", {"dashboard_id": "d1"}),
        ("get_shareable_users", {}, "get_shareable_users", {}),
        ("get_shareable_api_tokens", {}, "get_shareable_api_tokens", {}),
    ])
    async def test_execute_operation_dispatch(
        self, instana_credentials, operation, params, method, expected_kwargs
    ):
        client = create_custom_dashboard_client(instana_credentials)
        handler = AsyncMock(return_value={"ok": operation})
        setattr(client, method, handler)

        result = await client.execute_dashboard_operation(
            operation, params, ctx="ctx", resource_type="custom_dashboard", tool_name="manage_dashboards"
        )

        assert result == {"ok": operation}
        handler.assert_awaited_once()
        kwargs = handler.await_args.kwargs
        for key, value in expected_kwargs.items():
            assert kwargs[key] == value
        assert kwargs["ctx"] == "ctx"
        assert kwargs["resource_type"] == "custom_dashboard"
        assert kwargs["tool_name"] == "manage_dashboards"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_execute_operation_handler_exception(self, instana_credentials):
        client = create_custom_dashboard_client(instana_credentials)
        client.get_shareable_users = AsyncMock(side_effect=Exception("Boom"))

        result = await client.execute_dashboard_operation("get_shareable_users")

        assert "Error executing get_shareable_users" in result["error"]
        assert "Boom" in result["error"]
