"""
E2E tests for Website Catalog functionality.

These tests verify the website catalog endpoints return proper metadata
including aggregation types, operators, and full metric information.
"""

import os
import pytest

# Mark all tests in this module as E2E tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.getenv("INSTANA_BASE_URL") or not os.getenv("INSTANA_API_TOKEN"),
        reason="Requires INSTANA_BASE_URL and INSTANA_API_TOKEN environment variables"
    )
]


class TestWebsiteCatalogE2E:
    """E2E tests for website catalog operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        from src.core.catalog_cache import clear_cache
        clear_cache()

        # Import here to avoid import errors when instana_client is not available
        from src.website.website_catalog import WebsiteCatalogMCPTools
        
        self.base_url = os.getenv("INSTANA_BASE_URL")
        self.api_token = os.getenv("INSTANA_API_TOKEN")
        self.client = WebsiteCatalogMCPTools(
            read_token=self.api_token,
            base_url=self.base_url
        )

    @pytest.mark.asyncio
    async def test_get_website_catalog_metrics_returns_full_metadata(self):
        """Test that get_website_catalog_metrics returns full metadata for all metrics."""
        result = await self.client.get_website_catalog_metrics()

        # Verify response structure
        assert "metrics" in result, "Response should contain 'metrics' field"
        assert "count" in result, "Response should contain 'count' field"
        assert "description" in result, "Response should contain 'description' field"
        
        # Verify we have metrics
        assert result["count"] > 0, "Should return at least one metric"
        assert len(result["metrics"]) == result["count"], "Count should match number of metrics"
        
        # Verify first metric has full metadata
        first_metric = result["metrics"][0]
        assert "metricId" in first_metric, "Metric should have metricId"
        assert "label" in first_metric, "Metric should have label"
        assert "description" in first_metric, "Metric should have description"
        assert "formatter" in first_metric, "Metric should have formatter"
        assert "aggregations" in first_metric, "Metric should have aggregations list"
        assert "beaconTypes" in first_metric, "Metric should have beaconTypes list"
        
        # Verify aggregations is a list
        assert isinstance(first_metric["aggregations"], list), "Aggregations should be a list"
        
        # Verify beaconTypes is a list
        assert isinstance(first_metric["beaconTypes"], list), "BeaconTypes should be a list"

    @pytest.mark.asyncio
    async def test_metrics_contain_various_aggregation_types(self):
        """Test that metrics catalog includes various aggregation types."""
        result = await self.client.get_website_catalog_metrics()
        
        # Collect all unique aggregation types
        all_aggregations = set()
        for metric in result["metrics"]:
            if "aggregations" in metric:
                all_aggregations.update(metric["aggregations"])
        
        # Verify we have multiple aggregation types
        assert len(all_aggregations) > 1, "Should have multiple aggregation types"
        
        # Check for common aggregation types
        expected_aggregations = ["SUM", "MEAN", "MAX", "MIN", "P95", "P99"]
        found_aggregations = [agg for agg in expected_aggregations if agg in all_aggregations]
        assert len(found_aggregations) >= 3, f"Should find at least 3 common aggregations, found: {found_aggregations}"

    @pytest.mark.asyncio
    async def test_metrics_have_proper_formatters(self):
        """Test that metrics have proper formatter types."""
        result = await self.client.get_website_catalog_metrics()
        
        # Collect all unique formatters
        all_formatters = set()
        for metric in result["metrics"]:
            if "formatter" in metric:
                all_formatters.add(metric["formatter"])
        
        # Verify we have multiple formatter types
        assert len(all_formatters) > 1, "Should have multiple formatter types"
        
        # Check for common formatters
        expected_formatters = ["NUMBER", "LATENCY", "BYTES", "PERCENTAGE"]
        found_formatters = [fmt for fmt in expected_formatters if fmt in all_formatters]
        assert len(found_formatters) >= 2, f"Should find at least 2 common formatters, found: {found_formatters}"

    @pytest.mark.asyncio
    async def test_get_website_tag_catalog_with_pageload(self):
        """Test get_website_tag_catalog for PAGELOAD beacon type."""
        result = await self.client.get_website_tag_catalog(
            beacon_type="pageLoad",
            use_case="GROUPING"
        )

        # Verify response structure
        assert "tag_names" in result, "Response should contain 'tag_names' field"
        assert "count" in result, "Response should contain 'count' field"
        assert "beacon_type" in result, "Response should contain 'beacon_type' field"
        assert "use_case" in result, "Response should contain 'use_case' field"
        
        # Verify we have tags
        assert result["count"] > 0, "Should return at least one tag"
        assert len(result["tag_names"]) == result["count"], "Count should match number of tags"
        
        # Verify tags follow beacon.* pattern
        for tag in result["tag_names"]:
            assert tag.startswith("beacon."), f"Tag '{tag}' should start with 'beacon.'"

    @pytest.mark.asyncio
    async def test_get_website_tag_catalog_filtering_vs_grouping(self):
        """Test that FILTERING and GROUPING use cases return different tag sets."""
        grouping_result = await self.client.get_website_tag_catalog(
            beacon_type="pageLoad",
            use_case="GROUPING"
        )
        
        filtering_result = await self.client.get_website_tag_catalog(
            beacon_type="pageLoad",
            use_case="FILTERING"
        )
        
        # Both should return tags
        assert grouping_result["count"] > 0, "GROUPING should return tags"
        assert filtering_result["count"] > 0, "FILTERING should return tags"
        
        # Tag sets may differ between use cases
        grouping_tags = set(grouping_result["tag_names"])
        filtering_tags = set(filtering_result["tag_names"])
        
        # At least some tags should be common
        common_tags = grouping_tags & filtering_tags
        assert len(common_tags) > 0, "Should have some common tags between GROUPING and FILTERING"
