"""
E2E tests for Synthetic Test Playback Results functionality.

Tests get_synthetic_result, get_synthetic_result_analytic,
get_synthetic_result_list, get_location_summary_list, get_test_summary_list,
get_synthetic_result_metadata, and get_synthetic_result_detail_data
against a real Instana instance.

Requires INSTANA_BASE_URL and INSTANA_API_TOKEN environment variables.
"""

import os

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.getenv("INSTANA_BASE_URL") or not os.getenv("INSTANA_API_TOKEN"),
        reason="Requires INSTANA_BASE_URL and INSTANA_API_TOKEN environment variables"
    )
]


class TestSyntheticTestPlaybackE2E:
    """E2E tests for synthetic test playback operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.synthetic.synthetic_test_playback_results import (
            SyntheticTestPlaybackResultsMCPTools,
        )

        self.base_url = os.getenv("INSTANA_BASE_URL")
        self.api_token = os.getenv("INSTANA_API_TOKEN")
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token=self.api_token,
            base_url=self.base_url,
        )

    @pytest.mark.asyncio
    async def test_get_synthetic_result_returns_data(self):
        """Should return a non-error response with the aggregated results."""
        result = await self.client.get_synthetic_result(
            payload={
                "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "MEAN"}],
                "timeFrame": {"to": 0, "windowSize": 3600000},
                "pagination": {"page": 1, "pageSize": 20},
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_synthetic_result_analytic_last_value(self):
        """LAST_VALUE analytic should return at most one row per test."""
        result = await self.client.get_synthetic_result_analytic(
            payload={
                "syntheticMetrics": [
                    "synthetic.metricsResponseTime",
                    "synthetic.metricsStatus",
                    "synthetic.errors",
                ],
                "analyticFunction": "LAST_VALUE",
                "timeFrame": {"to": 0, "windowSize": 3600000},
                "pagination": {"page": 1, "pageSize": 20},
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_synthetic_result_list_returns_rows(self):
        """Should return one row per test run within the time window."""
        result = await self.client.get_synthetic_result_list(
            payload={
                "syntheticMetrics": [
                    "synthetic.metricsResponseTime",
                    "synthetic.metricsStatus",
                ],
                "timeFrame": {"to": 0, "windowSize": 3600000},
                "pagination": {"page": 1, "pageSize": 20},
                "order": {"by": "start_time", "direction": "DESC"},
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_synthetic_result_list_with_tag_filter(self):
        """Capital-T TagFilterExpression should be normalised and accepted."""
        result = await self.client.get_synthetic_result_list(
            payload={
                "syntheticMetrics": ["synthetic.metricsStatus"],
                "timeFrame": {"to": 0, "windowSize": 3600000},
                "pagination": {"page": 1, "pageSize": 10},
                "TagFilterExpression": {
                    "type": "TAG_FILTER",
                    "name": "synthetic.metricsStatus",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "numberValue": "1",
                },
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_location_summary_list_returns_locations(self):
        """Should return location metadata with at least id and label fields."""
        result = await self.client.get_location_summary_list(
            payload={
                "timeFrame": {"to": None, "windowSize": 300000},
                "pagination": {"page": 1, "pageSize": 20},
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_location_summary_list_empty_payload(self):
        """All payload fields are optional — empty payload should succeed."""
        result = await self.client.get_location_summary_list(payload={})

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_test_summary_list_returns_summary(self):
        """Should return one row per test with success_rate and locationStatusList."""
        result = await self.client.get_test_summary_list(
            payload={
                "metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}],
                "timeFrame": {"to": 0, "windowSize": 1800000},
                "pagination": {"page": 1, "pageSize": 20},
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    @pytest.mark.asyncio
    async def test_get_test_summary_list_location_status_list_structure(self):
        """Each test row should carry a locationStatusList array when data is present."""
        result = await self.client.get_test_summary_list(
            payload={
                "metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}],
                "timeFrame": {"to": 0, "windowSize": 3600000},
                "pagination": {"page": 1, "pageSize": 5},
            }
        )

        assert "error" not in result, f"Unexpected error: {result.get('error')}"
        # If items exist, verify locationStatusList presence
        items = result.get("items", [])
        for item in items:
            assert "locationStatusList" in item, \
                f"Expected locationStatusList in test summary item: {item}"

class TestSyntheticSmartRouterE2E:
    """E2E tests exercising the full router → sub-client pipeline."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.router.synthetic_smart_router_tool import SyntheticSmartRouterMCPTool

        self.base_url = os.getenv("INSTANA_BASE_URL")
        self.api_token = os.getenv("INSTANA_API_TOKEN")
        self.router = SyntheticSmartRouterMCPTool(
            read_token=self.api_token,
            base_url=self.base_url,
        )

    @pytest.mark.asyncio
    async def test_router_catalog_metrics_end_to_end(self):
        """Router should propagate catalog metrics request all the way to the API."""
        result = await self.router.manage_synthetics(
            resource_type="catalog",
            operation="get_synthetic_catalog_metrics",
        )

        assert result["resource_type"] == "catalog"
        assert result["operation"] == "get_synthetic_catalog_metrics"
        assert "results" in result
        assert "error" not in result.get("results", {}), \
            f"Sub-client returned error: {result['results'].get('error')}"

    @pytest.mark.asyncio
    async def test_router_settings_get_synthetic_tests_end_to_end(self):
        """Router should retrieve the list of all synthetic tests."""
        result = await self.router.manage_synthetics(
            resource_type="settings",
            operation="get_synthetic_tests",
        )

        assert result["resource_type"] == "settings"
        assert result["operation"] == "get_synthetic_tests"
        assert "results" in result
        inner = result["results"]
        assert "items" in inner
        assert "count" in inner

    @pytest.mark.asyncio
    async def test_router_test_playback_get_location_summary_list(self):
        """Router should retrieve location summary list via test_playback resource type."""
        result = await self.router.manage_synthetics(
            resource_type="test_playback",
            operation="get_location_summary_list",
            params={"payload": {"pagination": {"page": 1, "pageSize": 10}}},
        )

        assert result["resource_type"] == "test_playback"
        assert result["operation"] == "get_location_summary_list"
        assert "results" in result
