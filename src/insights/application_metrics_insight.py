"""
Application Insights MCP Tools Module

Intelligently handles different query types for applications, services, and endpoints.

Uses:
- ApplicationMetricsApi for application queries (both with and without metrics)
- ApplicationResourcesApi for looking up entity IDs by name

Supports queries with or without metrics:
- List all applications (with/without metrics)
- List all services (with/without metrics)
- List services in an application (with/without metrics)
- List endpoints in an application (with/without metrics)
- List endpoints in a service (with/without metrics)
- List endpoints in a service within an application (with/without metrics)
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.types import ToolAnnotations

from src.prompts import mcp
from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
from src.insights.helpers import LookupHelpers, MetricsFilterHelpers

# Import SDK classes
try:
    from instana_client.api.application_metrics_api import ApplicationMetricsApi
    from instana_client.models.get_applications import GetApplications
    from instana_client.models.get_services import GetServices
    from instana_client.models.get_endpoints import GetEndpoints
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)


class ApplicationMetricsInsightMCPTools(BaseInstanaClient):
    """Unified tool for application insights in Instana MCP using SDK methods."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Metrics Insight MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)
        self.lookup_helpers = LookupHelpers(read_token=read_token, base_url=base_url)
        self.metrics_filter_helpers = MetricsFilterHelpers(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Application Insights",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationMetricsApi)
    async def application_insights(
        self,
        application_name: Optional[str] = None,
        service_name: Optional[str] = None,
        plugin_type: Optional[str] = None,
        metrics: Optional[List[Dict[str, str]]] = None,
        time_frame: Optional[Dict[str, int]] = None,
        ctx=None,
        api_client=None,
    ) -> Dict[str, Any]:
        """
        Retrieve applications, services, endpoints and their metrics from Instana.
        
        Use this tool to list or analyze application perspectives, services, and endpoints.
        Supports filtering by application and service names, with optional performance metrics.
        
        Common queries:
        - List all applications
        - Get services in an application
        - View endpoints for a service
        - Fetch application/service metrics (calls, latency, errors)
        - Get COMBINED app + infra metrics for a service (service_name + plugin_type)
        
        SPECIAL BEHAVIOR: When both service_name AND plugin_type are provided:
        - Returns BOTH application metrics (calls, latency) AND infrastructure metrics (CPU, memory)
        - Flow: service_name → service_id → app_metrics + snapshot_ids → infra_metrics
        - Example: service_name="frontend", plugin_type="host" returns complete service metrics
        
        Args:
            application_name: Filter by application name (optional)
            service_name: Filter by service name; use "*" for all (optional)
            plugin_type: Infrastructure plugin type (e.g., "host", "process", "jvm", "docker")
                        When used WITH service_name, returns combined app + infra metrics (optional)
            metrics: Include metrics like [{"metric": "calls", "aggregation": "SUM"}] (optional)
            time_frame: Time range in milliseconds (optional, defaults to last hour)
        
        Returns:
            Applications, services, or endpoints with optional metrics and summary
            When service_name + plugin_type: Returns combined application_metrics + infrastructure_metrics
        """
        try:
            logger.debug(f"application_insights called with application_name={application_name}, service_name={service_name}, plugin_type={plugin_type}, metrics={metrics}")

            # Set default time range if not provided
            if not time_frame:
                to_time = int(datetime.now().timestamp() * 1000)
                from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
                time_frame = {"from": from_time, "to": to_time}

            # Set default metrics for API calls (we'll filter out if user doesn't want metrics)
            api_metrics = metrics if metrics else [{"metric": "calls", "aggregation": "SUM"}]
            
            # Ensure api_client is not None
            if api_client is None:
                return {"error": "API client not initialized"}
            
            # New Case: Get combined metrics for service with plugin type
            if not application_name and service_name and plugin_type:
                logger.debug(f"Getting combined metrics for service_name='{service_name}' with plugin_type='{plugin_type}'")
                
                # Default infra metrics if not specified
                infra_metrics = ["cpu.used", "memory.used"]
                
                # Use the combined metrics helper
                return await self.metrics_filter_helpers.get_combined_service_metrics(
                    service_name=service_name,
                    plugin_type=plugin_type,
                    app_metrics=api_metrics,
                    infra_metrics=infra_metrics,
                    time_frame=time_frame,
                    rollup=60
                )
            
            # Case 1 & 2: List all applications (with or without metrics)
            if not application_name and not service_name:
                return await self._list_applications(api_client, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 2.5: List all services (service_name="*" without application_name)
            elif not application_name and service_name == "*":
                return await self._list_services(api_client, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 3 & 4: List services in an application (with or without metrics)
            elif application_name and not service_name:
                # Lookup application ID using helper class
                app_id = await self.lookup_helpers.lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                return await self._list_services_in_application(api_client, app_id, application_name, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 5: List endpoints of application (service_name="*")
            elif application_name and service_name == "*":
                # Lookup application ID
                app_id = await self.lookup_helpers.lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                return await self._list_endpoints_in_application(api_client, app_id, application_name, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 6: List endpoints of service (no application_name)
            elif not application_name and service_name and service_name != "*":
                # Lookup service ID
                service_id = await self.lookup_helpers.lookup_service_id(service_name, time_frame)
                if isinstance(service_id, dict) and "error" in service_id:
                    return service_id
                
                if not isinstance(service_id, str):
                    return {"error": "Invalid service ID returned"}
                
                return await self._list_endpoints_in_service(api_client, service_id, service_name, None, None, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 7: List endpoints of service in application
            elif application_name and service_name and service_name != "*":
                # Lookup both application and service IDs
                app_id = await self.lookup_helpers.lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                service_id = await self.lookup_helpers.lookup_service_id(service_name, time_frame)
                if isinstance(service_id, dict) and "error" in service_id:
                    return service_id
                
                if not isinstance(service_id, str):
                    return {"error": "Invalid service ID returned"}
                
                return await self._list_endpoints_in_service(api_client, service_id, service_name, app_id, application_name, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            else:
                return {"error": "Invalid parameter combination. Please check the usage examples."}

        except Exception as e:
            logger.error(f"Error in application_insights: {e}", exc_info=True)
            return {"error": f"Failed to get application insights: {e!s}"}

    async def _list_applications(
        self,
        api_client: ApplicationMetricsApi,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        **kwargs  # Accept any additional parameters for metrics queries
    ) -> Dict[str, Any]:
        """
        List all applications using ApplicationMetricsApi.
        
        Args:
            api_client: The ApplicationMetricsApi client
            metrics: List of metrics to fetch
            time_frame: Time range dictionary
            include_metrics: If False, strip metrics from response and return only names
            **kwargs: Additional optional parameters when include_metrics=True:
                - applicationBoundaryScope: "ALL" or "INBOUND"
                - nameFilter: Filter by name with contains semantic
                - technologies: List of technologies to filter by
                - order: Ordering specification
                - pagination: Pagination specification
        """
        try:
            # Create request body
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame
            }
            
            # Add optional parameters only when fetching metrics
            if include_metrics and kwargs:
                # Add supported optional parameters if provided
                for key in ['applicationBoundaryScope', 'nameFilter', 'technologies', 'order', 'pagination']:
                    if key in kwargs and kwargs[key] is not None:
                        request_body[key] = kwargs[key]
            
            # Create GetApplications model
            get_applications = GetApplications(**request_body)
            
            # Call SDK method
            result = api_client.get_application_metrics(
                fill_time_series=True,
                get_applications=get_applications
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            if include_metrics:
                return {
                    "query_type": "list_applications_with_metrics",
                    "applications_with_metrics": items,
                    "summary": {
                        "total_applications": len(items),
                        "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics],
                        "time_range": time_frame
                    }
                }
            else:
                # Strip metrics, return only names
                applications = [
                    {"id": app.get("application", {}).get("id"), "name": app.get("application", {}).get("label")}
                    for app in items if app.get("application", {}).get("label")
                ]
                applications.sort(key=lambda x: x["name"])
                
                return {
                    "query_type": "list_applications",
                    "applications": applications,
                    "summary": {
                        "total_applications": len(applications),
                        "time_range": time_frame,
                        "note": "Application names only (no metrics)"
                    }
                }
            
        except Exception as e:
            logger.error(f"Error listing applications: {e}", exc_info=True)
            return {"error": f"Failed to list applications: {e!s}"}
    
    async def _list_services(
        self,
        api_client: ApplicationMetricsApi,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        **kwargs  # Accept any additional parameters for metrics queries
    ) -> Dict[str, Any]:
        """
        List all services in instana using applicationMetricsApi.
        
        Args:
            **kwargs: Additional optional parameters when include_metrics=True:
                - applicationBoundaryScope: "ALL" or "INBOUND"
                - serviceId: Filter by specific service ID
                - nameFilter: Filter by name with contains semantic
                - technologies: List of technologies to filter by
                - order: Ordering specification
                - pagination: Pagination specification
        """
        try:
            # Convert time_frame to proper format for GetServices
            # GetServices expects windowSize and to, not from and to
            if "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            elif "windowSize" in time_frame and "to" in time_frame:
                formatted_time_frame = time_frame
            else:
                # Default to 1 hour if not properly specified
                from datetime import datetime
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            
            # Create request body with applicationId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": formatted_time_frame,
            }
            
            # Add optional parameters only when fetching metrics
            if include_metrics and kwargs:
                # Add supported optional parameters if provided
                for key in ['applicationBoundaryScope', 'serviceId', 'nameFilter', 'technologies', 'order', 'pagination']:
                    if key in kwargs and kwargs[key] is not None:
                        request_body[key] = kwargs[key]
            
            # Create GetServices model
            get_services = GetServices(**request_body)
            
            # Call SDK method
            result = api_client.get_services_metrics(
                fill_time_series=True,
                include_snapshot_ids=False,
                get_services=get_services
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            if include_metrics:
                return {
                    "query_type": "list_services_in_application_with_metrics",
                    "services_with_metrics": items,
                    "summary": {
                        "total_services": len(items),
                        "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics],
                        "time_frame": time_frame
                    }
                }
            else:
                # Strip metrics, return only names
                services = [
                    {"id": svc.get("service", {}).get("id"), "name": svc.get("service", {}).get("label")}
                    for svc in items if svc.get("service", {}).get("label")
                ]
                services.sort(key=lambda x: x["name"])
                
                return {
                    "query_type": "list_services_in_application",
                    "services": services,
                    "summary": {
                        "total_services": len(services),
                        "time_frame": time_frame,
                        "note": "Service names only (no metrics)"
                    }
                }
            
        except Exception as e:
            logger.error(f"Error listing services: {e}", exc_info=True)
            return {"error": f"Failed to list services: {e!s}"}


    async def _list_services_in_application(
        self,
        api_client: ApplicationMetricsApi,
        application_id: str,
        application_name: str,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        **kwargs  # Accept any additional parameters for metrics queries
    ) -> Dict[str, Any]:
        """
        List services in an application using ApplicationMetricsApi.
        
        Args:
            **kwargs: Additional optional parameters when include_metrics=True:
                - applicationBoundaryScope: "ALL" or "INBOUND"
                - serviceId: Filter by specific service ID
                - nameFilter: Filter by name with contains semantic
                - technologies: List of technologies to filter by
                - order: Ordering specification
                - pagination: Pagination specification
        """
        try:
            # Convert time_frame to proper format for GetServices
            # GetServices expects windowSize and to, not from and to
            if "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            elif "windowSize" in time_frame and "to" in time_frame:
                formatted_time_frame = time_frame
            else:
                # Default to 1 hour if not properly specified
                from datetime import datetime
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            
            # Create request body with applicationId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": formatted_time_frame,
                "applicationId": application_id
            }
            
            # Add optional parameters only when fetching metrics
            if include_metrics and kwargs:
                # Add supported optional parameters if provided
                for key in ['applicationBoundaryScope', 'serviceId', 'nameFilter', 'technologies', 'order', 'pagination']:
                    if key in kwargs and kwargs[key] is not None:
                        request_body[key] = kwargs[key]
            
            # Create GetServices model
            get_services = GetServices(**request_body)
            
            # Call SDK method
            result = api_client.get_services_metrics(
                fill_time_series=True,
                include_snapshot_ids=False,
                get_services=get_services
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            if include_metrics:
                return {
                    "query_type": "list_services_in_application_with_metrics",
                    "application": {"id": application_id, "name": application_name},
                    "services_with_metrics": items,
                    "summary": {
                        "total_services": len(items),
                        "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics],
                        "time_frame": time_frame
                    }
                }
            else:
                # Strip metrics, return only names
                services = [
                    {"id": svc.get("service", {}).get("id"), "name": svc.get("service", {}).get("label")}
                    for svc in items if svc.get("service", {}).get("label")
                ]
                services.sort(key=lambda x: x["name"])
                
                return {
                    "query_type": "list_services_in_application",
                    "application": {"id": application_id, "name": application_name},
                    "services": services,
                    "summary": {
                        "total_services": len(services),
                        "time_frame": time_frame,
                        "note": "Service names only (no metrics)"
                    }
                }
            
        except Exception as e:
            logger.error(f"Error listing services: {e}", exc_info=True)
            return {"error": f"Failed to list services: {e!s}"}

    async def _list_endpoints_in_application(
        self,
        api_client: ApplicationMetricsApi,
        application_id: str,
        application_name: str,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        **kwargs  # Accept any additional parameters for metrics queries
    ) -> Dict[str, Any]:
        """
        List endpoints in an application using ApplicationMetricsApi.
        
        Args:
            **kwargs: Additional optional parameters when include_metrics=True:
                - applicationBoundaryScope: "ALL" or "INBOUND"
                - serviceId: Filter by specific service ID
                - endpointId: Filter by specific endpoint ID
                - endpointTypes: List of endpoint types to filter by
                - nameFilter: Filter by name with contains semantic
                - technologies: List of technologies to filter by
                - order: Ordering specification
                - pagination: Pagination specification
        """
        try:
            # Create request body with applicationId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame,
                "applicationId": application_id
            }
            
            # Add optional parameters only when fetching metrics
            if include_metrics and kwargs:
                # Add supported optional parameters if provided
                for key in ['applicationBoundaryScope', 'serviceId', 'endpointId', 'endpointTypes', 'nameFilter', 'technologies', 'order', 'pagination']:
                    if key in kwargs and kwargs[key] is not None:
                        request_body[key] = kwargs[key]
            
            # Create GetEndpoints model
            get_endpoints = GetEndpoints(**request_body)
            
            # Call SDK method
            result = api_client.get_endpoints_metrics(
                fill_time_series=True,
                get_endpoints=get_endpoints
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            if include_metrics:
                return {
                    "query_type": "list_endpoints_in_application_with_metrics",
                    "application": {"id": application_id, "name": application_name},
                    "endpoints_with_metrics": items,
                    "summary": {
                        "total_endpoints": len(items),
                        "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics],
                        "time_range": time_frame
                    }
                }
            else:
                # Strip metrics, return only names
                endpoints = [
                    {"id": ep.get("endpoint", {}).get("id"), "name": ep.get("endpoint", {}).get("label")}
                    for ep in items if ep.get("endpoint", {}).get("label")
                ]
                endpoints.sort(key=lambda x: x["name"])
                
                return {
                    "query_type": "list_endpoints_in_application",
                    "application": {"id": application_id, "name": application_name},
                    "endpoints": endpoints,
                    "summary": {
                        "total_endpoints": len(endpoints),
                        "time_range": time_frame,
                        "note": "Endpoint names only (no metrics)"
                    }
                }
            
        except Exception as e:
            logger.error(f"Error listing endpoints: {e}", exc_info=True)
            return {"error": f"Failed to list endpoints: {e!s}"}

    async def _list_endpoints_in_service(
        self,
        api_client: ApplicationMetricsApi,
        service_id: str,
        service_name: str,
        application_id: Optional[str],
        application_name: Optional[str],
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        **kwargs  # Accept any additional parameters for metrics queries
    ) -> Dict[str, Any]:
        """
        List endpoints in a service using ApplicationMetricsApi.
        
        Args:
            **kwargs: Additional optional parameters when include_metrics=True:
                - applicationBoundaryScope: "ALL" or "INBOUND"
                - endpointId: Filter by specific endpoint ID
                - endpointTypes: List of endpoint types to filter by
                - nameFilter: Filter by name with contains semantic
                - technologies: List of technologies to filter by
                - order: Ordering specification
                - pagination: Pagination specification
        """
        try:
            # Create request body with serviceId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame,
                "serviceId": service_id
            }
            
            # Add applicationId if provided
            if application_id:
                request_body["applicationId"] = application_id
            
            # Add optional parameters only when fetching metrics
            if include_metrics and kwargs:
                # Add supported optional parameters if provided
                for key in ['applicationBoundaryScope', 'endpointId', 'endpointTypes', 'nameFilter', 'technologies', 'order', 'pagination']:
                    if key in kwargs and kwargs[key] is not None:
                        request_body[key] = kwargs[key]
            
            # Create GetEndpoints model
            get_endpoints = GetEndpoints(**request_body)
            
            # Call SDK method
            result = api_client.get_endpoints_metrics(
                fill_time_series=True,
                get_endpoints=get_endpoints
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            response: Dict[str, Any] = {
                "service": {"id": service_id, "name": service_name}
            }
            
            if application_id:
                response["application"] = {"id": application_id, "name": application_name}
                query_type_suffix = "_in_application"
            else:
                query_type_suffix = ""
            
            if include_metrics:
                response["query_type"] = f"list_endpoints_in_service{query_type_suffix}_with_metrics"
                response["endpoints_with_metrics"] = items
                response["summary"] = {
                    "total_endpoints": len(items),
                    "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics],
                    "time_range": time_frame
                }
            else:
                # Strip metrics, return only names
                endpoints = [
                    {"id": ep.get("endpoint", {}).get("id"), "name": ep.get("endpoint", {}).get("label")}
                    for ep in items if ep.get("endpoint", {}).get("label")
                ]
                endpoints.sort(key=lambda x: x["name"])
                
                response["query_type"] = f"list_endpoints_in_service{query_type_suffix}"
                response["endpoints"] = endpoints
                response["summary"] = {
                    "total_endpoints": len(endpoints),
                    "time_frame": time_frame,
                    "note": "Endpoint names only (no metrics)"
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error listing endpoints: {e}", exc_info=True)
            return {"error": f"Failed to list endpoints: {e!s}"}

    async def _list_applications_by_service_filters(
        self,
        api_client: ApplicationMetricsApi,
        service_name: str,
        plugin_type: str,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool
    ) -> Dict[str, Any]:
        """
        List applications that contain services matching service name and plugin type.
        
        Uses the MetricsFilterHelpers.list_applications_by_service_filters helper method.
        
        Args:
            api_client: The ApplicationMetricsApi client
            service_name: Service name pattern to match
            plugin_type: Plugin type to filter by
            metrics: List of metrics to fetch
            time_frame: Time range dictionary
            include_metrics: Whether to include metrics in response
        
        Returns:
            Dictionary with matching applications and their metrics
        """
        return await self.metrics_filter_helpers.list_applications_by_service_filters(
            service_name=service_name,
            plugin_type=plugin_type,
            metrics=metrics,
            time_frame=time_frame,
            include_metrics=include_metrics,
            fetch_applications_func=self._list_applications,
            api_client=api_client
        )
