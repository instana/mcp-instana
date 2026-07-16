"""
Application Analyze MCP Tools Module

This module provides application analyze tool functionality for Instana monitoring.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.application_analyze_api import ApplicationAnalyzeApi
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration
    from instana_client.models.get_call_groups import GetCallGroups
    from instana_client.models.get_trace_groups import GetTraceGroups
    from instana_client.models.get_traces import GetTraces

except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import application analyze API", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationAnalyzeMCPTools(BaseInstanaClient):
    """Tools for application analyze in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Analyze MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

        try:

            # Configure the API client with the correct base URL and authentication
            configuration = Configuration()
            configuration.host = base_url
            configuration.api_key['ApiKeyAuth'] = read_token
            configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

            # Create an API client with this configuration
            api_client = ApiClient(configuration=configuration)

            # Initialize the Instana SDK's ApplicationAnalyzeApi with our configured client
            self.analyze_api = ApplicationAnalyzeApi(api_client=api_client)
        except Exception as e:
            logger.error(f"Error initializing ApplicationAnalyzeApi: {e}", exc_info=True)
            raise

    # CRUD Operations Dispatcher - called by application_smart_router_tool.py
    async def execute_analyze_operation(
        self,
        operation: str,
        params: Optional[Union[Dict[str, Any], str]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """
        Execute Application Analyze operations.
        Called by the smart router tool.

        Args:
            operation: Operation to perform (get_all_traces, get_trace_details)
            params: Dictionary containing operation-specific parameters
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            if operation == "get_all_traces":
                payload = params.get('payload')
                return await self.get_all_traces(payload, ctx=ctx)
            elif operation == "get_trace_details":
                return await self.get_trace_details(
                    id=params.get('id'),
                    retrieval_size=params.get('retrievalSize'),
                    offset=params.get('offset'),
                    ingestion_time=params.get('ingestionTime'),
                    ctx=ctx
                )
            elif operation == "get_trace_groups":
                payload = params.get('payload') if params else None
                return await self.get_trace_groups(payload, ctx=ctx)
            else:
                return {"error": f"Operation '{operation}' not supported"}

        except Exception as e:
            logger.error(f"Error executing {operation}: {e}", exc_info=True)
            return {"error": f"Error executing {operation}: {e!s}"}

    def _validate_trace_details_params(self, id: str, retrieval_size: Optional[int], offset: Optional[int], ingestion_time: Optional[int]) -> Optional[Dict[str, Any]]:
        """Validate parameters for get_trace_details."""
        if not id:
            logger.warning("Trace ID must be provided")
            return {"error": "Trace ID must be provided"}

        if offset is not None and ingestion_time is None:
            logger.warning("If offset is provided, ingestion_time must also be provided")
            return {"error": "If offset is provided, ingestion_time must also be provided"}

        if retrieval_size is not None and (retrieval_size < 1 or retrieval_size > 10000):
            logger.warning(f"retrieval_size must be between 1 and 10000, got: {retrieval_size}")
            return {"error": "retrieval_size must be between 1 and 10000"}

        return None


    @with_header_auth(ApplicationAnalyzeApi)
    async def get_trace_details(
        self,
        id: str,
        retrieval_size: Optional[int] = None,
        offset: Optional[int] = None,
        ingestion_time: Optional[int] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Get details of a specific trace.
        This tool is to retrieve comprehensive details of a particular trace.

        Args:
            id (str): The ID of the trace.
            retrieval_size (Optional[int]): The number of records to retrieve in a single request.
                                        Minimum value is 1 and maximum value is 10000.
            offset (Optional[int]): The number of records to be skipped from the ingestion_time.
            ingestion_time (Optional[int]): The timestamp indicating the starting point from which data was ingested.
            ctx: Optional context for the request.

        Returns:
            Dict containing items (trace detail records), itemCount, canLoadMore,
            and cursor fields (ingestionTime, offset) if more data available
        """
        try:
            # Validate parameters
            validation_error = self._validate_trace_details_params(id, retrieval_size, offset, ingestion_time)
            if validation_error:
                return validation_error

            # Fetch trace details
            logger.debug(f"Fetching trace details for id={id}")
            result = api_client.get_trace_download(
                id=id,
                retrieval_size=retrieval_size,
                offset=offset,
                ingestion_time=ingestion_time
            )

            # Convert result to dictionary
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
            logger.debug(f"Result from get_trace_details: {result_dict}")

            items = result_dict.get("items", [])
            can_load_more = result_dict.get("canLoadMore", False)

            # Build response with trace detail records
            response = {
                "items": items,
                "itemCount": len(items),
                "canLoadMore": can_load_more
            }

            # Add cursor fields if available
            if items and can_load_more and "cursor" in items[-1]:
                cursor = items[-1]["cursor"]
                if "ingestionTime" in cursor:
                    response["ingestionTime"] = cursor["ingestionTime"]
                if "offset" in cursor:
                    response["offset"] = cursor["offset"]

            return response

        except Exception as e:
            logger.error(f"Error getting trace details: {e}", exc_info=True)
            return {"error": f"Failed to get trace details: {e!s}"}


    def _parse_traces_payload(self, payload: Optional[Union[Dict[str, Any], str]]) -> Union[Dict[str, Any], Dict[str, str]]:
        """Parse payload string to dictionary."""
        if not isinstance(payload, str):
            return payload if payload is not None else {}

        logger.debug("Payload is a string, attempting to parse")
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            try:
                return json.loads(payload.replace("'", "\""))
            except json.JSONDecodeError:
                import ast
                try:
                    return ast.literal_eval(payload)
                except (SyntaxError, ValueError) as e:
                    return {"error": f"Invalid payload format: {e}"}

    def _build_paginated_response(
        self,
        result_dict: Dict[str, Any],
        include_total_hits: bool = True
    ) -> Dict[str, Any]:
        """
        Build a standardized paginated response with cursor fields.

        Args:
            result_dict: The API response dictionary
            include_total_hits: Whether to include totalHits in response

        Returns:
            Standardized response dictionary with items, itemCount, canLoadMore,
            and cursor fields if available
        """
        items = result_dict.get("items", [])
        can_load_more = result_dict.get("canLoadMore", False)

        response = {
            "items": items,
            "itemCount": len(items),
            "canLoadMore": can_load_more
        }

        if include_total_hits:
            total_hits = result_dict.get("totalHits")
            if total_hits is not None:
                response["totalHits"] = total_hits

        # Add cursor fields if more data available
        if items and can_load_more and "cursor" in items[-1]:
            cursor = items[-1]["cursor"]
            if "ingestionTime" in cursor:
                response["ingestionTime"] = cursor["ingestionTime"]
            if "offset" in cursor:
                response["offset"] = cursor["offset"]

        return response


    def _sanitize_service_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize trace data to handle None values in Service.technologies field.
        The Instana API sometimes returns None for technologies, but the SDK model requires a list.
        """
        if isinstance(data, dict):
            # Check if this is a service object with None technologies
            if "technologies" in data and data["technologies"] is None:
                data["technologies"] = []
                logger.debug("Sanitized None technologies field to empty list")

            # Recursively process nested dictionaries
            for key, value in data.items():
                if isinstance(value, dict):
                    data[key] = self._sanitize_service_data(value)
                elif isinstance(value, list):
                    data[key] = [self._sanitize_service_data(item) if isinstance(item, dict) else item for item in value]

        return data

    @with_header_auth(ApplicationAnalyzeApi)
    async def get_all_traces(
        self,
        payload: Optional[Union[Dict[str, Any], str]]=None,
        api_client = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Get traces from Instana API.

        Fetches one page of traces and returns them directly in the response.
        Supports pagination using cursor fields for fetching subsequent pages.

        Args:
            payload: Request payload for GetTraces API
            api_client: API client instance
            ctx: MCP context

        Sample payload: {
        "includeInternal": false,
        "includeSynthetic": false,
        "pagination": {
            "retrievalSize": 200,
            "ingestionTime": 1234567890,
            "offset": 10
        },
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
            {
                "type": "TAG_FILTER",
                "name": "endpoint.name",
                "operator": "EQUALS",
                "entity": "DESTINATION",
                "value": "GET /"
            },
            {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "EQUALS",
                "entity": "DESTINATION",
                "value": "groundskeeper"
            }
            ]
        },
        "order": {
            "by": "traceLabel",
            "direction": "DESC"
        }
        }


        Returns:
            Dict containing items (trace records), itemCount, canLoadMore, totalHits,
            and cursor fields (ingestionTime, offset) if more data available
        """
        try:
            # Parse the payload
            request_body = self._parse_traces_payload(payload)
            if "error" in request_body:
                return request_body

            # Call API using _without_preload_content to get raw response
            config = GetTraces.from_dict(request_body)
            result = api_client.get_traces_without_preload_content(get_traces=config)

            # Parse raw JSON response
            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            # Sanitize the data to handle None values in Service.technologies
            result_dict = self._sanitize_service_data(result_dict)

            # Build and return standardized response
            return self._build_paginated_response(result_dict, include_total_hits=True)

        except Exception as e:
            logger.error(f"Error in get_traces: {e}", exc_info=True)
            return {"error": f"Failed to get traces: {e!s}"}

    @with_header_auth(ApplicationAnalyzeApi)
    async def get_trace_groups(
        self,
        payload: Optional[Union[Dict[str, Any], str]] = None,
        api_client: Any = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Get grouped trace metrics from Instana API.

        Fetches grouped trace results from the trace groups endpoint.
        The payload must include the required 'group' and 'metrics' fields.

        CRITICAL: The "calls" metric is NOT supported for trace operations. Use "traces" or other trace-specific metrics.
        Use get_metric_catalog first to retrieve valid metric names and aggregations as described in the critical workflow.

        The required 'group' object must contain:
            - groupbyTag: the name of the group tag (the supported 'groupbyTag' values are 'trace.endpoint.name' and 'trace.service.name').
            - groupbyTagEntity: the entity to group by. Allowed values are
              'NOT_APPLICABLE', 'DESTINATION', and 'SOURCE'.
                * SOURCE: apply tag filter to the source entity.
                * DESTINATION: apply tag filter to the destination entity.
                * NOT_APPLICABLE: use when the tag is independent of source/destination.
            - groupbyTagSecondLevelKey: optional second-level tag key if present.

        Args:
            payload: Request payload for GetTraceGroups API
            api_client: API client instance
            ctx: MCP context

        Returns:
            Dict containing items (grouped trace records), itemCount, canLoadMore,
            totalHits, and cursor fields (ingestionTime, offset) if more data available
        """
        try:
            request_body = self._parse_traces_payload(payload)
            if "error" in request_body:
                return request_body

            config = GetTraceGroups.from_dict(request_body)
            result = api_client.get_trace_groups_without_preload_content(get_trace_groups=config)

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)
            result_dict = self._sanitize_service_data(result_dict)

            # Build and return standardized response
            return self._build_paginated_response(result_dict, include_total_hits=True)

        except Exception as e:
            logger.error(f"Error in get_trace_groups: {e}", exc_info=True)
            return {"error": f"Failed to get trace groups: {e!s}"}

