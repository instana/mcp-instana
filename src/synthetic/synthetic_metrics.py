"""
Synthetic Metrics MCP Tools Module

This module provides synthetic metrics-specific MCP tools for Instana monitoring.
"""

import json
import logging
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api.synthetic_metrics_api import SyntheticMetricsApi
    from instana_client.models.get_metrics_result import GetMetricsResult
except ImportError as e:
    logger.error("Error importing Instana SDK: %s", e, exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    parse_payload,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.core.validation import StructureValidator


class SyntheticMetricsMCPTools(BaseInstanaClient):
    """Tools for synthetic metrics in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Synthetic Metrics MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)


    @with_header_auth(SyntheticMetricsApi)
    async def get_metrics_result(self,
                                payload: Optional[Union[Dict[str, Any], str]] = None,
                                ctx=None, api_client=None,
                                resource_type: Optional[str] = None,
                                tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get synthetic beacon metrics.

        This API endpoint retrieves one or more supported aggregations of metrics for synthetic monitoring beacons.
        For example, retrieve MEAN aggregation of page load time metric for specific synthetics.

        Args:
            payload: Complete request payload as a dictionary or JSON string
                {
                    "pagination": {
                        "page": 1,
                        "pageSize": 3
                    },
                    "metrics": [
                        {
                        "metric": "synthetic.metricsResponseTime",
                        "aggregation": "SUM"
                        }
                    ],
                    "timeFrame": {
                        "to": 0,
                        "windowSize": 3600000
                    },
                    "groups": [
                        {
                        "groupbyTag": "synthetic.applicationId"
                        },
                        {
                        "groupbyTag": "synthetic.tags",
                        "groupbyTagSecondLevelTag": "region"
                        }
                    ]
                }
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing synthetic metrics data or error information
        """
        try:
            logger.debug("[get_metrics_result] called")

            request_body = parse_payload(payload)
            if "error" in request_body:
                logger.warning("[get_metrics_result] Payload parse error: %s", request_body.get("error"))
                return request_body
            if not request_body:
                return {"error": "payload must not be an empty object"}

            validation = StructureValidator.validate_synthetic_playback_structure(
                "get_metrics_result", request_body,
                requires_metrics=True,
                check_granularity_ratio=True,
            )
            if validation:
                logger.warning("[get_metrics_result] Validation failed: %s", validation)
                return validation

            try:
                config_object = GetMetricsResult.from_dict(request_body)
                logger.debug("[get_metrics_result] Successfully created GetMetricsResult object")
            except Exception as e:
                logger.debug("[get_metrics_result] Error creating GetMetricsResult: %s", e)
                return {"error": f"Failed to build GetMetricsResult: {e!s}"}

            logger.debug("[get_metrics_result] Calling get_metrics_result with config object")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_metrics_result_without_preload_content,
                    get_metrics_result=config_object,
                ),
                ctx=ctx,
                operation_name="get_metrics_result",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                return self.handle_api_error_response(response, "get synthetic metrics", logger)

            logger.debug("[get_metrics_result] Returning result")
            return json.loads(decode_response(response))
        except Exception as e:
            logger.error("[get_metrics_result] Error: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic metrics: {e!s}"}
