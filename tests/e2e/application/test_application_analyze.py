"""
E2E tests for Application Analyze MCP Tools
"""

from unittest.mock import MagicMock, patch

import pytest

from src.application.application_analyze import ApplicationAnalyzeMCPTools


class TestApplicationAnalyzeE2E:
    """End-to-end tests for Application Analyze MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_call_details_mocked(self, instana_credentials):
        """Test getting call details with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "call123",
            "traceId": "trace123",
            "timestamp": 1625097600000,
            "duration": 150,
            "erroneous": False,
            "service": "test-service",
            "endpoint": "/api/test"
        }

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_call_details = MagicMock()
        mock_api_client.get_call_details.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_call_details(
            trace_id="trace123",
            call_id="call123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == "call123"
        assert result["service"] == "test-service"

        # Verify the API was called correctly
        mock_api_client.get_call_details.assert_called_once_with(
            trace_id="trace123",
            call_id="call123"
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_call_details_missing_params(self, instana_credentials):
        """Test get_call_details with missing parameters."""

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test with missing trace_id
            result = await client.get_call_details(trace_id="", call_id="call123")
            assert isinstance(result, dict)
            assert "error" in result
            assert "Both trace_id and call_id must be provided" in result["error"]

            # Test with missing call_id
            result = await client.get_call_details(trace_id="trace123", call_id="")
            assert isinstance(result, dict)
            assert "error" in result
            assert "Both trace_id and call_id must be provided" in result["error"]

            # Verify the API was not called
            mock_api.get_call_details.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_call_details_error_handling(self, instana_credentials):
        """Test error handling in get_call_details."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_call_details = MagicMock()
        mock_api_client.get_call_details.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_call_details(
            trace_id="trace123",
            call_id="call123",
            api_client=mock_api_client
        )

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_mocked(self, instana_credentials):
        """Test getting trace details with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "id": "trace123",
            "timestamp": 1625097600000,
            "duration": 250,
            "calls": [
                {
                    "id": "call123",
                    "service": "service-a",
                    "endpoint": "/api/test"
                },
                {
                    "id": "call456",
                    "service": "service-b",
                    "endpoint": "/api/other"
                }
            ]
        }

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_trace_download = MagicMock()
        mock_api_client.get_trace_download.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_trace_details(
            id="trace123",
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == "trace123"
        assert len(result["calls"]) == 2
        assert result["calls"][0]["id"] == "call123"
        assert result["calls"][1]["id"] == "call456"

        # Verify the API was called correctly
        mock_api_client.get_trace_download.assert_called_once_with(
            id="trace123",
            retrieval_size=None,
            offset=None,
            ingestion_time=None
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_with_params(self, instana_credentials):
        """Test get_trace_details with additional parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"id": "trace123"}

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_trace_download = MagicMock()
        mock_api_client.get_trace_download.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with additional parameters
        result = await client.get_trace_details(
            id="trace123",
            retrievalSize=100,
            offset=10,
            ingestionTime=1625097600000,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "id" in result
        assert result["id"] == "trace123"

        # Verify the API was called correctly
        mock_api_client.get_trace_download.assert_called_once_with(
            id="trace123",
            retrieval_size=100,
            offset=10,
            ingestion_time=1625097600000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_missing_id(self, instana_credentials):
        """Test get_trace_details with missing ID."""

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with missing ID
            result = await client.get_trace_details(id="")

            # Verify the result contains an error message
            assert isinstance(result, dict)
            assert "error" in result
            assert "Trace ID must be provided" in result["error"]

            # Verify the API was not called
            mock_api.get_trace_download.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_invalid_params(self, instana_credentials):
        """Test get_trace_details with invalid parameters."""

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test with offset but no ingestion_time
            result = await client.get_trace_details(id="trace123", offset=10)
            assert isinstance(result, dict)
            assert "error" in result
            assert "If offset is provided, ingestionTime must also be provided" in result["error"]

            # Test with invalid retrieval_size
            result = await client.get_trace_details(id="trace123", retrievalSize=20000)
            assert isinstance(result, dict)
            assert "error" in result
            assert "retrievalSize must be between 1 and 10000" in result["error"]

            # Verify the API was not called
            mock_api.get_trace_download.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_error_handling(self, instana_credentials):
        """Test error handling in get_trace_details."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_trace_download = MagicMock()
        mock_api_client.get_trace_download.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_trace_details(
            id="trace123",
            api_client=mock_api_client
        )

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_traces_mocked(self, instana_credentials):
        """Test getting all traces with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {
                    "id": "trace123",
                    "timestamp": 1625097600000,
                    "duration": 150
                },
                {
                    "id": "trace456",
                    "timestamp": 1625097700000,
                    "duration": 200
                }
            ],
            "page": {
                "size": 2,
                "totalElements": 2
            }
        }

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_traces = MagicMock()
        mock_api_client.get_traces.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_traces(api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, dict)
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == "trace123"
        assert result["items"][1]["id"] == "trace456"

        # Verify the API was called
        mock_api_client.get_traces.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_traces_with_params(self, instana_credentials):
        """Test get_all_traces with parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_traces = MagicMock()
        mock_api_client.get_traces.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with parameters
        payload = {
            "includeInternal": True,
            "includeSynthetic": False,
            "timeFrame": {"from": 1625097600000, "to": 1625097700000}
        }

        result = await client.get_all_traces(
            payload=payload,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "items" in result

        # Verify the API was called
        mock_api_client.get_traces.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_traces_error_handling(self, instana_credentials):
        """Test error handling in get_all_traces."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_traces = MagicMock()
        mock_api_client.get_traces.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_all_traces(api_client=mock_api_client)

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_trace_metrics_mocked(self, instana_credentials):
        """Test getting grouped trace metrics with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {
                    "group": {"name": "service-a"},
                    "metrics": {"latency": 150, "calls": 100}
                },
                {
                    "group": {"name": "service-b"},
                    "metrics": {"latency": 200, "calls": 50}
                }
            ]
        }

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_trace_groups = MagicMock()
        mock_api_client.get_trace_groups.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with required parameters
        payload = {
            "group": {"groupbyTag": "service", "groupbyTagEntity": "DESTINATION"},
            "metrics": [{"metric": "latency", "aggregation": "MEAN"}, {"metric": "calls", "aggregation": "SUM"}]
        }

        result = await client.get_grouped_trace_metrics(
            payload=payload,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["group"]["name"] == "service-a"
        assert result["items"][1]["group"]["name"] == "service-b"

        # Verify the API was called
        mock_api_client.get_trace_groups.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_trace_metrics_with_params(self, instana_credentials):
        """Test get_grouped_trace_metrics with additional parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}

        # Create mock API client
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_trace_groups = MagicMock()
        mock_api_client.get_trace_groups.return_value = mock_response

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with additional parameters
        payload = {
            "group": {"groupbyTag": "service", "groupbyTagEntity": "DESTINATION"},
            "metrics": [{"metric": "latency", "aggregation": "MEAN"}],
            "includeInternal": True,
            "timeFrame": {"from": 1625097600000, "to": 1625097700000}
        }

        result = await client.get_grouped_trace_metrics(
            payload=payload,
            fill_time_series=True,
            api_client=mock_api_client
        )

        # Verify the result
        assert isinstance(result, dict)
        assert "items" in result

        # Verify the API was called
        mock_api_client.get_trace_groups.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_trace_metrics_error_handling(self, instana_credentials):
        """Test error handling in get_grouped_trace_metrics."""

        # Create mock API client that raises an exception
        mock_api_client = type('MockClient', (), {})()
        mock_api_client.get_trace_groups = MagicMock()
        mock_api_client.get_trace_groups.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        payload = {
            "group": {"groupbyTag": "service", "groupbyTagEntity": "DESTINATION"},
            "metrics": [{"metric": "latency", "aggregation": "MEAN"}]
        }

        result = await client.get_grouped_trace_metrics(
            payload=payload,
            api_client=mock_api_client
        )

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_mocked(self, instana_credentials):
        """Test getting grouped calls metrics with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {
                    "group": {"name": "endpoint-a"},
                    "metrics": {"latency": 150, "calls": 100}
                },
                {
                    "group": {"name": "endpoint-b"},
                    "metrics": {"latency": 200, "calls": 50}
                }
            ]
        }

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class, \
             patch('src.application.application_analyze.GetCallGroups') as mock_get_call_groups:

            # Set up the mocks
            mock_api = MagicMock()
            mock_api.get_call_group.return_value = mock_response
            mock_api_class.return_value = mock_api
            mock_get_call_groups.return_value = {}

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with required parameters
            group = {"groupbyTag": "endpoint", "groupbyTagEntity": "NOT_APPLICABLE"}
            metrics = [{"metric": "latency", "aggregation": "MEAN"}, {"metric": "calls", "aggregation": "SUM"}]

            result = await client.get_grouped_calls_metrics(
                payload={
                    "group": group,
                    "metrics": metrics
                },
                api_client=mock_api
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "items" in result
            assert len(result["items"]) == 2
            assert result["items"][0]["group"]["name"] == "endpoint-a"
            assert result["items"][1]["group"]["name"] == "endpoint-b"

            # Verify the API was called
            mock_api.get_call_group.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_with_params(self, instana_credentials):
        """Test get_grouped_calls_metrics with additional parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class, \
             patch('src.application.application_analyze.GetCallGroups') as mock_get_call_groups:

            # Set up the mocks
            mock_api = MagicMock()
            mock_api.get_call_group.return_value = mock_response
            mock_api_class.return_value = mock_api
            mock_get_call_groups.return_value = {}

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with additional parameters
            group = {"groupbyTag": "endpoint", "groupbyTagEntity": "NOT_APPLICABLE"}
            metrics = [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame = {"from": 1625097600000, "to": 1625097700000}
            include_synthetic = True
            fill_time_series = True

            result = await client.get_grouped_calls_metrics(
                payload={
                    "group": group,
                    "metrics": metrics,
                    "includeSynthetic": include_synthetic,
                    "fillTimeSeries": fill_time_series,
                    "timeFrame": time_frame
                },
                api_client=mock_api
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "items" in result

            # Verify the API was called
            mock_api.get_call_group.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_error_handling(self, instana_credentials):
        """Test error handling in get_grouped_calls_metrics."""

        from src.application.application_analyze import ApplicationAnalyzeMCPTools
        client = ApplicationAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Mock the SDK method to raise an exception
        client.analyze_api.get_call_group = MagicMock(side_effect=Exception("API Error"))

        # Test the method with correct group structure
        group = {
            "groupbyTag": "endpoint",
            "groupbyTagEntity": "NOT_APPLICABLE"  # Use correct enum value
        }
        metrics = [{"metric": "latency", "aggregation": "MEAN"}]

        result = await client.get_grouped_calls_metrics(
            payload={
                "group": group,
                "metrics": metrics
            }
        )

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Error" in result["error"]
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_correlated_traces_mocked(self, instana_credentials):
        """Test getting correlated traces with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "traceId": "trace123",
            "timestamp": 1625097600000,
            "correlationType": "BACKEND_TRACE"
        }

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_correlated_traces.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            correlation_id = "beacon123"
            result = await client.get_correlated_traces(correlation_id=correlation_id, api_client=mock_api)

            # Verify the result
            assert isinstance(result, dict)
            assert "traceId" in result
            assert result["traceId"] == "trace123"
            assert result["correlationType"] == "BACKEND_TRACE"

            # Verify the API was called correctly
            mock_api.get_correlated_traces.assert_called_once_with(
                correlation_id=correlation_id
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_correlated_traces_missing_id(self, instana_credentials):
        """Test get_correlated_traces with missing correlation ID."""

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with missing correlation ID
            result = await client.get_correlated_traces(correlation_id="")

            # Verify the result contains an error message
            assert isinstance(result, dict)
            assert "error" in result
            assert "Correlation ID must be provided" in result["error"]

            # Verify the API was not called
            mock_api.get_correlated_traces.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.skip(reason="Module already imported, can't test import errors")
    async def test_import_error_handling(self):
        """Test import error handling during client initialization."""
        # This test is skipped because the module is already imported
        # and we can't properly test import errors in this context
        pass

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization_error_handling(self, instana_credentials):
        """Test error handling during client initialization."""
        with patch('src.application.application_analyze.ApplicationAnalyzeApi',
                  side_effect=Exception("API initialization failed")):

            # Creating the client should raise the exception
            with pytest.raises(Exception) as exc_info:
                _ = ApplicationAnalyzeMCPTools(
                    read_token=instana_credentials["api_token"],
                    base_url=instana_credentials["base_url"]
                )

            assert "API initialization failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_traces_with_all_params(self, instana_credentials):
        """Test get_all_traces with all optional parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class, \
             patch('src.application.application_analyze.GetTraces') as mock_get_traces:

            # Set up the mocks
            mock_api = MagicMock()
            mock_api.get_traces.return_value = mock_response
            mock_api_class.return_value = mock_api
            mock_get_traces.return_value = {}

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with all parameters
            order = {"by": "timestamp", "direction": "DESC"}
            pagination = {"size": 10, "cursor": "abc123"}
            tag_filter = {"type": "AND", "tags": [{"name": "service", "value": "test-service"}]}
            time_frame = {"from": 1625097600000, "to": 1625097700000}

            result = await client.get_all_traces(
                payload={
                    "includeInternal": True,
                    "includeSynthetic": True,
                    "order": order,
                    "pagination": pagination,
                    "tagFilterExpression": tag_filter,
                    "timeFrame": time_frame
                },
                api_client=mock_api
            )

            # Verify the result
            assert isinstance(result, dict)

            # Verify the API was called
            mock_api.get_traces.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_trace_metrics_with_all_params(self, instana_credentials):
        """Test get_grouped_trace_metrics with all optional parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class, \
             patch('src.application.application_analyze.GetTraces') as mock_get_traces:

            # Set up the mocks
            mock_api = MagicMock()
            mock_api.get_trace_groups.return_value = mock_response
            mock_api_class.return_value = mock_api
            mock_get_traces.return_value = {}

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with all parameters
            group = {"groupbyTag": "service", "groupbyTagEntity": "NOT_APPLICABLE"}
            metrics = [{"metric": "latency", "aggregation": "MEAN"}]
            order = {"by": "timestamp", "direction": "DESC"}
            pagination = {"size": 10, "cursor": "abc123"}
            tag_filter = {"type": "AND", "tags": [{"name": "service", "value": "test-service"}]}
            time_frame = {"from": 1625097600000, "to": 1625097700000}

            result = await client.get_grouped_trace_metrics(
                payload={
                    "group": group,
                    "metrics": metrics,
                    "includeInternal": True,
                    "includeSynthetic": True,
                    "fillTimeSeries": True,
                    "order": order,
                    "pagination": pagination,
                    "tagFilterExpression": tag_filter,
                    "timeFrame": time_frame
                },
                api_client=mock_api
            )

            # Verify the result
            assert isinstance(result, dict)

            # Verify the API was called
            mock_api.get_trace_groups.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_grouped_calls_metrics_with_all_params(self, instana_credentials):
        """Test get_grouped_calls_metrics with all optional parameters."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}

        with patch('src.application.application_analyze.ApplicationAnalyzeApi') as mock_api_class, \
             patch('src.application.application_analyze.GetCallGroups') as mock_get_call_groups:

            # Set up the mocks
            mock_api = MagicMock()
            mock_api.get_call_group.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Mock GetCallGroups to return a valid object
            mock_config = MagicMock()
            mock_get_call_groups.return_value = mock_config

            # Create the client
            client = ApplicationAnalyzeMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with all parameters
            group = {"groupbyTag": "service.name", "groupbyTagEntity": "NOT_APPLICABLE"}
            metrics = [{"metric": "latency", "aggregation": "MEAN"}]
            order = {"by": "timestamp", "direction": "DESC"}
            pagination = {"size": 10, "cursor": "abc123"}
            tag_filter = {"type": "AND", "tags": [{"name": "endpoint", "value": "/api/test"}]}
            time_frame = {"from": 1625097600000, "to": 1625097700000}

            result = await client.get_grouped_calls_metrics(
                payload={
                    "group": group,
                    "metrics": metrics,
                    "includeInternal": True,
                    "includeSynthetic": True,
                    "fillTimeSeries": True,
                    "order": order,
                    "pagination": pagination,
                    "tagFilterExpression": tag_filter,
                    "timeFrame": time_frame
                },
                api_client=mock_api
            )

            # Verify the result
            assert isinstance(result, dict)

            # Verify the API was called
            mock_api.get_call_group.assert_called_once()
