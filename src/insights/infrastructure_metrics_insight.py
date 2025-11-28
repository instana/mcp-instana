"""
Infrastructure Metrics Insights MCP Tools Module

Handles infrastructure metrics queries for services with automatic snapshot ID resolution.

Uses:
- ApplicationMetricsApi for getting service snapshot IDs
- ApplicationResourcesApi for looking up entity IDs by name
- InfrastructureMetricsApi for infrastructure metrics queries

Supports four main use cases:
1. Specific service only - lookup service → get snapshot IDs → fetch infra metrics
2. Service within an application - lookup app → lookup service → get snapshot IDs → fetch infra metrics
3. All services in an application - lookup app → list services → collect snapshot IDs → fetch infra metrics
4. All services across all applications - list all services → collect snapshot IDs → fetch infra metrics
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.types import ToolAnnotations

from src.prompts import mcp
from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
from src.insights.helpers import LookupHelpers, ServiceHelpers

# Import SDK classes
try:
    from instana_client.api.infrastructure_metrics_api import InfrastructureMetricsApi
    from instana_client.models.get_combined_metrics import GetCombinedMetrics
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)


class InfrastructureMetricsInsightMCPTools(BaseInstanaClient):
    """Tool for infrastructure metrics insights in Instana MCP using SDK methods."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Metrics Insight MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)
        self.lookup_helpers = LookupHelpers(read_token=read_token, base_url=base_url)
        self.service_helpers = ServiceHelpers(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Infrastructure Metrics for Services (CPU, Memory, etc.)",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    async def infrastructure_metrics_insights(
        self,
        service_name: Optional[str] = None,
        application_name: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        plugin: Optional[str] = None,
        time_frame: Optional[Dict[str, int]] = None,
        rollup: Optional[int] = None,
        query: Optional[str] = None,
        ctx=None,
    ) -> Dict[str, Any]:
        """
        Get infrastructure metrics (CPU, memory, etc.) for services with automatic snapshot ID resolution.
        
        This is the PRIMARY tool for getting infrastructure-level metrics like CPU usage, memory usage,
        disk I/O, etc. for services. Use this when users ask about:
        - CPU usage for a service
        - Memory consumption of a service
        - Infrastructure performance metrics
        - Host-level or container-level metrics for services
        
        Simple Usage Examples:
        - "Show CPU usage for service DOTNETIIS" → infrastructure_metrics_insights(service_name="DOTNETIIS")
        - "Get memory for service MyService" → infrastructure_metrics_insights(service_name="MyService", metrics=["memory.used"])
        - "CPU usage for MyService in MyApp" → infrastructure_metrics_insights(application_name="MyApp", service_name="MyService")
        
        The tool automatically:
        1. Looks up the service ID by name
        2. Gets snapshot IDs for the service's infrastructure entities
        3. Fetches infrastructure metrics for those entities
        
        Args:
            service_name: Service name to get infrastructure metrics for (optional)
            application_name: Application name to filter by (optional)
            metrics: List of infrastructure metrics (optional, defaults to ["cpu.used", "memory.used"])
                     Common metrics: cpu.used, memory.used, disk.used, network.in, network.out
            plugin: Plugin type (optional, defaults to "host")
                    Options: host, jvm, docker, kubernetes, process
            query: Query string for filtering (optional, uses snapshot IDs if not provided)
            time_frame: Time range in milliseconds (optional, defaults to last 1 hour)
            rollup: Rollup interval in seconds (optional, defaults to 60)
        
        Returns:
            Dictionary with infrastructure metrics data including snapshot IDs and metric values
        """
        try:
            logger.debug(f"infrastructure_metrics_insights called with service_name={service_name}, application_name={application_name}, plugin={plugin}")

            # Set smart defaults for optional parameters
            if not metrics:
                metrics = ["cpu.used", "memory.used"]  # Default to CPU and memory
                logger.debug(f"Using default metrics: {metrics}")
            
            # Plugin is optional - if not provided, we'll try to auto-detect
            plugin_provided = plugin is not None
            if not plugin:
                plugin = "host"  # Default to host plugin, but we'll try others if this fails
                logger.debug(f"No plugin specified, starting with default: {plugin}")
            else:
                logger.debug(f"Using specified plugin: {plugin}")
            
            # Query is optional - if not provided, we'll use snapshot IDs directly
            if query:
                logger.debug(f"Using provided query: {query}")
            else:
                logger.debug("No query provided, will use snapshot IDs directly")

            # Set default time range if not provided
            if not time_frame:
                to_time = int(datetime.now().timestamp() * 1000)
                from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour
                time_frame = {"from": from_time, "to": to_time}

            if not rollup:
                rollup = 60  # Default rollup to 60 seconds

            # Use Case 2: Application + Service (lookup both IDs)
            if application_name and service_name:
                logger.debug(f"Use Case 2: Fetching metrics for service '{service_name}' in application '{application_name}'")
                
                # Step 1: Lookup application ID
                app_id = await self.lookup_helpers.lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                logger.debug(f"Found application ID: {app_id}")
                
                # Step 2: Lookup service ID
                service_id = await self.lookup_helpers.lookup_service_id(service_name, time_frame)
                if isinstance(service_id, dict) and "error" in service_id:
                    return service_id
                
                if not isinstance(service_id, str):
                    return {"error": "Invalid service ID returned"}
                
                logger.debug(f"Found service ID: {service_id}")
                
                # Step 3: Get service metrics with snapshot IDs
                snapshot_ids = await self.service_helpers.get_service_snapshot_ids(service_id, app_id, time_frame, service_name=service_name)
                if isinstance(snapshot_ids, dict) and "error" in snapshot_ids:
                    return snapshot_ids
                
                if not snapshot_ids:
                    return {
                        "error": f"No infrastructure snapshot IDs found for service '{service_name}' in application '{application_name}'",
                        "details": {
                            "service_id": service_id,
                            "application_id": app_id,
                            "plugin_tried": plugin,
                            "possible_reasons": [
                                "Service may not have infrastructure entities (hosts, containers, etc.) associated with it",
                                "Service might be an external or synthetic service without infrastructure monitoring",
                                "The time range may not contain any infrastructure data",
                                "Infrastructure monitoring may not be enabled for this service"
                            ],
                            "suggestion": "Try using 'application_metrics_insights' tool instead to get application-level metrics (calls, latency, errors) for this service. Note: The tool now automatically tries multiple plugin types (process, host, jvm, docker, kubernetes)."
                        }
                    }
                
                logger.debug(f"Found {len(snapshot_ids)} snapshot IDs")
                
                # Step 4: Get infrastructure metrics
                infra_metrics = await self._get_infrastructure_metrics(
                    snapshot_ids=snapshot_ids,
                    metrics=metrics,
                    plugin=plugin,
                    query=query,
                    time_frame=time_frame,
                    rollup=rollup
                )
                
                return {
                    "query_type": "infrastructure_metrics_for_service_in_application",
                    "application": {"id": app_id, "name": application_name},
                    "service": {"id": service_id, "name": service_name},
                    "snapshot_ids": snapshot_ids,
                    "infrastructure_metrics": infra_metrics,
                    "summary": {
                        "total_snapshots": len(snapshot_ids),
                        "metrics_requested": metrics,
                        "plugin": plugin,
                        "time_range": time_frame
                    }
                }
            
            # Use Case 3: Application only (get all services in application)
            elif application_name and not service_name:
                logger.debug(f"Use Case 3: Fetching metrics for all services in application '{application_name}'")
                
                # Step 1: Lookup application ID
                app_id = await self.lookup_helpers.lookup_application_id(application_name, time_frame)
                if isinstance(app_id, dict) and "error" in app_id:
                    return app_id
                
                if not isinstance(app_id, str):
                    return {"error": "Invalid application ID returned"}
                
                logger.debug(f"Found application ID: {app_id}")
                
                # Step 2: Get all services in the application
                services_result = await self.service_helpers.get_services_in_application(app_id, time_frame)
                if isinstance(services_result, dict) and "error" in services_result:
                    return services_result
                
                services = services_result.get("services", [])
                if not services:
                    return {"error": f"No services found in application '{application_name}'"}
                
                logger.debug(f"Found {len(services)} services in application")
                
                # Step 3: Loop through services and collect all snapshot IDs
                all_snapshot_ids = []
                services_with_snapshots = []
                services_without_snapshots = []
                
                for service in services:
                    service_id = service.get("id")
                    service_name = service.get("name")
                    snapshot_ids = await self.service_helpers.get_service_snapshot_ids(
                        service_id, app_id, time_frame, service_name=service_name
                    )
                    if isinstance(snapshot_ids, list) and snapshot_ids:
                        all_snapshot_ids.extend(snapshot_ids)
                        services_with_snapshots.append(service_name)
                    else:
                        services_without_snapshots.append(service_name)
                
                # Remove duplicates
                all_snapshot_ids = list(set(all_snapshot_ids))
                
                if not all_snapshot_ids:
                    return {
                        "error": f"No infrastructure snapshot IDs found for any services in application '{application_name}'",
                        "details": {
                            "total_services": len(services),
                            "services_checked": [s.get("name") for s in services],
                            "possible_reasons": [
                                "Services may not have infrastructure entities (hosts, containers, etc.) associated with them",
                                "Services might be external or synthetic services without infrastructure monitoring",
                                "The time range may not contain any infrastructure data",
                                "Infrastructure monitoring may not be enabled for these services"
                            ],
                            "suggestion": "Try using 'application_metrics_insights' tool instead to get application-level metrics (calls, latency, errors) for these services"
                        }
                    }
                
                logger.debug(f"Found {len(all_snapshot_ids)} total snapshot IDs across all services")
                
                # Step 4: Get infrastructure metrics
                infra_metrics = await self._get_infrastructure_metrics(
                    snapshot_ids=all_snapshot_ids,
                    metrics=metrics,
                    plugin=plugin,
                    query=query,
                    time_frame=time_frame,
                    rollup=rollup
                )
                
                return {
                    "query_type": "infrastructure_metrics_for_all_services_in_application",
                    "application": {"id": app_id, "name": application_name},
                    "services_count": len(services),
                    "snapshot_ids": all_snapshot_ids,
                    "infrastructure_metrics": infra_metrics,
                    "summary": {
                        "total_services": len(services),
                        "total_snapshots": len(all_snapshot_ids),
                        "metrics_requested": metrics,
                        "plugin": plugin,
                        "time_range": time_frame
                    }
                }
            
            # Use Case 1: Service only (lookup service ID)
            elif service_name and not application_name:
                logger.debug(f"Use Case 1: Fetching metrics for service '{service_name}'")
                
                # Step 1: Lookup service ID
                service_id = await self.lookup_helpers.lookup_service_id(service_name, time_frame)
                if isinstance(service_id, dict) and "error" in service_id:
                    return service_id
                
                if not isinstance(service_id, str):
                    return {"error": "Invalid service ID returned"}
                
                logger.debug(f"Found service ID: {service_id}")
                
                # Step 2: Get service metrics with snapshot IDs
                snapshot_ids = await self.service_helpers.get_service_snapshot_ids(service_id, None, time_frame, service_name=service_name)
                if isinstance(snapshot_ids, dict) and "error" in snapshot_ids:
                    return snapshot_ids
                
                if not snapshot_ids:
                    return {
                        "error": f"No infrastructure snapshot IDs found for service '{service_name}'",
                        "details": {
                            "service_id": service_id,
                            "plugin_tried": plugin,
                            "possible_reasons": [
                                "Service may not have infrastructure entities (hosts, containers, etc.) associated with it",
                                "Service might be an external or synthetic service without infrastructure monitoring",
                                "The time range may not contain any infrastructure data",
                                "Infrastructure monitoring may not be enabled for this service"
                            ],
                            "suggestion": "Try using 'application_metrics_insights' tool instead to get application-level metrics (calls, latency, errors) for this service. Note: The tool now automatically tries multiple plugin types (process, host, jvm, docker, kubernetes)."
                        }
                    }
                
                logger.debug(f"Found {len(snapshot_ids)} snapshot IDs")
                
                # Step 3: Get infrastructure metrics
                infra_metrics = await self._get_infrastructure_metrics(
                    snapshot_ids=snapshot_ids,
                    metrics=metrics,
                    plugin=plugin,
                    query=query,
                    time_frame=time_frame,
                    rollup=rollup
                )
                
                return {
                    "query_type": "infrastructure_metrics_for_service",
                    "service": {"id": service_id, "name": service_name},
                    "snapshot_ids": snapshot_ids,
                    "infrastructure_metrics": infra_metrics,
                    "summary": {
                        "total_snapshots": len(snapshot_ids),
                        "metrics_requested": metrics,
                        "plugin": plugin,
                        "time_range": time_frame
                    }
                }
            
            # Use Case 4: No application or service (get all services)
            else:
                logger.debug(f"Use Case 4: Fetching metrics for all services across all applications")
                
                # Step 1: Get all services
                services_result = await self.service_helpers.get_all_services(time_frame)
                if isinstance(services_result, dict) and "error" in services_result:
                    return services_result
                
                service_ids = services_result.get("service_ids", [])
                if not service_ids:
                    return {"error": "No services found"}
                
                logger.debug(f"Found {len(service_ids)} services total")
                
                # Step 2: Loop through services and collect all snapshot IDs
                all_snapshot_ids = []
                services_with_snapshots = 0
                services_without_snapshots = 0
                
                for service_id in service_ids:
                    snapshot_ids = await self.service_helpers.get_service_snapshot_ids(service_id, None, time_frame)
                    if isinstance(snapshot_ids, list) and snapshot_ids:
                        all_snapshot_ids.extend(snapshot_ids)
                        services_with_snapshots += 1
                    else:
                        services_without_snapshots += 1
                
                # Remove duplicates
                all_snapshot_ids = list(set(all_snapshot_ids))
                
                if not all_snapshot_ids:
                    return {
                        "error": "No infrastructure snapshot IDs found for any services",
                        "details": {
                            "total_services_checked": len(service_ids),
                            "possible_reasons": [
                                "Services may not have infrastructure entities (hosts, containers, etc.) associated with them",
                                "Services might be external or synthetic services without infrastructure monitoring",
                                "The time range may not contain any infrastructure data",
                                "Infrastructure monitoring may not be enabled for these services"
                            ],
                            "suggestion": "Try using 'application_metrics_insights' tool instead to get application-level metrics (calls, latency, errors) for services"
                        }
                    }
                
                logger.debug(f"Found {len(all_snapshot_ids)} total snapshot IDs across all services")
                
                # Step 3: Get infrastructure metrics
                infra_metrics = await self._get_infrastructure_metrics(
                    snapshot_ids=all_snapshot_ids,
                    metrics=metrics,
                    plugin=plugin,
                    query=query,
                    time_frame=time_frame,
                    rollup=rollup
                )
                
                return {
                    "query_type": "infrastructure_metrics_for_all_services",
                    "services_count": len(service_ids),
                    "snapshot_ids": all_snapshot_ids,
                    "infrastructure_metrics": infra_metrics,
                    "summary": {
                        "total_services": len(service_ids),
                        "services_with_infrastructure": services_with_snapshots,
                        "services_without_infrastructure": services_without_snapshots,
                        "total_snapshots": len(all_snapshot_ids),
                        "metrics_requested": metrics,
                        "plugin": plugin,
                        "time_range": time_frame
                    }
                }

        except Exception as e:
            logger.error(f"Error in infrastructure_metrics_insights: {e}", exc_info=True)
            return {"error": f"Failed to get infrastructure metrics insights: {e!s}"}

    

    @with_header_auth(InfrastructureMetricsApi)
    async def _get_infrastructure_metrics(
        self,
        snapshot_ids: List[str],
        metrics: List[str],
        plugin: str,
        query: str,
        time_frame: Dict[str, int],
        rollup: int,
        ctx=None,
        api_client=None
    ) -> Any:
        """
        Get infrastructure metrics using InfrastructureMetricsApi.
        
        Args:
            snapshot_ids: List of snapshot IDs to get metrics for
            metrics: List of metrics to retrieve
            plugin: Plugin type
            query: Query string for filtering
            time_frame: Time range dictionary
            rollup: Rollup interval in seconds
            api_client: InfrastructureMetricsApi client (injected by decorator)
        
        Returns:
            Infrastructure metrics data or error dict
        """
        try:
            # Create request body
            request_body = {
                "metrics": metrics,
                "plugin": plugin,
                "rollup": rollup,
                "timeFrame": time_frame,
                "snapshotIds": snapshot_ids
            }
            
            # Add query only if provided
            if query:
                request_body["query"] = query
            
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
