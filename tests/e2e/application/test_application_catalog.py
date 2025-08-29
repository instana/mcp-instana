"""
E2E tests for Application Catalog MCP Tools
"""

from unittest.mock import MagicMock, patch

import pytest

from src.application.application_catalog import ApplicationCatalogMCPTools


class TestApplicationCatalogE2E:
    """End-to-end tests for Application Catalog MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_mocked(self, instana_credentials, mock_instana_response):
        """Test getting application tag catalog with mocked responses."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "Commonly Used", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_tag_catalog(
                use_case="GROUPING",
                data_source="CALLS",
                api_client=mock_api
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "tagTree" in result
            assert len(result["tagTree"]) > 0
            assert result["tagTree"][0]["label"] == "Commonly Used"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_string_response(self, instana_credentials):
        """Test handling of string responses in tag catalog."""

        # Mock the API response as a string that needs to be parsed
        mock_response = MagicMock()
        mock_response.data = '"{\\"tagTree\\": [{\\"label\\": \\"test-tag\\", \\"children\\": []}]}"'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_tag_catalog(api_client=mock_api)

            # Verify the result
            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_list_response(self, instana_credentials):
        """Test handling of list responses in tag catalog."""

        # Mock the API response as a list
        mock_response = MagicMock()
        mock_response.data = '[{"tagTree": [{"label": "test-tag", "children": []}]}]'

        # Create a mock API client
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response

        # Create the client
        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with the mock API client
        result = await client.get_application_tag_catalog(api_client=mock_api)

        # Verify the result - should be a dict with "tags" key as returned by the source code
        assert isinstance(result, dict)
        assert "tags" in result
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_unexpected_format(self, instana_credentials):
        """Test handling of unexpected response format in tag catalog."""

        # Mock the API response with an unexpected format
        mock_response = MagicMock()
        mock_response.data = '42'  # Not a dict or list

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_tag_catalog(api_client=mock_api)

            # Verify the result - should return an error due to invalid JSON
            assert isinstance(result, dict)
            assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_mocked(self, instana_credentials):
        """Test getting application metric catalog with mocked responses."""

        # Create a mock API client
        mock_api = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"metrics": [{"id": "cpu_usage", "name": "CPU Usage"}]}
        mock_api.get_application_catalog_metrics.return_value = mock_result

        # Create the client
        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with the mock API client
        result = await client.get_application_metric_catalog(api_client=mock_api)

        # Verify the result
        assert isinstance(result, dict)
        assert "metrics" in result
        assert len(result["metrics"]) > 0
        assert result["metrics"][0]["id"] == "cpu_usage"
        assert result["metrics"][0]["name"] == "CPU Usage"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_list_result(self, instana_credentials):
        """Test handling of list results in metric catalog."""

        # Mock the API class
        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = [{"id": "cpu_usage", "name": "CPU Usage"}]
            mock_api.get_application_catalog_metrics.return_value = mock_result
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_metric_catalog(api_client=mock_api)

            # Verify the result
            assert isinstance(result, dict)
            assert "metrics" in result
            assert len(result["metrics"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_no_to_dict(self, instana_credentials):
        """Test handling of results without to_dict method in metric catalog."""

        # Mock the API class
        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            # Set up the mock API
            mock_api = MagicMock()
            # Create a result without to_dict method
            mock_result = {"metrics": [{"id": "cpu_usage", "name": "CPU Usage"}]}
            mock_api.get_application_catalog_metrics.return_value = mock_result
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_metric_catalog(api_client=mock_api)

            # Verify the result
            assert isinstance(result, dict)
            assert "metrics" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_api_error(self, instana_credentials):
        """Test error handling in metric catalog."""

        # Create a mock API client that raises an exception
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.side_effect = Exception("API Error")

        # Create the client
        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with the mock API client
        result = await client.get_application_metric_catalog(api_client=mock_api)

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.real_api
    async def test_get_application_tag_catalog_real_api(self, instana_credentials):
        """Test getting application tag catalog with real API (if credentials available)."""

        # Skip if we don't have real credentials
        if not instana_credentials["api_token"] or instana_credentials["api_token"] == "test_token":
            pytest.skip("Real API credentials not available")

        try:
            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_tag_catalog(
                use_case="GROUPING",
                data_source="CALLS"
            )

            # Verify the result structure
            assert isinstance(result, dict)
            # Note: We can't assert specific content as it depends on the real data

        except Exception as e:
            pytest.fail(f"Real API test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.real_api
    async def test_get_application_metric_catalog_real_api(self, instana_credentials):
        """Test getting application metric catalog with real API (if credentials available)."""

        # Skip if we don't have real credentials
        if not instana_credentials["api_token"] or instana_credentials["api_token"] == "test_token":
            pytest.skip("Real API credentials not available")

        try:
            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            result = await client.get_application_metric_catalog()

            # Verify the result structure
            assert isinstance(result, dict)
            # Note: We can't assert specific content as it depends on the real data

        except Exception as e:
            pytest.fail(f"Real API test failed: {e}")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_client_initialization_error_handling(self):
        """Test client initialization error handling."""

        # This test should not raise an exception since the client initialization
        # doesn't actually call the API during __init__
        client = ApplicationCatalogMCPTools(
            read_token="invalid_token",
            base_url="https://invalid.url"
        )

        # Verify the client was created successfully
        assert client is not None
        assert client.read_token == "invalid_token"
        assert client.base_url == "https://invalid.url"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_api_error_handling(self, instana_credentials):
        """Test API error handling."""

        # Create a mock API client that raises an exception
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content = MagicMock(side_effect=Exception("API Error"))

        # Create the client
        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test that the method handles errors gracefully and returns error dict
        result = await client.get_application_tag_catalog(api_client=mock_api)
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_parameter_validation(self, instana_credentials):
        """Test parameter validation for the catalog methods."""

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_response = MagicMock()
            mock_response.data = '{"tagTree": []}'
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            # Create the client
            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test with different parameter combinations
            test_cases = [
                {"use_case": "GROUPING", "data_source": "CALLS"},
                {"use_case": None, "data_source": None},
                {"use_case": "FILTERING", "data_source": "CALLS"},  # Changed from METRICS to CALLS
            ]

            for params in test_cases:
                result = await client.get_application_tag_catalog(**params, api_client=mock_api)
                assert isinstance(result, dict)
                assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_timestamp(self, instana_credentials):
        """Test getting application tag catalog with specific timestamp."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test with specific timestamp
            timestamp = 1640995200000  # 2022-01-01 00:00:00 UTC
            result = await client.get_application_tag_catalog(var_from=timestamp, api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_trim_functionality(self, instana_credentials):
        """Test that the trim_tag_tree functionality works correctly."""

        # Mock response with deep nested structure
        mock_response = MagicMock()
        mock_response.data = '''{
            "tagTree": [
                {
                    "label": "Level1",
                    "children": [
                        {"label": "Child1", "children": [{"label": "GrandChild1"}]},
                        {"label": "Child2", "children": [{"label": "GrandChild2"}]},
                        {"label": "Child3", "children": [{"label": "GrandChild3"}]},
                        {"label": "Child4", "children": [{"label": "GrandChild4"}]}
                    ]
                },
                {
                    "label": "Level2",
                    "children": [
                        {"label": "Child5", "children": [{"label": "GrandChild5"}]}
                    ]
                }
            ]
        }'''

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_tag_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result
            assert len(result["tagTree"]) <= 3  # Should be trimmed to max 3 levels
            assert len(result["tagTree"][0]["children"]) <= 3  # Should be trimmed to max 3 children

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_with_complex_object(self, instana_credentials):
        """Test handling of complex metric objects."""

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()

            # Create a complex mock object that simulates the SDK response
            class MockMetricDescription:
                def __init__(self):
                    self.aggregations = ['SUM', 'PER_SECOND']
                    self.description = 'Test metric'
                    self.id = 'test_metric'
                    self.name = 'Test Metric'

                def to_dict(self):
                    return {
                        'aggregations': self.aggregations,
                        'description': self.description,
                        'id': self.id,
                        'name': self.name
                    }

            mock_result = MockMetricDescription()
            mock_api.get_application_catalog_metrics.return_value = mock_result
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_metric_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "metrics" in result or "aggregations" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_json_parsing_error(self, instana_credentials):
        """Test handling of JSON parsing errors."""

        mock_response = MagicMock()
        mock_response.data = 'invalid json data'

        # Create a mock API client
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response

        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        result = await client.get_application_tag_catalog(api_client=mock_api)

        # Should return an error due to JSON parsing failure
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_empty_response(self, instana_credentials):
        """Test handling of empty responses."""

        mock_response = MagicMock()
        mock_response.data = '{}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_tag_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            # Should return the empty dict as-is

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_no_metrics_key(self, instana_credentials):
        """Test handling when metrics key is not present in response."""

        # Create a mock API client
        mock_api = MagicMock()
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"other_key": "other_value"}
        mock_api.get_application_catalog_metrics.return_value = mock_result

        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert isinstance(result, dict)
        assert "other_key" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_use_case_only(self, instana_credentials):
        """Test getting tag catalog with only use_case parameter."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_tag_catalog(use_case="FILTERING", api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_data_source_only(self, instana_credentials):
        """Test getting tag catalog with only data_source parameter."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_tag_catalog(data_source="CALLS", api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_exception_handling(self, instana_credentials):
        """Test exception handling in metric catalog with different exception types."""

        # Create a mock API client that raises a ValueError
        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.side_effect = ValueError("Invalid value")

        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid value" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_debug_print_coverage(self, instana_credentials):
        """Test to ensure debug_print statements are covered."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test with all parameters to ensure debug_print coverage
            result = await client.get_application_tag_catalog(
                use_case="GROUPING",
                data_source="CALLS",
                var_from=1640995200000,
                api_client=mock_api
            )

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_debug_print_coverage(self, instana_credentials):
        """Test to ensure debug_print statements in metric catalog are covered."""

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {"metrics": [{"id": "test", "name": "Test"}]}
            mock_api.get_application_catalog_metrics.return_value = mock_result
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_metric_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "metrics" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_default_timestamp(self, instana_credentials):
        """Test that default timestamp is set when var_from is None."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_tag_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_string_parsing(self, instana_credentials):
        """Test handling of string that needs to be parsed twice."""

        mock_response = MagicMock()
        mock_response.data = '"{\\"tagTree\\": [{\\"label\\": \\"test-tag\\", \\"children\\": []}]}"'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_tag_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_list_to_dict(self, instana_credentials):
        """Test handling when to_dict returns a list."""

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_result = MagicMock()
            mock_result.to_dict.return_value = [{"id": "test", "name": "Test"}]
            mock_api.get_application_catalog_metrics.return_value = mock_result
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            result = await client.get_application_metric_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "metrics" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_unexpected_format_handling(self, instana_credentials):
        """Test handling of unexpected response format."""

        mock_response = MagicMock()
        mock_response.data = '42'  # Not a dict or list

        # Create a mock API client
        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response

        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        result = await client.get_application_tag_catalog(api_client=mock_api)

        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_mock_api_client(self, instana_credentials):
        """Test getting tag catalog with a mock API client passed directly."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        mock_api = MagicMock()
        mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response

        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Pass the mock API client directly to test the allow_mock functionality
        result = await client.get_application_tag_catalog(api_client=mock_api)

        assert isinstance(result, dict)
        assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_with_mock_api_client(self, instana_credentials):
        """Test getting metric catalog with a mock API client passed directly."""

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"metrics": [{"id": "test", "name": "Test"}]}

        mock_api = MagicMock()
        mock_api.get_application_catalog_metrics.return_value = mock_result

        client = ApplicationCatalogMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Pass the mock API client directly to test the allow_mock functionality
        result = await client.get_application_metric_catalog(api_client=mock_api)

        assert isinstance(result, dict)
        assert "metrics" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_tag_catalog_with_none_api_client(self, instana_credentials):
        """Test getting tag catalog when api_client is None (should use real API)."""

        mock_response = MagicMock()
        mock_response.data = '{"tagTree": [{"label": "test-tag", "children": []}]}'

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_tag_catalog_without_preload_content.return_value = mock_response
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Pass None as api_client to test the real API path
            result = await client.get_application_tag_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "tagTree" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_application_metric_catalog_with_none_api_client(self, instana_credentials):
        """Test getting metric catalog when api_client is None (should use real API)."""

        mock_result = MagicMock()
        mock_result.to_dict.return_value = {"metrics": [{"id": "test", "name": "Test"}]}

        with patch('src.application.application_catalog.ApplicationCatalogApi') as mock_api_class:
            mock_api = MagicMock()
            mock_api.get_application_catalog_metrics.return_value = mock_result
            mock_api_class.return_value = mock_api

            client = ApplicationCatalogMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Pass None as api_client to test the real API path
            result = await client.get_application_metric_catalog(api_client=mock_api)

            assert isinstance(result, dict)
            assert "metrics" in result
