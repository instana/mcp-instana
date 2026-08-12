"""Smart router for read-only Instana log search."""

from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_nested_datetime_param
from src.core.utils import BaseInstanaClient, register_as_tool
from src.core.validation import WINDOW_SIZE_MAX_MS

DEFAULT_REQUESTED_TAGS = ["log.timestamp", "log.level", "log.message"]
VALID_OPERATORS = {
    "EQUALS", "NOT_EQUAL", "CONTAINS", "NOT_CONTAIN", "STARTS_WITH",
    "ENDS_WITH", "NOT_EMPTY", "IS_EMPTY",
}
VALID_ENTITIES = {"NOT_APPLICABLE", "DESTINATION", "SOURCE"}


class LogSmartRouterMCPTool(BaseInstanaClient):
    """Expose the documented log search API as a single MCP operation."""

    def __init__(self, read_token: str, base_url: str):
        super().__init__(read_token=read_token, base_url=base_url)
        from src.log.log_search import LogSearchMCPTools

        self.log_search_client = LogSearchMCPTools(read_token, base_url)

    @staticmethod
    def _validate_filter(node: Any, path: str, errors: List[str]) -> None:
        if not isinstance(node, dict):
            errors.append(f"{path}: must be an object")
            return
        kind = node.get("type")
        if kind == "TAG_FILTER":
            if not isinstance(node.get("name"), str) or not node["name"].strip():
                errors.append(f"{path}.name: must be a non-empty string")
            if node.get("entity") not in VALID_ENTITIES:
                errors.append(f"{path}.entity: must be one of {sorted(VALID_ENTITIES)}")
            operator = node.get("operator")
            if operator not in VALID_OPERATORS:
                errors.append(f"{path}.operator: must be one of {sorted(VALID_OPERATORS)}")
            if operator not in {"NOT_EMPTY", "IS_EMPTY"} and "value" not in node:
                errors.append(f"{path}.value: is required unless operator is NOT_EMPTY or IS_EMPTY")
            return
        if kind == "EXPRESSION":
            if node.get("logicalOperator") not in {"AND", "OR"}:
                errors.append(f"{path}.logicalOperator: must be AND or OR")
            elements = node.get("elements")
            if not isinstance(elements, list):
                errors.append(f"{path}.elements: must be a list")
            else:
                for index, element in enumerate(elements):
                    LogSmartRouterMCPTool._validate_filter(element, f"{path}.elements[{index}]", errors)
            return
        errors.append(f"{path}.type: must be TAG_FILTER or EXPRESSION")

    @staticmethod
    def _validation_error(errors: List[str]) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": f"log search payload has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": "Correct the log search payload and retry:\n" + "\n".join(f"  - {error}" for error in errors),
        }

    @register_as_tool(
        title="Manage Instana Logs",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False),
        description="""Search Instana logs through the documented logging API.

Only the read-only `search` operation is supported. Defaults: the last hour,
the log.timestamp/log.level/log.message tags, 10 results, offset 0, and DESC.
Use offset to request a subsequent page; the tool never follows pagination itself.
Log-native filters use entity NOT_APPLICABLE; service-related filters use DESTINATION.""",
    )
    async def manage_logs(
        self, operation: str, params: Optional[Dict[str, Any]] = None, ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """Search Instana logs."""
        if operation != "search":
            return self._validation_error(["operation: must be 'search'"])
        params = params or {}
        converted = convert_nested_datetime_param(params, "time_frame", "to", default_timezone="UTC")
        if "error" in converted:
            return self._validation_error([converted["error"]])
        params = converted["params"]

        errors: List[str] = []
        time_frame = params.get("time_frame", {})
        if not isinstance(time_frame, dict):
            errors.append("time_frame: must be an object")
            time_frame = {}
        else:
            time_frame = {"to": time_frame.get("to"), "windowSize": time_frame.get("windowSize", 3_600_000)}
            if time_frame["to"] is None:
                time_frame.pop("to")
            window_size = time_frame["windowSize"]
            if isinstance(window_size, bool) or not isinstance(window_size, int) or not 0 <= window_size <= WINDOW_SIZE_MAX_MS:
                errors.append(f"time_frame.windowSize: must be an integer from 0 to {WINDOW_SIZE_MAX_MS}")

        requested_tags = params.get("requested_tags", DEFAULT_REQUESTED_TAGS)
        if not isinstance(requested_tags, list) or not requested_tags or len(requested_tags) > 10:
            errors.append("requested_tags: must be a non-empty list with at most 10 items")
        elif any(not isinstance(tag, str) or not tag.strip() for tag in requested_tags):
            errors.append("requested_tags: every item must be a non-empty string")

        retrieval_size = params.get("retrieval_size", 10)
        if isinstance(retrieval_size, bool) or not isinstance(retrieval_size, int) or not 1 <= retrieval_size <= 200:
            errors.append("retrieval_size: must be an integer from 1 to 200")
        offset = params.get("offset", 0)
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 2000:
            errors.append("offset: must be an integer from 0 to 2000")
        order_direction = params.get("order_direction", "DESC")
        if order_direction not in {"ASC", "DESC"}:
            errors.append("order_direction: must be ASC or DESC")
        tag_filter_expression = params.get("tag_filter_expression")
        if tag_filter_expression is not None:
            self._validate_filter(tag_filter_expression, "tag_filter_expression", errors)

        if errors:
            return self._validation_error(errors)
        results = await self.log_search_client.search_logs(
            time_frame=time_frame,
            requested_tags=requested_tags,
            tag_filter_expression=tag_filter_expression,
            retrieval_size=retrieval_size,
            offset=offset,
            order_direction=order_direction,
        )
        return {"operation": "search", "results": results}
