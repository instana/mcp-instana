"""
E2E tests for Synthetic Settings functionality.

Tests get_synthetic_test, get_synthetic_tests, get_locations,
get_location_by_id, and get_all_datacenters against a real Instana instance.

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


class TestSyntheticSettingsE2E:
    """E2E tests for synthetic settings operations."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.synthetic.synthetic_settings import SyntheticSettingsMCPTools

        self.base_url = os.getenv("INSTANA_BASE_URL")
        self.api_token = os.getenv("INSTANA_API_TOKEN")
        self.client = SyntheticSettingsMCPTools(
            read_token=self.api_token,
            base_url=self.base_url,
        )

    @pytest.mark.asyncio
    async def test_get_synthetic_tests_returns_list(self):
        """Should return items and count fields."""
        result = await self.client.get_synthetic_tests()

        assert "items" in result, "Response should contain 'items' field"
        assert "count" in result, "Response should contain 'count' field"
        assert isinstance(result["items"], list)
        assert result["count"] == len(result["items"])

    @pytest.mark.asyncio
    async def test_get_synthetic_tests_items_have_required_fields(self):
        """Each test record should carry id and label."""
        result = await self.client.get_synthetic_tests()

        if result["count"] == 0:
            pytest.skip("No synthetic tests configured on this instance")

        for test in result["items"]:
            assert "id" in test, f"Test record missing id: {test}"
            assert "label" in test, f"Test record missing label: {test}"

    @pytest.mark.asyncio
    async def test_get_synthetic_tests_with_limit(self):
        """Applying limit=1 should return at most 1 test."""
        result = await self.client.get_synthetic_tests(limit=1)

        assert "items" in result
        assert len(result["items"]) <= 1

    @pytest.mark.asyncio
    async def test_get_synthetic_test_by_id(self):
        """Fetching a test by ID should return the full record."""
        # First, list tests to get a real ID
        list_result = await self.client.get_synthetic_tests(limit=1)
        if list_result["count"] == 0:
            pytest.skip("No synthetic tests configured on this instance")

        test_id = list_result["items"][0]["id"]
        result = await self.client.get_synthetic_test(test_id=test_id)

        assert "id" in result, "Response should contain 'id' field"
        assert result["id"] == test_id

    @pytest.mark.asyncio
    async def test_get_synthetic_test_by_name(self):
        """Name resolution should map label → ID and return the record."""
        list_result = await self.client.get_synthetic_tests(limit=1)
        if list_result["count"] == 0:
            pytest.skip("No synthetic tests configured on this instance")

        test_label = list_result["items"][0]["label"]
        result = await self.client.get_synthetic_test(test_name=test_label)

        assert "id" in result
        assert result["label"] == test_label

    @pytest.mark.asyncio
    async def test_get_locations_returns_list(self):
        result = await self.client.get_locations()

        assert "items" in result
        assert "count" in result
        assert "filters_applied" in result
        assert isinstance(result["items"], list)

    @pytest.mark.asyncio
    async def test_get_locations_items_have_required_fields(self):
        result = await self.client.get_locations()

        if result["count"] == 0:
            pytest.skip("No locations configured on this instance")

        for loc in result["items"]:
            assert "id" in loc
            assert "label" in loc
            assert "locationType" in loc

    @pytest.mark.asyncio
    async def test_get_locations_filter_managed(self):
        """location_type='Managed' should return only Managed locations."""
        result = await self.client.get_locations(location_type="Managed")

        for loc in result["items"]:
            assert loc["locationType"].lower() == "managed"

    @pytest.mark.asyncio
    async def test_get_locations_filter_online(self):
        """status='Online' should return only Online locations."""
        result = await self.client.get_locations(status="Online")

        for loc in result["items"]:
            assert loc["status"].lower() == "online"

    @pytest.mark.asyncio
    async def test_get_location_by_id(self):
        """Fetching a location by its ID should return the full record."""
        list_result = await self.client.get_locations(limit=1)
        if list_result["count"] == 0:
            pytest.skip("No locations configured on this instance")

        loc_id = list_result["items"][0]["id"]
        result = await self.client.get_location_by_id(location_id=loc_id)

        assert "id" in result
        assert result["id"] == loc_id

    @pytest.mark.asyncio
    async def test_get_all_datacenters_returns_managed_only(self):
        result = await self.client.get_all_datacenters()

        assert "items" in result
        assert "count" in result
        assert "total_online" in result

        for dc in result["items"]:
            assert dc["locationType"].lower() == "managed"

    @pytest.mark.asyncio
    async def test_get_all_datacenters_total_online_is_consistent(self):
        """total_online should match the number of Online items returned."""
        result = await self.client.get_all_datacenters()

        online_count = sum(1 for dc in result["items"] if dc.get("status", "").lower() == "online")
        assert result["total_online"] == online_count

    @pytest.mark.asyncio
    async def test_get_all_datacenters_online_filter(self):
        result = await self.client.get_all_datacenters(status="Online")

        for dc in result["items"]:
            assert dc["status"].lower() == "online"
