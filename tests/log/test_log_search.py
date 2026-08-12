import asyncio
import unittest
from unittest.mock import MagicMock

from src.log.log_search import LogSearchMCPTools


class TestLogSearchMCPTools(unittest.TestCase):
    def setUp(self):
        self.client = LogSearchMCPTools("stdio-token", "https://stdio.example")

    def test_search_converts_payload_and_preserves_response(self):
        api_client = MagicMock()
        api_client.search_logs.return_value = {
            "items": [{"log.message": "failure"}],
            "totalHits": 1,
            "canLoadMore": True,
        }

        result = asyncio.run(self.client.search_logs(
            time_frame={"to": 1_700_000_000_000, "windowSize": 60_000},
            requested_tags=["log.message"],
            tag_filter_expression={"type": "TAG_FILTER"},
            retrieval_size=10,
            offset=20,
            order_direction="ASC",
            api_client=api_client,
        ))

        self.assertEqual(result["totalHits"], 1)
        api_client.search_logs.assert_called_once_with(request_body={
            "timeConfig": {"to": 1_700_000_000_000, "windowSize": 60_000},
            "requestedTags": ["log.message"],
            "tagFilterExpression": {"type": "TAG_FILTER"},
            "retrievalSize": 10,
            "offset": 20,
            "orderDirection": "ASC",
        })

    def test_search_defaults(self):
        api_client = MagicMock()
        api_client.search_logs.return_value = {"items": [], "canLoadMore": False}
        asyncio.run(self.client.search_logs(api_client=api_client))

        payload = api_client.search_logs.call_args.kwargs["request_body"]
        self.assertEqual(payload["timeConfig"]["windowSize"], 3_600_000)
        self.assertEqual(payload["requestedTags"], ["log.timestamp", "log.level", "log.message"])
        self.assertEqual(payload["retrievalSize"], 10)
        self.assertEqual(payload["offset"], 0)
        self.assertEqual(payload["orderDirection"], "DESC")

    def test_search_handles_sdk_failure(self):
        api_client = MagicMock()
        api_client.search_logs.side_effect = RuntimeError("service unavailable")

        result = asyncio.run(self.client.search_logs(api_client=api_client))

        self.assertEqual(result, {"error": "Log search failed: service unavailable"})
