"""
Unit tests for the ApplicationAnalyzeMCPTools class
"""


import asyncio
import logging
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.application.application_analyze')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False  # Prevent logs from propagating to parent loggers


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

# Create mock modules and classes
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_topology_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_resources_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_catalog_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_analyze_api'] = MagicMock()
sys.modules['instana_client.api.application_resources_api'] = MagicMock()
sys.modules['instana_client.api.application_metrics_api'] = MagicMock()
sys.modules['instana_client.api.application_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.api.application_catalog_api'] = MagicMock()
sys.modules['instana_client.api.application_analyze_api'] = MagicMock()
sys.modules['instana_client.api.events_api'] = MagicMock()
sys.modules['instana_client.api.log_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_available_metrics_query'] = MagicMock()
sys.modules['instana_client.models.get_available_plugins_query'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_query'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_groups_query'] = MagicMock()
sys.modules['instana_client.models.get_traces'] = MagicMock()
sys.modules['instana_client.models.get_call_groups'] = MagicMock()
sys.modules['fastmcp'] = MagicMock()
sys.modules['fastmcp.server'] = MagicMock()
sys.modules['fastmcp.server.dependencies'] = MagicMock()
sys.modules['pydantic'] = MagicMock()

# Mock the get_http_headers function
mock_get_http_headers = MagicMock(return_value={})
sys.modules['fastmcp.server.dependencies'].get_http_headers = mock_get_http_headers

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_analyze_api = MagicMock()
mock_topology_api = MagicMock()
mock_resources_api = MagicMock()
mock_catalog_api = MagicMock()
mock_app_resources_api = MagicMock()
mock_app_metrics_api = MagicMock()
mock_app_alert_config_api = MagicMock()
mock_app_catalog_api = MagicMock()
mock_app_analyze_api = MagicMock()
mock_events_api = MagicMock()
mock_log_alert_config_api = MagicMock()
mock_metrics_query = MagicMock()
mock_plugins_query = MagicMock()
mock_infra_query = MagicMock()
mock_groups_query = MagicMock()
mock_get_traces = MagicMock()
mock_get_call_groups = MagicMock()

# Add __name__ attribute to mock classes
mock_analyze_api.__name__ = "InfrastructureAnalyzeApi"
mock_topology_api.__name__ = "InfrastructureTopologyApi"
mock_resources_api.__name__ = "InfrastructureResourcesApi"
mock_catalog_api.__name__ = "InfrastructureCatalogApi"
mock_app_resources_api.__name__ = "ApplicationResourcesApi"
mock_app_metrics_api.__name__ = "ApplicationMetricsApi"
mock_app_alert_config_api.__name__ = "ApplicationAlertConfigurationApi"
mock_app_catalog_api.__name__ = "ApplicationCatalogApi"
mock_app_analyze_api.__name__ = "ApplicationAnalyzeApi"
mock_events_api.__name__ = "EventsApi"
mock_log_alert_config_api.__name__ = "LogAlertConfigurationApi"
mock_get_traces.__name__ = "GetTraces"
mock_get_call_groups.__name__ = "GetCallGroups"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.infrastructure_analyze_api'].InfrastructureAnalyzeApi = mock_analyze_api
sys.modules['instana_client.api.infrastructure_topology_api'].InfrastructureTopologyApi = mock_topology_api
sys.modules['instana_client.api.infrastructure_resources_api'].InfrastructureResourcesApi = mock_resources_api
sys.modules['instana_client.api.infrastructure_catalog_api'].InfrastructureCatalogApi = mock_catalog_api
sys.modules['instana_client.api.application_resources_api'].ApplicationResourcesApi = mock_app_resources_api
sys.modules['instana_client.api.application_metrics_api'].ApplicationMetricsApi = mock_app_metrics_api
sys.modules['instana_client.api.application_alert_configuration_api'].ApplicationAlertConfigurationApi = mock_app_alert_config_api
sys.modules['instana_client.api.application_catalog_api'].ApplicationCatalogApi = mock_app_catalog_api
sys.modules['instana_client.api.application_analyze_api'].ApplicationAnalyzeApi = mock_app_analyze_api
sys.modules['instana_client.api.events_api'].EventsApi = mock_events_api
sys.modules['instana_client.api.log_alert_configuration_api'].LogAlertConfigurationApi = mock_log_alert_config_api
sys.modules['instana_client.models.get_available_metrics_query'].GetAvailableMetricsQuery = mock_metrics_query
sys.modules['instana_client.models.get_available_plugins_query'].GetAvailablePluginsQuery = mock_plugins_query
sys.modules['instana_client.models.get_infrastructure_query'].GetInfrastructureQuery = mock_infra_query
sys.modules['instana_client.models.get_infrastructure_groups_query'].GetInfrastructureGroupsQuery = mock_groups_query
sys.modules['instana_client.models.get_traces'].GetTraces = mock_get_traces
sys.modules['instana_client.models.get_call_groups'].GetCallGroups = mock_get_call_groups

# Patch the with_header_auth decorator
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    # Import the class to test
    from src.application.application_analyze import ApplicationAnalyzeMCPTools
class TestApplicationAnalyzeMCPTools(unittest.TestCase):
    """Test the ApplicationAnalyzeMCPTools class"""


    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_app_analyze_api.reset_mock()
        mock_get_traces.reset_mock()
        mock_get_call_groups.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.app_analyze_api = mock_app_analyze_api

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = ApplicationAnalyzeMCPTools(read_token=self.read_token, base_url=self.base_url)

        # Set up the client's API attribute
        self.client.analyze_api = mock_app_analyze_api

        # Patch the logger to prevent logging during tests
        patcher = patch('src.application.application_analyze.logger')
        self.mock_logger = patcher.start()
        self.addCleanup(patcher.stop)
    def tearDown(self):
        """Tear down test fixtures"""
        # No need to stop patchers since we're directly mocking the module imports
        pass
    def test_init(self):
        """Test that the client is initialized with the correct values"""
        # Since we're mocking at the module level, we can't easily test the initialization
        # Just verify that the client was created with the correct values
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)
    def test_get_call_details_success(self):
        """Test get_call_details with a successful response"""
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={
            "id": "call123",
            "traceId": "trace123",
            "timestamp": 1625097600000,
            "duration": 150,
            "erroneous": False,
            "service": "test-service",
            "endpoint": "/api/test"
        })
        self.client.analyze_api.get_call_details = MagicMock(return_value=mock_response)
        trace_id = "trace123"
        call_id = "call123"
        result = asyncio.run(self.client.get_call_details(trace_id=trace_id, call_id=call_id))
        self.client.analyze_api.get_call_details.assert_called_once_with(
            trace_id=trace_id,
            call_id=call_id
        )
        self.assertEqual(result["id"], "call123")
        self.assertEqual(result["traceId"], "trace123")
        self.assertEqual(result["service"], "test-service")

    def test_get_call_details_missing_params(self):
        """Test get_call_details with missing parameters"""
        result = asyncio.run(self.client.get_call_details(trace_id="", call_id="call123"))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Both trace_id and call_id must be provided", result["error"])
        result = asyncio.run(self.client.get_call_details(trace_id="trace123", call_id=""))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Both trace_id and call_id must be provided", result["error"])

    def test_get_call_details_error(self):
        """Test get_call_details error handling"""
        self.client.analyze_api.get_call_details = MagicMock(side_effect=Exception("Test error"))
        result = asyncio.run(self.client.get_call_details(trace_id="trace123", call_id="call123"))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Failed to get call details", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_trace_details_success(self):
        """Test get_trace_details with a successful response"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={
            "id": "trace123",
            "timestamp": 1625097600000,
            "duration": 250,
            "erroneous": False,
            "calls": [
                {"id": "call123", "service": "service-a", "endpoint": "/api/test"},
                {"id": "call456", "service": "service-b", "endpoint": "/api/other"}
            ]
        })
        self.client.analyze_api.get_trace_download = MagicMock(return_value=mock_response)
        trace_id = "trace123"
        result = asyncio.run(self.client.get_trace_details(id=trace_id))
        self.client.analyze_api.get_trace_download.assert_called_once_with(
            id=trace_id,
            retrieval_size=None,
            offset=None,
            ingestion_time=None
        )
        self.assertEqual(result["id"], "trace123")
        self.assertEqual(len(result["calls"]), 2)
        self.assertEqual(result["calls"][0]["service"], "service-a")
        self.assertEqual(result["calls"][1]["service"], "service-b")

    def test_get_trace_details_with_params(self):
        """Test get_trace_details with additional parameters"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={"id": "trace123"})
        self.client.analyze_api.get_trace_download = MagicMock(return_value=mock_response)
        trace_id = "trace123"
        retrieval_size = 100
        offset = 10
        ingestion_time = 1625097600000
        result = asyncio.run(self.client.get_trace_details(
            id=trace_id,
            retrievalSize=retrieval_size,
            offset=offset,
            ingestionTime=ingestion_time
        ))
        self.client.analyze_api.get_trace_download.assert_called_once_with(
            id=trace_id,
            retrieval_size=retrieval_size,
            offset=offset,
            ingestion_time=ingestion_time
        )
        self.assertEqual(result["id"], "trace123")

    def test_get_trace_details_missing_id(self):
        """Test get_trace_details with missing ID"""
        result = asyncio.run(self.client.get_trace_details(id=""))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Trace ID must be provided", result["error"])

    def test_get_trace_details_invalid_params(self):
        """Test get_trace_details with invalid parameters"""
        result = asyncio.run(self.client.get_trace_details(id="trace123", offset=10))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("If offset is provided, ingestionTime must also be provided", result["error"])
        result = asyncio.run(self.client.get_trace_details(id="trace123", retrievalSize=20000))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("retrievalSize must be between 1 and 10000", result["error"])

    def test_get_trace_details_error(self):
        """Test get_trace_details error handling"""
        self.client.analyze_api.get_trace_download = MagicMock(side_effect=Exception("Test error"))
        result = asyncio.run(self.client.get_trace_details(id="trace123"))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Failed to get trace details", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_trace_details_edge_case_min_retrieval_size(self):
        """Test get_trace_details with minimum valid retrieval size"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={"id": "trace123"})
        self.client.analyze_api.get_trace_download = MagicMock(return_value=mock_response)

        result = asyncio.run(self.client.get_trace_details(id="trace123", retrievalSize=1))
        self.client.analyze_api.get_trace_download.assert_called_once_with(
            id="trace123",
            retrieval_size=1,
            offset=None,
            ingestion_time=None
        )
        self.assertEqual(result["id"], "trace123")

    def test_get_all_traces_success(self):
        """Test get_all_traces with a successful response"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={
            "items": [
                {"id": "trace123", "timestamp": 1625097600000, "duration": 150},
                {"id": "trace456", "timestamp": 1625097700000, "duration": 200}
            ],
            "page": {"size": 2, "totalElements": 2}
        })
        self.client.analyze_api.get_traces = MagicMock(return_value=mock_response)
        self.mock_get_traces = MagicMock(return_value={})
        result = asyncio.run(self.client.get_all_traces())
        self.client.analyze_api.get_traces.assert_called_once()
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["id"], "trace123")
        self.assertEqual(result["items"][1]["id"], "trace456")

    def test_get_all_traces_with_params(self):
        """Test get_all_traces with parameters"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={"items": []})
        self.client.analyze_api.get_traces = MagicMock(return_value=mock_response)
        time_frame = {"from": 1625097600000, "to": 1625097700000}
        include_internal = True
        include_synthetic = False
        result = asyncio.run(self.client.get_all_traces(
            includeInternal=include_internal,
            includeSynthetic=include_synthetic,
            timeFrame=time_frame
        ))
        self.assertEqual(result["items"], [])

    def test_get_all_traces_with_all_params(self):
        """Test get_all_traces with all possible parameters"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={"items": []})
        self.client.analyze_api.get_traces = MagicMock(return_value=mock_response)

        # Create a local mock for GetTraces to avoid interference with other tests
        local_mock_get_traces = MagicMock()
        with patch('src.application.application_analyze.GetTraces', local_mock_get_traces):
            time_frame = {"from": 1625097600000, "to": 1625097700000}
            include_internal = True
            include_synthetic = False
            order = {"by": "timestamp", "direction": "DESC"}
            pagination = {"retrievalSize": 50}
            tag_filter = {"type": "TAG_FILTER", "name": "service", "value": "test-service"}

            asyncio.run(self.client.get_all_traces(
                includeInternal=include_internal,
                includeSynthetic=include_synthetic,
                order=order,
                pagination=pagination,
                tagFilterExpression=tag_filter,
                timeFrame=time_frame
            ))

            self.client.analyze_api.get_traces.assert_called_once()
            # Verify the GetTraces constructor was called with all parameters
            local_mock_get_traces.assert_called_once()
            call_args = local_mock_get_traces.call_args[1]
            self.assertEqual(call_args["includeInternal"], include_internal)
            self.assertEqual(call_args["includeSynthetic"], include_synthetic)
            self.assertEqual(call_args["order"], order)
            self.assertEqual(call_args["pagination"], pagination)
            self.assertEqual(call_args["tagFilterExpression"], tag_filter)
            self.assertEqual(call_args["timeFrame"], time_frame)

    def test_get_all_traces_error(self):
        """Test get_all_traces error handling"""
        self.client.analyze_api.get_traces = MagicMock(side_effect=Exception("Test error"))
        result = asyncio.run(self.client.get_all_traces())
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Failed to get all traces", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_grouped_trace_metrics_success(self):
        """Test get_grouped_trace_metrics with a successful response"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={
            "items": [
                {"group": {"name": "service-a"}, "metrics": {"latency": 150, "calls": 100}},
                {"group": {"name": "service-b"}, "metrics": {"latency": 200, "calls": 50}}
            ]
        })
        self.client.analyze_api.get_trace_groups = MagicMock(return_value=mock_response)
        group = {"groupbyTag": "service"}
        metrics = [{"metric": "latency", "aggregation": "MEAN"}, {"metric": "calls", "aggregation": "SUM"}]
        result = asyncio.run(self.client.get_grouped_trace_metrics(group=group, metrics=metrics))
        self.client.analyze_api.get_trace_groups.assert_called_once()
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["group"]["name"], "service-a")
        self.assertEqual(result["items"][1]["group"]["name"], "service-b")

    def test_get_grouped_trace_metrics_with_params(self):
        """Test get_grouped_trace_metrics with additional parameters"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={"items": []})
        self.client.analyze_api.get_trace_groups = MagicMock(return_value=mock_response)

        # Create a local mock for GetTraces to avoid interference with other tests
        local_mock_get_traces = MagicMock()
        with patch('src.application.application_analyze.GetTraces', local_mock_get_traces):
            group = {"groupbyTag": "service"}
            metrics = [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame = {"from": 1625097600000, "to": 1625097700000}
            include_internal = True
            include_synthetic = False
            fill_time_series = True
            order = {"by": "latency", "direction": "DESC"}
            pagination = {"retrievalSize": 50}
            tag_filter = {"type": "TAG_FILTER", "name": "endpoint", "value": "/api/test"}

            asyncio.run(self.client.get_grouped_trace_metrics(
                group=group,
                metrics=metrics,
                includeInternal=include_internal,
                includeSynthetic=include_synthetic,
                fill_time_series=fill_time_series,
                order=order,
                pagination=pagination,
                tagFilterExpression=tag_filter,
                timeFrame=time_frame
            ))

            self.client.analyze_api.get_trace_groups.assert_called_once()
            # Verify the GetTraces constructor was called with all parameters
            local_mock_get_traces.assert_called_once()
            call_args = local_mock_get_traces.call_args[1]
            self.assertEqual(call_args["group"], group)
            self.assertEqual(call_args["metrics"], metrics)
            self.assertEqual(call_args["includeInternal"], include_internal)
            self.assertEqual(call_args["includeSynthetic"], include_synthetic)
            self.assertEqual(call_args["fillTimeSeries"], fill_time_series)
            self.assertEqual(call_args["order"], order)
            self.assertEqual(call_args["pagination"], pagination)
            self.assertEqual(call_args["tagFilterExpression"], tag_filter)
            self.assertEqual(call_args["timeFrame"], time_frame)

    def test_get_grouped_trace_metrics_error(self):
        """Test get_grouped_trace_metrics error handling"""
        self.client.analyze_api.get_trace_groups = MagicMock(side_effect=Exception("Test error"))
        group = {"groupbyTag": "service"}
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        result = asyncio.run(self.client.get_grouped_trace_metrics(group=group, metrics=metrics))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Failed to get grouped trace metrics", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_grouped_calls_metrics_success(self):
        """Test get_grouped_calls_metrics with a successful response"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={
            "items": [
                {"group": {"name": "endpoint-a"}, "metrics": {"latency": 150, "calls": 100}},
                {"group": {"name": "endpoint-b"}, "metrics": {"latency": 200, "calls": 50}}
            ]
        })
        self.client.analyze_api.get_call_group = MagicMock(return_value=mock_response)
        group = {"groupbyTag": "endpoint"}
        metrics = [{"metric": "latency", "aggregation": "MEAN"}, {"metric": "calls", "aggregation": "SUM"}]
        result = asyncio.run(self.client.get_grouped_calls_metrics(group=group, metrics=metrics))
        self.client.analyze_api.get_call_group.assert_called_once()
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["group"]["name"], "endpoint-a")
        self.assertEqual(result["items"][1]["group"]["name"], "endpoint-b")

    def test_get_grouped_calls_metrics_with_params(self):
        """Test get_grouped_calls_metrics with additional parameters"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={"items": []})
        self.client.analyze_api.get_call_group = MagicMock(return_value=mock_response)

        # Create a local mock for GetCallGroups to avoid interference with other tests
        local_mock_get_call_groups = MagicMock()
        with patch('src.application.application_analyze.GetCallGroups', local_mock_get_call_groups):
            group = {"groupbyTag": "endpoint"}
            metrics = [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame = {"from": 1625097600000, "to": 1625097700000}
            include_internal = True
            include_synthetic = False
            fill_time_series = True
            order = {"by": "latency", "direction": "DESC"}
            pagination = {"retrievalSize": 50}
            tag_filter = {"type": "TAG_FILTER", "name": "service", "value": "test-service"}

            asyncio.run(self.client.get_grouped_calls_metrics(
                group=group,
                metrics=metrics,
                includeInternal=include_internal,
                includeSynthetic=include_synthetic,
                fill_time_series=fill_time_series,
                order=order,
                pagination=pagination,
                tagFilterExpression=tag_filter,
                timeFrame=time_frame
            ))

            self.client.analyze_api.get_call_group.assert_called_once()
            # Verify the GetCallGroups constructor was called with all parameters
            local_mock_get_call_groups.assert_called_once()
            call_args = local_mock_get_call_groups.call_args[1]
            self.assertEqual(call_args["group"], group)
            self.assertEqual(call_args["metrics"], metrics)
            self.assertEqual(call_args["includeInternal"], include_internal)
            self.assertEqual(call_args["includeSynthetic"], include_synthetic)
            self.assertEqual(call_args["fillTimeSeries"], fill_time_series)
            self.assertEqual(call_args["order"], order)
            self.assertEqual(call_args["pagination"], pagination)
            self.assertEqual(call_args["tagFilterExpression"], tag_filter)
            self.assertEqual(call_args["timeFrame"], time_frame)

    def test_get_grouped_calls_metrics_error(self):
        """Test get_grouped_calls_metrics error handling"""
        self.client.analyze_api.get_call_group = MagicMock(side_effect=Exception("Test error"))
        group = {"groupbyTag": "endpoint"}
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        result = asyncio.run(self.client.get_grouped_calls_metrics(group=group, metrics=metrics))
        self.assertTrue(isinstance(result, dict))
        self.assertIn("error", result)
        self.assertIn("Failed to get grouped calls metrics", result["error"])
        self.assertIn("Test error", result["error"])

    def test_get_correlated_traces_success(self):
        """Test get_correlated_traces with a successful response"""
        mock_response = MagicMock()
        mock_response.to_dict = MagicMock(return_value={
            "traceId": "trace123",
            "timestamp": 1625097600000,
            "correlationType": "BACKEND_TRACE"
        })
        self.client.analyze_api.get_correlated_traces = MagicMock(return_value=mock_response)
        correlation_id = "beacon123"
        result = asyncio.run(self.client.get_correlated_traces(correlation_id=correlation_id))
        self.client.analyze_api.get_correlated_traces.assert_called_once_with(
            correlation_id=correlation_id
        )
        self.assertEqual(result["traceId"], "trace123")
        self.assertEqual(result["correlationType"], "BACKEND_TRACE")
def test_get_correlated_traces_missing_id(self):
    """Test get_correlated_traces with missing correlation ID"""
    result = asyncio.run(self.client.get_correlated_traces(correlation_id=""))
    self.assertTrue(isinstance(result, dict))
    self.assertIn("error", result)
    self.assertIn("Correlation ID must be provided", result["error"])

def test_get_correlated_traces_error(self):
    """Test get_correlated_traces error handling"""
    self.client.analyze_api.get_correlated_traces = MagicMock(side_effect=Exception("Test error"))
    result = asyncio.run(self.client.get_correlated_traces(correlation_id="beacon123"))
    self.assertTrue(isinstance(result, dict))
    self.assertIn("error", result)
    self.assertIn("Failed to get correlated traces", result["error"])
    self.assertIn("Test error", result["error"])


if __name__ == '__main__':
    unittest.main()
