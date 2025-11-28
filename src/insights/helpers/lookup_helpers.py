"""
Lookup Helper Functions for Instana Insights

Provides reusable helper class for looking up entity IDs by name.
"""
import logging
from datetime import datetime
from typing import Any, Dict

from src.core.utils import BaseInstanaClient, with_header_auth

# Import SDK classes
try:
    from instana_client.api.application_resources_api import ApplicationResourcesApi
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)


class LookupHelpers(BaseInstanaClient):
    """Helper class for looking up entity IDs by name."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the lookup helpers."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(ApplicationResourcesApi)
    async def lookup_application_id(
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
    async def lookup_service_id(
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
                name_filter=service_name
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

#  
