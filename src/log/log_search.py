"""Read-only Instana log search via the documented logging REST API."""

import logging
import time
from typing import Any, Dict, List, Optional

from instana_client.api.logging_analyze_api import LoggingAnalyzeApi

from src.core.utils import BaseInstanaClient, with_header_auth

DEFAULT_REQUESTED_TAGS = ["log.timestamp", "log.level", "log.message"]
logger = logging.getLogger(__name__)


class LogSearchMCPTools(BaseInstanaClient):
    """Client for Instana's logging search endpoint."""

    @with_header_auth(LoggingAnalyzeApi)
    async def search_logs(
        self,
        time_frame: Optional[Dict[str, Any]] = None,
        requested_tags: Optional[List[str]] = None,
        tag_filter_expression: Optional[Dict[str, Any]] = None,
        retrieval_size: int = 10,
        offset: int = 0,
        order_direction: str = "DESC",
        api_client: Any = None,
    ) -> Dict[str, Any]:
        """Search logs without following pagination automatically."""
        time_frame = time_frame or {}
        payload: Dict[str, Any] = {
            "timeConfig": {
                "to": time_frame.get("to", int(time.time() * 1000)),
                "windowSize": time_frame.get("windowSize", 3_600_000),
            },
            "requestedTags": requested_tags or DEFAULT_REQUESTED_TAGS,
            "retrievalSize": retrieval_size,
            "offset": offset,
            "orderDirection": order_direction,
        }
        if tag_filter_expression:
            payload["tagFilterExpression"] = tag_filter_expression

        try:
            return api_client.search_logs(request_body=payload)
        except Exception as error:
            logger.error("Log search failed: %s", error, exc_info=True)
            return {"error": f"Log search failed: {error!s}"}
