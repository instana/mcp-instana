"""Mocked e2e tests for src/core/alert_config_utils.py."""

import json
from unittest.mock import MagicMock

import pytest

from src.core.alert_config_utils import (
    parse_alert_config_response,
    parse_single_alert_config_response,
)


def _response(body) -> MagicMock:
    resp = MagicMock()
    resp.data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
    return resp


class TestParseAlertConfigResponseE2E:
    """parse_alert_config_response: list/object/empty bodies and malformed JSON."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_list_reports_no_configs(self):
        result = parse_alert_config_response(_response([]), "website", "web-1")
        assert result["configs"] == []
        assert result["count"] == 0
        assert result["total"] == 0
        assert "No active alert configurations found for website ID: web-1" in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_single_object_is_wrapped_in_list(self):
        result = parse_alert_config_response(
            _response({"id": "a1", "name": "High latency"}), "mobile app", "app-1"
        )
        assert result["configs"] == [{"id": "a1", "name": "High latency"}]
        assert result["count"] == 1
        assert result["total"] == 1
        assert result["showing"] == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_object_is_treated_as_no_configs(self):
        result = parse_alert_config_response(_response({}), "website", "web-1")
        assert result["configs"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_result_is_truncated_to_ten_items(self):
        configs = [{"id": f"a{i}"} for i in range(25)]
        result = parse_alert_config_response(_response(configs), "website", "web-1")
        assert result["total"] == 25
        assert result["count"] == 10
        assert result["showing"] == 10
        assert len(result["configs"]) == 10
        assert "Found 25 active alert configuration(s)" in result["message"]
        assert "Showing first 10." in result["message"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_malformed_json_returns_error(self):
        result = parse_alert_config_response(_response(b"{not json"), "website", "web-1")
        assert "error" in result
        assert result["error"].startswith("Failed to parse response JSON")


class TestParseSingleAlertConfigResponseE2E:
    """parse_single_alert_config_response: passthrough of the decoded object."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_returns_decoded_object(self):
        payload = {"id": "a1", "name": "Error rate", "severity": 10}
        assert parse_single_alert_config_response(_response(payload)) == payload

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_malformed_json_returns_error(self):
        result = parse_single_alert_config_response(_response(b"<html>oops"))
        assert result["error"].startswith("Failed to parse response JSON")
