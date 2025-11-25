"""
Application Insights MCP Tools Module

This module provides comprehensive application insights for Instana monitoring using SDK methods.
Intelligently handles different query types for applications, services, and endpoints.

Uses:
- ApplicationMetricsApi for all queries (both with and without metrics)
- ApplicationResourcesApi for looking up entity IDs by name

Supports queries with or without metrics:
- List all applications (with/without metrics)
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

# Import SDK classes
try:
    from instana_client.api.application_metrics_api import ApplicationMetricsApi
    from instana_client.api.application_resources_api import ApplicationResourcesApi
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

    @register_as_tool(
        title="Get Application Insights",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationMetricsApi)
    async def application_insights(
        self,
        application_name: Optional[str] = None,
        service_name: Optional[str] = None,
        metrics: Optional[List[Dict[str, str]]] = None,
        time_frame: Optional[Dict[str, int]] = None,
        ctx=None,
        api_client=None,
    ) -> Dict[str, Any]:
        """
        Get application insights - intelligently handles all query types using SDK methods.
        
        The AI assistant interprets the user's natural language query and calls this function with appropriate parameters.
        The function automatically determines what data to fetch based on the parameters provided.
        
        **Supported Query Types:**
        
        1. **"list all applications"** (no parameters)
           - Returns: List of application names only
           - Call: application_insights()
        
        2. **"list all applications with metrics"** or **"list applications with call metrics"**
           - Returns: Applications with their metrics data
           - Call: application_insights(metrics=[{"metric": "calls", "aggregation": "SUM"}])
        
        3. **"list services in application XYZ"**
           - Returns: List of service names in the specified application
           - Call: application_insights(application_name="XYZ")
        
        4. **"list services in application XYZ with call metrics"**
           - Returns: Services with their metrics data
           - Call: application_insights(application_name="XYZ", metrics=[{"metric": "calls", "aggregation": "SUM"}])
        
        5. **"list endpoints of application XYZ"**
           - Returns: List of endpoint names in the specified application
           - Call: application_insights(application_name="XYZ", service_name="*")
        
        6. **"list endpoints of service ABC"**
           - Returns: List of endpoint names in the specified service
           - Call: application_insights(service_name="ABC")
        
        7. **"list endpoints of service ABC in application XYZ"**
           - Returns: List of endpoint names filtered by both application and service
           - Call: application_insights(application_name="XYZ", service_name="ABC")
        
        Args:
            application_name: Name of the application to filter by (optional)
            service_name: Name of the service to filter by. Use "*" to get all endpoints in an application (optional)
            metrics: List of metrics with aggregations. If None, returns entity names only (no metrics).
                    If provided, returns entities with their metrics data.
                    Example: [{"metric": "calls", "aggregation": "SUM"}]
            time_frame: Time range with 'from' and 'to' timestamps in milliseconds.
                       If not provided, defaults to last 1 hour.
                       Example: {"from": 1617994800000, "to": 1618081200000}
            ctx: The MCP context (optional)
            api_client: The ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary containing application/service/endpoint data with or without metrics based on the query type
        """
        try:
            logger.debug(f"application_insights called with application_name={application_name}, service_name={service_name}, metrics={metrics}")

            # Set default time range if not provided
            if not time_frame:
                to_time = int(datetime.now().timestamp() * 1000)
                from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
                time_frame = {"from": from_time, "to": to_time}

            # Set default metrics for API calls (we'll filter out if user doesn't want metrics)
            api_metrics = metrics if metrics else [{"metric": "calls", "aggregation": "SUM"}]
            
            # Determine query type based on parameters
            
            # Ensure api_client is not None
            if api_client is None:
                return {"error": "API client not initialized"}
            
            # Case 1 & 2: List all applications (with or without metrics)
            if not application_name and not service_name:
                return await self._list_applications(api_client, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 3 & 4: List services in an application (with or without metrics)
            elif application_name and not service_name:
                # Lookup application ID using ApplicationResourcesApi
                app_id = await self._lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                return await self._list_services_in_application(api_client, app_id, application_name, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 5: List endpoints of application (service_name="*")
            elif application_name and service_name == "*":
                # Lookup application ID
                app_id = await self._lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                return await self._list_endpoints_in_application(api_client, app_id, application_name, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 6: List endpoints of service (no application_name)
            elif not application_name and service_name and service_name != "*":
                # Lookup service ID
                service_id = await self._lookup_service_id(service_name, time_frame)
                if isinstance(service_id, dict) and "error" in service_id:
                    return service_id
                
                if not isinstance(service_id, str):
                    return {"error": "Invalid service ID returned"}
                
                return await self._list_endpoints_in_service(api_client, service_id, service_name, None, None, api_metrics, time_frame, include_metrics=(metrics is not None))
            
            # Case 7: List endpoints of service in application
            elif application_name and service_name and service_name != "*":
                # Lookup both application and service IDs
                app_id = await self._lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                service_id = await self._lookup_service_id(service_name, time_frame)
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
        include_metrics: bool
    ) -> Dict[str, Any]:
        """
        List all applications using ApplicationMetricsApi.
        
        Args:
            api_client: The ApplicationMetricsApi client
            metrics: List of metrics to fetch
            time_frame: Time range dictionary
            include_metrics: If False, strip metrics from response and return only names
        """
        try:
            # Create request body
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame
            }
            
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

    async def _list_services_in_application(
        self,
        api_client: ApplicationMetricsApi,
        application_id: str,
        application_name: str,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool
    ) -> Dict[str, Any]:
        """
        List services in an application using ApplicationMetricsApi.
        """
        try:
            # Create request body with applicationId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame,
                "applicationIds": [application_id]
            }
            
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
                        "time_range": time_frame,
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
        include_metrics: bool
    ) -> Dict[str, Any]:
        """
        List endpoints in an application using ApplicationMetricsApi.
        """
        try:
            # Create request body with applicationId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame,
                "applicationIds": [application_id]
            }
            
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
        include_metrics: bool
    ) -> Dict[str, Any]:
        """
        List endpoints in a service using ApplicationMetricsApi.
        """
        try:
            # Create request body with serviceId filter
            request_body = {
                "metrics": metrics,
                "timeFrame": time_frame,
                "serviceIds": [service_id]
            }
            
            # Add applicationId if provided
            if application_id:
                request_body["applicationIds"] = [application_id]
            
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
                    "time_range": time_frame,
                    "note": "Endpoint names only (no metrics)"
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error listing endpoints: {e}", exc_info=True)
            return {"error": f"Failed to list endpoints: {e!s}"}

    @with_header_auth(ApplicationResourcesApi)
    async def _lookup_application_id(
        self,
        app_name: str,
        time_frame: Dict[str, int],
        ctx=None,
        api_client=None
    ) -> Any:
        """
        Look up application ID by name using ApplicationResourcesApi.
        
        Args:
            app_name: Application name to search for
            time_frame: Time range dictionary
            api_client: ApplicationResourcesApi client (injected by decorator)
        
        Returns:
            Application ID string or error dict
        """
        try:
            # Calculate window_size and to timestamp
            if "windowSize" in time_frame and "to" in time_frame:
                window_size = time_frame["windowSize"]
                to_time = time_frame["to"]
            elif "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
            else:
                # Default to 1 hour if not properly specified
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
            
            logger.debug(f"Looking up application '{app_name}' with window_size={window_size}, to={to_time}")
            
            # Call SDK method to get applications
            result = api_client.get_applications(
                window_size=window_size,
                to=to_time,
                name_filter=app_name,
                application_boundary_scope="ALL"
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            if not items:
                return {"error": f"No application found with name matching '{app_name}'"}
            
            app = items[0]
            logger.debug(f"Found application: id={app.get('id')}, label={app.get('label')}")
            return app.get("id")
            
        except Exception as e:
            logger.error(f"Error looking up application ID: {e}", exc_info=True)
            return {"error": f"Failed to lookup application: {e!s}"}

    @with_header_auth(ApplicationResourcesApi)
    async def _lookup_service_id(
        self,
        service_name: str,
        time_frame: Dict[str, int],
        ctx=None,
        api_client=None
    ) -> Any:
        """
        Look up service ID by name using ApplicationResourcesApi.
        
        Args:
            service_name: Service name to search for
            time_frame: Time range dictionary
            api_client: ApplicationResourcesApi client (injected by decorator)
        
        Returns:
            Service ID string or error dict
        """
        try:
            # Calculate window_size and to timestamp
            if "windowSize" in time_frame and "to" in time_frame:
                window_size = time_frame["windowSize"]
                to_time = time_frame["to"]
            elif "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
            else:
                # Default to 1 hour if not properly specified
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
            
            logger.debug(f"Looking up service '{service_name}' with window_size={window_size}, to={to_time}")
            
            # Call SDK method to get services
            result = api_client.get_services(
                window_size=window_size,
                to=to_time,
                name_filter=service_name,
                include_snapshot_ids=False
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            if not items:
                return {"error": f"No service found with name matching '{service_name}'"}
            
            service = items[0]
            logger.debug(f"Found service: id={service.get('id')}, label={service.get('label')}")
            return service.get("id")
            
        except Exception as e:
            logger.error(f"Error looking up service ID: {e}", exc_info=True)
            return {"error": f"Failed to lookup service: {e!s}"}

# Made with Bob
