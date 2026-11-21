"""Mocked e2e tests for the releases smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.releases_smart_router_tool import ReleasesSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = ReleasesSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.releases_client = AsyncMock()
    tool.releases_client.get_all_releases.return_value = {"items": []}
    tool.releases_client.get_release.return_value = {"id": "rel-1"}
    tool.releases_client.create_release.return_value = {"id": "rel-new"}
    tool.releases_client.update_release.return_value = {"id": "rel-1"}
    tool.releases_client.delete_release.return_value = {"deleted": True}
    return tool


class TestReleasesSmartRouterE2E:
    """Dispatch and validation tests for ReleasesSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_operation_returns_elicitation(self, router):
        result = await router.manage_releases(operation="bogus")
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        router.releases_client.get_all_releases.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_converts_time_and_forwards(self, router):
        result = await router.manage_releases(
            operation="get_all_releases",
            params={
                "from_time": 1742369820000,
                "to_time": 1742373420000,
                "name_filter": "frontend",
                "page_size": 10,
            },
        )
        assert result == {"operation": "get_all_releases", "results": {"items": []}}
        kwargs = router.releases_client.get_all_releases.call_args.kwargs
        assert kwargs["from_time"] == 1742369820000
        assert kwargs["to_time"] == 1742373420000
        assert kwargs["name_filter"] == "frontend"
        assert kwargs["page_size"] == 10
        assert kwargs["tool_name"] == "manage_releases"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_alias_maps_to_page_number(self, router):
        await router.manage_releases(
            operation="get_all_releases", params={"page": 3}
        )
        kwargs = router.releases_client.get_all_releases.call_args.kwargs
        assert kwargs["page_number"] == 3

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_page_navigation_reruns_get_all_releases(self, router):
        await router.manage_releases(
            operation="page_2", params={"name_filter": "api"}
        )
        kwargs = router.releases_client.get_all_releases.call_args.kwargs
        assert kwargs["page_number"] == 2
        assert kwargs["name_filter"] == "api"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_time_params_returns_elicitation(self, router):
        result = await router.manage_releases(
            operation="get_all_releases",
            params={"from_time": "not a real date", "to_time": 1742373420000},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"
        router.releases_client.get_all_releases.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_release_requires_release_id(self, router):
        result = await router.manage_releases(operation="get_release", params={})
        assert result["elicitation_needed"] is True
        assert result["reason"] == "missing_required_params"
        router.releases_client.get_release.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_release_forwards_id(self, router):
        result = await router.manage_releases(
            operation="get_release", params={"release_id": "rel-1"}
        )
        assert result["results"] == {"id": "rel-1"}
        router.releases_client.get_release.assert_awaited_once()
        assert router.releases_client.get_release.call_args.kwargs["release_id"] == "rel-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_release_missing_fields_lists_all_errors(self, router):
        result = await router.manage_releases(operation="create_release", params={})
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["name", "start"]
        router.releases_client.create_release.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_release_converts_start_and_forwards(self, router):
        result = await router.manage_releases(
            operation="create_release",
            params={
                "name": "frontend/release-2000",
                "start": 1742369820000,
                "applications": [{"name": "My App"}],
            },
        )
        assert result["results"] == {"id": "rel-new"}
        kwargs = router.releases_client.create_release.call_args.kwargs
        assert kwargs["name"] == "frontend/release-2000"
        assert kwargs["start"] == 1742369820000
        assert kwargs["applications"] == [{"name": "My App"}]
        assert kwargs["services"] is None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_create_release_invalid_start_returns_elicitation(self, router):
        result = await router.manage_releases(
            operation="create_release",
            params={"name": "r", "start": "not a real date"},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"
        router.releases_client.create_release.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_release_missing_fields_lists_all_errors(self, router):
        result = await router.manage_releases(operation="update_release", params={})
        assert result["elicitation_needed"] is True
        fields = [e["field"] for e in result["api_error"]]
        assert fields == ["release_id", "name", "start"]
        router.releases_client.update_release.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_update_release_forwards_converted_start(self, router):
        result = await router.manage_releases(
            operation="update_release",
            params={"release_id": "rel-1", "name": "r-2", "start": 1742349976000},
        )
        assert result["operation"] == "update_release"
        kwargs = router.releases_client.update_release.call_args.kwargs
        assert kwargs["release_id"] == "rel-1"
        assert kwargs["start"] == 1742349976000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_release_requires_release_id(self, router):
        result = await router.manage_releases(operation="delete_release", params={})
        assert result["reason"] == "missing_required_params"
        router.releases_client.delete_release.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_release_forwards_id(self, router):
        result = await router.manage_releases(
            operation="delete_release", params={"release_id": "rel-1"}
        )
        assert result["results"] == {"deleted": True}
        assert router.releases_client.delete_release.call_args.kwargs["release_id"] == "rel-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_exception_is_wrapped_as_error(self, router):
        router.releases_client.get_release.side_effect = RuntimeError("boom")
        result = await router.manage_releases(
            operation="get_release", params={"release_id": "rel-1"}
        )
        assert "boom" in result["error"]
        assert result["operation"] == "get_release"
