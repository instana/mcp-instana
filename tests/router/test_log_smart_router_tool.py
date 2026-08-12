import asyncio
import unittest
from unittest.mock import AsyncMock

from src.router.log_smart_router_tool import LogSmartRouterMCPTool


class TestLogSmartRouterMCPTool(unittest.TestCase):
    def setUp(self):
        self.router = LogSmartRouterMCPTool("token", "https://logs.example")
        self.router.log_search_client.search_logs = AsyncMock(return_value={"items": [], "canLoadMore": False})

    def test_dispatches_defaults_and_converts_datetime(self):
        result = asyncio.run(self.router.manage_logs("search", {
            "time_frame": {"to": "19 March 2026, 2:47 PM|IST"},
        }))
        self.assertEqual(result["operation"], "search")
        kwargs = self.router.log_search_client.search_logs.call_args.kwargs
        self.assertIsInstance(kwargs["time_frame"]["to"], int)
        self.assertEqual(kwargs["time_frame"]["windowSize"], 3_600_000)
        self.assertEqual(kwargs["retrieval_size"], 10)

    def test_rejects_invalid_parameters_without_calling_client(self):
        result = asyncio.run(self.router.manage_logs("search", {
            "time_frame": {"windowSize": -1},
            "requested_tags": [],
            "retrieval_size": 201,
            "offset": 2001,
            "order_direction": "DOWN",
            "tag_filter_expression": {"type": "TAG_FILTER", "name": "log.level", "operator": "BAD"},
        }))
        self.assertTrue(result["elicitation_needed"])
        self.assertGreaterEqual(len(result["api_error"]), 6)
        self.router.log_search_client.search_logs.assert_not_called()

    def test_valid_nested_filter_and_invalid_operation(self):
        valid_filter = {
            "type": "EXPRESSION", "logicalOperator": "AND", "elements": [{
                "type": "TAG_FILTER", "name": "service.name", "operator": "EQUALS",
                "entity": "DESTINATION", "value": "payment",
            }],
        }
        result = asyncio.run(self.router.manage_logs("search", {"tag_filter_expression": valid_filter}))
        self.assertIn("results", result)
        invalid = asyncio.run(self.router.manage_logs("delete"))
        self.assertTrue(invalid["elicitation_needed"])

    def test_rejects_empty_filter_without_calling_client(self):
        result = asyncio.run(self.router.manage_logs("search", {"tag_filter_expression": []}))

        self.assertTrue(result["elicitation_needed"])
        self.assertIn("tag_filter_expression: must be an object", result["api_error"])
        self.router.log_search_client.search_logs.assert_not_called()
