"""Mocked e2e tests for the application smart router."""

from unittest.mock import AsyncMock

import pytest

from src.router.application_smart_router_tool import ApplicationSmartRouterMCPTool


@pytest.fixture
def router(instana_credentials):
    tool = ApplicationSmartRouterMCPTool(
        instana_credentials["api_token"], instana_credentials["base_url"]
    )
    tool.app_call_group_client = AsyncMock()
    tool.app_call_group_client.get_grouped_calls_metrics.return_value = {"items": []}
    tool.app_alert_config_client = AsyncMock()
    tool.app_alert_config_client.execute_alert_config_operation.return_value = {
        "configs": []
    }
    tool.app_global_alert_config_client = AsyncMock()
    tool.app_global_alert_config_client.execute_alert_config_operation.return_value = {
        "configs": []
    }
    tool.app_resources_client = AsyncMock()
    tool.app_resources_client.execute_resources_operation.return_value = {"items": []}
    tool.app_resources_client._get_applications_internal.return_value = {"items": []}
    tool.app_settings_client = AsyncMock()
    tool.app_settings_client.execute_settings_operation.return_value = []
    tool.app_catalog_client = AsyncMock()
    tool.app_catalog_client.get_application_tag_catalog.return_value = {"tags": []}
    tool.app_catalog_client.get_application_metric_catalog.return_value = {"metrics": []}
    tool.app_analyze_client = AsyncMock()
    tool.app_analyze_client.execute_analyze_operation.return_value = {"traces": []}
    return tool


class TestApplicationSmartRouterE2E:
    """Dispatch and validation tests for ApplicationSmartRouterMCPTool."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_resource_type_returns_elicitation(self, router):
        result = await router.manage_applications(
            resource_type="bogus", operation="get_all"
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_resource_type"
        assert "bogus" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_none_params_defaults_to_empty_dict(self, router):
        result = await router.manage_applications(
            resource_type="catalog", operation="get_metric_catalog", params=None
        )
        assert result["resource_type"] == "catalog"
        assert result["results"] == {"metrics": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metrics_forwards_parameters(self, router):
        params = {
            "metrics": [{"metric": "calls", "aggregation": "SUM"}],
            "time_frame": {"windowSize": 3600000},
            "group": {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"},
            "include_internal": False,
            "include_synthetic": False,
        }
        result = await router.manage_applications(
            resource_type="metrics", operation="get_grouped_calls_metrics", params=params
        )
        assert result["resource_type"] == "metrics"
        assert result["results"] == {"items": []}
        kwargs = router.app_call_group_client.get_grouped_calls_metrics.call_args.kwargs
        assert kwargs["metrics"] == [{"metric": "calls", "aggregation": "SUM"}]
        assert kwargs["time_frame"] == {"windowSize": 3600000}
        assert kwargs["include_internal"] is False
        assert kwargs["tool_name"] == "manage_applications"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metrics_strips_zero_to_and_converts_datetime(self, router):
        params = {"time_frame": {"to": 0, "windowSize": 3600000}}
        await router.manage_applications(
            resource_type="metrics", operation="get_grouped_calls_metrics", params=params
        )
        kwargs = router.app_call_group_client.get_grouped_calls_metrics.call_args.kwargs
        assert "to" not in kwargs["time_frame"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_metrics_invalid_datetime_returns_elicitation(self, router):
        params = {"time_frame": {"to": "not-a-date", "windowSize": 3600000}}
        result = await router.manage_applications(
            resource_type="metrics", operation="get_grouped_calls_metrics", params=params
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_time_params"
        router.app_call_group_client.get_grouped_calls_metrics.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_invalid_operation(self, router):
        result = await router.manage_applications(
            resource_type="alert_config", operation="explode", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        router.app_alert_config_client.execute_alert_config_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_find_active_forwards_ids_and_page(self, router):
        params = {"application_id": "app-1", "alert_ids": ["a1", "a2"], "page": 2, "page_size": 5}
        result = await router.manage_applications(
            resource_type="alert_config", operation="find_active", params=params
        )
        assert result["resource_type"] == "alert_config"
        assert result["application_id"] == "app-1"
        kwargs = router.app_alert_config_client.execute_alert_config_operation.call_args.kwargs
        assert kwargs["operation"] == "find_active"
        assert kwargs["alert_ids"] == ["a1", "a2"]
        assert kwargs["tool_name"] == "manage_applications"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_page_navigation_rewrites_operation(self, router):
        result = await router.manage_applications(
            resource_type="alert_config",
            operation="page_3",
            params={"application_id": "app-1"},
        )
        assert result["operation"] == "find_active"
        kwargs = router.app_alert_config_client.execute_alert_config_operation.call_args.kwargs
        assert kwargs["operation"] == "find_active"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_resolves_application_name(self, router):
        router.app_resources_client._get_applications_internal.return_value = {
            "items": [{"id": "app-9", "label": "Checkout"}]
        }
        result = await router.manage_applications(
            resource_type="alert_config",
            operation="find_active",
            params={"application_name": "Checkout"},
        )
        assert result["application_id"] == "app-9"
        assert result["application_name"] == "Checkout"
        kwargs = router.app_alert_config_client.execute_alert_config_operation.call_args.kwargs
        assert kwargs["application_id"] == "app-9"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_alert_config_name_resolution_failure_returns_error(self, router):
        router.app_resources_client._get_applications_internal.return_value = {"items": []}
        result = await router.manage_applications(
            resource_type="alert_config",
            operation="find_active",
            params={"application_name": "Missing"},
        )
        assert "Failed to resolve application name 'Missing'" in result["error"]
        router.app_alert_config_client.execute_alert_config_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_global_alert_config_invalid_operation(self, router):
        result = await router.manage_applications(
            resource_type="global_alert_config", operation="update_baseline", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_global_alert_config_create_forwards_payload(self, router):
        payload = {"name": "Global Alert"}
        result = await router.manage_applications(
            resource_type="global_alert_config",
            operation="create",
            params={"application_id": "app-1", "payload": payload},
        )
        assert result["resource_type"] == "global_alert_config"
        kwargs = router.app_global_alert_config_client.execute_alert_config_operation.call_args.kwargs
        assert kwargs["operation"] == "create"
        assert kwargs["payload"] == payload
        assert kwargs["application_id"] == "app-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_global_alert_config_name_resolution_failure(self, router):
        router.app_resources_client._get_applications_internal.return_value = {"items": []}
        result = await router.manage_applications(
            resource_type="global_alert_config",
            operation="find",
            params={"application_name": "Nope", "id": "g-1"},
        )
        assert result["resource_type"] == "global_alert_config"
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_global_alert_config_resolves_application_name(self, router):
        router.app_resources_client._get_applications_internal.return_value = {
            "items": [{"id": "app-7", "label": "Billing"}]
        }
        result = await router.manage_applications(
            resource_type="global_alert_config",
            operation="find_active",
            params={"application_name": "billing"},
        )
        assert result["application_id"] == "app-7"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_invalid_resource_subtype(self, router):
        result = await router.manage_applications(
            resource_type="settings",
            operation="get_all",
            params={"resource_subtype": "database"},
        )
        assert result["elicitation_needed"] is True
        assert "database" in result["reason"]
        router.app_settings_client.execute_settings_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_invalid_operation(self, router):
        result = await router.manage_applications(
            resource_type="settings",
            operation="rename",
            params={"resource_subtype": "application"},
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_all_without_pagination_returns_full_list(self, router):
        router.app_settings_client.execute_settings_operation.return_value = [
            {"id": "1", "label": "A"},
            {"id": "2", "label": "B"},
        ]
        result = await router.manage_applications(
            resource_type="settings",
            operation="get_all",
            params={"resource_subtype": "application"},
        )
        assert len(result["results"]) == 2
        assert "pagination" not in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_all_with_page_size_paginates(self, router):
        router.app_settings_client.execute_settings_operation.return_value = [
            {"id": str(i), "label": f"App {i}"} for i in range(5)
        ]
        result = await router.manage_applications(
            resource_type="settings",
            operation="get_all",
            params={"resource_subtype": "application", "page": 1, "page_size": 2},
        )
        assert len(result["results"]) == 2
        assert "pagination" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_resolves_application_name(self, router):
        router.app_settings_client.execute_settings_operation.side_effect = [
            [{"id": "cfg-1", "label": "Checkout"}],
            {"id": "cfg-1", "label": "Checkout"},
        ]
        result = await router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "checkout"},
        )
        assert result["resolved_id"] == "cfg-1"
        assert result["application_name"] == "checkout"
        get_call = router.app_settings_client.execute_settings_operation.call_args_list[-1]
        assert get_call.kwargs["id"] == "cfg-1"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_get_name_not_found_returns_error(self, router):
        router.app_settings_client.execute_settings_operation.return_value = [
            {"id": "cfg-1", "label": "Other"}
        ]
        result = await router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "Missing"},
        )
        assert "No application perspective found with name 'Missing'" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_name_resolution_non_list_returns_error(self, router):
        router.app_settings_client.execute_settings_operation.return_value = {"error": "x"}
        result = await router.manage_applications(
            resource_type="settings",
            operation="get",
            params={"resource_subtype": "application", "application_name": "Any"},
        )
        assert "Failed to retrieve application perspectives" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_settings_create_forwards_payload(self, router):
        payload = {"label": "New App"}
        result = await router.manage_applications(
            resource_type="settings",
            operation="create",
            params={"resource_subtype": "application", "payload": payload},
        )
        assert result["operation"] == "create"
        kwargs = router.app_settings_client.execute_settings_operation.call_args.kwargs
        assert kwargs["payload"] == payload
        assert kwargs["resource_subtype"] == "application"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_invalid_operation(self, router):
        result = await router.manage_applications(
            resource_type="analyze", operation="get_spans", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        router.app_analyze_client.execute_analyze_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_converts_zero_to_and_forwards(self, router):
        params = {"payload": {"timeFrame": {"to": 0, "windowSize": 3600000}}}
        result = await router.manage_applications(
            resource_type="analyze", operation="get_all_traces", params=params
        )
        assert result["results"] == {"traces": []}
        kwargs = router.app_analyze_client.execute_analyze_operation.call_args.kwargs
        assert "to" not in kwargs["params"]["payload"]["timeFrame"]
        assert kwargs["tool_name"] == "manage_applications"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_invalid_datetime_returns_error(self, router):
        params = {"payload": {"timeFrame": {"to": "garbage"}}}
        result = await router.manage_applications(
            resource_type="analyze", operation="get_trace_groups", params=params
        )
        assert result["resource_type"] == "analyze"
        assert "error" in result
        router.app_analyze_client.execute_analyze_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_trace_details_converts_ingestion_time(self, router):
        params = {"id": "trace-1", "ingestionTime": "19 March 2026, 2:47 PM|UTC"}
        result = await router.manage_applications(
            resource_type="analyze", operation="get_trace_details", params=params
        )
        assert result["operation"] == "get_trace_details"
        kwargs = router.app_analyze_client.execute_analyze_operation.call_args.kwargs
        assert isinstance(kwargs["params"]["ingestionTime"], int)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_invalid_operation(self, router):
        result = await router.manage_applications(
            resource_type="catalog", operation="get_sources", params={}
        )
        assert result["elicitation_needed"] is True
        assert "get_sources" in result["reason"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_tag_catalog_forwards_parameters(self, router):
        params = {"use_case": "GROUPING", "data_source": "CALLS", "var_from": 1710658800000}
        result = await router.manage_applications(
            resource_type="catalog", operation="get_tag_catalog", params=params
        )
        assert result["results"] == {"tags": []}
        kwargs = router.app_catalog_client.get_application_tag_catalog.call_args.kwargs
        assert kwargs["use_case"] == "GROUPING"
        assert kwargs["data_source"] == "CALLS"
        assert kwargs["var_from"] == 1710658800000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resources_invalid_operation(self, router):
        result = await router.manage_applications(
            resource_type="resources", operation="get_endpoints", params={}
        )
        assert result["elicitation_needed"] is True
        assert result["reason"] == "invalid_operation"
        router.app_resources_client.execute_resources_operation.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_resources_forwards_filters(self, router):
        params = {
            "application_id": "app-1",
            "service_id": "svc-2",
            "name_filter": "api",
            "types": ["HTTP"],
            "technologies": ["Java"],
            "include_snapshot_ids": True,
        }
        result = await router.manage_applications(
            resource_type="resources",
            operation="get_application_services",
            params=params,
        )
        assert result["resource_type"] == "resources"
        assert result["results"] == {"items": []}
        kwargs = router.app_resources_client.execute_resources_operation.call_args.kwargs
        assert kwargs["operation"] == "get_application_services"
        assert kwargs["application_id"] == "app-1"
        assert kwargs["service_id"] == "svc-2"
        assert kwargs["types"] == ["HTTP"]
        assert kwargs["include_snapshot_ids"] is True
        assert kwargs["tool_name"] == "manage_applications"
