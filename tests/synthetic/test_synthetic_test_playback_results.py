"""
Unit tests for Synthetic Test Playback Results Module

Tests execute_playback_operation dispatch
and all individual playback methods.
"""

import asyncio
import json
import os
import sys
import unittest
from functools import wraps
from unittest.mock import AsyncMock, MagicMock, Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.playback_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# Mock external dependencies
for mod in [
    'instana_client',
    'instana_client.api',
    'instana_client.api.synthetic_test_playback_results_api',
    'instana_client.configuration',
    'instana_client.api_client',
    'instana_client.models',
    'instana_client.models.get_test_result',
    'instana_client.models.get_test_result_analytic',
    'instana_client.models.get_test_result_list',
    'instana_client.models.get_test_result_base',
    'instana_client.models.get_test_summary_result',
    'mcp',
    'mcp.types',
    'fastmcp',
]:
    sys.modules[mod] = MagicMock()

mock_playback_api_class = MagicMock()
mock_playback_api_class.__name__ = "SyntheticTestPlaybackResultsApi"
sys.modules['instana_client.api.synthetic_test_playback_results_api'].SyntheticTestPlaybackResultsApi = mock_playback_api_class

# SDK model mocks — from_dict returns a MagicMock by default
for model_name in ['GetTestResult', 'GetTestResultAnalytic', 'GetTestResultList',
                   'GetTestResultBase', 'GetTestSummaryResult']:
    mock_cls = MagicMock()
    mock_cls.__name__ = model_name
    mock_cls.from_dict = MagicMock(return_value=MagicMock())
    mod_key = f'instana_client.models.{model_name[3:].replace("", "get_").lower()}'
    setattr(
        sys.modules['instana_client.models.get_test_result'],
        model_name, mock_cls
    )

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.synthetic.synthetic_test_playback_results import (
        SyntheticTestPlaybackResultsMCPTools,
    )


def _ok_response(payload):
    r = Mock()
    r.status = 200
    r.data = json.dumps(payload).encode('utf-8')
    r.headers = {'Content-Type': 'application/json; charset=utf-8'}
    return r


def _error_response(status, body=b'Error'):
    r = Mock()
    r.status = status
    r.data = body
    r.headers = {'Content-Type': 'text/plain'}
    return r


_CAPITAL_T_FILTER = {
    "type": "TAG_FILTER", "name": "synthetic.locationId", "operator": "EQUALS",
    "entity": "NOT_APPLICABLE", "stringValue": "loc-1",
}


class TestExecutePlaybackOperation(unittest.TestCase):
    """Tests for the execute_playback_operation dispatcher."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api

    def _patch_method(self, method_name, return_value):
        """Patch an async method on self.client to return return_value."""
        mock = AsyncMock(return_value=return_value)
        setattr(self.client, method_name, mock)
        return mock

    def test_dispatch_to_real_method_keeps_capital_t_filter(self):
        """The dispatcher path (real method, mocked SDK) must not drop a capital-T filter."""
        from instana_client.models.get_test_result_list import GetTestResultList
        GetTestResultList.from_dict = MagicMock(return_value=MagicMock())
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result_list",
            {"payload": {
                "syntheticMetrics": ["synthetic.metricsStatus"],
                "TagFilterExpression": _CAPITAL_T_FILTER,
            }}
        ))
        sent = GetTestResultList.from_dict.call_args[0][0]
        self.assertEqual(sent["tagFilterExpression"]["stringValue"], "loc-1")
        self.assertNotIn("TagFilterExpression", sent)

    def test_dispatches_get_synthetic_result(self):
        m = self._patch_method("get_synthetic_result", {"items": []})
        result = asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result",
            {"payload": {"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}}
        ))
        m.assert_called_once()
        self.assertEqual(result, {"items": []})

    def test_dispatches_get_synthetic_result_analytic(self):
        m = self._patch_method("get_synthetic_result_analytic", {"results": []})
        result = asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result_analytic",
            {"payload": {"syntheticMetrics": ["synthetic.metricsStatus"], "analyticFunction": "LAST_VALUE"}}
        ))
        m.assert_called_once()
        self.assertEqual(result, {"results": []})

    def test_dispatches_get_synthetic_result_list(self):
        m = self._patch_method("get_synthetic_result_list", {"items": []})
        asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result_list",
            {"payload": {"syntheticMetrics": ["synthetic.metricsStatus"]}}
        ))
        m.assert_called_once()

    def test_dispatches_get_location_summary_list(self):
        m = self._patch_method("get_location_summary_list", {"items": []})
        asyncio.run(self.client.execute_playback_operation(
            "get_location_summary_list",
            {"payload": {"timeFrame": {"to": None, "windowSize": 300000}}}
        ))
        m.assert_called_once()

    def test_dispatches_get_test_summary_list(self):
        m = self._patch_method("get_test_summary_list", {"items": []})
        asyncio.run(self.client.execute_playback_operation(
            "get_test_summary_list",
            {"payload": {"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]}}
        ))
        m.assert_called_once()

    def test_dispatches_get_synthetic_result_metadata(self):
        m = self._patch_method("get_synthetic_result_metadata", {"types": []})
        asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result_metadata",
            {"testid": "t1", "testresultid": "r1"}
        ))
        m.assert_called_once_with(testid="t1", testresultid="r1", start_time=None, ctx=None, resource_type=None, tool_name=None)

    def test_dispatches_get_synthetic_result_detail_data(self):
        m = self._patch_method("get_synthetic_result_detail_data", {"data": "..."})
        asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result_detail_data",
            {"testid": "t1", "testresultid": "r1", "type": "HAR"}
        ))
        m.assert_called_once_with(testid="t1", testresultid="r1", detail_type="HAR", name=None, start_time=None, ctx=None, resource_type=None, tool_name=None)

    def test_unknown_operation_returns_error(self):
        result = asyncio.run(self.client.execute_playback_operation("no_such_op", {}))
        self.assertIn("error", result)
        self.assertIn("no_such_op", result["error"])

    def test_none_params_defaults_to_empty_dict(self):
        """None params should not raise; unknown op returns error gracefully."""
        result = asyncio.run(self.client.execute_playback_operation("unknown_op", None))
        self.assertIn("error", result)

    def test_sub_client_raises_is_caught(self):
        """An exception raised inside a dispatched sub-client method is caught (lines 119-121)."""
        async def boom(*args, **kwargs):
            raise RuntimeError("sub-client exploded")
        self.client.get_synthetic_result = boom

        result = asyncio.run(self.client.execute_playback_operation(
            "get_synthetic_result",
            {"payload": {"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}}
        ))
        self.assertIn("error", result)


class TestGetSyntheticResult(unittest.TestCase):
    """Tests for get_synthetic_result."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api
        # Reset SDK model mock
        from instana_client.models.get_test_result import GetTestResult
        GetTestResult.from_dict = MagicMock(return_value=MagicMock())

    def test_success(self):
        self.playback_api.get_synthetic_result_without_preload_content = Mock(
            return_value=_ok_response({"items": [{"testId": "t1"}]})
        )
        result = asyncio.run(self.client.get_synthetic_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "MEAN"}]}
        ))
        self.assertNotIn("error", result)

    def test_capital_t_filter_is_renamed(self):
        from instana_client.models.get_test_result import GetTestResult
        self.playback_api.get_synthetic_result_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        asyncio.run(self.client.get_synthetic_result(payload={
            "metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "MEAN"}],
            "TagFilterExpression": _CAPITAL_T_FILTER,
        }))
        sent = GetTestResult.from_dict.call_args[0][0]
        self.assertEqual(sent["tagFilterExpression"]["stringValue"], "loc-1")
        self.assertNotIn("TagFilterExpression", sent)

    def test_missing_metrics_field(self):
        result = asyncio.run(self.client.get_synthetic_result(
            payload={"timeFrame": {"to": 0, "windowSize": 3600000}}
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("metrics" in e for e in result.get("api_error", [])))

    def test_invalid_payload_type(self):
        """Non-dict, non-string payload returns parse error (line 168)."""
        result = asyncio.run(self.client.get_synthetic_result(payload=12345))
        self.assertIn("error", result)

    def test_from_dict_raises(self):
        """GetTestResult.from_dict raising is caught and returned as error (lines 176-178)."""
        from instana_client.models.get_test_result import GetTestResult
        GetTestResult.from_dict = MagicMock(side_effect=ValueError("bad field"))
        result = asyncio.run(self.client.get_synthetic_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))
        self.assertIn("error", result)
        self.assertIn("GetTestResult", result["error"])

    def test_http_error(self):
        self.playback_api.get_synthetic_result_without_preload_content = Mock(
            return_value=_error_response(500)
        )
        result = asyncio.run(self.client.get_synthetic_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))
        self.assertIn("error", result)

    def test_http_error_decode_fails(self):
        """decode_response raising inside the HTTP error branch (lines 192-194)."""
        bad_response = Mock()
        bad_response.status = 503
        bad_response.data = None  # causes decode_response to raise
        bad_response.headers = {}
        self.playback_api.get_synthetic_result_without_preload_content = Mock(
            return_value=bad_response
        )
        result = asyncio.run(self.client.get_synthetic_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))
        self.assertIn("error", result)

    def test_outer_exception(self):
        """Top-level exception in get_synthetic_result is caught (lines 198-200)."""
        self.playback_api.get_synthetic_result_without_preload_content = Mock(
            side_effect=Exception("network failure")
        )
        result = asyncio.run(self.client.get_synthetic_result(
            payload={"metrics": [{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}]}
        ))
        self.assertIn("error", result)


class TestGetSyntheticResultAnalytic(unittest.TestCase):
    """Tests for get_synthetic_result_analytic."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api
        from instana_client.models.get_test_result_analytic import GetTestResultAnalytic
        GetTestResultAnalytic.from_dict = MagicMock(return_value=MagicMock())

    def test_success(self):
        self.playback_api.get_synthetic_result_analytic_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        result = asyncio.run(self.client.get_synthetic_result_analytic(
            payload={
                "syntheticMetrics": ["synthetic.metricsStatus"],
                "analyticFunction": "LAST_VALUE",
            }
        ))
        self.assertNotIn("error", result)

    def test_capital_t_filter_is_renamed(self):
        from instana_client.models.get_test_result_analytic import GetTestResultAnalytic
        self.playback_api.get_synthetic_result_analytic_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        asyncio.run(self.client.get_synthetic_result_analytic(payload={
            "syntheticMetrics": ["synthetic.metricsStatus"],
            "analyticFunction": "LAST_VALUE",
            "TagFilterExpression": _CAPITAL_T_FILTER,
        }))
        sent = GetTestResultAnalytic.from_dict.call_args[0][0]
        self.assertEqual(sent["tagFilterExpression"]["stringValue"], "loc-1")
        self.assertNotIn("TagFilterExpression", sent)

    def test_missing_synthetic_metrics_field(self):
        result = asyncio.run(self.client.get_synthetic_result_analytic(
            payload={"analyticFunction": "LAST_VALUE"}
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("syntheticMetrics" in e for e in result.get("api_error", [])))

    def test_invalid_payload_type(self):
        """Non-dict, non-string payload returns parse error (line 266)."""
        result = asyncio.run(self.client.get_synthetic_result_analytic(payload=42))
        self.assertIn("error", result)

    def test_from_dict_raises(self):
        """GetTestResultAnalytic.from_dict raising is caught (lines 274-276)."""
        from instana_client.models.get_test_result_analytic import GetTestResultAnalytic
        GetTestResultAnalytic.from_dict = MagicMock(side_effect=ValueError("bad"))
        result = asyncio.run(self.client.get_synthetic_result_analytic(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)
        self.assertIn("GetTestResultAnalytic", result["error"])

    def test_http_error(self):
        self.playback_api.get_synthetic_result_analytic_without_preload_content = Mock(
            return_value=_error_response(403)
        )
        result = asyncio.run(self.client.get_synthetic_result_analytic(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)

    def test_http_error_decode_fails(self):
        """decode_response raising inside the HTTP error branch (lines 290-292)."""
        bad_response = Mock()
        bad_response.status = 503
        bad_response.data = None
        bad_response.headers = {}
        self.playback_api.get_synthetic_result_analytic_without_preload_content = Mock(
            return_value=bad_response
        )
        result = asyncio.run(self.client.get_synthetic_result_analytic(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)

    def test_outer_exception(self):
        """Top-level exception in get_synthetic_result_analytic is caught (lines 296-298)."""
        self.playback_api.get_synthetic_result_analytic_without_preload_content = Mock(
            side_effect=Exception("boom")
        )
        result = asyncio.run(self.client.get_synthetic_result_analytic(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)


class TestGetSyntheticResultList(unittest.TestCase):
    """Tests for get_synthetic_result_list."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api
        from instana_client.models.get_test_result_list import GetTestResultList
        GetTestResultList.from_dict = MagicMock(return_value=MagicMock())

    def test_success(self):
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            return_value=_ok_response({"items": [{"testId": "t1", "status": 1}]})
        )
        result = asyncio.run(self.client.get_synthetic_result_list(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertNotIn("error", result)

    def test_json_string_payload_keeps_capital_t_filter(self):
        """A JSON-string payload with TagFilterExpression must keep its filter
        (previously the rename was skipped for non-dict input)."""
        from instana_client.models.get_test_result_list import GetTestResultList
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        payload = json.dumps({
            "syntheticMetrics": ["synthetic.metricsStatus"],
            "TagFilterExpression": {
                "type": "TAG_FILTER", "name": "synthetic.locationId", "operator": "EQUALS",
                "entity": "NOT_APPLICABLE", "stringValue": "loc-1",
            },
        })
        result = asyncio.run(self.client.get_synthetic_result_list(payload=payload))
        self.assertNotIn("error", result)
        sent = GetTestResultList.from_dict.call_args[0][0]
        self.assertEqual(sent["tagFilterExpression"]["stringValue"], "loc-1")
        self.assertNotIn("TagFilterExpression", sent)

    def test_direct_call_keeps_capital_t_filter(self):
        """Direct service calls (no execute_playback_operation) are covered too."""
        from instana_client.models.get_test_result_list import GetTestResultList
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        asyncio.run(self.client.get_synthetic_result_list(payload={
            "syntheticMetrics": ["synthetic.metricsStatus"],
            "TagFilterExpression": {
                "type": "TAG_FILTER", "name": "synthetic.locationId", "operator": "EQUALS",
                "entity": "NOT_APPLICABLE", "stringValue": "loc-1",
            },
        }))
        sent = GetTestResultList.from_dict.call_args[0][0]
        self.assertIn("tagFilterExpression", sent)
        self.assertNotIn("TagFilterExpression", sent)

    def test_missing_synthetic_metrics_field(self):
        result = asyncio.run(self.client.get_synthetic_result_list(
            payload={"timeFrame": {"to": 0, "windowSize": 3600000}}
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("syntheticMetrics" in e for e in result.get("api_error", [])))

    def test_invalid_payload_type(self):
        """Non-dict, non-string payload returns parse error (line 362)."""
        result = asyncio.run(self.client.get_synthetic_result_list(payload=[]))
        self.assertIn("error", result)

    def test_from_dict_raises(self):
        """GetTestResultList.from_dict raising is caught (lines 370-372)."""
        from instana_client.models.get_test_result_list import GetTestResultList
        GetTestResultList.from_dict = MagicMock(side_effect=ValueError("bad"))
        result = asyncio.run(self.client.get_synthetic_result_list(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)
        self.assertIn("GetTestResultList", result["error"])

    def test_http_error(self):
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            return_value=_error_response(422)
        )
        result = asyncio.run(self.client.get_synthetic_result_list(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)

    def test_http_error_decode_fails(self):
        """decode_response raising inside the HTTP error branch (lines 386-388)."""
        bad_response = Mock()
        bad_response.status = 503
        bad_response.data = None
        bad_response.headers = {}
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            return_value=bad_response
        )
        result = asyncio.run(self.client.get_synthetic_result_list(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)

    def test_outer_exception(self):
        """Top-level exception in get_synthetic_result_list is caught (lines 393-394)."""
        self.playback_api.get_synthetic_result_list_without_preload_content = Mock(
            side_effect=Exception("boom")
        )
        result = asyncio.run(self.client.get_synthetic_result_list(
            payload={"syntheticMetrics": ["synthetic.metricsStatus"]}
        ))
        self.assertIn("error", result)


class TestGetLocationSummaryList(unittest.TestCase):
    """Tests for get_location_summary_list."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api
        from instana_client.models.get_test_result_base import GetTestResultBase
        GetTestResultBase.from_dict = MagicMock(return_value=MagicMock())

    def test_success_with_none_payload(self):
        """None payload is rejected by parse_payload — caller must pass a non-empty dict."""
        result = asyncio.run(self.client.get_location_summary_list(payload=None))
        self.assertIn("error", result)

    def test_success_with_time_frame(self):
        """A non-empty payload with timeFrame should succeed."""
        self.playback_api.get_location_summary_list_without_preload_content = Mock(
            return_value=_ok_response({"items": [{"locationId": "loc-1", "label": "us-east-1"}]})
        )
        result = asyncio.run(self.client.get_location_summary_list(
            payload={"timeFrame": {"to": None, "windowSize": 300000}}
        ))
        self.assertNotIn("error", result)

    def test_capital_t_filter_is_renamed(self):
        from instana_client.models.get_test_result_base import GetTestResultBase
        self.playback_api.get_location_summary_list_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        asyncio.run(self.client.get_location_summary_list(payload={
            "timeFrame": {"to": None, "windowSize": 300000},
            "TagFilterExpression": _CAPITAL_T_FILTER,
        }))
        sent = GetTestResultBase.from_dict.call_args[0][0]
        self.assertEqual(sent["tagFilterExpression"]["stringValue"], "loc-1")
        self.assertNotIn("TagFilterExpression", sent)

    def test_success_with_pagination_only(self):
        """A payload carrying only pagination should also succeed."""
        self.playback_api.get_location_summary_list_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        result = asyncio.run(self.client.get_location_summary_list(
            payload={"pagination": {"page": 1, "pageSize": 10}}
        ))
        self.assertNotIn("error", result)

    def test_from_dict_raises(self):
        """GetTestResultBase.from_dict raising is caught (lines 435-437)."""
        from instana_client.models.get_test_result_base import GetTestResultBase
        GetTestResultBase.from_dict = MagicMock(side_effect=ValueError("bad"))
        result = asyncio.run(self.client.get_location_summary_list(
            payload={"timeFrame": {"to": None, "windowSize": 300000}}
        ))
        self.assertIn("error", result)
        self.assertIn("GetTestResultBase", result["error"])

    def test_http_error(self):
        self.playback_api.get_location_summary_list_without_preload_content = Mock(
            return_value=_error_response(500)
        )
        result = asyncio.run(self.client.get_location_summary_list(
            payload={"timeFrame": {"to": None, "windowSize": 300000}}
        ))
        self.assertIn("error", result)

    def test_http_error_decode_fails(self):
        """decode_response raising inside the HTTP error branch (lines 451-453)."""
        bad_response = Mock()
        bad_response.status = 503
        bad_response.data = None
        bad_response.headers = {}
        self.playback_api.get_location_summary_list_without_preload_content = Mock(
            return_value=bad_response
        )
        result = asyncio.run(self.client.get_location_summary_list(
            payload={"timeFrame": {"to": None, "windowSize": 300000}}
        ))
        self.assertIn("error", result)

    def test_outer_exception(self):
        """Top-level exception in get_location_summary_list is caught (lines 457-459)."""
        self.playback_api.get_location_summary_list_without_preload_content = Mock(
            side_effect=Exception("boom")
        )
        result = asyncio.run(self.client.get_location_summary_list(
            payload={"timeFrame": {"to": None, "windowSize": 300000}}
        ))
        self.assertIn("error", result)


class TestGetTestSummaryList(unittest.TestCase):
    """Tests for get_test_summary_list."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api
        from instana_client.models.get_test_summary_result import GetTestSummaryResult
        GetTestSummaryResult.from_dict = MagicMock(return_value=MagicMock())

    def test_success(self):
        self.playback_api.get_test_summary_list_without_preload_content = Mock(
            return_value=_ok_response({
                "items": [{
                    "testId": "t1",
                    "successRate": 0.95,
                    "locationStatusList": [
                        {"locationId": "loc-1", "totalTestRuns": 20, "successRuns": 19}
                    ]
                }]
            })
        )
        result = asyncio.run(self.client.get_test_summary_list(
            payload={
                "metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]
            }
        ))
        self.assertNotIn("error", result)

    def test_capital_t_filter_is_renamed(self):
        from instana_client.models.get_test_summary_result import GetTestSummaryResult
        self.playback_api.get_test_summary_list_without_preload_content = Mock(
            return_value=_ok_response({"items": []})
        )
        asyncio.run(self.client.get_test_summary_list(payload={
            "metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}],
            "TagFilterExpression": _CAPITAL_T_FILTER,
        }))
        sent = GetTestSummaryResult.from_dict.call_args[0][0]
        self.assertEqual(sent["tagFilterExpression"]["stringValue"], "loc-1")
        self.assertNotIn("TagFilterExpression", sent)

    def test_missing_metrics_field(self):
        result = asyncio.run(self.client.get_test_summary_list(
            payload={"timeFrame": {"to": 0, "windowSize": 1800000}}
        ))
        self.assertTrue(result.get("elicitation_needed"))
        self.assertTrue(any("metrics" in e for e in result.get("api_error", [])))

    def test_invalid_payload_type(self):
        """Non-dict, non-string payload returns parse error (line 515)."""
        result = asyncio.run(self.client.get_test_summary_list(payload=True))
        self.assertIn("error", result)

    def test_from_dict_raises(self):
        """GetTestSummaryResult.from_dict raising is caught (lines 523-525)."""
        from instana_client.models.get_test_summary_result import GetTestSummaryResult
        GetTestSummaryResult.from_dict = MagicMock(side_effect=ValueError("bad"))
        result = asyncio.run(self.client.get_test_summary_list(
            payload={"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]}
        ))
        self.assertIn("error", result)
        self.assertIn("GetTestSummaryResult", result["error"])

    def test_http_error(self):
        self.playback_api.get_test_summary_list_without_preload_content = Mock(
            return_value=_error_response(503)
        )
        result = asyncio.run(self.client.get_test_summary_list(
            payload={"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]}
        ))
        self.assertIn("error", result)

    def test_http_error_decode_fails(self):
        """decode_response raising inside the HTTP error branch (lines 539-541)."""
        bad_response = Mock()
        bad_response.status = 503
        bad_response.data = None
        bad_response.headers = {}
        self.playback_api.get_test_summary_list_without_preload_content = Mock(
            return_value=bad_response
        )
        result = asyncio.run(self.client.get_test_summary_list(
            payload={"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]}
        ))
        self.assertIn("error", result)

    def test_outer_exception(self):
        """Top-level exception in get_test_summary_list is caught (lines 545-547)."""
        self.playback_api.get_test_summary_list_without_preload_content = Mock(
            side_effect=Exception("boom")
        )
        result = asyncio.run(self.client.get_test_summary_list(
            payload={"metrics": [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}]}
        ))
        self.assertIn("error", result)


class TestGetSyntheticResultMetadata(unittest.TestCase):
    """Tests for get_synthetic_result_metadata."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api

    def test_success(self):
        self.playback_api.get_synthetic_result_metadata_without_preload_content = Mock(
            return_value=_ok_response({"types": [{"type": "HAR", "count": 1}]})
        )
        result = asyncio.run(
            self.client.get_synthetic_result_metadata(testid="t1", testresultid="r1")
        )
        self.assertNotIn("error", result)
        self.playback_api.get_synthetic_result_metadata_without_preload_content.assert_called_once_with(
            testid="t1", testresultid="r1", start_time=None
        )

    def test_missing_testid(self):
        result = asyncio.run(
            self.client.get_synthetic_result_metadata(testid=None, testresultid="r1")
        )
        self.assertIn("error", result)

    def test_missing_testresultid(self):
        result = asyncio.run(
            self.client.get_synthetic_result_metadata(testid="t1", testresultid=None)
        )
        self.assertIn("error", result)

    def test_http_error(self):
        self.playback_api.get_synthetic_result_metadata_without_preload_content = Mock(
            return_value=_error_response(404)
        )
        result = asyncio.run(
            self.client.get_synthetic_result_metadata(testid="t1", testresultid="r1")
        )
        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])

    def test_http_error_decode_fails(self):
        """decode_response raising inside the HTTP error branch (lines 598-600)."""
        bad_response = Mock()
        bad_response.status = 503
        bad_response.data = None
        bad_response.headers = {}
        self.playback_api.get_synthetic_result_metadata_without_preload_content = Mock(
            return_value=bad_response
        )
        result = asyncio.run(
            self.client.get_synthetic_result_metadata(testid="t1", testresultid="r1")
        )
        self.assertIn("error", result)

    def test_outer_exception(self):
        """Top-level exception in get_synthetic_result_metadata is caught (lines 606-608)."""
        self.playback_api.get_synthetic_result_metadata_without_preload_content = Mock(
            side_effect=Exception("boom")
        )
        result = asyncio.run(
            self.client.get_synthetic_result_metadata(testid="t1", testresultid="r1")
        )
        self.assertIn("error", result)


class TestGetSyntheticResultDetailData(unittest.TestCase):
    """Tests for get_synthetic_result_detail_data."""

    def setUp(self):
        self.playback_api = MagicMock()
        self.client = SyntheticTestPlaybackResultsMCPTools(
            read_token="test_token",
            base_url="https://test.instana.io"
        )
        self.client.playback_api = self.playback_api

    def test_success_har(self):
        self.playback_api.get_synthetic_result_detail_data_without_preload_content = Mock(
            return_value=_ok_response({"log": {"version": "1.2"}})
        )
        result = asyncio.run(
            self.client.get_synthetic_result_detail_data(
                testid="t1", testresultid="r1", detail_type="HAR"
            )
        )
        self.assertNotIn("error", result)
        self.playback_api.get_synthetic_result_detail_data_without_preload_content.assert_called_once_with(
            testid="t1", testresultid="r1", type="HAR", name=None, start_time=None
        )

    def test_success_with_name(self):
        self.playback_api.get_synthetic_result_detail_data_without_preload_content = Mock(
            return_value=_ok_response({"content": "log line"})
        )
        result = asyncio.run(
            self.client.get_synthetic_result_detail_data(
                testid="t1", testresultid="r1", detail_type="LOGS", name="stdout.log"
            )
        )
        self.assertNotIn("error", result)

    def test_missing_testid(self):
        result = asyncio.run(
            self.client.get_synthetic_result_detail_data(
                testid=None, testresultid="r1", detail_type="HAR"
            )
        )
        self.assertIn("error", result)

    def test_missing_testresultid(self):
        result = asyncio.run(
            self.client.get_synthetic_result_detail_data(
                testid="t1", testresultid=None, detail_type="HAR"
            )
        )
        self.assertIn("error", result)

    def test_http_error(self):
        self.playback_api.get_synthetic_result_detail_data_without_preload_content = Mock(
            return_value=_error_response(404)
        )
        result = asyncio.run(
            self.client.get_synthetic_result_detail_data(
                testid="t1", testresultid="r1", detail_type="HAR"
            )
        )
        self.assertIn("error", result)
        self.assertIn("HTTP 404", result["error"])

    def test_exception(self):
        self.playback_api.get_synthetic_result_detail_data_without_preload_content = Mock(
            side_effect=Exception("I/O error")
        )
        result = asyncio.run(
            self.client.get_synthetic_result_detail_data(
                testid="t1", testresultid="r1", detail_type="SCREENSHOT"
            )
        )
        self.assertIn("error", result)


if __name__ == '__main__':
    unittest.main()
