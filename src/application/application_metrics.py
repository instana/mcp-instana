"""
Application Metrics MCP Tools Module

This module provides application metrics-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

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

    @register_as_tool(
        title="Get Application Data Metrics V2",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationMetricsApi)
    async def get_application_data_metrics_v2(self,
                                              metrics: Optional[List[Dict[str, Any]]] = None,
                                              time_frame: Optional[Dict[str, int]] = None,
                                              application_id: Optional[str] = None,
                                              service_id: Optional[str] = None,
                                              endpoint_id: Optional[str] = None,
                                              ctx=None, api_client=None) -> Dict[str, Any]:
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

            logger.debug(f"Result from get_application_data_metrics_v2: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_application_data_metrics_v2: {e}", exc_info=True)
            return {"error": f"Failed to get application data metrics: {e!s}"}

    @register_as_tool(
        title="Get Application Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationMetricsApi)
    async def get_application_metrics(self,
                                      application_ids: Optional[List[str]] = None,
                                      metrics: Optional[List[Dict[str, str]]] = None,
                                      time_frame: Optional[Dict[str, int]] = None,
                                      fill_time_series: Optional[bool] = True,
                                      ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get metrics for specific applications.

        This API endpoint retrieves one or more supported aggregations of metrics for an Application Perspective.

        Args:
            application_ids: List of application IDs to get metrics for
            metrics: List of metrics to retrieve with their aggregations
                Example: [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
                Example: {"from": 1617994800000, "to": 1618081200000}
            fill_time_series: Whether to fill missing data points with timestamp and value 0
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing application metrics data or error information
        """
        try:
            logger.debug(f"get_application_metrics called with application_ids={application_ids}")

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

            # Add application IDs if provided
            if application_ids:
                request_body["applicationIds"] = application_ids

            # Create the GetApplications object
            get_applications = GetApplications(**request_body)

            # Call the get_application_metrics method from the SDK
            result = api_client.get_application_metrics(
                fill_time_series=fill_time_series,
                get_applications=get_applications
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_application_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_application_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get application metrics: {e!s}"}

    @register_as_tool(
        title="Get Endpoints Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationMetricsApi)
    async def get_endpoints_metrics(self,
                                    endpoint_ids: Optional[List[str]] = None,
                                    metrics: Optional[List[Dict[str, str]]] = None,
                                    time_frame: Optional[Dict[str, int]] = None,
                                    fill_time_series: Optional[bool] = True,
                                    ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get metrics for specific endpoints.

        This API endpoint retrieves one or more supported aggregations of metrics for an Endpoint.

        Args:
            endpoint_ids: List of endpoint IDs to get metrics for
            metrics: List of metrics to retrieve with their aggregations
                Example: [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
                Example: {"from": 1617994800000, "to": 1618081200000}
            fill_time_series: Whether to fill missing data points with timestamp and value 0
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoint metrics data or error information
        """
        try:
            logger.debug(f"get_endpoints_metrics called with endpoint_ids={endpoint_ids}")

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

            # Add endpoint IDs if provided
            if endpoint_ids:
                request_body["endpointIds"] = endpoint_ids

            # Create the GetEndpoints object
            get_endpoints = GetEndpoints(**request_body)

            # Call the get_endpoints_metrics method from the SDK
            result = api_client.get_endpoints_metrics(
                fill_time_series=fill_time_series,
                get_endpoints=get_endpoints
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_endpoints_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_endpoints_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get endpoints metrics: {e!s}"}

    @register_as_tool(
        title="Get Services Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationMetricsApi)
    async def get_services_metrics(self,
                                   service_ids: Optional[List[str]] = None,
                                   metrics: Optional[List[Dict[str, str]]] = None,
                                   time_frame: Optional[Dict[str, int]] = None,
                                   fill_time_series: Optional[bool] = True,
                                   include_snapshot_ids: Optional[bool] = False,
                                   ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get metrics for specific services.

        This API endpoint retrieves one or more supported aggregations of metrics for a Service.

        Args:
            service_ids: List of service IDs to get metrics for
            metrics: List of metrics to retrieve with their aggregations
                Example: [{"metric": "latency", "aggregation": "MEAN"}]
            time_frame: Dictionary with 'from' and 'to' timestamps in milliseconds
                Example: {"from": 1617994800000, "to": 1618081200000}
            fill_time_series: Whether to fill missing data points with timestamp and value 0
            include_snapshot_ids: Whether to include snapshot IDs in the results
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing service metrics data or error information
        """
        try:
            logger.debug(f"get_services_metrics called with service_ids={service_ids}")

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

            # Add service IDs if provided
            if service_ids:
                request_body["serviceIds"] = service_ids

            # Create the GetServices object
            get_services = GetServices(**request_body)

            # Call the get_services_metrics method from the SDK
            result = api_client.get_services_metrics(
                fill_time_series=fill_time_series,
                include_snapshot_ids=include_snapshot_ids,
                get_services=get_services
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_services_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_services_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get services metrics: {e!s}"}
