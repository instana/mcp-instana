import asyncio
import unittest
from unittest.mock import MagicMock

from instana_client.models.logs_query import LogsQuery

from src.log.log_search import LogSearchMCPTools


class TestLogSearchMCPTools(unittest.TestCase):
    def setUp(self):
        self.client = LogSearchMCPTools("stdio-token", "https://stdio.example")

    def test_search_converts_payload_and_preserves_response(self):
        api_client = MagicMock()
        api_client.get_logs.return_value = {
            "items": [{"log.message": "failure"}],
            "totalHits": 1,
            "canLoadMore": True,
        }

        result = asyncio.run(self.client.search_logs(
            time_frame={"to": 1_700_000_000_000, "windowSize": 60_000},
            requested_tags=["log.message"],
            tag_filter_expression={
                "type": "TAG_FILTER",
                "name": "log.level",
                "entity": "NOT_APPLICABLE",
                "operator": "EQUALS",
                "value": "ERROR",
            },
            retrieval_size=10,
            offset=20,
            order_direction="ASC",
            api_client=api_client,
        ))

        self.assertEqual(result["totalHits"], 1)
        api_client.get_logs.assert_called_once()
        logs_query = api_client.get_logs.call_args.kwargs["logs_query"]
        self.assertIsInstance(logs_query, LogsQuery)
        payload = logs_query.to_dict()
        self.assertEqual(payload["timeConfig"]["to"], 1_700_000_000_000)
        self.assertEqual(payload["timeConfig"]["windowSize"], 60_000)
        self.assertEqual(payload["requestedTags"], ["log.message"])
        self.assertEqual(payload["tagFilterExpression"], {
            "type": "TAG_FILTER",
            "name": "log.level",
            "entity": "NOT_APPLICABLE",
            "operator": "EQUALS",
            "value": "ERROR",
        })
        self.assertEqual(payload["retrievalSize"], 10)
        self.assertEqual(payload["offset"], 20)
        self.assertEqual(payload["orderDirection"], "ASC")

    def test_search_defaults(self):
        api_client = MagicMock()
        api_client.get_logs.return_value = {"items": [], "canLoadMore": False}
        asyncio.run(self.client.search_logs(api_client=api_client))

        payload = api_client.get_logs.call_args.kwargs["logs_query"].to_dict()
        self.assertEqual(payload["timeConfig"]["windowSize"], 3_600_000)
        self.assertEqual(payload["requestedTags"], ["log.timestamp", "log.level", "log.message"])
        self.assertEqual(payload["retrievalSize"], 10)
        self.assertEqual(payload["offset"], 0)
        self.assertEqual(payload["orderDirection"], "DESC")

    def test_search_supports_pagination_and_requested_tag_limits(self):
        api_client = MagicMock()
        api_client.get_logs.return_value = {"items": [], "canLoadMore": True}
        requested_tags = [f"log.custom.{index}" for index in range(10)]
        tag_filter_expression = {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [{
                "type": "TAG_FILTER",
                "name": "log.level",
                "entity": "NOT_APPLICABLE",
                "operator": "EQUALS",
                "value": "ERROR",
            }],
        }

        asyncio.run(self.client.search_logs(
            requested_tags=requested_tags,
            tag_filter_expression=tag_filter_expression,
            retrieval_size=200,
            offset=2000,
            api_client=api_client,
        ))

        payload = api_client.get_logs.call_args.kwargs["logs_query"].to_dict()
        self.assertEqual(payload["requestedTags"], requested_tags)
        self.assertEqual(payload["retrievalSize"], 200)
        self.assertEqual(payload["offset"], 2000)
        self.assertEqual(payload["tagFilterExpression"], tag_filter_expression)

    def test_search_handles_sdk_failure(self):
        api_client = MagicMock()
        api_client.get_logs.side_effect = RuntimeError("service unavailable")

        result = asyncio.run(self.client.search_logs(api_client=api_client))

        self.assertEqual(result, {"error": "Log search failed: service unavailable"})

    def test_search_serializes_sdk_response(self):
        api_client = MagicMock()
        response = MagicMock()
        response.to_dict.return_value = {"items": [{"log.message": "failure"}], "canLoadMore": False}
        api_client.get_logs.return_value = response

        result = asyncio.run(self.client.search_logs(api_client=api_client))

        response.to_dict.assert_called_once_with()
        self.assertEqual(result, response.to_dict.return_value)
