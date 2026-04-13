"""
Application Metrics MCP Tools Module

This module provides application metrics-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.application_metrics_api import (
        ApplicationMetricsApi,
    )
    from instana_client.models.get_application_metrics import (
        GetApplicationMetrics,
    )
    from instana_client.models.get_applications import GetApplications
    from instana_client.models.get_endpoints import GetEndpoints
    from instana_client.models.get_services import GetServices
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationMetricsMCPTools(BaseInstanaClient):
    """Tools for application metrics in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Metrics MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    # @register_as_tool decorator commented out - not exposed as MCP tool
    # @register_as_tool(
    #     title="Get Application Data Metrics V2",
    #     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    # )
    @with_header_auth(ApplicationMetricsApi)
    async def get_application_data_metrics_v2(self,
                                              metrics: Optional[List[Dict[str, Any]]] = None,
                                              time_frame: Optional[Dict[str, int]] = None,
                                              application_id: Optional[str] = None,
                                              service_id: Optional[str] = None,
                                              endpoint_id: Optional[str] = None,
                                              ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get application data metrics using the v2 API.

        This API endpoint retrieves one or more supported aggregations of metrics for a combination of entities.
        For example, retrieve MEAN aggregation of latency metric for an Endpoint, Service, and Application.

        Args:
            metrics: List of metrics to retrieve with their aggregations
                Example: [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
                Example: {"from": 1617994800000, "to": 1618081200000}
            application_id: ID of the application to get metrics for (optional)
            service_id: ID of the service to get metrics for (optional)
            endpoint_id: ID of the endpoint to get metrics for (optional)
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing metrics data or error information
        """
        try:
            logger.debug(f"get_application_data_metrics_v2 called with application_id={application_id}, service_id={service_id}, endpoint_id={endpoint_id}")

            # Two-Pass Elicitation: Check for required and recommended parameters
            elicitation_request = self._check_elicitation_for_app_metrics(
                metrics, time_frame, application_id, service_id, endpoint_id
            )
            if elicitation_request:
                logger.info("Elicitation needed for application metrics")
                return elicitation_request

            # Set default time range if not provided
            if not time_frame:
                to_time = int(datetime.now().timestamp() * 1000)
                from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
                time_frame = {
                    "from": from_time,
                    "to": to_time
                }

            # Set default metrics if not provided
            if not metrics:
                metrics = [
                    {
                        "metric": "latency",
                        "aggregation": "MEAN"
                    }
                ]

            # Create the request body
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame
            }

            # Add entity IDs if provided
            if application_id:
                request_body["applicationId"] = application_id
            if service_id:
                request_body["serviceId"] = service_id
            if endpoint_id:
                request_body["endpointId"] = endpoint_id

            # Create the GetApplicationMetrics object
            get_app_metrics = GetApplicationMetrics(**request_body)

            # Call the get_application_data_metrics_v2 method from the SDK
            result = api_client.get_application_data_metrics_v2(
                get_application_metrics=get_app_metrics
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            # 🔍 DEBUG: Log the API response structure and data
            logger.info("=" * 80)
            logger.info("📥 INSTANA API RESPONSE DEBUG")
            logger.info("=" * 80)
            logger.info(f"Response Type: {type(result_dict)}")
            logger.info(f"Response Keys: {result_dict.keys() if isinstance(result_dict, dict) else 'N/A'}")

            # Log detailed structure for each metric
            if isinstance(result_dict, dict) and 'items' in result_dict:
                logger.info(f"Number of items: {len(result_dict['items'])}")
                for idx, item in enumerate(result_dict['items'][:3]):  # Log first 3 items
                    logger.info(f"\nItem {idx}:")
                    logger.info(f"  Keys: {item.keys() if isinstance(item, dict) else 'N/A'}")
                    if isinstance(item, dict):
                        if 'metrics' in item:
                            logger.info(f"  Metrics: {item['metrics'].keys() if isinstance(item['metrics'], dict) else item['metrics']}")
                            # Log actual metric values
                            for metric_name, metric_data in (item['metrics'].items() if isinstance(item['metrics'], dict) else []):
                                logger.info(f"    {metric_name}:")
                                if isinstance(metric_data, dict):
                                    logger.info(f"      Keys: {metric_data.keys()}")
                                    if 'values' in metric_data:
                                        values = metric_data['values']
                                        logger.info(f"      Number of data points: {len(values) if isinstance(values, list) else 'N/A'}")
                                        if isinstance(values, list) and len(values) > 0:
                                            logger.info(f"      First value: {values[0]}")
                                            logger.info(f"      Last value: {values[-1]}")
                                            # Calculate sum if it's a list of numbers
                                            try:
                                                numeric_values = [v[1] if isinstance(v, list) and len(v) > 1 else v for v in values]
                                                total = sum(numeric_values)
                                                logger.info(f"      ⚠️  SUM of all data points: {total}")
                                            except (TypeError, ValueError):
                                                pass
                                    if 'aggregation' in metric_data:
                                        logger.info(f"      Aggregation: {metric_data['aggregation']}")
                                else:
                                    logger.info(f"      Value: {metric_data}")

            logger.info("=" * 80)
            logger.debug(f"Full Result: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_application_data_metrics_v2: {e}", exc_info=True)
            return {"error": f"Failed to get application data metrics: {e!s}"}

    # @register_as_tool(
    #     title="Get Application Metrics",
    #     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    # )
    # @with_header_auth(ApplicationMetricsApi)
    # async def get_application_metrics(self,
    #                                   application_id: Optional[str] = None,
    #                                   metrics: Optional[List[Dict[str, str]]] = None,
    #                                   time_frame: Optional[Dict[str, int]] = None,
    #                                   fill_time_series: Optional[bool] = True,
    #                                   ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
    #     """
    #     Get metrics for a specific application.

    #     This API endpoint retrieves one or more supported aggregations of metrics for an Application Perspective.

    #     Args:
    #         application_id: Application ID to get metrics for (single application)
    #         metrics: List of metrics to retrieve with their aggregations
    #             Example: [{"metric": "latency", "aggregation": "MEAN"}]
    #         time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
    #             Example: {"from": 1617994800000, "to": 1618081200000}
    #         fill_time_series: Whether to fill missing data points with timestamp and value 0
    #         ctx: The MCP context (optional)

    #     Returns:
    #         Dictionary containing application metrics data or error information
    #     """
    #     try:
    #         logger.debug(f"get_application_metrics called with application_id={application_id}")

    #         # Set default time range if not provided
    #         if not time_frame:
    #             to_time = int(datetime.now().timestamp() * 1000)
    #             from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
    #             time_frame = {
    #                 "from": from_time,
    #                 "to": to_time
    #             }

    #         # Set default metrics if not provided
    #         if not metrics:
    #             metrics = [
    #                 {
    #                     "metric": "latency",
    #                     "aggregation": "MEAN"
    #                 }
    #             ]

    #         # Create the request body
    #         request_body = {
    #             "metrics": metrics,
    #             "timeFrame": time_frame
    #         }

    #         # Add application ID if provided
    #         if application_id:
    #             request_body["applicationId"] = application_id

    #         # Create the GetApplications object
    #         get_applications = GetApplications(**request_body)

    #         # Call the get_application_metrics method from the SDK
    #         result = api_client.get_application_metrics(
    #             fill_time_series=fill_time_series,
    #             get_applications=get_applications
    #         )

    #         # Convert the result to a dictionary
    #         if hasattr(result, 'to_dict'):
    #             result_dict = result.to_dict()
    #         else:
    #             # If it's already a dict or another format, use it as is
    #             result_dict = result

    #         logger.debug(f"Result from get_application_metrics: {result_dict}")
    #         return result_dict
    #     except Exception as e:
    #         logger.error(f"Error in get_application_metrics: {e}", exc_info=True)
    #         return {"error": f"Failed to get application metrics: {e!s}"}

    # @register_as_tool(
    #     title="Get Endpoints Metrics",
    #     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    # )
    # @with_header_auth(ApplicationMetricsApi)
    # async def get_endpoints_metrics(self,
    #                                 endpoint_id: Optional[str] = None,
    #                                 metrics: Optional[List[Dict[str, str]]] = None,
    #                                 time_frame: Optional[Dict[str, int]] = None,
    #                                 fill_time_series: Optional[bool] = True,
    #                                 ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
    #     """
    #     Get metrics for a specific endpoint.

    #     This API endpoint retrieves one or more supported aggregations of metrics for an Endpoint.

    #     Args:
    #         endpoint_id: Endpoint ID to get metrics for (single endpoint)
    #         metrics: List of metrics to retrieve with their aggregations
    #             Example: [{"metric": "latency", "aggregation": "MEAN"}]
    #         time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
    #             Example: {"from": 1617994800000, "to": 1618081200000}
    #         fill_time_series: Whether to fill missing data points with timestamp and value 0
    #         ctx: The MCP context (optional)

    #     Returns:
    #         Dictionary containing endpoint metrics data or error information
    #     """
    #     try:
    #         logger.debug(f"get_endpoints_metrics called with endpoint_id={endpoint_id}")

    #         # Set default time range if not provided
    #         if not time_frame:
    #             to_time = int(datetime.now().timestamp() * 1000)
    #             from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
    #             time_frame = {
    #                 "from": from_time,
    #                 "to": to_time
    #             }

    #         # Set default metrics if not provided
    #         if not metrics:
    #             metrics = [
    #                 {
    #                     "metric": "latency",
    #                     "aggregation": "MEAN"
    #                 }
    #             ]

    #         # Create the request body
    #         request_body = {
    #             "metrics": metrics,
    #             "timeFrame": time_frame
    #         }

    #         # Add endpoint ID if provided
    #         if endpoint_id:
    #             request_body["endpointId"] = endpoint_id

    #         # Create the GetEndpoints object
    #         get_endpoints = GetEndpoints(**request_body)

    #         # Call the get_endpoints_metrics method from the SDK
    #         result = api_client.get_endpoints_metrics(
    #             fill_time_series=fill_time_series,
    #             get_endpoints=get_endpoints
    #         )

    #         # Convert the result to a dictionary
    #         if hasattr(result, 'to_dict'):
    #             result_dict = result.to_dict()
    #         else:
    #             # If it's already a dict or another format, use it as is
    #             result_dict = result

    #         logger.debug(f"Result from get_endpoints_metrics: {result_dict}")
    #         return result_dict
    #     except Exception as e:
    #         logger.error(f"Error in get_endpoints_metrics: {e}", exc_info=True)
    #         return {"error": f"Failed to get endpoints metrics: {e!s}"}

    # @register_as_tool(
    #     title="Get Services Metrics",
    #     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    # )
    # @with_header_auth(ApplicationMetricsApi)
    # async def get_services_metrics(self,
    #                                service_id: Optional[str] = None,
    #                                metrics: Optional[List[Dict[str, str]]] = None,
    #                                time_frame: Optional[Dict[str, int]] = None,
    #                                fill_time_series: Optional[bool] = True,
    #                                include_snapshot_ids: Optional[bool] = False,
    #                                ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
    #     """
    #     Get metrics for a specific service.

    #     This API endpoint retrieves one or more supported aggregations of metrics for a Service.

    #     Args:
    #         service_id: Service ID to get metrics for (single service)
    #         metrics: List of metrics to retrieve with their aggregations
    #             Example: [{"metric": "latency", "aggregation": "MEAN"}]
    #         time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
    #             Example: {"from": 1617994800000, "to": 1618081200000}
    #         fill_time_series: Whether to fill missing data points with timestamp and value 0
    #         include_snapshot_ids: Whether to include snapshot IDs in the results
    #         ctx: The MCP context (optional)

    #     Returns:
    #         Dictionary containing service metrics data or error information
    #     """
    #     try:
    #         logger.debug(f"get_services_metrics called with service_id={service_id}")

    #         # Set default time range if not provided
    #         if not time_frame:
    #             to_time = int(datetime.now().timestamp() * 1000)
    #             from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
    #             time_frame = {
    #                 "from": from_time,
    #                 "to": to_time
    #             }

    #         # Set default metrics if not provided
    #         if not metrics:
    #             metrics = [
    #                 {
    #                     "metric": "latency",
    #                     "aggregation": "MEAN"
    #                 }
    #             ]

    #         # Create the request body
    #         request_body = {
    #             "metrics": metrics,
    #             "timeFrame": time_frame
    #         }

    #         # Add service ID if provided
    #         if service_id:
    #             request_body["serviceId"] = service_id

    #         # Create the GetServices object
    #         get_services = GetServices(**request_body)

    #         # Call the get_services_metrics method from the SDK
    #         result = api_client.get_services_metrics(
    #             fill_time_series=fill_time_series,
    #             include_snapshot_ids=include_snapshot_ids,
    #             get_services=get_services
    #         )

    #         # Convert the result to a dictionary
    #         if hasattr(result, 'to_dict'):
    #             result_dict = result.to_dict()
    #         else:
    #             # If it's already a dict or another format, use it as is
    #             result_dict = result

    #         logger.debug(f"Result from get_services_metrics: {result_dict}")
    #         return result_dict
    #     except Exception as e:
    #         logger.error(f"Error in get_services_metrics: {e}", exc_info=True)

    def _check_elicitation_for_app_metrics(
        self,
        metrics: Optional[List[Dict[str, str]]],
        time_frame: Optional[Dict[str, int]],
        application_id: Optional[str],
        service_id: Optional[str],
        endpoint_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Check for required and recommended parameters (Two-Pass Elicitation).

        Args:
            metrics: Metrics list if provided
            time_frame: Time frame if provided
            application_id: Application ID if provided
            service_id: Service ID if provided
            endpoint_id: Endpoint ID if provided

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
                    {"metric": "errors", "aggregation": "SUM"}
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
                    {"windowSize": 86400000}  # Last 24 hours
                ],
                "type": "dict",
                "note": "If not provided, defaults to last hour"
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
                examples = "latency, calls, errors, erroneousCalls"
            elif param['name'] == 'time_frame':
                examples = "last hour, last 24 hours, last 10 minutes"
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
            "instructions": "Call query_instana_metrics again with these parameters filled in."
        }
    #         return {"error": f"Failed to get services metrics: {e!s}"}
