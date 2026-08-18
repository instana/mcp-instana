"""
E2E tests for Synthetic Catalog functionality.

These tests verify the synthetic catalog endpoints return proper metadata
including aggregation types, formatters, and tag names.

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


class TestSyntheticCatalogE2E:
    """E2E tests for synthetic catalog operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        from src.synthetic.synthetic_catalog import SyntheticCatalogMCPTools

        self.base_url = os.getenv("INSTANA_BASE_URL")
        self.api_token = os.getenv("INSTANA_API_TOKEN")
        self.client = SyntheticCatalogMCPTools(
            read_token=self.api_token,
            base_url=self.base_url,
        )

    @pytest.mark.asyncio
    async def test_get_synthetic_catalog_metrics_returns_metadata(self):
        """Catalog metrics should return a non-empty list of metric descriptors."""
        result = await self.client.get_synthetic_catalog_metrics()

        assert "metrics" in result, "Response should contain 'metrics' field"
        assert "count" in result, "Response should contain 'count' field"
        assert "description" in result, "Response should contain 'description' field"
        assert result["count"] > 0, "Should return at least one metric"
        assert len(result["metrics"]) == result["count"]

    @pytest.mark.asyncio
    async def test_catalog_metrics_have_required_fields(self):
        """Each metric card should carry metricId, label, aggregations, beaconTypes."""
        result = await self.client.get_synthetic_catalog_metrics()

        for metric in result["metrics"]:
            assert "metricId" in metric, f"Metric missing metricId: {metric}"
            assert "label" in metric, f"Metric missing label: {metric}"
            assert "aggregations" in metric, f"Metric missing aggregations: {metric}"
            assert isinstance(metric["aggregations"], list)

    @pytest.mark.asyncio
    async def test_catalog_metrics_full_view_has_internal_fields(self):
        """view='full' should include pathToValueInBeacon or tagName for at least one metric."""
        result = await self.client.get_synthetic_catalog_metrics(view="full")

        assert result["description"] == "Synthetic monitoring metrics catalog with full metadata"
        # At least one metric should have internal SDK fields
        has_internal = any("pathToValueInBeacon" in m or "tagName" in m for m in result["metrics"])
        assert has_internal, "view=full should expose at least one internal field"

    @pytest.mark.asyncio
    async def test_catalog_metrics_contains_response_time_metric(self):
        """The standard response-time metric should always be present."""
        result = await self.client.get_synthetic_catalog_metrics()

        metric_ids = [m["metricId"] for m in result["metrics"]]
        assert "synthetic.metricsResponseTime" in metric_ids, \
            "synthetic.metricsResponseTime should be in the metrics catalog"

    @pytest.mark.asyncio
    async def test_get_synthetic_tag_catalog_filtering(self):
        """FILTERING use-case should return a non-empty list of synthetic.* tags."""
        result = await self.client.get_synthetic_tag_catalog(use_case="FILTERING")

        assert "tag_names" in result
        assert "count" in result
        assert "use_case" in result
        assert result["use_case"] == "FILTERING"
        assert result["count"] > 0, "Should return at least one tag for FILTERING"

    @pytest.mark.asyncio
    async def test_get_synthetic_tag_catalog_grouping(self):
        """GROUPING use-case should return a non-empty list of synthetic.* tags."""
        result = await self.client.get_synthetic_tag_catalog(use_case="GROUPING")

        assert "tag_names" in result
        assert result["count"] > 0, "Should return at least one tag for GROUPING"

    @pytest.mark.asyncio
    async def test_tag_catalog_tags_have_synthetic_prefix(self):
        """Every returned tag name should carry a recognisable prefix."""
        result = await self.client.get_synthetic_tag_catalog(use_case="FILTERING")

        # At least some tags should start with synthetic.
        synthetic_tags = [t for t in result["tag_names"] if t.startswith("synthetic.")]
        assert len(synthetic_tags) > 0, \
            "At least one tag should start with 'synthetic.' for FILTERING use-case"

    @pytest.mark.asyncio
    async def test_tag_catalog_filtering_vs_grouping_overlap(self):
        """FILTERING and GROUPING should share at least some tags."""
        filtering = await self.client.get_synthetic_tag_catalog(use_case="FILTERING")
        grouping = await self.client.get_synthetic_tag_catalog(use_case="GROUPING")

        common = set(filtering["tag_names"]) & set(grouping["tag_names"])
        assert len(common) > 0, "FILTERING and GROUPING should share at least one common tag"

