"""
Unit tests for the ApplicationAnalyzeMCPTools class
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


logging.basicConfig(level=logging.ERROR)

app_logger = logging.getLogger('src.application.application_analyze')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.application_analyze_api'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_call_groups'] = MagicMock()
sys.modules['instana_client.models.get_traces'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()

mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_analyze_api = MagicMock()
mock_get_call_groups = MagicMock()
mock_get_traces = MagicMock()

mock_analyze_api.__name__ = "ApplicationAnalyzeApi"
mock_get_call_groups.__name__ = "GetCallGroups"
mock_get_traces.__name__ = "GetTraces"

sys.modules['instana_client.configuration'].Configuration = mock_configuration
sys.modules['instana_client.api_client'].ApiClient = mock_api_client
sys.modules['instana_client.api.application_analyze_api'].ApplicationAnalyzeApi = mock_analyze_api
sys.modules['instana_client.models.get_call_groups'].GetCallGroups = mock_get_call_groups
sys.modules['instana_client.models.get_traces'].GetTraces = mock_get_traces

from src.application.application_analyze import ApplicationAnalyzeMCPTools


class TestApplicationAnalyzeMCPTools(unittest.TestCase):
    """Test the ApplicationAnalyzeMCPTools class"""

    def setUp(self):
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_analyze_api.reset_mock()
        mock_get_call_groups.reset_mock()
        mock_get_traces.reset_mock()

        mock_configuration.side_effect = None
        mock_api_client.side_effect = None
        mock_analyze_api.side_effect = None
        mock_get_call_groups.side_effect = None
        mock_get_traces.side_effect = None

        mock_configuration.return_value = MagicMock()
        mock_configuration.return_value.api_key = {}
        mock_configuration.return_value.api_key_prefix = {}
        mock_api_client.return_value = MagicMock()
        mock_analyze_api.return_value = MagicMock()

        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"

    def test_init_success(self):
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        self.assertEqual(client.read_token, self.read_token)
        self.assertEqual(client.base_url, self.base_url)
        self.assertIs(client.analyze_api, analyze_api_instance)

        self.assertEqual(configuration_instance.host, self.base_url)
        self.assertEqual(configuration_instance.api_key['ApiKeyAuth'], self.read_token)
        self.assertEqual(configuration_instance.api_key_prefix['ApiKeyAuth'], 'apiToken')

        mock_api_client.assert_called_once_with(configuration=configuration_instance)
        mock_analyze_api.assert_called_once_with(api_client=api_client_instance)

    def test_init_configuration_failure(self):
        mock_configuration.side_effect = Exception("configuration failed")

        with self.assertRaises(Exception) as context:
            ApplicationAnalyzeMCPTools(
                read_token=self.read_token,
                base_url=self.base_url
            )

        self.assertIn("configuration failed", str(context.exception))
        mock_api_client.assert_not_called()
        mock_analyze_api.assert_not_called()

    def test_init_api_client_failure(self):
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance
        mock_api_client.side_effect = Exception("api client failed")

        with self.assertRaises(Exception) as context:
            ApplicationAnalyzeMCPTools(
                read_token=self.read_token,
                base_url=self.base_url
            )

        self.assertIn("api client failed", str(context.exception))
        mock_analyze_api.assert_not_called()

    def test_init_analyze_api_failure(self):
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance
        mock_analyze_api.side_effect = Exception("analyze api failed")

        with self.assertRaises(Exception) as context:
            ApplicationAnalyzeMCPTools(
                read_token=self.read_token,
                base_url=self.base_url
            )

        self.assertIn("analyze api failed", str(context.exception))
        mock_api_client.assert_called_once_with(configuration=configuration_instance)
        mock_analyze_api.assert_called_once_with(api_client=api_client_instance)

    def test_init_logs_error_on_failure(self):
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance
        mock_api_client.side_effect = Exception("boom")

        with patch('src.application.application_analyze.logger.error') as mock_logger_error:
            with self.assertRaises(Exception) as context:
                ApplicationAnalyzeMCPTools(
                    read_token=self.read_token,
                    base_url=self.base_url
                )
            self.assertEqual(str(context.exception), "boom")

        mock_logger_error.assert_called_once()
        self.assertIn("Error initializing ApplicationAnalyzeApi", mock_logger_error.call_args[0][0])

    def test_execute_analyze_operation_get_all_traces(self):
        """Test execute_analyze_operation with get_all_traces"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock get_all_traces
        with patch.object(client, 'get_all_traces') as mock_get_traces:
            mock_get_traces.return_value = {"filePath": "/tmp/test.jsonl", "itemCount": 10}

            result = asyncio.run(client.execute_analyze_operation(
                operation="get_all_traces",
                params={"payload": {"timeFrame": {"windowSize": 3600000}}}
            ))

            self.assertIn("filePath", result)
            mock_get_traces.assert_called_once()

    def test_execute_analyze_operation_get_trace_details(self):
        """Test execute_analyze_operation with get_trace_details"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock get_trace_details
        with patch.object(client, 'get_trace_details') as mock_get_details:
            mock_get_details.return_value = {"filePath": "/tmp/trace.jsonl", "itemCount": 5}

            result = asyncio.run(client.execute_analyze_operation(
                operation="get_trace_details",
                params={"id": "trace123", "retrievalSize": 100}
            ))

            self.assertIn("filePath", result)
            mock_get_details.assert_called_once()

    def test_execute_analyze_operation_invalid_operation(self):
        """Test execute_analyze_operation with invalid operation"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        result = asyncio.run(client.execute_analyze_operation(
            operation="invalid_operation",
            params={}
        ))

        self.assertIn("error", result)
        self.assertIn("not supported", result["error"])

    def test_execute_analyze_operation_exception(self):
        """Test execute_analyze_operation with exception"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock get_all_traces to raise exception
        with patch.object(client, 'get_all_traces') as mock_get_traces:
            mock_get_traces.side_effect = Exception("Test error")

            result = asyncio.run(client.execute_analyze_operation(
                operation="get_all_traces",
                params={"payload": {}}
            ))

            self.assertIn("error", result)
            self.assertIn("Test error", result["error"])

    def test_get_trace_details_success(self):
        """Test get_trace_details with successful response"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock API response
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "items": [
                {"id": "call1", "cursor": {"ingestionTime": 123, "offset": 0}},
                {"id": "call2", "cursor": {"ingestionTime": 123, "offset": 1}}
            ],
            "canLoadMore": True
        }

        analyze_api_instance.get_trace_download = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True):

            mock_stat.return_value.st_size = 1024

            result = asyncio.run(client.get_trace_details(
                id="trace123",
                retrieval_size=100,
                api_client=analyze_api_instance
            ))

            self.assertIn("filePath", result)
            self.assertIn("itemCount", result)
            self.assertIn("canLoadMore", result)
            self.assertEqual(result["itemCount"], 2)
            self.assertTrue(result["canLoadMore"])

    def test_get_trace_details_missing_id(self):
        """Test get_trace_details with missing trace ID"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        result = asyncio.run(client.get_trace_details(
            id="",
            api_client=analyze_api_instance
        ))

        self.assertIn("error", result)
        self.assertIn("must be provided", result["error"])

    def test_get_trace_details_invalid_retrieval_size(self):
        """Test get_trace_details with invalid retrievalSize"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        result = asyncio.run(client.get_trace_details(
            id="trace123",
            retrieval_size=20000,
            api_client=analyze_api_instance
        ))

        self.assertIn("error", result)
        self.assertIn("between 1 and 10000", result["error"])

    def test_get_trace_details_offset_without_ingestion_time(self):
        """Test get_trace_details with offset but no ingestionTime"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        result = asyncio.run(client.get_trace_details(
            id="trace123",
            offset=10,
            api_client=analyze_api_instance
        ))

        self.assertIn("error", result)
        self.assertIn("ingestion_time must also be provided", result["error"])

    def test_get_trace_details_exception(self):
        """Test get_trace_details with exception"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        analyze_api_instance.get_trace_download = MagicMock(side_effect=Exception("API error"))

        result = asyncio.run(client.get_trace_details(
            id="trace123",
            api_client=analyze_api_instance
        ))

        self.assertIn("error", result)
        self.assertIn("API error", result["error"])

    def test_get_all_traces_success(self):
        """Test get_all_traces with successful response"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock API response
        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "items": [
                {"traceId": "trace1", "cursor": {"ingestionTime": 123, "offset": 0}},
                {"traceId": "trace2", "cursor": {"ingestionTime": 123, "offset": 1}}
            ],
            "canLoadMore": False,
            "totalHits": 2
        }).encode('utf-8')

        analyze_api_instance.get_traces_without_preload_content = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):

            mock_stat.return_value.st_size = 2048

            result = asyncio.run(client.get_all_traces(
                payload={"timeFrame": {"windowSize": 3600000}},
                api_client=analyze_api_instance
            ))

            self.assertIn("filePath", result)
            self.assertIn("itemCount", result)
            self.assertIn("totalHits", result)
            self.assertEqual(result["itemCount"], 2)
            self.assertEqual(result["totalHits"], 2)

    def test_get_all_traces_with_none_payload(self):
        """Test get_all_traces with None payload (should use empty dict)"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock API response
        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "items": [],
            "canLoadMore": False,
            "totalHits": 0
        }).encode('utf-8')

        analyze_api_instance.get_traces_without_preload_content = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):

            mock_stat.return_value.st_size = 0

            result = asyncio.run(client.get_all_traces(
                payload=None,
                api_client=analyze_api_instance
            ))

            # Should succeed with empty payload (converted to {})
            self.assertIn("filePath", result)
            self.assertIn("itemCount", result)
            self.assertEqual(result["itemCount"], 0)

    def test_get_all_traces_exception(self):
        """Test get_all_traces with exception"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        analyze_api_instance.get_traces_without_preload_content = MagicMock(side_effect=Exception("API error"))

        result = asyncio.run(client.get_all_traces(
            payload={"timeFrame": {"windowSize": 3600000}},
            api_client=analyze_api_instance
        ))

        self.assertIn("error", result)
        self.assertIn("API error", result["error"])


    def test_get_trace_details_result_without_to_dict(self):
        """Test get_trace_details when result doesn't have to_dict method"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        # Mock API response as plain dict (no to_dict method)
        mock_result = {
            "items": [{"id": "call1"}],
            "canLoadMore": False
        }

        analyze_api_instance.get_trace_download = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True):

            mock_stat.return_value.st_size = 512

            result = asyncio.run(client.get_trace_details(
                id="trace123",
                api_client=analyze_api_instance
            ))

            self.assertIn("filePath", result)
            self.assertEqual(result["itemCount"], 1)

    def test_get_trace_details_file_cleanup_on_exception(self):
        """Test that file is cleaned up when exception occurs"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        analyze_api_instance.get_trace_download = MagicMock(side_effect=Exception("API error"))

        # Mock the file operations
        mock_file = mock_open()
        with patch('builtins.open', mock_file), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink') as mock_unlink:

            result = asyncio.run(client.get_trace_details(
                id="trace123",
                api_client=analyze_api_instance
            ))

            self.assertIn("error", result)
            mock_unlink.assert_called_once()

    def test_get_all_traces_string_payload_json(self):
        """Test get_all_traces with JSON string payload"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "items": [{"traceId": "trace1"}],
            "canLoadMore": False,
            "totalHits": 1
        }).encode('utf-8')

        analyze_api_instance.get_traces_without_preload_content = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):

            mock_stat.return_value.st_size = 100

            result = asyncio.run(client.get_all_traces(
                payload='{"timeFrame": {"windowSize": 3600000}}',
                api_client=analyze_api_instance
            ))

            self.assertIn("filePath", result)

    def test_get_all_traces_string_payload_single_quotes(self):
        """Test get_all_traces with single-quoted string payload"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "items": [],
            "canLoadMore": False,
            "totalHits": 0
        }).encode('utf-8')

        analyze_api_instance.get_traces_without_preload_content = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):

            mock_stat.return_value.st_size = 0

            result = asyncio.run(client.get_all_traces(
                payload="{'timeFrame': {'windowSize': 3600000}}",
                api_client=analyze_api_instance
            ))

            self.assertIn("filePath", result)

    def test_get_all_traces_string_payload_ast_literal_eval(self):
        """Test get_all_traces with payload requiring ast.literal_eval"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "items": [],
            "canLoadMore": False,
            "totalHits": 0
        }).encode('utf-8')

        analyze_api_instance.get_traces_without_preload_content = MagicMock(return_value=mock_result)

        # Payload that will fail json.loads but work with ast.literal_eval
        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):

            mock_stat.return_value.st_size = 0

            result = asyncio.run(client.get_all_traces(
                payload="{'timeFrame': {'windowSize': 3600000}, 'includeInternal': False}",
                api_client=analyze_api_instance
            ))

            self.assertIn("filePath", result)

    def test_get_all_traces_invalid_string_payload(self):
        """Test get_all_traces with invalid string payload"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        result = asyncio.run(client.get_all_traces(
            payload="invalid{json}string",
            api_client=analyze_api_instance
        ))

        self.assertIn("error", result)
        self.assertIn("Invalid payload format", result["error"])

    def test_get_all_traces_with_cursor_in_response(self):
        """Test get_all_traces returns cursor fields when available"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        mock_result = MagicMock()
        mock_result.data = json.dumps({
            "items": [
                {"traceId": "trace1", "cursor": {"ingestionTime": 1234567890, "offset": 99}}
            ],
            "canLoadMore": True,
            "totalHits": 200
        }).encode('utf-8')

        analyze_api_instance.get_traces_without_preload_content = MagicMock(return_value=mock_result)

        with patch('builtins.open', mock_open()), \
             patch('pathlib.Path.stat') as mock_stat, \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):

            mock_stat.return_value.st_size = 100

            result = asyncio.run(client.get_all_traces(
                payload={"timeFrame": {"windowSize": 3600000}},
                api_client=analyze_api_instance
            ))

            self.assertIn("ingestionTime", result)
            self.assertIn("offset", result)
            self.assertEqual(result["ingestionTime"], 1234567890)
            self.assertEqual(result["offset"], 99)

    def test_get_all_traces_file_cleanup_on_exception(self):
        """Test that file is cleaned up when exception occurs"""
        configuration_instance = MagicMock()
        configuration_instance.api_key = {}
        configuration_instance.api_key_prefix = {}
        mock_configuration.return_value = configuration_instance

        api_client_instance = MagicMock()
        mock_api_client.return_value = api_client_instance

        analyze_api_instance = MagicMock()
        mock_analyze_api.return_value = analyze_api_instance

        client = ApplicationAnalyzeMCPTools(
            read_token=self.read_token,
            base_url=self.base_url
        )

        analyze_api_instance.get_traces = MagicMock(side_effect=Exception("API error"))

        # Mock the file operations
        mock_file = mock_open()
        with patch('builtins.open', mock_file), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink') as mock_unlink:

            result = asyncio.run(client.get_all_traces(
                payload={"timeFrame": {"windowSize": 3600000}},
                api_client=analyze_api_instance
            ))

            self.assertIn("error", result)
            mock_unlink.assert_called_once()


if __name__ == '__main__':
    unittest.main()
