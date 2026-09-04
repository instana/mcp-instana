"""
Application Call Group MCP Tools Module

This module provides application call group metrics-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.application_analyze_api import ApplicationAnalyzeApi
    from instana_client.models.get_call_groups import GetCallGroups
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.core.validation import (
    BooleanCoercer,
    StructureValidator,
)

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationCallGroupMCPTools(BaseInstanaClient):
    """Tools for application call group metrics in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Call Group MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    # @register_as_tool decorator commented out - not exposed as MCP tool
    # @register_as_tool(
    #     title="Get Grouped Calls Metrics",
    #     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    # )
    @staticmethod
    def _validate_call_group_structure(
        metrics: Optional[List[Dict[str, Any]]],
        time_frame: Optional[Dict[str, int]],
        group: Optional[Dict[str, str]],
        tag_filter_expression: Optional[Dict[str, Any]],
        order: Optional[Dict[str, str]],
        pagination: Optional[Dict[str, int]],
    ) -> Optional[Dict[str, Any]]:
        """Run structural validators; return an elicitation dict on failure, else None."""
        all_errors: List[str] = []
        for validator_fn, field_val, kwargs in [
            (StructureValidator.validate_metrics_array, metrics, {"required": False}),
            (StructureValidator.validate_group, group, {"required": False}),
            (StructureValidator.validate_tag_filter_expression, tag_filter_expression, {}),
            (StructureValidator.validate_order, order, {}),
            (StructureValidator.validate_pagination, pagination, {}),
            (StructureValidator.validate_time_frame, time_frame, {}),
        ]:
            result = validator_fn(field_val, **kwargs)
            if result:
                all_errors.extend(result["api_error"])
        # Cross-field: granularity/windowSize ratio (granularity in seconds for application)
        _gr = StructureValidator.validate_granularity_ratio(metrics, time_frame, granularity_in_ms=False)
        if _gr:
            all_errors.extend(_gr["api_error"])
        if not all_errors:
            return None
        return {
            "elicitation_needed": True,
            "reason": f"get_grouped_calls_metrics payload has {len(all_errors)} validation problem(s)",
            "api_error": all_errors,
            "message": (
                f"The get_grouped_calls_metrics payload has {len(all_errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in all_errors)
            ),
        }

    @staticmethod
    def _apply_call_group_defaults(
        metrics: Optional[List[Dict[str, Any]]],
        time_frame: Optional[Dict[str, int]],
        group: Optional[Dict[str, str]],
    ) -> tuple:
        """Return (metrics, time_frame, group) with defaults applied where None/empty."""
        if not time_frame:
            time_frame = {
                "to": int(datetime.now().timestamp() * 1000),
                "windowSize": 3600000,
            }
        if not metrics:
            metrics = [
                {"metric": "calls", "aggregation": "SUM"},
                {"metric": "latency", "aggregation": "MEAN"},
            ]
        if not group:
            group = {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
        return metrics, time_frame, group

    @staticmethod
    def _build_call_group_request(
        metrics: List[Dict[str, Any]],
        time_frame: Dict[str, int],
        group: Dict[str, str],
        tag_filter_expression: Optional[Dict[str, Any]],
        order: Optional[Dict[str, str]],
        pagination: Optional[Dict[str, int]],
        include_internal: Optional[bool],
        include_synthetic: Optional[bool],
    ) -> Dict[str, Any]:
        """Assemble the camelCase SDK request body from validated parameters."""
        body: Dict[str, Any] = {
            "group": group,
            "metrics": metrics,
            "timeFrame": time_frame,
        }
        if tag_filter_expression:
            body["tagFilterExpression"] = tag_filter_expression
        if pagination:
            body["pagination"] = pagination
        if order:
            body["order"] = order
        if include_internal is not None:
            body["includeInternal"] = include_internal
        if include_synthetic is not None:
            body["includeSynthetic"] = include_synthetic
        return body

    @staticmethod
    def _log_response_item(idx: int, item: Any) -> None:
        """Log debug info for a single response item."""
        logger.debug(f"\nGroup {idx}:")
        logger.debug(f"  Keys: {item.keys() if isinstance(item, dict) else 'N/A'}")
        if isinstance(item, dict) and "metrics" in item:
            logger.debug(f"  Metrics: {item['metrics'].keys() if isinstance(item['metrics'], dict) else item['metrics']}")

    @staticmethod
    def _log_call_group_response(result_dict: Any) -> None:
        """Emit debug-level diagnostics for the raw API response."""
        logger.debug("=" * 80)
        logger.debug("📥 INSTANA API RESPONSE DEBUG - CALL GROUPS")
        logger.debug("=" * 80)
        logger.debug(f"Response Type: {type(result_dict)}")
        logger.debug(f"Response Keys: {result_dict.keys() if isinstance(result_dict, dict) else 'N/A'}")
        if isinstance(result_dict, dict) and "items" in result_dict:
            logger.debug(f"Number of groups: {len(result_dict['items'])}")
            for idx, item in enumerate(result_dict["items"][:3]):
                ApplicationCallGroupMCPTools._log_response_item(idx, item)
        logger.debug("=" * 80)
        logger.debug(f"Full Result: {result_dict}")

    @with_header_auth(ApplicationAnalyzeApi)
    async def get_grouped_calls_metrics(
        self,
        metrics: Optional[List[Dict[str, Any]]] = None,
        time_frame: Optional[Dict[str, int]] = None,
        group: Optional[Dict[str, str]] = None,
        tag_filter_expression: Optional[Dict[str, Any]] = None,
        include_internal: Optional[bool] = False,
        include_synthetic: Optional[bool] = False,
        order: Optional[Dict[str, str]] = None,
        pagination: Optional[Dict[str, int]] = None,
        fill_time_series: Optional[bool] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get grouped calls metrics.

        This API endpoint retrieves metrics for calls grouped by tags (e.g., service name, endpoint name).
        Use this to analyze call patterns, latency, and errors across different services or endpoints.

        Args:
            metrics: List of metrics to retrieve with their aggregations
                Example: [
                    {"metric": "calls", "aggregation": "SUM"},
                    {"metric": "latency", "aggregation": "P75", "granularity": 360}
                ]
            time_frame: Time range for metrics
                Example: {"to": 1688366990000, "windowSize": 600000}
            group: Grouping configuration
                Example: {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
            tag_filter_expression: Filter expression for tags
                Example: {
                    "type": "EXPRESSION",
                    "logicalOperator": "AND",
                    "elements": [
                        {
                            "type": "TAG_FILTER",
                            "name": "call.type",
                            "operator": "EQUALS",
                            "entity": "NOT_APPLICABLE",
                            "value": "DATABASE"
                        }
                    ]
                }
            include_internal: Whether to include internal calls (default: False)
            include_synthetic: Whether to include synthetic calls (default: False)
            order: Ordering configuration
                Example: {"by": "calls", "direction": "DESC"}
            pagination: Pagination configuration
                Example: {"retrievalSize": 20}
            fill_time_series: Whether to fill missing data points with zeroes
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing grouped call metrics data or error information
        """
        try:
            logger.debug(f"get_grouped_calls_metrics called with metrics={metrics}, group={group}")

            include_internal = BooleanCoercer.coerce(include_internal) if include_internal is not None else include_internal
            include_synthetic = BooleanCoercer.coerce(include_synthetic) if include_synthetic is not None else include_synthetic

            elicitation_request = self._check_elicitation_for_call_group_metrics(metrics, time_frame, group)
            if elicitation_request:
                logger.info("Elicitation needed for call group metrics")
                return elicitation_request

            validation_error = self._validate_call_group_structure(
                metrics, time_frame, group, tag_filter_expression, order, pagination
            )
            if validation_error:
                return validation_error

            metrics, time_frame, group = self._apply_call_group_defaults(metrics, time_frame, group)

            request_body = self._build_call_group_request(
                metrics, time_frame, group, tag_filter_expression, order, pagination,
                include_internal, include_synthetic,
            )

            logger.debug("=" * 80)
            logger.debug("📤 REQUEST BODY DEBUG - BEFORE SDK CONVERSION")
            logger.debug("=" * 80)
            logger.debug(f"Request Body Type: {type(request_body)}")
            logger.debug(f"Request Body Keys: {request_body.keys()}")
            logger.debug(f"Full Request Body: {request_body}")
            logger.debug("=" * 80)

            logger.debug(f"Creating GetCallGroups from request_body: {request_body}")
            get_call_groups = GetCallGroups.from_dict(request_body)
            logger.debug("Successfully created GetCallGroups object")

            logger.debug("=" * 80)
            logger.debug("📦 SDK OBJECT DEBUG - AFTER CONVERSION")
            logger.debug("=" * 80)
            if hasattr(get_call_groups, 'to_dict'):
                logger.debug(f"SDK Object as Dict: {get_call_groups.to_dict()}")
            logger.debug("=" * 80)

            logger.debug("Calling get_call_group with GetCallGroups object")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_call_group,
                    get_call_groups=get_call_groups,
                    fill_time_series=fill_time_series
                ),
                ctx=ctx,
                operation_name="get_call_group",
                resource_type=resource_type, tool_name=tool_name,
            )


            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            self._log_call_group_response(result_dict)

            processed_result = self._process_metrics_response(result_dict)
            if group and self._should_aggregate_results(metrics, group):
                processed_result = self._aggregate_grouped_results(processed_result, metrics)

            return processed_result
        except Exception as e:
            logger.error(f"Error in get_grouped_calls_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get grouped calls metrics: {e!s}"}

    @staticmethod
    def _extract_metric_entry(metric_key: str, metric_data: Any) -> tuple:
        """Return (extracted_entry, metric_name, value) for a single metric data array, or (None, None, None)."""
        if not (isinstance(metric_data, list) and metric_data):
            return None, None, None
        first = metric_data[0]
        if not (isinstance(first, list) and len(first) >= 2):
            return None, None, None
        timestamp, value = first[0], first[1]
        entry = {"timestamp": timestamp, "value": value, "raw_data": metric_data}
        return entry, metric_key.split('.')[0], value

    @staticmethod
    def _build_metric_summary(metric_name: str, value: Any, summary: Dict[str, Any]) -> None:
        """Populate the human-readable summary dict in-place for a single metric."""
        if metric_name == 'errors':
            summary['error_rate'] = f"{value * 100:.2f}%"
            summary['error_rate_decimal'] = value
        elif metric_name == 'calls':
            summary['total_calls'] = int(value)
        elif metric_name == 'latency':
            summary['latency_ms'] = f"{value:.2f}ms"
        elif metric_name == 'erroneousCalls':
            summary['erroneous_calls'] = int(value)

    @staticmethod
    def _build_interpretation(metric_summary: Dict[str, Any]) -> str:
        """Compose a pipe-separated interpretation string from the metric summary."""
        parts = []
        if 'error_rate' in metric_summary:
            parts.append(f"Error Rate: {metric_summary['error_rate']}")
        if 'total_calls' in metric_summary:
            parts.append(f"Total Calls: {metric_summary['total_calls']}")
        if 'erroneous_calls' in metric_summary:
            parts.append(f"Erroneous Calls: {metric_summary['erroneous_calls']}")
        if 'latency_ms' in metric_summary:
            parts.append(f"Latency: {metric_summary['latency_ms']}")
        return " | ".join(parts)

    @staticmethod
    def _process_item_metrics(item: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single response item with extracted metrics, summary, and interpretation."""
        processed_item = item.copy()
        raw_metrics = item.get('metrics')
        if not isinstance(raw_metrics, dict):
            return processed_item

        extracted_metrics: Dict[str, Any] = {}
        metric_summary: Dict[str, Any] = {}
        for metric_key, metric_data in raw_metrics.items():
            entry, metric_name, value = ApplicationCallGroupMCPTools._extract_metric_entry(metric_key, metric_data)
            if entry is not None:
                extracted_metrics[metric_key] = entry
                ApplicationCallGroupMCPTools._build_metric_summary(metric_name, value, metric_summary)

        processed_item['metrics_extracted'] = extracted_metrics
        processed_item['metrics_summary'] = metric_summary
        if metric_summary:
            processed_item['interpretation'] = ApplicationCallGroupMCPTools._build_interpretation(metric_summary)
        return processed_item

    def _process_metrics_response(self, result_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the metrics response to extract values from nested arrays.

        The API returns metrics in format:
        "metrics": {
            "errors.mean": [[timestamp, value]],
            "calls.sum": [[timestamp, value]]
        }

        This function extracts the actual values and adds a human-readable summary.

        Args:
            result_dict: Raw API response

        Returns:
            Processed response with extracted metric values
        """
        try:
            if not isinstance(result_dict, dict) or 'items' not in result_dict:
                return result_dict

            processed_items = []
            for item in result_dict.get('items', []):
                if not isinstance(item, dict):
                    processed_items.append(item)
                    continue
                processed_items.append(self._process_item_metrics(item))

            result_dict['items'] = processed_items
            if processed_items:
                result_dict['summary'] = {
                    "total_groups": len(processed_items),
                    "note": "Check 'metrics_summary' and 'interpretation' fields in each item for human-readable values",
                }
            return result_dict

        except Exception as e:
            logger.error(f"Error processing metrics response: {e}", exc_info=True)
            return result_dict

    def _should_aggregate_results(
        self,
        metrics: Optional[List[Dict[str, Any]]],
        group: Optional[Dict[str, str]]
    ) -> bool:
        """
        Determine if results should be aggregated (no grouping in output).

        This is true when:
        - Only MEAN latency is requested (no other metrics)
        - Group is by endpoint.name (which we want to aggregate away)

        Args:
            metrics: List of metrics requested
            group: Grouping configuration

        Returns:
            True if results should be aggregated, False otherwise
        """
        if not metrics or not group:
            return False

        # Check if only latency MEAN is requested
        if len(metrics) == 1:
            metric = metrics[0]
            if (metric.get("metric") == "latency" and
                metric.get("aggregation") == "MEAN"):
                # Check if grouping by endpoint.name
                if group.get("groupbyTag") == "endpoint.name":
                    return True

        return False

    @staticmethod
    def _accumulate_metric_value(
        metric_key: str,
        metric_info: Any,
        aggregated: Dict[str, float],
        counts: Dict[str, int],
    ) -> None:
        """Add a single metric value to the running totals in-place."""
        if isinstance(metric_info, dict):
            value = metric_info.get('value', 0)
        elif isinstance(metric_info, (int, float)):
            value = metric_info
        else:
            return
        aggregated.setdefault(metric_key, 0)
        counts.setdefault(metric_key, 0)
        aggregated[metric_key] += value
        counts[metric_key] += 1

    @staticmethod
    def _compute_overall_metrics(
        aggregated: Dict[str, float],
        counts: Dict[str, int],
    ) -> Dict[str, Any]:
        """Convert running totals into per-key average dicts."""
        overall: Dict[str, Any] = {}
        for metric_key, total in aggregated.items():
            count = counts.get(metric_key, 1)
            if count <= 0:
                continue
            is_latency_mean = 'latency' in metric_key.lower() and 'mean' in metric_key.lower()
            if is_latency_mean:
                overall[metric_key] = {"value": total / count, "unit": "ms", "aggregation": "MEAN",
                                       "note": f"Average across {count} endpoints"}
            else:
                overall[metric_key] = {"value": total / count, "aggregation": "MEAN",
                                       "note": f"Average across {count} groups"}
        return overall

    def _aggregate_grouped_results(
        self,
        result_dict: Dict[str, Any],
        metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate grouped results into a single overall metric.

        This calculates the overall mean latency across all endpoints/services
        by averaging the individual group values.

        Args:
            result_dict: Processed API response with grouped data
            metrics: List of metrics that were requested

        Returns:
            Aggregated result with overall metrics only
        """
        try:
            if not isinstance(result_dict, dict) or 'items' not in result_dict:
                return result_dict

            items = result_dict.get('items', [])
            if not items:
                return {"aggregated": True, "message": "No data available for the specified filters", "overall_metrics": {}}

            aggregated_metrics: Dict[str, float] = {}
            metric_counts: Dict[str, int] = {}
            for item in items:
                if not isinstance(item, dict):
                    continue
                metrics_data = item.get('metrics_extracted', item.get('metrics', {}))
                for metric_key, metric_info in metrics_data.items():
                    self._accumulate_metric_value(metric_key, metric_info, aggregated_metrics, metric_counts)

            overall_metrics = self._compute_overall_metrics(aggregated_metrics, metric_counts)

            aggregated_result: Dict[str, Any] = {
                "aggregated": True,
                "message": "Results aggregated across all groups",
                "total_groups_analyzed": len(items),
                "overall_metrics": overall_metrics,
                "original_group_count": len(items),
            }
            if 'latency.mean' in overall_metrics:
                latency_value = overall_metrics['latency.mean']['value']
                aggregated_result['summary'] = f"Overall mean latency: {latency_value:.2f}ms across {len(items)} endpoints"

            logger.info(f"Aggregated {len(items)} groups into overall metrics")
            return aggregated_result

        except Exception as e:
            logger.error(f"Error aggregating grouped results: {e}", exc_info=True)
            return result_dict

    def _check_elicitation_for_call_group_metrics(
        self,
        metrics: Optional[List[Dict[str, str]]],
        time_frame: Optional[Dict[str, int]],
        group: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Check for required and recommended parameters (Two-Pass Elicitation).

        Args:
            metrics: Metrics list if provided
            time_frame: Time frame if provided
            group: Group configuration if provided

        Returns:
            Elicitation request dict if parameters are missing, None otherwise
        """
        missing_params = []

        # Check for REQUIRED parameters
        if not metrics:
            missing_params.append({
                "name": "metrics",
                "description": "List of metric names with aggregations (REQUIRED)",
                "examples": [
                    {"metric": "calls", "aggregation": "SUM"},
                    {"metric": "latency", "aggregation": "MEAN"},
                    {"metric": "errors", "aggregation": "SUM"},
                    {"metric": "latency", "aggregation": "P75", "granularity": 360}
                ],
                "type": "list"
            })

        # Check for RECOMMENDED parameters
        if not time_frame:
            missing_params.append({
                "name": "time_frame",
                "description": "Time range for metrics (RECOMMENDED)",
                "examples": [
                    {"windowSize": 3600000},  # Last hour
                    {"windowSize": 86400000},  # Last 24 hours
                    {"to": 1688366990000, "windowSize": 600000}  # Specific time
                ],
                "type": "dict",
                "note": "If not provided, defaults to last hour"
            })

        if not group:
            missing_params.append({
                "name": "group",
                "description": "Grouping configuration (RECOMMENDED)",
                "examples": [
                    {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"},
                    {"groupbyTag": "endpoint.name", "groupbyTagEntity": "DESTINATION"},
                    {"groupbyTag": "call.type", "groupbyTagEntity": "NOT_APPLICABLE"}
                ],
                "type": "dict",
                "note": "If not provided, defaults to grouping by service.name"
            })

        # If any required or recommended parameters are missing, return elicitation request
        if missing_params:
            return self._create_elicitation_request(missing_params)

        return None

    def _create_elicitation_request(self, missing_params: list) -> Dict[str, Any]:
        """
        Create an elicitation request following MCP pattern.

        Args:
            missing_params: List of missing parameter descriptions

        Returns:
            Elicitation request dict
        """
        # Build simple, user-friendly parameter descriptions
        param_lines = []
        for param in missing_params:
            # Format examples in a simple, readable way
            if param['name'] == 'metrics':
                examples = "calls, latency, errors, erroneousCalls"
            elif param['name'] == 'time_frame':
                examples = "last hour, last 24 hours, last 10 minutes"
            elif param['name'] == 'group':
                examples = "service.name, endpoint.name, call.type"
            else:
                examples = ", ".join([str(ex) for ex in param["examples"][:3]])

            param_lines.append(f"{param['name']}: {examples}")

        message = (
            "I need:\n\n"
            + "\n".join(param_lines)
        )

        return {
            "elicitation_needed": True,
            "message": message,
            "missing_parameters": [p["name"] for p in missing_params],
            "parameter_details": missing_params,
            "instructions": "Call get_grouped_calls_metrics again with these parameters filled in."
        }

