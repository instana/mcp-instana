"""
Unit tests for the ApplicationCallGroupMCPTools class
"""

import asyncio
import logging
import os
import sys
import unittest
from datetime import datetime
from functools import wraps
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import src


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use DEBUG level to see all logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Get the application logger and enable it for debugging
app_logger = logging.getLogger('src.application.application_call_group')
app_logger.setLevel(logging.DEBUG)
# Comment out the NullHandler to see logs
# app_logger.handlers = []
# app_logger.addHandler(NullHandler())
# app_logger.propagate = False  # Prevent logs from propagating to parent loggers

# Suppress traceback printing for expected test exceptions
import traceback

original_print_exception = traceback.print_exception
original_print_exc = traceback.print_exc

def custom_print_exception(etype, value, tb, limit=None, file=None, chain=True):
    # Skip printing exceptions from the mock side_effect
    if isinstance(value, Exception) and str(value) == "Test error":
        return
    original_print_exception(etype, value, tb, limit, file, chain)

def custom_print_exc(limit=None, file=None, chain=True):
    # Just do nothing - this will suppress all traceback printing from print_exc
    pass

traceback.print_exception = custom_print_exception
traceback.print_exc = custom_print_exc

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Just pass the API client directly
            kwargs['api_client'] = self.analyze_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Create mock modules and classes BEFORE importing anything from src
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.application_analyze_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_call_groups'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_analyze_api = MagicMock()
mock_get_call_groups = MagicMock()

# Add __name__ attribute to mock classes
mock_analyze_api.__name__ = "ApplicationAnalyzeApi"
mock_get_call_groups.__name__ = "GetCallGroups"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_analyze_api'].ApplicationAnalyzeApi = mock_analyze_api
sys.modules['instana_client.models.get_call_groups'].GetCallGroups = mock_get_call_groups

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Now import the class to test - it will use our mocked decorator
    from src.application.application_call_group import ApplicationCallGroupMCPTools


class TestApplicationCallGroupMCPTools(unittest.TestCase):
    """Test the ApplicationCallGroupMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_analyze_api.reset_mock()
        mock_get_call_groups.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.analyze_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationCallGroupMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.analyze_api = self.analyze_api

    def test_init(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)

    def test_get_grouped_calls_metrics_with_elicitation(self):
        """Test get_grouped_calls_metrics returns elicitation when metrics missing"""
        # Call without metrics (required parameter)
        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=None,
            time_frame=None,
            group=None
        ))

        # Check that elicitation is returned
        self.assertIn("elicitation_needed", result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("missing_parameters", result)
        self.assertIn("metrics", result["missing_parameters"])

    def test_get_grouped_calls_metrics_with_defaults(self):
        """Test get_grouped_calls_metrics applies defaults when parameters not provided"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {
                    "name": "test-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]],
                        "latency.mean": [[1234567890, 50.5]]
                    }
                }
            ]
        }
        self.analyze_api.get_call_group.return_value = mock_result

        # Mock GetCallGroups.from_dict
        mock_get_call_groups.from_dict.return_value = MagicMock()

        # Call with all parameters to avoid elicitation
        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
        ))

        # Verify API was called
        self.analyze_api.get_call_group.assert_called_once()
        self.assertIn("items", result)

    def test_get_grouped_calls_metrics_success(self):
        """Test get_grouped_calls_metrics with successful response"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {
                    "name": "test-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]],
                        "latency.mean": [[1234567890, 50.5]]
                    }
                }
            ]
        }
        self.analyze_api.get_call_group.return_value = mock_result

        # Mock GetCallGroups.from_dict
        mock_get_call_groups.from_dict.return_value = MagicMock()

        # Call with all parameters
        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
        ))

        # Check that the result is processed
        self.assertIn("items", result)
        self.assertEqual(len(result["items"]), 1)

    def test_get_grouped_calls_metrics_alias_group_is_normalised_before_sdk(self):
        """groupByTag/groupByTagEntity must reach GetCallGroups.from_dict as the
        canonical keys; the SDK silently drops the aliases."""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"items": []}
        self.analyze_api.get_call_group.return_value = mock_result
        mock_get_call_groups.from_dict.return_value = MagicMock()

        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group={"groupByTag": "service.name", "groupByTagEntity": "DESTINATION"},
        ))

        self.assertNotIn("elicitation_needed", result)
        sent_group = mock_get_call_groups.from_dict.call_args[0][0]["group"]
        self.assertEqual(
            sent_group,
            {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"},
        )

    def test_get_grouped_calls_metrics_error(self):
        """Test get_grouped_calls_metrics error handling"""
        # Mock the API to raise an exception
        self.analyze_api.get_call_group.side_effect = Exception("Test error")

        # Mock GetCallGroups.from_dict
        mock_get_call_groups.from_dict.return_value = MagicMock()

        # Call the method
        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
        ))

        # Check that error is returned
        self.assertIn("error", result)
        self.assertIn("Failed to get grouped calls metrics", result["error"])

    def test_process_metrics_response_with_valid_data(self):
        """Test _process_metrics_response with valid metrics data"""
        result_dict = {
            "items": [
                {
                    "name": "test-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]],
                        "latency.mean": [[1234567890, 50.5]],
                        "errors.mean": [[1234567890, 0.05]]
                    }
                }
            ]
        }

        processed = self.client._process_metrics_response(result_dict)

        # Check that metrics are extracted
        self.assertIn("items", processed)
        self.assertEqual(len(processed["items"]), 1)
        item = processed["items"][0]
        self.assertIn("metrics_extracted", item)
        self.assertIn("metrics_summary", item)
        self.assertIn("interpretation", item)

        # Check specific metric extractions
        self.assertIn("calls.sum", item["metrics_extracted"])
        self.assertEqual(item["metrics_extracted"]["calls.sum"]["value"], 100)
        self.assertIn("total_calls", item["metrics_summary"])
        self.assertEqual(item["metrics_summary"]["total_calls"], 100)

    def test_process_metrics_response_with_empty_items(self):
        """Test _process_metrics_response with empty items"""
        result_dict = {"items": []}

        processed = self.client._process_metrics_response(result_dict)

        # Check that empty result is handled
        self.assertIn("items", processed)
        self.assertEqual(len(processed["items"]), 0)

    def test_process_metrics_response_with_invalid_data(self):
        """Test _process_metrics_response with invalid data structure"""
        result_dict = {"items": [{"name": "test", "metrics": "invalid"}]}

        processed = self.client._process_metrics_response(result_dict)

        # Should return processed items without crashing
        self.assertIn("items", processed)

    def test_process_metrics_response_error_handling(self):
        """Test _process_metrics_response error handling"""
        # Pass non-dict to trigger error path
        result_dict = "invalid"

        processed = self.client._process_metrics_response(result_dict)

        # Should return original on error
        self.assertEqual(processed, result_dict)

    def test_should_aggregate_results_true(self):
        """Test _should_aggregate_results returns True for latency MEAN with endpoint grouping"""
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]
        group = {"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"}

        result = self.client._should_aggregate_results(metrics, group)

        self.assertTrue(result)

    def test_should_aggregate_results_false_multiple_metrics(self):
        """Test _should_aggregate_results returns False for multiple metrics"""
        metrics = [
            {"metric": "latency", "aggregation": "MEAN"},
            {"metric": "calls", "aggregation": "SUM"}
        ]
        group = {"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"}

        result = self.client._should_aggregate_results(metrics, group)

        self.assertFalse(result)

    def test_should_aggregate_results_false_different_metric(self):
        """Test _should_aggregate_results returns False for non-latency metric"""
        metrics = [{"metric": "calls", "aggregation": "SUM"}]
        group = {"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"}

        result = self.client._should_aggregate_results(metrics, group)

        self.assertFalse(result)

    def test_should_aggregate_results_false_no_metrics(self):
        """Test _should_aggregate_results returns False when metrics is None"""
        result = self.client._should_aggregate_results(None, {"groupbyTag": "endpoint.name"})

        self.assertFalse(result)

    def test_should_aggregate_results_false_no_group(self):
        """Test _should_aggregate_results returns False when group is None"""
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]
        result = self.client._should_aggregate_results(metrics, None)

        self.assertFalse(result)

    def test_aggregate_grouped_results_success(self):
        """Test _aggregate_grouped_results with valid data"""
        result_dict = {
            "items": [
                {
                    "name": "endpoint1",
                    "metrics_extracted": {
                        "latency.mean": {"value": 50.0}
                    }
                },
                {
                    "name": "endpoint2",
                    "metrics_extracted": {
                        "latency.mean": {"value": 60.0}
                    }
                }
            ]
        }
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        aggregated = self.client._aggregate_grouped_results(result_dict, metrics)

        # Check aggregation
        self.assertTrue(aggregated["aggregated"])
        self.assertIn("overall_metrics", aggregated)
        self.assertIn("latency.mean", aggregated["overall_metrics"])
        # Average of 50 and 60 should be 55
        self.assertEqual(aggregated["overall_metrics"]["latency.mean"]["value"], 55.0)
        self.assertIn("summary", aggregated)

    def test_aggregate_grouped_results_empty_items(self):
        """Test _aggregate_grouped_results with empty items"""
        result_dict = {"items": []}
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        aggregated = self.client._aggregate_grouped_results(result_dict, metrics)

        # Check empty result handling
        self.assertTrue(aggregated["aggregated"])
        self.assertIn("No data available", aggregated["message"])
        self.assertEqual(aggregated["overall_metrics"], {})

    def test_aggregate_grouped_results_error_handling(self):
        """Test _aggregate_grouped_results error handling"""
        # Pass invalid data to trigger error path
        result_dict = "invalid"
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        aggregated = self.client._aggregate_grouped_results(result_dict, metrics)

        # Should return original on error
        self.assertEqual(aggregated, result_dict)

    def test_check_elicitation_missing_metrics(self):
        """Test _check_elicitation_for_call_group_metrics with missing metrics"""
        result = self.client._check_elicitation_for_call_group_metrics(
            metrics=None,
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "service.name"}
        )

        # Should return elicitation request
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("metrics", result["missing_parameters"])

    def test_check_elicitation_missing_time_frame(self):
        """Test _check_elicitation_for_call_group_metrics with missing time_frame"""
        result = self.client._check_elicitation_for_call_group_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame=None,
            group={"groupbyTag": "service.name"}
        )

        # Should return elicitation request
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("time_frame", result["missing_parameters"])

    def test_check_elicitation_missing_group(self):
        """Test _check_elicitation_for_call_group_metrics with missing group"""
        result = self.client._check_elicitation_for_call_group_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group=None
        )

        # Should return elicitation request
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("group", result["missing_parameters"])

    def test_check_elicitation_all_params_provided(self):
        """Test _check_elicitation_for_call_group_metrics with all parameters"""
        result = self.client._check_elicitation_for_call_group_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "service.name"}
        )

        # Should return None (no elicitation needed)
        self.assertIsNone(result)

    def test_create_elicitation_request(self):
        """Test _create_elicitation_request creates proper format"""
        missing_params = [
            {
                "name": "metrics",
                "description": "List of metric names",
                "examples": [{"metric": "calls", "aggregation": "SUM"}],
                "type": "list"
            }
        ]

        result = self.client._create_elicitation_request(missing_params)

        # Check elicitation format
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("message", result)
        self.assertIn("missing_parameters", result)
        self.assertEqual(result["missing_parameters"], ["metrics"])
        self.assertIn("parameter_details", result)
        self.assertIn("instructions", result)
        self.assertIn("get_grouped_calls_metrics", result["instructions"])

    def test_get_grouped_calls_metrics_full_flow_with_all_params(self):
        """Test full flow through get_grouped_calls_metrics with all parameters"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {
                    "name": "test-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]],
                        "latency.mean": [[1234567890, 50.5]]
                    }
                }
            ]
        }
        self.analyze_api.get_call_group.return_value = mock_result

        # Mock GetCallGroups.from_dict
        mock_get_call_groups_instance = MagicMock()
        mock_get_call_groups_instance.to_dict.return_value = {"test": "data"}
        mock_get_call_groups.from_dict.return_value = mock_get_call_groups_instance

        # Call with all optional parameters to cover all branches
        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=[{"metric": "calls", "aggregation": "SUM"}],
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"},
            tag_filter_expression={"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
            include_internal=True,
            include_synthetic=True,
            order={"by": "calls", "direction": "DESC"},
            pagination={"retrievalSize": 20},
            fill_time_series=True
        ))

        # Verify the API was called
        self.analyze_api.get_call_group.assert_called_once()
        # Verify result is processed
        self.assertIn("items", result)

    def test_get_grouped_calls_metrics_with_aggregation_flow(self):
        """Test flow when results should be aggregated"""
        # Mock the API response with multiple endpoints
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {
                    "name": "endpoint1",
                    "metrics": {
                        "latency.mean": [[1234567890, 50.0]]
                    }
                },
                {
                    "name": "endpoint2",
                    "metrics": {
                        "latency.mean": [[1234567890, 60.0]]
                    }
                }
            ]
        }
        self.analyze_api.get_call_group.return_value = mock_result

        # Mock GetCallGroups.from_dict
        mock_get_call_groups.from_dict.return_value = MagicMock()

        # Call with latency MEAN and endpoint.name grouping to trigger aggregation
        result = asyncio.run(self.client.get_grouped_calls_metrics(
            metrics=[{"metric": "latency", "aggregation": "MEAN"}],
            time_frame={"windowSize": 3600000},
            group={"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"}
        ))

        # Verify aggregation occurred
        self.assertTrue(result.get("aggregated", False))
        self.assertIn("overall_metrics", result)

    def test_process_metrics_response_with_all_metric_types(self):
        """Test _process_metrics_response with all metric types"""
        result_dict = {
            "items": [
                {
                    "name": "test-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]],
                        "latency.mean": [[1234567890, 50.5]],
                        "errors.mean": [[1234567890, 0.05]],
                        "erroneousCalls.sum": [[1234567890, 5]]
                    }
                }
            ]
        }

        processed = self.client._process_metrics_response(result_dict)

        # Check all metric types are processed
        item = processed["items"][0]
        self.assertIn("total_calls", item["metrics_summary"])
        self.assertIn("latency_ms", item["metrics_summary"])
        self.assertIn("error_rate", item["metrics_summary"])
        self.assertIn("erroneous_calls", item["metrics_summary"])

        # Check interpretation includes all metrics
        self.assertIn("Total Calls", item["interpretation"])
        self.assertIn("Latency", item["interpretation"])
        self.assertIn("Error Rate", item["interpretation"])
        self.assertIn("Erroneous Calls", item["interpretation"])

    def test_process_metrics_response_with_non_dict_item(self):
        """Test _process_metrics_response handles non-dict items"""
        result_dict = {
            "items": [
                "invalid_item",
                {
                    "name": "valid-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]]
                    }
                }
            ]
        }

        processed = self.client._process_metrics_response(result_dict)

        # Should handle both items
        self.assertEqual(len(processed["items"]), 2)
        # First item should be unchanged
        self.assertEqual(processed["items"][0], "invalid_item")

    def test_aggregate_grouped_results_with_non_dict_item(self):
        """Test _aggregate_grouped_results handles non-dict items"""
        result_dict = {
            "items": [
                "invalid_item",
                {
                    "name": "endpoint1",
                    "metrics_extracted": {
                        "latency.mean": {"value": 50.0}
                    }
                }
            ]
        }
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        aggregated = self.client._aggregate_grouped_results(result_dict, metrics)

        # Should aggregate only valid items
        self.assertTrue(aggregated["aggregated"])
        self.assertEqual(aggregated["total_groups_analyzed"], 2)

    def test_aggregate_grouped_results_with_numeric_metric_value(self):
        """Test _aggregate_grouped_results handles numeric metric values"""
        result_dict = {
            "items": [
                {
                    "name": "endpoint1",
                    "metrics_extracted": {
                        "latency.mean": 50.0  # Direct numeric value
                    }
                }
            ]
        }
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        aggregated = self.client._aggregate_grouped_results(result_dict, metrics)

        # Should handle numeric values
        self.assertTrue(aggregated["aggregated"])
        self.assertIn("latency.mean", aggregated["overall_metrics"])

    def test_aggregate_grouped_results_with_non_latency_metric(self):
        """Test _aggregate_grouped_results with non-latency metrics"""
        result_dict = {
            "items": [
                {
                    "name": "service1",
                    "metrics_extracted": {
                        "calls.sum": {"value": 100.0}
                    }
                }
            ]
        }
        metrics = [{"metric": "calls", "aggregation": "SUM"}]

        aggregated = self.client._aggregate_grouped_results(result_dict, metrics)

        # Should aggregate non-latency metrics too
        self.assertTrue(aggregated["aggregated"])
        self.assertIn("calls.sum", aggregated["overall_metrics"])
        # Should not have latency-specific summary
        self.assertNotIn("summary", aggregated)

    def test_create_elicitation_request_with_time_frame(self):
        """Test _create_elicitation_request with time_frame parameter"""
        missing_params = [
            {
                "name": "time_frame",
                "description": "Time range",
                "examples": [{"windowSize": 3600000}],
                "type": "dict"
            }
        ]

        result = self.client._create_elicitation_request(missing_params)

        # Check time_frame specific formatting
        self.assertIn("time_frame", result["message"])
        self.assertIn("last hour", result["message"])

    def test_create_elicitation_request_with_group(self):
        """Test _create_elicitation_request with group parameter"""
        missing_params = [
            {
                "name": "group",
                "description": "Grouping config",
                "examples": [{"groupbyTag": "service.name"}],
                "type": "dict"
            }
        ]

        result = self.client._create_elicitation_request(missing_params)

        # Check group specific formatting
        self.assertIn("group", result["message"])
        self.assertIn("service.name", result["message"])

    def test_create_elicitation_request_with_other_param(self):
        """Test _create_elicitation_request with other parameter types"""
        missing_params = [
            {
                "name": "other_param",
                "description": "Other parameter",
                "examples": ["example1", "example2", "example3", "example4"],
                "type": "string"
            }
        ]

        result = self.client._create_elicitation_request(missing_params)

        # Check generic parameter formatting (should use first 3 examples)
        self.assertIn("other_param", result["message"])

    def test_debug_log_is_called(self):
        """Test that the debug log at line 100 is actually called"""
        # Mock the API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {
                    "name": "test-service",
                    "metrics": {
                        "calls.sum": [[1234567890, 100]]
                    }
                }
            ]
        }
        self.analyze_api.get_call_group.return_value = mock_result
        mock_get_call_groups.from_dict.return_value = MagicMock()

        # Patch the logger to verify it's called
        with patch('src.application.application_call_group.logger') as mock_logger:
            # Call with all parameters to bypass elicitation
            result = asyncio.run(self.client.get_grouped_calls_metrics(
                metrics=[{"metric": "calls", "aggregation": "SUM"}],
                time_frame={"windowSize": 3600000},
                group={"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
            ))

            # Verify the debug log was called
            mock_logger.debug.assert_any_call(
                "get_grouped_calls_metrics called with metrics=[{'metric': 'calls', 'aggregation': 'SUM'}], group={'groupbyTag': 'service.name', 'groupbyTagEntity': 'DESTINATION'}"
            )

            # Also verify the method completed successfully
            self.assertIn("items", result)

if __name__ == '__main__':
    unittest.main()

