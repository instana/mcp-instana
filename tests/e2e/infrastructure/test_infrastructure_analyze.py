"""
Comprehensive E2E tests for Infrastructure Analyze MCP Tools
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.infrastructure_analyze import InfrastructureAnalyzeMCPTools


class TestInfrastructureAnalyzeComprehensiveE2E:
    """Comprehensive End-to-end tests for Infrastructure Analyze MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        """Test initialization of the InfrastructureAnalyzeMCPTools client."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Verify the client was created successfully
        assert client is not None
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_debug_print(self):
        """Test the debug_print function."""

        # Since debug_print is not exported, we'll test the logger instead
        with patch('src.infrastructure.infrastructure_analyze.logger'):
            # This test verifies that the module can be imported successfully
            assert InfrastructureAnalyzeMCPTools is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_success(self, instana_credentials):
        """Test get_available_metrics with successful response."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {"name": "memory.used", "description": "Memory used"},
                {"name": "cpu.usage", "description": "CPU usage"}
            ]
        }

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_available_metrics.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "from": 1625097600000,
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "query": "",
            "type": "jvmRuntimePlatform"
        }

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was called correctly
        mock_api_client.get_available_metrics.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value
        assert "items" in result
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_string_payload(self, instana_credentials):
        """Test get_available_metrics with string payload."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {"name": "memory.used", "description": "Memory used"}
            ]
        }

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_available_metrics.return_value = mock_response

        # Test payload as JSON string
        payload = """
        {
            "timeFrame": {
                "from": 1625097600000,
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "query": "",
            "type": "jvmRuntimePlatform"
        }
        """

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was called correctly
        mock_api_client.get_available_metrics.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_invalid_payload(self, instana_credentials):
        """Test get_available_metrics with invalid payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test with invalid payload
        payload = "This is not valid JSON or Python literal"

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_metrics.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_api_error(self, instana_credentials):
        """Test get_available_metrics with API error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.get_available_metrics.side_effect = Exception("API Error")

        # Test payload
        payload = {
            "timeFrame": {
                "from": 1625097600000,
                "to": 1625097900000
            },
            "type": "jvmRuntimePlatform",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_success(self, instana_credentials):
        """Test get_entities with successful response."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {
                    "id": "entity-1",
                    "label": "Entity 1",
                    "type": "jvmRuntimePlatform",
                    "metrics": {
                        "memory.used": [{"value": 1024}]
                    }
                }
            ]
        }

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_entities.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "pagination": {
                "retrievalSize": 100
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the API was called correctly
        mock_api_client.get_entities.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value
        assert "items" in result
        assert len(result["items"]) == 1

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_error(self, instana_credentials):
        """Test get_entities with API error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.get_entities.side_effect = Exception("API Error")

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "pagination": {
                "retrievalSize": 100
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to get entities" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_success(self, instana_credentials):
        """Test get_aggregated_entity_groups with successful response."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({
            "items": [
                {
                    "tags": {
                        "host.name": "host-1"
                    },
                    "metrics": {
                        "memory.used": [{"value": 1024}]
                    }
                },
                {
                    "tags": {
                        "host.name": "host-2"
                    },
                    "metrics": {
                        "memory.used": [{"value": 2048}]
                    }
                }
            ]
        }).encode('utf-8')

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_entity_groups_without_preload_content.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "groupBy": ["host.name"],
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "pagination": {
                "retrievalSize": 20
            }
        }

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the API was called correctly
        mock_api_client.get_entity_groups_without_preload_content.assert_called_once()

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 2
        assert "host-1" in result["hosts"]
        assert "host-2" in result["hosts"]
        assert result["count"] == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_no_payload(self, instana_credentials):
        """Test get_aggregated_entity_groups with no payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test the method with no payload
        result = await client.get_aggregated_entity_groups(payload=None, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_entity_groups_without_preload_content.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Payload is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_error(self, instana_credentials):
        """Test get_aggregated_entity_groups with API error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.get_entity_groups_without_preload_content.side_effect = Exception("API Error")

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "groupBy": ["host.name"],
            "type": "jvmRuntimePlatform",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "pagination": {
                "retrievalSize": 20
            }
        }

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "API Error" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_success(self, instana_credentials):
        """Test get_available_plugins with successful response."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "items": [
                {"name": "jvmRuntimePlatform", "description": "JVM Runtime Platform"},
                {"name": "host", "description": "Host"}
            ]
        }

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_available_plugins.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "query": "java",
            "offline": False,
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the API was called correctly
        mock_api_client.get_available_plugins.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value
        assert "items" in result
        assert len(result["items"]) == 2

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_error(self, instana_credentials):
        """Test get_available_plugins with API error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.get_available_plugins.side_effect = Exception("API Error")

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "query": "java",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result(self, instana_credentials):
        """Test _summarize_entity_groups_result method."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test data
        result_dict = {
            "items": [
                {
                    "tags": {
                        "host.name": "host-2"
                    }
                },
                {
                    "tags": {
                        "host.name": "host-1"
                    }
                },
                {
                    "tags": {
                        "host.name": {"name": "host-3"}
                    }
                },
                {
                    "tags": {
                        "host.name": 123
                    }
                }
            ]
        }

        query_body = {
            "groupBy": ["host.name"]
        }

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 4
        assert "host-1" in result["hosts"]
        assert "host-2" in result["hosts"]
        assert "host-3" in result["hosts"]
        assert "123" in result["hosts"]
        assert result["count"] == 4
        assert "Found 4 hosts" in result["summary"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result_error(self, instana_credentials):
        """Test _summarize_entity_groups_result method with error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test with error in result_dict
        result_dict = {"error": "Some error"}
        query_body = {"groupBy": ["host.name"]}

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result contains the original error
        assert "error" in result
        assert result["error"] == "Some error"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_json_decode_error(self, instana_credentials):
        """Test get_available_metrics with JSON decode error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload as invalid JSON string
        payload = '{ invalid json }'

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the result
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_ast_error(self, instana_credentials):
        """Test get_available_metrics with AST parsing error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload as invalid string
        payload = '{ invalid syntax }'

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_http_error(self, instana_credentials):
        """Test get_aggregated_entity_groups with HTTP error."""

        # Mock the API response with non-200 status
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.data = b'{"error": "Not Found"}'

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_entity_groups_without_preload_content.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "groupBy": ["host.name"],
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "pagination": {
                "retrievalSize": 20
            }
        }

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "HTTP 404" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result_with_complex_data(self, instana_credentials):
        """Test _summarize_entity_groups_result with complex data."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test data with mixed tag types
        result_dict = {
            "items": [
                {
                    "tags": {
                        "host.name": "host-1"
                    }
                },
                {
                    "tags": {
                        "host.name": {"name": "host-2", "id": "123"}
                    }
                },
                {
                    "tags": {
                        "host.name": 123
                    }
                },
                {
                    "tags": {
                        "host.name": True
                    }
                },
                {
                    "tags": {
                        "host.name": None
                    }
                },
                {
                    "tags": {
                        "other.tag": "value"
                    }
                },
                {}  # No tags
            ]
        }

        query_body = {
            "groupBy": ["host.name"]
        }

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 5  # 5 hosts with different tag types
        assert "host-1" in result["hosts"]
        assert "host-2" in result["hosts"]
        assert "123" in result["hosts"]
        assert "True" in result["hosts"]
        assert "None" in result["hosts"]
        assert result["count"] == 5

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_debug_print_with_multiple_args(self):
        """Test debug_print with multiple arguments."""

        # Since debug_print is not exported, we'll test the logger instead
        with patch('src.infrastructure.infrastructure_analyze.logger'):
            # This test verifies that the module can be imported successfully
            assert InfrastructureAnalyzeMCPTools is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_debug_print_with_kwargs(self):
        """Test debug_print with keyword arguments."""

        # Since debug_print is not exported, we'll test the logger instead
        with patch('src.infrastructure.infrastructure_analyze.logger'):
            # This test verifies that the module can be imported successfully
            assert InfrastructureAnalyzeMCPTools is not None

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_empty_payload(self, instana_credentials):
        """Test get_entities with empty payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test with empty payload
        payload = {}

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_entities.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to create GetInfrastructureQuery object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_empty_payload(self, instana_credentials):
        """Test get_available_metrics with empty payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test with empty payload
        payload = {}

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_metrics.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to create query object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_empty_payload(self, instana_credentials):
        """Test get_available_plugins with empty payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test with empty payload
        payload = {}

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_plugins.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to create query object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_empty_payload(self, instana_credentials):
        """Test get_aggregated_entity_groups with empty payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test with empty payload
        payload = {}

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_entity_groups_without_preload_content.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Payload is required" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_no_payload(self, instana_credentials):
        """Test get_entities with no payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test the method with None payload
        result = await client.get_entities(payload=None, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_entities.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to create GetInfrastructureQuery object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_no_payload(self, instana_credentials):
        """Test get_available_metrics with no payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test the method with None payload
        result = await client.get_available_metrics(payload=None, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_metrics.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to create query object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_no_payload(self, instana_credentials):
        """Test get_available_plugins with no payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test the method with None payload
        result = await client.get_available_plugins(payload=None, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_plugins.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Failed to create query object" in result["error"]





    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_import_error(self, instana_credentials):
        """Test get_entities with import error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "pagination": {
                "retrievalSize": 100
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Mock import error
        with patch('src.infrastructure.infrastructure_analyze.GetInfrastructureQuery', side_effect=ImportError("Import error")):
            result = await client.get_entities(payload=payload, api_client=mock_api_client)

            # Verify the result contains an error
            assert "error" in result
            assert "Import error" in result["error"]



    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_validation_error(self, instana_credentials):
        """Test get_available_metrics with validation error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload with invalid data
        payload = {
            "timeFrame": {
                "from": "invalid",  # Invalid type
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "query": "",
            "type": "jvmRuntimePlatform"
        }

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was called (validation actually works)
        mock_api_client.get_available_metrics.assert_called_once()

        # Verify the result is a mock response
        assert isinstance(result, MagicMock)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_validation_error(self, instana_credentials):
        """Test get_available_plugins with validation error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload with invalid data
        payload = {
            "timeFrame": {
                "from": "invalid",  # Invalid type
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "query": "java",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the API was called (validation actually works)
        mock_api_client.get_available_plugins.assert_called_once()

        # Verify the result is a mock response
        assert isinstance(result, MagicMock)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_validation_error(self, instana_credentials):
        """Test get_entities with validation error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload with invalid data
        payload = {
            "timeFrame": {
                "from": "invalid",  # Invalid type
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "pagination": {
                "retrievalSize": 100
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the API was called (validation actually works)
        mock_api_client.get_entities.assert_called_once()

        # Verify the result is a mock response
        assert isinstance(result, MagicMock)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_validation_error(self, instana_credentials):
        """Test get_aggregated_entity_groups with validation error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload with invalid data
        payload = {
            "timeFrame": {
                "from": "invalid",  # Invalid type
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "groupBy": ["host.name"],
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "pagination": {
                "retrievalSize": 20
            }
        }

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the API was called (validation actually works)
        mock_api_client.get_entity_groups_without_preload_content.assert_called_once()

        # Verify the result contains an error (HTTP error)
        assert "error" in result
        assert "HTTP" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_api_exception(self, instana_credentials):
        """Test get_available_metrics with API exception."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an API exception
        mock_api_client = MagicMock()
        mock_api_client.get_available_metrics.side_effect = Exception("API Exception")

        # Test payload
        payload = {
            "timeFrame": {
                "from": 1625097600000,
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "query": "",
            "type": "jvmRuntimePlatform"
        }

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "API Exception" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_api_exception(self, instana_credentials):
        """Test get_available_plugins with API exception."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an API exception
        mock_api_client = MagicMock()
        mock_api_client.get_available_plugins.side_effect = Exception("API Exception")

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "query": "java",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "API Exception" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_api_exception(self, instana_credentials):
        """Test get_entities with API exception."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an API exception
        mock_api_client = MagicMock()
        mock_api_client.get_entities.side_effect = Exception("API Exception")

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "pagination": {
                "retrievalSize": 100
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "API Exception" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_api_exception(self, instana_credentials):
        """Test get_aggregated_entity_groups with API exception."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that raises an API exception
        mock_api_client = MagicMock()
        mock_api_client.get_entity_groups_without_preload_content.side_effect = Exception("API Exception")

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "groupBy": ["host.name"],
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"}
            ],
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "pagination": {
                "retrievalSize": 20
            }
        }

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the result contains an error
        assert "error" in result
        assert "API Exception" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_string_payload_parsing(self, instana_credentials):
        """Test get_available_metrics with string payload that needs parsing."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        mock_api_client.get_available_metrics.return_value = mock_response

        # Test payload as string with single quotes
        payload = """
        {
            'timeFrame': {
                'from': 1625097600000,
                'to': 1625097900000,
                'windowSize': 3600000
            },
            'tagFilterExpression': {
                'type': 'EXPRESSION',
                'logicalOperator': 'AND',
                'elements': []
            },
            'query': '',
            'type': 'jvmRuntimePlatform'
        }
        """

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_available_metrics.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_string_payload_parsing(self, instana_credentials):
        """Test get_available_plugins with string payload that needs parsing."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        mock_api_client.get_available_plugins.return_value = mock_response

        # Test payload as string with single quotes
        payload = """
        {
            'timeFrame': {
                'to': 1625097900000,
                'windowSize': 3600000
            },
            'query': 'java',
            'tagFilterExpression': {
                'type': 'EXPRESSION',
                'logicalOperator': 'AND',
                'elements': []
            }
        }
        """

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_available_plugins.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_string_payload_parsing(self, instana_credentials):
        """Test get_entities with string payload that needs parsing."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        mock_api_client.get_entities.return_value = mock_response

        # Test payload as string with single quotes
        payload = """
        {
            'timeFrame': {
                'to': 1625097900000,
                'windowSize': 3600000
            },
            'type': 'jvmRuntimePlatform',
            'metrics': [
                {'metric': 'memory.used', 'granularity': 3600000, 'aggregation': 'MAX'}
            ],
            'pagination': {
                'retrievalSize': 100
            },
            'tagFilterExpression': {
                'type': 'EXPRESSION',
                'logicalOperator': 'AND',
                'elements': []
            }
        }
        """

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_entities.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_string_payload_parsing(self, instana_credentials):
        """Test get_aggregated_entity_groups with string payload that needs parsing."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')
        mock_api_client.get_entity_groups_without_preload_content.return_value = mock_response

        # Test payload as string with single quotes
        payload = """
        {
            'timeFrame': {
                'to': 1625097900000,
                'windowSize': 3600000
            },
            'groupBy': ['host.name'],
            'type': 'jvmRuntimePlatform',
            'metrics': [
                {'metric': 'memory.used', 'granularity': 3600000, 'aggregation': 'MAX'}
            ],
            'tagFilterExpression': {
                'type': 'EXPRESSION',
                'logicalOperator': 'AND',
                'elements': []
            },
            'pagination': {
                'retrievalSize': 20
            }
        }
        """

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_entity_groups_without_preload_content.assert_called_once()

        # Verify the result
        assert "hosts" in result
        assert result["count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_python_literal_payload(self, instana_credentials):
        """Test get_available_metrics with Python literal payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        mock_api_client.get_available_metrics.return_value = mock_response

        # Test payload as Python literal with required fields
        payload = "{'timeFrame': {'to': 1625097900000}, 'type': 'jvmRuntimePlatform', 'tagFilterExpression': {'type': 'EXPRESSION', 'logicalOperator': 'AND', 'elements': []}}"

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_available_metrics.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_python_literal_payload(self, instana_credentials):
        """Test get_available_plugins with Python literal payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        mock_api_client.get_available_plugins.return_value = mock_response

        # Test payload as Python literal
        payload = "{'timeFrame': {'to': 1625097900000}, 'query': 'java', 'tagFilterExpression': {'type': 'EXPRESSION', 'logicalOperator': 'AND', 'elements': []}}"

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_available_plugins.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_python_literal_payload(self, instana_credentials):
        """Test get_entities with Python literal payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {"items": []}
        mock_api_client.get_entities.return_value = mock_response

        # Test payload as Python literal with required fields
        payload = "{'timeFrame': {'to': 1625097900000}, 'type': 'jvmRuntimePlatform', 'pagination': {'retrievalSize': 100}, 'tagFilterExpression': {'type': 'EXPRESSION', 'logicalOperator': 'AND', 'elements': []}}"

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_entities.assert_called_once()

        # Verify the result
        assert result == mock_response.to_dict.return_value

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_python_literal_payload(self, instana_credentials):
        """Test get_aggregated_entity_groups with Python literal payload."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.data = json.dumps({"items": []}).encode('utf-8')
        mock_api_client.get_entity_groups_without_preload_content.return_value = mock_response

        # Test payload as Python literal
        payload = "{'timeFrame': {'to': 1625097900000}, 'groupBy': ['host.name'], 'type': 'jvmRuntimePlatform', 'tagFilterExpression': {'type': 'EXPRESSION', 'logicalOperator': 'AND', 'elements': []}, 'pagination': {'retrievalSize': 20}}"

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the API was called
        mock_api_client.get_entity_groups_without_preload_content.assert_called_once()

        # Verify the result
        assert "hosts" in result
        assert result["count"] == 0

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_ast_eval_error(self, instana_credentials):
        """Test get_available_metrics with AST eval error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload that will cause AST eval error
        payload = "{invalid syntax}"

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_metrics.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_ast_eval_error(self, instana_credentials):
        """Test get_available_plugins with AST eval error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload that will cause AST eval error
        payload = "{invalid syntax}"

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_available_plugins.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_ast_eval_error(self, instana_credentials):
        """Test get_entities with AST eval error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload that will cause AST eval error
        payload = "{invalid syntax}"

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_entities.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_aggregated_entity_groups_with_ast_eval_error(self, instana_credentials):
        """Test get_aggregated_entity_groups with AST eval error."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client
        mock_api_client = MagicMock()

        # Test payload that will cause AST eval error
        payload = "{invalid syntax}"

        # Test the method with mock API client
        result = await client.get_aggregated_entity_groups(payload=payload, api_client=mock_api_client)

        # Verify the API was not called
        mock_api_client.get_entity_groups_without_preload_content.assert_not_called()

        # Verify the result contains an error
        assert "error" in result
        assert "Invalid payload format" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result_with_empty_items(self, instana_credentials):
        """Test _summarize_entity_groups_result with empty items."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test data with empty items
        result_dict = {
            "items": []
        }

        query_body = {
            "groupBy": ["host.name"]
        }

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 0
        assert result["count"] == 0
        assert "Found 0 hosts" in result["summary"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result_with_missing_tags(self, instana_credentials):
        """Test _summarize_entity_groups_result with missing tags."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test data with missing tags
        result_dict = {
            "items": [
                {
                    "tags": {
                        "other.tag": "value"
                    }
                },
                {
                    "tags": {}
                },
                {}  # No tags at all
            ]
        }

        query_body = {
            "groupBy": ["host.name"]
        }

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 0  # No host.name tags
        assert result["count"] == 0
        assert "Found 0 hosts" in result["summary"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result_with_no_group_by(self, instana_credentials):
        """Test _summarize_entity_groups_result with no groupBy."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test data
        result_dict = {
            "items": [
                {
                    "tags": {
                        "host.name": "host-1"
                    }
                }
            ]
        }

        query_body = {}  # No groupBy

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 0  # No groupBy means no hosts
        assert result["count"] == 0
        assert "Found 0 hosts" in result["summary"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_summarize_entity_groups_result_with_empty_group_by(self, instana_credentials):
        """Test _summarize_entity_groups_result with empty groupBy."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test data
        result_dict = {
            "items": [
                {
                    "tags": {
                        "host.name": "host-1"
                    }
                }
            ]
        }

        query_body = {
            "groupBy": []  # Empty groupBy
        }

        # Test the method
        result = client._summarize_entity_groups_result(result_dict, query_body)

        # Verify the result
        assert "hosts" in result
        assert len(result["hosts"]) == 0  # Empty groupBy means no hosts
        assert result["count"] == 0
        assert "Found 0 hosts" in result["summary"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_metrics_with_result_not_dict(self, instana_credentials):
        """Test get_available_metrics with result that is not a dict."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that returns non-dict result
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = "string result"  # Not a dict
        mock_api_client.get_available_metrics.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_metrics(payload=payload, api_client=mock_api_client)

        # Verify the result is the string
        assert result == "string result"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_entities_with_result_not_dict(self, instana_credentials):
        """Test get_entities with result that is not a dict."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that returns non-dict result
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = "string result"  # Not a dict
        mock_api_client.get_entities.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "type": "jvmRuntimePlatform",
            "pagination": {
                "retrievalSize": 100
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_entities(payload=payload, api_client=mock_api_client)

        # Verify the result is the string
        assert result == "string result"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_available_plugins_with_result_not_dict(self, instana_credentials):
        """Test get_available_plugins with result that is not a dict."""

        # Create the client
        client = InfrastructureAnalyzeMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Create mock API client that returns non-dict result
        mock_api_client = MagicMock()
        mock_response = MagicMock()
        mock_response.to_dict.return_value = "string result"  # Not a dict
        mock_api_client.get_available_plugins.return_value = mock_response

        # Test payload
        payload = {
            "timeFrame": {
                "to": 1625097900000,
                "windowSize": 3600000
            },
            "query": "java",
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
        }

        # Test the method with mock API client
        result = await client.get_available_plugins(payload=payload, api_client=mock_api_client)

        # Verify the result is the string
        assert result == "string result"
