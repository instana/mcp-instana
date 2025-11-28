"""
Service Helper Functions for Instana Insights

Provides reusable helper class for working with services and snapshot IDs.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.utils import BaseInstanaClient, with_header_auth

# Import SDK classes
try:
    from instana_client.api.application_metrics_api import ApplicationMetricsApi
    from instana_client.api.infrastructure_resources_api import InfrastructureResourcesApi
    from instana_client.models.get_services import GetServices
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)


class ServiceHelpers(BaseInstanaClient):
    """Helper class for working with services and snapshot IDs."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the service helpers."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(ApplicationMetricsApi)
    async def get_service_snapshot_ids(
        self,
        service_id: str,
        application_id: Optional[str],
        time_frame: Dict[str, int],
        service_name: Optional[str] = None,
        ctx=None,
        api_client=None
    ) -> Any:
        """
        Get snapshot IDs for a service using ApplicationMetricsApi.
        Falls back to infrastructure search if no snapshot IDs found.
        
        Args:
            service_id: Service ID to get snapshots for
            application_id: Optional application ID to filter by
            time_frame: Time range dictionary
            service_name: Optional service name for fallback search
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            List of snapshot IDs or error dict
        """
        try:
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
            
            # Create request body with serviceId filter
            request_body = {
                "metrics": [{"metric": "calls", "aggregation": "SUM"}],  # Dummy metric
                "timeFrame": formatted_time_frame,
                "serviceId": service_id
            }
            
            # Add applicationId if provided
            if application_id:
                request_body["applicationId"] = application_id
            
            logger.debug(f"Fetching snapshot IDs for service {service_id} (name: {service_name})")
            logger.debug(f"Request body: {request_body}")
            
            # Create GetServices model
            get_services = GetServices(**request_body)
            
            # Call SDK method with include_snapshot_ids=True
            result = api_client.get_services_metrics(
                fill_time_series=False,
                include_snapshot_ids=True,
                get_services=get_services
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            logger.debug(f"API returned {len(items)} items")
            
            # Log first item structure for debugging
            if items:
                logger.debug(f"First item keys: {list(items[0].keys())}")
            
            # Extract snapshot IDs from all items
            snapshot_ids = []
            for idx, item in enumerate(items):
                # The response structure has snapshotIds inside the "service" object
                service = item.get("service", {})
                item_snapshot_ids = service.get("snapshotIds", service.get("snapshot_ids", []))
                service_label = service.get("label", service.get("id", "unknown"))
                logger.debug(f"Item {idx} ({service_label}): found {len(item_snapshot_ids)} snapshot IDs")
                if item_snapshot_ids:
                    logger.debug(f"  Snapshot IDs: {item_snapshot_ids[:3]}...")  # Show first 3
                snapshot_ids.extend(item_snapshot_ids)
            
            # Remove duplicates
            snapshot_ids = list(set(snapshot_ids))
            
            logger.debug(f"Found {len(snapshot_ids)} unique snapshot IDs from service metrics API")
            
            # Fallback: If no snapshot IDs found and service_name provided, search infrastructure
            if not snapshot_ids and service_name:
                logger.debug(f"No snapshot IDs from service metrics, trying infrastructure search for service '{service_name}'")
                fallback_ids = await self._search_infrastructure_snapshots(service_name, time_frame)
                if isinstance(fallback_ids, list) and fallback_ids:
                    logger.debug(f"Found {len(fallback_ids)} snapshot IDs from infrastructure search")
                    snapshot_ids = fallback_ids
            
            return snapshot_ids
            
        except Exception as e:
            logger.error(f"Error getting service snapshot IDs: {e}", exc_info=True)
            return {"error": f"Failed to get snapshot IDs: {e!s}"}
    
    @with_header_auth(InfrastructureResourcesApi)
    async def _search_infrastructure_snapshots(
        self,
        service_name: str,
        time_frame: Dict[str, int],
        ctx=None,
        api_client=None
    ) -> List[str]:
        """
        Search for infrastructure snapshots by service name as fallback.
        Tries multiple plugin types (process, host, jvm, docker, kubernetes) to find snapshots.
        
        Args:
            service_name: Service name to search for
            time_frame: Time range dictionary
            api_client: InfrastructureResourcesApi client (injected by decorator)
        
        Returns:
            List of snapshot IDs found
        """
        try:
            # Convert time_frame
            if "from" in time_frame and "to" in time_frame:
                from_time = time_frame["from"]
                to_time = time_frame["to"]
                window_size = to_time - from_time
            elif "windowSize" in time_frame and "to" in time_frame:
                window_size = time_frame["windowSize"]
                to_time = time_frame["to"]
                from_time = to_time - window_size
            else:
                to_time = int(datetime.now().timestamp() * 1000)
                window_size = 60 * 60 * 1000
                from_time = to_time - window_size
            
            # Try multiple plugin types in order of likelihood
            plugin_types = ["process", "host", "jvm", "docker", "kubernetes"]
            all_snapshot_ids = []
            
            for plugin_type in plugin_types:
                # Search for snapshots with service name and plugin type
                query = f"entity.service.name:{service_name} AND entity.type:{plugin_type}"
                logger.debug(f"Searching infrastructure with query: {query}")
                
                result = api_client.get_snapshots(
                    query=query,
                    to=to_time,
                    window_size=window_size,
                    size=100,
                    offline=False
                )
                
                # Convert to dict
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                else:
                    result_dict = result
                
                items = result_dict.get("items", [])
                
                # Extract snapshot IDs
                for item in items:
                    snapshot_id = item.get("snapshotId")
                    if snapshot_id:
                        all_snapshot_ids.append(snapshot_id)
                
                if items:
                    logger.debug(f"Found {len(items)} snapshots with plugin type {plugin_type}")
            
            # Remove duplicates
            all_snapshot_ids = list(set(all_snapshot_ids))
            
            logger.debug(f"Infrastructure search found {len(all_snapshot_ids)} total snapshot IDs across all plugin types")
            return all_snapshot_ids
            
        except Exception as e:
            logger.error(f"Error searching infrastructure snapshots: {e}", exc_info=True)
            return []

    @with_header_auth(ApplicationMetricsApi)
    async def get_services_in_application(
        self,
        application_id: str,
        time_frame: Dict[str, int],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get all services (IDs and names) for an application using ApplicationMetricsApi.
        
        Args:
            application_id: Application ID to get services for
            time_frame: Time range dictionary
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary with service_ids list and services list (with id and name) or error dict
        """
        try:
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
            
            # Create request body with applicationId filter
            request_body = {
                "metrics": [{"metric": "calls", "aggregation": "SUM"}],  # Dummy metric
                "timeFrame": formatted_time_frame,
                "applicationId": application_id
            }
            
            logger.debug(f"Fetching services for application {application_id}")
            
            # Create GetServices model
            get_services = GetServices(**request_body)
            
            # Call SDK method
            result = api_client.get_services_metrics(
                fill_time_series=False,
                include_snapshot_ids=False,
                get_services=get_services
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            # Extract service IDs and full service info
            service_ids = []
            services = []
            for item in items:
                service = item.get("service", {})
                service_id = service.get("id")
                service_name = service.get("name")
                if service_id:
                    service_ids.append(service_id)
                    services.append({
                        "id": service_id,
                        "name": service_name or service_id  # Fallback to ID if no name
                    })
            
            logger.debug(f"Found {len(service_ids)} services in application")
            return {
                "service_ids": service_ids,
                "services": services
            }
            
        except Exception as e:
            logger.error(f"Error getting services in application: {e}", exc_info=True)
            return {"error": f"Failed to get services: {e!s}"}

    @with_header_auth(ApplicationMetricsApi)
    async def get_all_services(
        self,
        time_frame: Dict[str, int],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get all service IDs across all applications using ApplicationMetricsApi.
        
        Args:
            time_frame: Time range dictionary
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary with service_ids list or error dict
        """
        try:
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
            
            # Create request body without applicationId filter
            request_body = {
                "metrics": [{"metric": "calls", "aggregation": "SUM"}],  # Dummy metric
                "timeFrame": formatted_time_frame
            }
            
            logger.debug(f"Fetching all services")
            
            # Create GetServices model
            get_services = GetServices(**request_body)
            
            # Call SDK method
            result = api_client.get_services_metrics(
                fill_time_series=False,
                include_snapshot_ids=False,
                get_services=get_services
            )
            
            # Convert to dict
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            items = result_dict.get("items", [])
            
            # Extract service IDs
            service_ids = []
            for item in items:
                service = item.get("service", {})
                service_id = service.get("id")
                if service_id:
                    service_ids.append(service_id)
            
            logger.debug(f"Found {len(service_ids)} services total")
            return {"service_ids": service_ids}
            
        except Exception as e:
            logger.error(f"Error getting all services: {e}", exc_info=True)
            return {"error": f"Failed to get services: {e!s}"}

#  
