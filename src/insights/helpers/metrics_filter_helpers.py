"""
Metrics Filter Helper Functions for Instana Insights

Provides reusable helper class for filtering applications by service criteria.
Can be used by both application metrics and infrastructure metrics tools.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.utils import BaseInstanaClient, with_header_auth

# Import SDK classes
try:
    from instana_client.api.application_metrics_api import ApplicationMetricsApi
    from instana_client.api.infrastructure_resources_api import InfrastructureResourcesApi
    from instana_client.api.infrastructure_metrics_api import InfrastructureMetricsApi
    from instana_client.models.get_applications import GetApplications
    from instana_client.models.get_services import GetServices
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)


class MetricsFilterHelpers(BaseInstanaClient):
    """Helper class for filtering applications by service criteria for metrics queries."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the metrics filter helpers."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(ApplicationMetricsApi)
    async def find_applications_by_service_criteria(
        self,
        service_name_pattern: Optional[str] = None,
        plugin_type: Optional[str] = None,
        time_frame: Optional[Dict[str, int]] = None,
        max_applications: int = 50,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Find applications that contain services matching the specified criteria.
        
        OPTIMIZED VERSION: Uses pagination and batch queries to reduce API calls.
        
        This helper function searches through applications and identifies those
        that have services matching the given service name pattern and/or plugin type.
        
        Can be used by both application metrics and infrastructure metrics tools to
        filter applications before fetching their respective metrics.
        
        Args:
            service_name_pattern: Text pattern to match in service names (case-insensitive, optional)
            plugin_type: Plugin type to filter by (e.g., "jvm", "host", "docker", optional)
            time_frame: Time range dictionary (optional)
            max_applications: Maximum number of applications to check (default 50, prevents timeout)
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary with:
            - matching_applications: List of apps with their matching services
            - summary: Statistics about the search
        """
        try:
            logger.debug(f"find_applications_by_service_criteria called with service_name_pattern={service_name_pattern}, plugin_type={plugin_type}, max_applications={max_applications}")
            
            # Validate that at least one filter is provided
            if not service_name_pattern and not plugin_type:
                return {
                    "error": "At least one filter (service_name_pattern or plugin_type) must be provided"
                }
            
            # Set default time range if not provided
            if not time_frame:
                to_time = int(datetime.now().timestamp() * 1000)
                from_time = to_time - (60 * 60 * 1000)
                time_frame = {"from": from_time, "to": to_time}
            
            # Convert time_frame for GetServices
            if "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            elif "windowSize" in time_frame and "to" in time_frame:
                formatted_time_frame = time_frame
            else:
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            
            # Step 1: Get applications with pagination to limit scope
            logger.debug(f"Step 1: Fetching up to {max_applications} applications")
            
            # Convert time_frame to proper format for GetApplications
            # GetApplications also expects windowSize and to, not from and to
            if "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
                formatted_app_time_frame = {"windowSize": window_size, "to": to_time}
            elif "windowSize" in time_frame and "to" in time_frame:
                formatted_app_time_frame = time_frame
            else:
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
                formatted_app_time_frame = {"windowSize": window_size, "to": to_time}
            
            # Add pagination to limit the number of applications fetched
            request_body = {
                "metrics": [{"metric": "calls", "aggregation": "SUM"}],
                "timeFrame": formatted_app_time_frame,
                "pagination": {
                    "page": 1,
                    "pageSize": max_applications
                }
            }
            
            get_applications = GetApplications(**request_body)
            result = api_client.get_application_metrics(
                fill_time_series=False,
                get_applications=get_applications
            )
            
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            all_apps = result_dict.get("items", [])
            logger.debug(f"Found {len(all_apps)} applications (limited to {max_applications})")
            
            if not all_apps:
                return {
                    "matching_applications": [],
                    "summary": {
                        "total_applications_checked": 0,
                        "matching_applications": 0,
                        "filters": {
                            "service_name_pattern": service_name_pattern,
                            "plugin_type": plugin_type
                        }
                    }
                }
            
            # Step 2: For each application, get its services and check filters
            matching_apps = []
            apps_checked = 0
            
            for app_item in all_apps:
                app_data = app_item.get("application", {})
                app_id = app_data.get("id")
                app_name = app_data.get("label")
                
                if not app_id:
                    continue
                
                apps_checked += 1
                logger.debug(f"Checking application {apps_checked}/{len(all_apps)}: {app_name} ({app_id})")
                
                # Get services for this application with name filter if provided
                service_request_body = {
                    "metrics": [{"metric": "calls", "aggregation": "SUM"}],
                    "timeFrame": formatted_time_frame,
                    "applicationId": app_id
                }
                
                # Add name filter to reduce services fetched
                if service_name_pattern:
                    service_request_body["nameFilter"] = service_name_pattern
                
                get_services = GetServices(**service_request_body)
                services_result = api_client.get_services_metrics(
                    fill_time_series=False,
                    include_snapshot_ids=False,
                    get_services=get_services
                )
                
                if hasattr(services_result, 'to_dict'):
                    services_dict = services_result.to_dict()
                else:
                    services_dict = services_result
                
                services = services_dict.get("items", [])
                logger.debug(f"  Found {len(services)} services in {app_name}")
                
                # If no services match the name filter, skip this app
                if not services:
                    continue
                
                # Filter services based on criteria
                matching_services = []
                for service_item in services:
                    service_data = service_item.get("service", {})
                    service_name = service_data.get("label", "")
                    service_id = service_data.get("id", "")
                    
                    # Name already filtered by API if pattern provided
                    # Just do final check for plugin type if specified
                    plugin_matches = True
                    if plugin_type:
                        # OPTIMIZED: Check plugin type via infrastructure query
                        # This is still expensive, but we've already filtered by name
                        plugin_matches = await self._check_service_plugin_type(
                            service_id, plugin_type, formatted_time_frame
                        )
                    
                    if plugin_matches:
                        matching_services.append({
                            "id": service_id,
                            "name": service_name
                        })
                
                logger.debug(f"  {len(matching_services)} services match all criteria")
                
                # If this app has matching services, add it to results
                if matching_services:
                    matching_apps.append({
                        "application_id": app_id,
                        "application_name": app_name,
                        "matching_services": matching_services
                    })
                    
                    logger.debug(f"  Application {app_name} added to results with {len(matching_services)} matching services")
            
            # Prepare final result
            return {
                "matching_applications": matching_apps,
                "summary": {
                    "total_applications_checked": apps_checked,
                    "matching_applications": len(matching_apps),
                    "total_matching_services": sum(len(app["matching_services"]) for app in matching_apps),
                    "filters": {
                        "service_name_pattern": service_name_pattern,
                        "plugin_type": plugin_type
                    },
                    "time_range": time_frame,
                    "note": f"Limited to first {max_applications} applications to prevent timeout"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in find_applications_by_service_criteria: {e}", exc_info=True)
            return {"error": f"Failed to find applications by service criteria: {e!s}"}
    
    @with_header_auth(InfrastructureResourcesApi)
    async def _check_service_plugin_type(
        self,
        service_id: str,
        plugin_type: str,
        time_frame: Dict[str, int],
        ctx=None,
        api_client=None
    ) -> bool:
        """
        Check if a service has infrastructure entities with the specified plugin type.
        If plugin_type is None or empty, tries common plugin types (process, host, jvm, docker, kubernetes).
        
        Args:
            service_id: Service ID to check
            plugin_type: Plugin type to look for (e.g., "jvm", "host", "docker", "process")
                        If None, will try multiple common types
            time_frame: Time range dictionary with windowSize and to
            api_client: InfrastructureResourcesApi client (injected by decorator)
        
        Returns:
            True if service has entities with the specified plugin type (or any common type if None), False otherwise
        """
        try:
            # Convert time_frame
            if "windowSize" in time_frame and "to" in time_frame:
                window_size = time_frame["windowSize"]
                to_time = time_frame["to"]
            else:
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
            
            # If no plugin type specified, try common ones
            plugin_types_to_try = [plugin_type] if plugin_type else ["process", "host", "jvm", "docker", "kubernetes"]
            
            for pt in plugin_types_to_try:
                # Search for snapshots with the service ID and plugin type
                query = f"entity.service.id:{service_id} AND entity.type:{pt}"
                logger.debug(f"Checking plugin type with query: {query}")
                
                result = api_client.get_snapshots(
                    query=query,
                    to=to_time,
                    window_size=window_size,
                    size=1,  # We only need to know if any exist
                    offline=False
                )
                
                # Convert to dict
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                else:
                    result_dict = result
                
                items = result_dict.get("items", [])
                has_plugin = len(items) > 0
                
                if has_plugin:
                    logger.debug(f"Service {service_id} has plugin type {pt}: True")
                    return True
                else:
                    logger.debug(f"Service {service_id} has plugin type {pt}: False")
            
            # None of the plugin types matched
            logger.debug(f"Service {service_id} does not have any of the plugin types: {plugin_types_to_try}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking service plugin type: {e}", exc_info=True)
            # If we can't determine, assume it doesn't match
            return False

    @with_header_auth(ApplicationMetricsApi)
    async def list_applications_by_service_filters(
        self,
        service_name: str,
        plugin_type: str,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        fetch_applications_func,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        List applications that contain services matching service name and plugin type.
        
        This is a reusable helper that can be used by both application metrics and
        infrastructure metrics tools. It filters applications by service criteria and
        optionally fetches their metrics using the provided fetch function.
        
        Args:
            service_name: Service name pattern to match
            plugin_type: Plugin type to filter by
            metrics: List of metrics to fetch
            time_frame: Time range dictionary
            include_metrics: Whether to include metrics in response
            fetch_applications_func: Async function to fetch application metrics
                                    Should accept (api_client, metrics, time_frame, include_metrics, **kwargs)
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary with matching applications and their metrics (if requested)
        """
        try:
            # Use the filter helper to find matching applications
            filter_result = await self.find_applications_by_service_criteria(
                service_name_pattern=service_name,
                plugin_type=plugin_type,
                time_frame=time_frame
            )
            
            if "error" in filter_result:
                return filter_result
            
            matching_apps = filter_result.get("matching_applications", [])
            
            if not matching_apps:
                return {
                    "query_type": "list_applications_by_service_filters",
                    "applications": [],
                    "summary": {
                        **filter_result.get("summary", {}),
                        "message": "No applications found matching the specified service criteria"
                    }
                }
            
            # If metrics not requested, return just the application list
            if not include_metrics:
                apps_list = []
                for app in matching_apps:
                    apps_list.append({
                        "id": app.get("application_id"),
                        "name": app.get("application_name"),
                        "matching_services": app.get("matching_services", [])
                    })
                
                return {
                    "query_type": "list_applications_by_service_filters",
                    "applications": apps_list,
                    "summary": {
                        **filter_result.get("summary", {}),
                        "note": "Application names only (no metrics)"
                    }
                }
            
            # Get metrics for each matching application
            apps_with_metrics = []
            
            for app in matching_apps:
                app_name = app.get("application_name")
                
                # Get application metrics using the provided function
                app_metrics_result = await fetch_applications_func(
                    api_client, metrics, time_frame, include_metrics=True,
                    nameFilter=app_name
                )
                
                app_metrics = None
                if "applications_with_metrics" in app_metrics_result:
                    apps_list = app_metrics_result["applications_with_metrics"]
                    if apps_list:
                        app_metrics = apps_list[0]
                
                # Add matching services info to the metrics
                if app_metrics:
                    app_metrics["matching_services"] = app.get("matching_services", [])
                    apps_with_metrics.append(app_metrics)
            
            return {
                "query_type": "list_applications_by_service_filters_with_metrics",
                "applications_with_metrics": apps_with_metrics,
                "summary": {
                    **filter_result.get("summary", {}),
                    "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics]
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing applications by service filters: {e}", exc_info=True)
            return {"error": f"Failed to list applications by service filters: {e!s}"}

    @with_header_auth(ApplicationMetricsApi)
    async def get_combined_service_metrics(
        self,
        service_name: str,
        plugin_type: str,
        app_metrics: List[Dict[str, str]],
        infra_metrics: List[str],
        time_frame: Dict[str, int],
        rollup: int = 60,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get BOTH application metrics AND infrastructure metrics for a service.
        
        Flow:
        1. Service name → Service ID (lookup)
        2. Service ID → Application metrics (calls, latency, errors)
        3. Service ID → Snapshot IDs (infrastructure entities)
        4. Snapshot IDs + Plugin → Infrastructure metrics (CPU, memory, etc.)
        5. Result = Combined app metrics + infra metrics
        
        Args:
            service_name: Service name to get metrics for
            plugin_type: Infrastructure plugin type (e.g., "host", "process", "jvm")
            app_metrics: Application metrics to fetch (e.g., [{"metric": "calls", "aggregation": "SUM"}])
            infra_metrics: Infrastructure metrics to fetch (e.g., ["cpu.used", "memory.used"])
            time_frame: Time range dictionary
            rollup: Rollup interval in seconds for infra metrics (default 60)
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary with both application_metrics and infrastructure_metrics
        """
        try:
            from src.insights.helpers import LookupHelpers, ServiceHelpers
            from instana_client.api.infrastructure_metrics_api import InfrastructureMetricsApi
            from instana_client.models.get_combined_metrics import GetCombinedMetrics
            
            logger.debug(f"get_combined_service_metrics called for service '{service_name}' with plugin '{plugin_type}'")
            
            # Initialize helpers
            lookup_helpers = LookupHelpers(read_token=self.read_token, base_url=self.base_url)
            service_helpers = ServiceHelpers(read_token=self.read_token, base_url=self.base_url)
            
            # Step 1: Lookup service ID
            logger.debug(f"Step 1: Looking up service ID for '{service_name}'")
            service_id = await lookup_helpers.lookup_service_id(service_name, time_frame)
            if isinstance(service_id, dict) and "error" in service_id:
                return service_id
            
            if not isinstance(service_id, str):
                return {"error": "Invalid service ID returned"}
            
            logger.debug(f"Found service ID: {service_id}")
            
            # Step 2: Get application metrics for the service
            logger.debug(f"Step 2: Fetching application metrics for service")
            
            # Convert time_frame to proper format for GetServices
            if "from" in time_frame and "to" in time_frame:
                window_size = time_frame["to"] - time_frame["from"]
                to_time = time_frame["to"]
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            elif "windowSize" in time_frame and "to" in time_frame:
                formatted_time_frame = time_frame
            else:
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
                formatted_time_frame = {"windowSize": window_size, "to": to_time}
            
            # Get application metrics
            service_request_body = {
                "metrics": app_metrics,
                "timeFrame": formatted_time_frame,
                "serviceId": service_id
            }
            
            get_services = GetServices(**service_request_body)
            app_result = api_client.get_services_metrics(
                fill_time_series=True,
                include_snapshot_ids=False,
                get_services=get_services
            )
            
            if hasattr(app_result, 'to_dict'):
                app_result_dict = app_result.to_dict()
            else:
                app_result_dict = app_result
            
            app_items = app_result_dict.get("items", [])
            logger.debug(f"Found {len(app_items)} application metric items")
            
            # Step 3: Get snapshot IDs for infrastructure metrics
            logger.debug(f"Step 3: Getting snapshot IDs for service")
            snapshot_ids = await service_helpers.get_service_snapshot_ids(
                service_id, None, time_frame, service_name=service_name
            )
            
            if isinstance(snapshot_ids, dict) and "error" in snapshot_ids:
                # Return app metrics even if infra metrics fail
                return {
                    "query_type": "combined_service_metrics_partial",
                    "service": {"id": service_id, "name": service_name},
                    "application_metrics": app_items[0] if app_items else {},
                    "infrastructure_metrics": None,
                    "warning": f"Could not fetch infrastructure metrics: {snapshot_ids.get('error')}",
                    "summary": {
                        "has_application_metrics": len(app_items) > 0,
                        "has_infrastructure_metrics": False,
                        "plugin_type": plugin_type,
                        "time_range": time_frame
                    }
                }
            
            if not snapshot_ids:
                # Return app metrics even if no snapshots found
                return {
                    "query_type": "combined_service_metrics_partial",
                    "service": {"id": service_id, "name": service_name},
                    "application_metrics": app_items[0] if app_items else {},
                    "infrastructure_metrics": None,
                    "warning": f"No infrastructure snapshot IDs found for service '{service_name}' with plugin '{plugin_type}'",
                    "summary": {
                        "has_application_metrics": len(app_items) > 0,
                        "has_infrastructure_metrics": False,
                        "plugin_type": plugin_type,
                        "time_range": time_frame
                    }
                }
            
            logger.debug(f"Found {len(snapshot_ids)} snapshot IDs")
            
            # Step 4: Get infrastructure metrics
            logger.debug(f"Step 4: Fetching infrastructure metrics")
            infra_result = await self._get_infrastructure_metrics_internal(
                snapshot_ids=snapshot_ids,
                metrics=infra_metrics,
                plugin=plugin_type,
                time_frame=time_frame,
                rollup=rollup
            )
            
            # Step 5: Combine results
            return {
                "query_type": "combined_service_metrics",
                "service": {"id": service_id, "name": service_name},
                "application_metrics": app_items[0] if app_items else {},
                "infrastructure_metrics": infra_result,
                "summary": {
                    "has_application_metrics": len(app_items) > 0,
                    "has_infrastructure_metrics": not isinstance(infra_result, dict) or "error" not in infra_result,
                    "snapshot_count": len(snapshot_ids),
                    "app_metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in app_metrics],
                    "infra_metrics_requested": infra_metrics,
                    "plugin_type": plugin_type,
                    "time_range": time_frame
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_combined_service_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get combined service metrics: {e!s}"}
    
    @with_header_auth(InfrastructureMetricsApi)
    async def _get_infrastructure_metrics_internal(
        self,
        snapshot_ids: List[str],
        metrics: List[str],
        plugin: str,
        time_frame: Dict[str, int],
        rollup: int,
        ctx=None,
        api_client=None
    ) -> Any:
        """
        Internal method to get infrastructure metrics using InfrastructureMetricsApi.
        
        Args:
            snapshot_ids: List of snapshot IDs
            metrics: List of metrics to retrieve
            plugin: Plugin type
            time_frame: Time range dictionary
            rollup: Rollup interval in seconds
            api_client: InfrastructureMetricsApi client (injected by decorator)
        
        Returns:
            Infrastructure metrics data or error dict
        """
        try:
            from instana_client.models.get_combined_metrics import GetCombinedMetrics
            
            # Create request body
            request_body = {
                "metrics": metrics,
                "plugin": plugin,
                "rollup": rollup,
                "timeFrame": time_frame,
                "snapshotIds": snapshot_ids
            }
            
            logger.debug(f"Fetching infrastructure metrics with {len(snapshot_ids)} snapshot IDs")
            
            # Create GetCombinedMetrics model
            get_combined_metrics = GetCombinedMetrics(**request_body)
            
            # Call SDK method
            result = api_client.get_infrastructure_metrics(
                offline=False,
                get_combined_metrics=get_combined_metrics
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            # Limit the response size to top 3 items
            if "items" in result_dict and isinstance(result_dict["items"], list):
                items_list = result_dict["items"]
                original_count = len(items_list)
                if original_count > 3:
                    result_dict["items"] = items_list[:3]
                    result_dict["note"] = f"Showing 3 of {original_count} items"
                    logger.debug(f"Limited response items from {original_count} to 3")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Error getting infrastructure metrics: {e}", exc_info=True)
            return {"error": f"Failed to get infrastructure metrics: {e!s}"}


#  