"""Mocked e2e tests for uncovered branches in src/core/ui_links.py and metric_validation.py."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.catalog_cache import clear_cache
from src.core.metric_validation import fetch_metric_catalog_internal
from src.core.ui_links import (
    add_application_link,
    add_service_link,
    add_synthetic_test_link,
)

BASE = "https://tenant.instana.io"


@pytest.fixture(autouse=True)
def _isolated_catalog_cache():
    clear_cache()
    yield
    clear_cache()


def _response(payload, status=200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.data = json.dumps(payload).encode("utf-8")
    resp.headers = {"Content-Type": "application/json"}
    return resp


def _api_client(host: str) -> MagicMock:
    client = MagicMock()
    client.api_client = MagicMock()
    client.api_client.configuration.host = host
    return client


class TestUiLinksE2E:
    """Link helpers skip silently without a base URL or id, and add markdown otherwise."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_link_adds_markdown(self):
        app = {"id": "app-1", "label": "Checkout"}
        add_application_link(BASE, app)
        assert app["link"].startswith("[Checkout](")
        assert "app-1" in app["link"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_link_skipped_without_id(self):
        app = {"label": "No id"}
        add_application_link(BASE, app)
        assert "link" not in app

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_link_skipped_without_base_url(self):
        app = {"id": "app-1", "label": "Checkout"}
        with patch("src.core.ui_links._request_base_url", return_value=None):
            add_application_link("", app)
        assert "link" not in app

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_application_link_falls_back_to_id_for_label(self):
        app = {"id": "app-2"}
        add_application_link(BASE, app)
        assert app["link"].startswith("[app-2](")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_service_link_adds_markdown(self):
        service = {"id": "svc-1", "label": "cart"}
        add_service_link(BASE, "app-1", service, boundary_scope="INBOUND")
        assert service["link"].startswith("[cart](")
        assert "svc-1" in service["link"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_service_link_skipped_without_id(self):
        service = {"label": "cart"}
        add_service_link(BASE, "app-1", service)
        assert "link" not in service

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_synthetic_test_link_adds_markdown(self):
        test = {"id": "t-1", "label": "Login", "type": "HTTPAction", "locations": []}
        add_synthetic_test_link(BASE, test)
        assert test["link"].startswith("[Login](")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_add_synthetic_test_link_skipped_without_id(self):
        test = {"label": "Login"}
        add_synthetic_test_link(BASE, test)
        assert "link" not in test


class TestFetchMetricCatalogInternalE2E:
    """fetch_metric_catalog_internal: caching and failure branches."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_second_call_is_served_from_cache(self):
        raw = [{"metricId": "onLoadTime", "aggregations": ["MEAN"], "beaconTypes": ["pageLoad"]}]
        api = _api_client("cache-host.instana.io")
        catalog_cls = MagicMock()
        instance = catalog_cls.return_value
        instance.get_website_catalog_metrics_without_preload_content = AsyncMock(
            return_value=_response(raw)
        )
        method = "get_website_catalog_metrics_without_preload_content"

        first = await fetch_metric_catalog_internal(api, catalog_cls, method)
        second = await fetch_metric_catalog_internal(api, catalog_cls, method)

        assert first == second
        assert instance.get_website_catalog_metrics_without_preload_content.await_count == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_sdk_exception_returns_error_and_is_not_cached(self):
        api = _api_client("error-host.instana.io")
        catalog_cls = MagicMock()
        instance = catalog_cls.return_value
        instance.get_website_catalog_metrics_without_preload_content = AsyncMock(
            side_effect=RuntimeError("connection reset")
        )
        result = await fetch_metric_catalog_internal(
            api, catalog_cls, "get_website_catalog_metrics_without_preload_content"
        )
        assert "Failed to fetch metric catalog" in result["error"]
        assert "connection reset" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_http_error_status_returns_error(self):
        api = _api_client("status-host.instana.io")
        catalog_cls = MagicMock()
        instance = catalog_cls.return_value
        instance.get_website_catalog_metrics_without_preload_content = AsyncMock(
            return_value=_response({"error": "boom"}, status=503)
        )
        result = await fetch_metric_catalog_internal(
            api, catalog_cls, "get_website_catalog_metrics_without_preload_content"
        )
        assert "HTTP 503" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_catalog_class_instantiation_failure_returns_error(self):
        api = _api_client("init-host.instana.io")
        catalog_cls = MagicMock(side_effect=TypeError("bad api_client"))
        result = await fetch_metric_catalog_internal(api, catalog_cls, "anything")
        assert "Failed to instantiate catalog API" in result["error"]
