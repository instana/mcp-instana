"""
Infrastructure Analyze MCP Tools Module

This module provides infrastructure analysis-specific MCP tools for Instana monitoring.
"""

import json
import logging
import sys
from typing import Any, Dict, List, Optional, Union

# Configure logger for this module (before imports that might fail)
logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api.infrastructure_analyze_api import (
        InfrastructureAnalyzeApi,
    )
    from instana_client.models.get_available_metrics_query import (
        GetAvailableMetricsQuery,
    )
    from instana_client.models.get_available_plugins_query import (
        GetAvailablePluginsQuery,
    )
    from instana_client.models.get_infrastructure_groups_query import (
        GetInfrastructureGroupsQuery,
    )
    from instana_client.models.get_infrastructure_query import (
        GetInfrastructureQuery,
    )
except ImportError as e:
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    parse_payload,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.core.validation import StructureValidator


# Helper function for debug printing
def debug_print(*args, **kwargs):
    """Print debug information to stderr instead of stdout"""
    print(*args, file=sys.stderr, **kwargs)

class InfrastructureAnalyzeMCPTools(BaseInstanaClient):
    """Tools for infrastructure analysis in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Analyze MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _normalize_tag_filter_expression(self, filter_expr: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pass the tagFilterExpression through unchanged.

        The SDK's TagFilter.from_dict() correctly handles both "value" (mapped to the
        TagFilterAllOfValue wrapper) and the typed fields (stringValue / numberValue /
        booleanValue) — no pre-processing is needed here.  The infrastructure API
        also accepts both forms directly.

        Args:
            filter_expr: The tagFilterExpression from the payload

        Returns:
            The tagFilterExpression unchanged.
        """
        return filter_expr

    # @register_as_tool(...)  # Disabled for future reference
    @with_header_auth(InfrastructureAnalyzeApi)
    async def get_available_metrics(self,
                                    payload: Optional[Union[Dict[str, Any], str]] = None,
                                    ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get available metrics for infrastructure monitoring.

        This tool retrieves information about available metrics for a specific entity type.
        You can use this to discover what metrics are available for monitoring different components in your environment.

        Sample payload:
        {
            "timeFrame": {
                "from": 1743920395000,
                "to": 1743923995000,
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

        Args:
            payload: Complete request payload as a dictionary or a JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available metrics or error information
        """
        try:
            logger.debug(f"get_available_metrics called with payload={payload}")

            # Parse payload using shared utility
            request_body = parse_payload(payload)
            if "error" in request_body:
                return request_body

            logger.debug(f"Final request body: {request_body}")

            # Create a GetAvailableMetricsQuery object from the request body
            try:
                # Extract parameters from the request body
                query_params = {}

                # Handle timeFrame
                if request_body and "timeFrame" in request_body:
                    time_frame = {}
                    if "to" in request_body["timeFrame"]:
                        time_frame["to"] = request_body["timeFrame"]["to"]
                    if "from" in request_body["timeFrame"]:
                        time_frame["from"] = request_body["timeFrame"]["from"]
                    if "windowSize" in request_body["timeFrame"]:
                        time_frame["windowSize"] = request_body["timeFrame"]["windowSize"]
                    query_params["timeFrame"] = time_frame

                # Handle other parameters
                if request_body and "query" in request_body:
                    query_params["query"] = request_body["query"]

                if request_body and "type" in request_body:
                    query_params["type"] = request_body["type"]

                if request_body and "tagFilterExpression" in request_body:
                    query_params["tagFilterExpression"] = request_body["tagFilterExpression"]

                logger.debug(f"Creating GetAvailableMetricsQuery with params: {query_params}")
                query_object = GetAvailableMetricsQuery(**query_params)
                logger.debug(f"Successfully created query object: {query_object}")
            except Exception as e:
                logger.error(f"Error creating GetAvailableMetricsQuery: {e}")
                return {"error": f"Failed to create query object: {e!s}"}

            # Call the get_available_metrics method from the SDK with the query object
            logger.debug("Calling get_available_metrics with query object")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_available_metrics,
                    get_available_metrics_query=query_object,
                ),
                ctx=ctx, operation_name="get_available_metrics"
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_available_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_available_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get available metrics: {e!s}"}

    @with_header_auth(InfrastructureAnalyzeApi)
    async def get_entities(self,
                           payload: Optional[Union[Dict[str, Any], str]] = None,
                           ctx=None, api_client=None,
                           resource_type: Optional[str] = None,
                           tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get infrastructure entities for a given entity type along with requested metrics.

        We want to know the memory used and no of blocked threads for entity named JVMruntimeplatform for last 1 hour in Instana. can you help us get the details ?

        This tool retrieves entities of a specific type (e.g., hosts, processes, containers) along with
        their metrics. You can filter the results using tag filters and paginate through large result sets.

        Sample payload:
        {
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "entity": "NOT_APPLICABLE",
                "name": "label",
                "operator": "EQUALS",
                "value": "custom-metrics.jar"
            },
            "timeFrame": {
                "to": 1743923995000,
                "windowSize": 3600000
            },
            "pagination": {
                "retrievalSize": 200
            },
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MAX"},
                {"metric": "memory.used", "granularity": 600000, "aggregation": "MAX"},
                {"metric": "threads.blocked", "granularity": 3600000, "aggregation": "MEAN"},
                {"metric": "threads.blocked", "granularity": 600000, "aggregation": "MEAN"}
            ]
        }

        Args:
            payload: Complete request payload as a dictionary or a JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing infrastructure entities and their metrics or error information
        """
        try:
            logger.debug(f"get_entities called with payload={payload}")

            # Parse payload using shared utility
            request_body = parse_payload(payload)
            if "error" in request_body:
                return request_body

            logger.debug(f"Final request body: {request_body}")

            # --- Pre-flight validation (collect ALL errors in one pass) ---
            if isinstance(request_body, dict):
                _sv_errors: List[str] = []
                for _sv_fn, _sv_key, _sv_kw in [
                    (StructureValidator.validate_tag_filter_expression, "tagFilterExpression", {}),
                    (StructureValidator.validate_time_frame, "timeFrame", {}),
                    (StructureValidator.validate_pagination, "pagination", {}),
                    (StructureValidator.validate_metrics_array, "metrics", {"required": False}),
                ]:
                    _sv_res = _sv_fn(request_body.get(_sv_key), **_sv_kw)
                    if _sv_res:
                        _sv_errors.extend(_sv_res["api_error"])
                # Cross-field: granularity/windowSize ratio (granularity in ms for infrastructure)
                _gr = StructureValidator.validate_granularity_ratio(
                    request_body.get("metrics"), request_body.get("timeFrame"), granularity_in_ms=True
                )
                if _gr:
                    _sv_errors.extend(_gr["api_error"])
                if _sv_errors:
                    return {
                        "elicitation_needed": True,
                        "reason": f"get_entities payload has {len(_sv_errors)} validation problem(s)",
                        "api_error": _sv_errors,
                        "message": (
                            f"The get_entities payload has {len(_sv_errors)} problem(s). "
                            "Correct all issues below and retry:\n"
                            + "\n".join(f"  - {e}" for e in _sv_errors)
                        ),
                    }
            # --- End validation ---

            # Normalize tagFilterExpression if present
            if request_body and isinstance(request_body, dict) and "tagFilterExpression" in request_body:
                request_body["tagFilterExpression"] = self._normalize_tag_filter_expression(
                    request_body["tagFilterExpression"]
                )
                logger.debug(f"Normalized tagFilterExpression: {request_body['tagFilterExpression']}")

            # Use from_dict() — NOT GetInfrastructureQuery(**dict) — to construct the
            # model.  Pydantic's @validate_call on the public SDK method coerces the
            # argument using __init__, which maps tagFilterExpression to the base
            # TagFilterExpressionElement type (only "type" field).  from_dict() routes
            # through the discriminated-union dispatcher which correctly instantiates
            # TagFilter, preserving name/operator/entity/stringValue.
            try:
                get_infra_query = GetInfrastructureQuery.from_dict(request_body)
            except Exception as model_error:
                return {"error": f"Failed to create GetInfrastructureQuery: {model_error!s}"}

            logger.debug("Calling API method get_entities_without_preload_content")
            try:
                response = await sdk_call_with_keepalive(
                    call_sdk_fn(api_client.get_entities_without_preload_content,
                        get_infrastructure_query=get_infra_query,
                    ),
                    ctx=ctx, operation_name="get_entities",
                    resource_type=resource_type, tool_name=tool_name,
                )

                if response.status != 200:
                    return self.handle_api_error_response(response, "get entities", logger)

                response_text = decode_response(response)
                result_dict = json.loads(response_text)
                logger.debug("Successfully parsed raw get_entities response")
                return result_dict
            except Exception as api_error:
                error_msg = f"API call failed: {api_error}"
                logger.error(error_msg)
                return {"error": error_msg}
        except Exception as e:
            logger.error(f"Error in get_entities: {e}", exc_info=True)
            return {"error": f"Failed to get entities: {e!s}"}

    @with_header_auth(InfrastructureAnalyzeApi)
    async def get_aggregated_entity_groups(self,
                                           payload: Optional[Union[Dict[str, Any], str]] = None,
                                           ctx=None, api_client=None,
                                           resource_type: Optional[str] = None,
                                           tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get grouped infrastructure entities with aggregated metrics.

        This tool groups entities of a specific type by specified tags and aggregates metrics for these groups.
        For example, you can group hosts by their region and get average CPU usage per region.

        Sample payload:
        {
            "timeFrame": {
                "to": 1743923995000,
                "windowSize": 3600000
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "pagination": {
                "retrievalSize": 20
            },
            "groupBy": ["host.name"],
            "type": "jvmRuntimePlatform",
            "metrics": [
                {"metric": "memory.used", "granularity": 3600000, "aggregation": "MEAN"},
                {"metric": "memory.used", "granularity": 600000, "aggregation": "MEAN"},
                {"metric": "threads.blocked", "granularity": 3600000, "aggregation": "MEAN"},
                {"metric": "threads.blocked", "granularity": 600000, "aggregation": "MEAN"}
            ],
            "order": {
                "by": "label",
                "direction": "ASC"
            }
        }

        Args:
            payload: Complete request payload as a dictionary or a JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing grouped entities and their aggregated metrics or error information
        """
        try:
            logger.debug(f"get_aggregated_entity_groups called with payload={payload}")

            # Parse payload using shared utility
            request_body = parse_payload(payload)
            if "error" in request_body:
                return request_body

            logger.debug(f"Final request body: {request_body}")

            # --- Pre-flight validation (collect ALL errors in one pass) ---
            if isinstance(request_body, dict):
                _sv_errors: List[str] = []
                for _sv_fn, _sv_key, _sv_kw in [
                    (StructureValidator.validate_tag_filter_expression, "tagFilterExpression", {}),
                    (StructureValidator.validate_time_frame, "timeFrame", {}),
                    (StructureValidator.validate_order, "order", {}),
                    (StructureValidator.validate_pagination, "pagination", {}),
                    (StructureValidator.validate_metrics_array, "metrics", {"required": False}),
                ]:
                    _sv_res = _sv_fn(request_body.get(_sv_key), **_sv_kw)
                    if _sv_res:
                        _sv_errors.extend(_sv_res["api_error"])
                # Cross-field: granularity/windowSize ratio (granularity in ms for infrastructure)
                _gr = StructureValidator.validate_granularity_ratio(
                    request_body.get("metrics"), request_body.get("timeFrame"), granularity_in_ms=True
                )
                if _gr:
                    _sv_errors.extend(_gr["api_error"])
                if _sv_errors:
                    return {
                        "elicitation_needed": True,
                        "reason": f"get_aggregated_entity_groups payload has {len(_sv_errors)} validation problem(s)",
                        "api_error": _sv_errors,
                        "message": (
                            f"The get_aggregated_entity_groups payload has {len(_sv_errors)} problem(s). "
                            "Correct all issues below and retry:\n"
                            + "\n".join(f"  - {e}" for e in _sv_errors)
                        ),
                    }
            # --- End validation ---

            # Normalize tagFilterExpression if present
            if request_body and isinstance(request_body, dict) and "tagFilterExpression" in request_body:
                request_body["tagFilterExpression"] = self._normalize_tag_filter_expression(
                    request_body["tagFilterExpression"]
                )
                logger.debug(f"Normalized tagFilterExpression: {request_body['tagFilterExpression']}")

            # Use from_dict() — NOT GetInfrastructureGroupsQuery(**dict) — to construct
            # the model.  Pydantic's @validate_call on the public SDK method coerces the
            # argument using __init__, which maps tagFilterExpression to the base
            # TagFilterExpressionElement type (only "type" field).  from_dict() routes
            # through the discriminated-union dispatcher which correctly instantiates
            # TagFilter, preserving name/operator/entity/stringValue.
            try:
                get_groups_query = GetInfrastructureGroupsQuery.from_dict(request_body)
            except Exception as model_error:
                return {"error": f"Failed to create GetInfrastructureGroupsQuery: {model_error!s}"}

            logger.debug("Calling API method get_entity_groups_without_preload_content")
            try:
                response = await sdk_call_with_keepalive(
                    call_sdk_fn(api_client.get_entity_groups_without_preload_content,
                        get_infrastructure_groups_query=get_groups_query,
                    ),
                    ctx=ctx, operation_name="get_entity_groups",
                    resource_type=resource_type, tool_name=tool_name,
                )

                # Check if the response was successful
                if response.status != 200:
                    return self.handle_api_error_response(response, "get entity groups", logger)

                # Read the response content
                response_text = decode_response(response)

                # Parse the response as JSON
                result_dict = json.loads(response_text)

                logger.debug("Successfully parsed raw response")

                # Return the full raw response without summarization
                return result_dict
            except Exception as api_error:
                error_msg = f"API call failed: {api_error}"
                logger.error(error_msg)
                return {"error": error_msg}

        except Exception as e:
            logger.error(f"Error in get_aggregated_entity_groups: {e}", exc_info=True)
            return {"error": f"Failed to get aggregated entity groups: {e!s}"}

    def _summarize_entity_groups_result(self, result_dict, query_body):
        """
        Create a summarized version of the entity groups result.

        Args:
            result_dict: The full API response
            query_body: The query body used to make the request

        Returns:
            A summarized version of the results
        """
        try:
            # Check if there's an error in the result
            if isinstance(result_dict, dict) and "error" in result_dict:
                return result_dict

            # Extract the group by tag
            group_by_tag = None
            if "groupBy" in query_body and isinstance(query_body["groupBy"], list) and len(query_body["groupBy"]) > 0:
                group_by_tag = query_body["groupBy"][0]

            # Extract host names if available
            host_names = []

            # Process each item in the results
            if "items" in result_dict and isinstance(result_dict["items"], list):
                for item in result_dict["items"]:
                    # Extract the host name
                    if "tags" in item and isinstance(item["tags"], dict) and group_by_tag in item["tags"]:
                        # Get the tag value, ensuring it's a string
                        tag_value = item["tags"][group_by_tag]
                        if isinstance(tag_value, str):
                            host_name = tag_value
                        elif isinstance(tag_value, dict) and "name" in tag_value:
                            # Handle case where tag value is a dictionary with a name field
                            host_name = tag_value["name"]
                        else:
                            # Convert other types to string
                            host_name = str(tag_value)

                        if host_name not in host_names:
                            host_names.append(host_name)

            # Sort host names alphabetically
            host_names.sort()

            # Create the exact format requested
            summary = {
                "hosts": host_names,
                "count": len(host_names),
                "summary": f"Found {len(host_names)} hosts: {', '.join(host_names)}"
            }

            return summary
        except Exception as e:
            logger.error(f"Error in _summarize_entity_groups_result: {e}", exc_info=True)
            # If summarization fails, return an error message
            return {
                "error": f"Failed to summarize results: {e!s}"
            }

    @with_header_auth(InfrastructureAnalyzeApi)
    async def get_available_plugins(self,
                                    payload: Optional[Union[Dict[str, Any], str]] = None,
                                    ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get available plugins for infrastructure monitoring.

        This tool retrieves information about available plugins for infrastructure monitoring.
        You can use this to discover what types of entities can be monitored in your environment.

        Sample payload:
        {
            "timeFrame": {
                "to": 1743923995000,
                "windowSize": 3600000
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            },
            "query": "java",
            "offline": false
        }

        Args:
            payload: Complete request payload as a dictionary or a JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available plugins or error information
        """
        try:
            logger.debug(f"get_available_plugins called with payload={payload}")

            # Parse payload using shared utility
            request_body = parse_payload(payload)
            if "error" in request_body:
                return request_body

            logger.debug(f"Final request body: {request_body}")

            # Create a GetAvailablePluginsQuery object from the request body
            try:
                # Extract parameters from the request body
                query_params = {}

                # Handle timeFrame
                if request_body and "timeFrame" in request_body:
                    time_frame = {}
                    if "to" in request_body["timeFrame"]:
                        time_frame["to"] = request_body["timeFrame"]["to"]
                    if "windowSize" in request_body["timeFrame"]:
                        time_frame["windowSize"] = request_body["timeFrame"]["windowSize"]
                    query_params["timeFrame"] = time_frame

                # Handle other parameters
                if request_body and "query" in request_body:
                    query_params["query"] = request_body["query"]

                if request_body and "offline" in request_body:
                    query_params["offline"] = request_body["offline"]

                if request_body and "tagFilterExpression" in request_body:
                    query_params["tagFilterExpression"] = request_body["tagFilterExpression"]

                logger.debug(f"Creating GetAvailablePluginsQuery with params: {query_params}")
                query_object = GetAvailablePluginsQuery(**query_params)
                logger.debug(f"Successfully created query object: {query_object}")
            except Exception as e:
                logger.error(f"Error creating GetAvailablePluginsQuery: {e}")
                return {"error": f"Failed to create query object: {e!s}"}

            # Call the get_available_plugins method from the SDK with the query object
            logger.debug("Calling get_available_plugins with query object")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_available_plugins,
                    get_available_plugins_query=query_object,
                ),
                ctx=ctx, operation_name="get_available_plugins"
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_available_plugins: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_available_plugins: {e}", exc_info=True)
            return {"error": f"Failed to get available plugins: {e!s}"}
