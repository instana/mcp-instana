"""
Unit tests for Synthetic Metrics Module

Tests get_metrics_result with payload validation, SDK model construction,
and exception handling.

NOTE: SyntheticMetricsApi.get_metrics_result_without_preload_content returns
an HTTP response object (with .status and .data). The source code checks
response.status != 200 and parses the body via decode_response + json.loads.
"""

import asyncio
import builtins
import json
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.metrics_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# Mock external dependencies
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.synthetic_metrics_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_metrics_result'] = MagicMock()
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()

mock_metrics_api_class = MagicMock()
mock_metrics_api_class.__name__ = "SyntheticMetricsApi"
sys.modules['instana_client.api.synthetic_metrics_api'].SyntheticMetricsApi = mock_metrics_api_class

# GetMetricsResult.from_dict is patched per-test via this module-level reference
mock_get_metrics_result_class = MagicMock()
sys.modules['instana_client.models.get_metrics_result'].GetMetricsResult = mock_get_metrics_result_class

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.synthetic.synthetic_metrics import SyntheticMetricsMCPTools


def _make_response_mock(payload, status=200):
    """Return a mock that behaves like an HTTP response object."""
    m = MagicMock()
    m.status = status
    m.data = json.dumps(payload).encode("utf-8")
    m.headers = {"Content-Type": "application/json; charset=utf-8"}
    return m


class TestSyntheticMetricsMCPTools(unittest.TestCase):
    """Unit tests for SyntheticMetricsMCPTools."""

    def setUp(self):
        self.metrics_api = MagicMock()
        self.client = SyntheticMetricsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.metrics_api = self.metrics_api

        # Default: API returns a 200 response with an empty items body
        mock_get_metrics_result_class.reset_mock()
        mock_get_metrics_result_class.from_dict = MagicMock(return_value=MagicMock())
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=_make_response_mock({"items": []})
        )

    def test_initialization(self):
        self.assertEqual(self.client.read_token, "test_token")
        self.assertEqual(self.client.base_url, "https://test.instana.io")


    def test_get_metrics_result_success(self):
        """Valid payload should return the parsed JSON body from the HTTP response."""
        expected = {"items": [{"testId": "t1", "metricsResponseTime": 250.0}]}
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=_make_response_mock(expected)
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={
                "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "MEAN"}],
                "timeFrame": {"to": 0, "windowSize": 3600000},
            }
        ))

        self.assertNotIn("error", result)
        self.assertEqual(result, expected)

    def test_get_metrics_result_with_json_string_payload(self):
        """Payload supplied as a JSON string should be parsed and accepted."""
        expected = {"items": []}
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=_make_response_mock(expected)
        )

        payload_str = json.dumps({
            "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}],
            "timeFrame": {"to": 0, "windowSize": 3600000},
        })

        result = asyncio.run(self.client.get_metrics_result(payload=payload_str))

        self.assertNotIn("error", result)

    def test_get_metrics_result_missing_metrics_field(self):
        """Payload without 'metrics' key should return elicitation error."""
        result = asyncio.run(self.client.get_metrics_result(
            payload={"timeFrame": {"to": 0, "windowSize": 3600000}}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("metrics" in e for e in result.get("api_error", [])))

    def test_get_metrics_result_none_payload(self):
        """None payload causes parse_payload to return an error dict."""
        result = asyncio.run(self.client.get_metrics_result(payload=None))

        self.assertIn("error", result)

    def test_get_metrics_result_invalid_json_string(self):
        """Malformed JSON string payload should return parse error."""
        result = asyncio.run(self.client.get_metrics_result(payload="not-valid-json{"))

        self.assertIn("error", result)

    def test_get_metrics_result_model_construction_failure(self):
        """Invalid aggregation should be caught by preflight validation, not from_dict."""
        result = asyncio.run(self.client.get_metrics_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "INVALID"}]}
        ))

        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("INVALID" in e for e in result.get("api_error", [])))
        self.metrics_api.get_metrics_result_without_preload_content.assert_not_called()

    def test_get_metrics_result_api_raises_exception(self):
        """An exception from the underlying API call should be caught and returned as error."""
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            side_effect=Exception("API internal error")
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))

        self.assertIn("error", result)

    def test_get_metrics_result_http_error(self):
        """HTTP error response should be returned as error dict with status_code."""
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=_make_response_mock({"message": "Unauthorized"}, status=401)
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 401", result["error"])
        self.assertEqual(result["status_code"], 401)

    def test_get_metrics_result_http_error_decode_fails(self):
        """When decode_response raises on an error response, status_code is still returned."""
        mock_response = Mock()
        mock_response.status = 503
        mock_response.data = None  # causes decode_response to raise
        mock_response.headers = {}
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=mock_response
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))

        self.assertIn("error", result)
        self.assertIn("HTTP 503", result["error"])
        self.assertEqual(result["status_code"], 503)

    def test_get_metrics_result_exception(self):
        """A network-level exception should be caught and returned as error dict."""
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            side_effect=ConnectionError("Network failure")
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))

        self.assertIn("error", result)

    def test_get_metrics_result_with_groups(self):
        """Payload with groups should be forwarded to the API without error."""
        expected = {"items": [{"group": "loc-1", "metricsResponseTime": 100.0}]}
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=_make_response_mock(expected)
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={
                "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "MEAN"}],
                "groups": [{"groupbyTag": "synthetic.locationId", "groupbyTagEntity": "NOT_APPLICABLE", "direction": "DESC"}],
                "timeFrame": {"to": 0, "windowSize": 3600000},
            }
        ))

        self.assertNotIn("error", result)
        self.metrics_api.get_metrics_result_without_preload_content.assert_called_once()

    def test_get_metrics_result_with_tag_filter(self):
        """Payload with tagFilterExpression should be forwarded without error."""
        expected = {"items": []}
        self.metrics_api.get_metrics_result_without_preload_content = Mock(
            return_value=_make_response_mock(expected)
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={
                "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}],
                "tagFilterExpression": {
                    "type": "TAG_FILTER",
                    "name": "synthetic.testName",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "Login Flow",
                },
            }
        ))

        self.assertNotIn("error", result)

    def test_get_metrics_result_from_dict_raises(self):
        """When GetMetricsResult.from_dict raises, lines 95-97 are hit and an error is returned."""
        mock_get_metrics_result_class.from_dict = MagicMock(
            side_effect=Exception("from_dict failure")
        )

        result = asyncio.run(self.client.get_metrics_result(
            payload={
                "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}],
                "timeFrame": {"to": 0, "windowSize": 3600000},
            }
        ))

        self.assertIn("error", result)
        self.assertIn("from_dict failure", result["error"])
        self.metrics_api.get_metrics_result_without_preload_content.assert_not_called()


class TestSyntheticMetricsImportError(unittest.TestCase):
    """Covers the ImportError branch (lines 14-17) in synthetic_metrics.py."""

    def test_import_error_branch_logs_and_raises(self):
        """When the instana_client SDK import fails, the module logs and re-raises."""
        module_name = "src.synthetic.synthetic_metrics"
        original_module = sys.modules.get(module_name)
        real_import = builtins.__import__

        def failing_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "instana_client.api.synthetic_metrics_api":
                raise ImportError("SDK missing")
            return real_import(name, globals, locals, fromlist, level)

        try:
            sys.modules.pop(module_name, None)

            with patch("builtins.__import__", side_effect=failing_import), \
                 patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                with self.assertRaises(ImportError) as ctx:
                    __import__(module_name, fromlist=["SyntheticMetricsMCPTools"])

                self.assertIn("SDK missing", str(ctx.exception))
                mock_logger.error.assert_called_once()
                self.assertIn("Error importing Instana SDK", mock_logger.error.call_args.args[0])
        finally:
            if original_module is not None:
                sys.modules[module_name] = original_module
            else:
                sys.modules.pop(module_name, None)


if __name__ == '__main__':
    unittest.main()
