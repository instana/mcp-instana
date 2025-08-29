"""
Application Topology MCP Tools Module

This module provides application topology-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.utils import BaseInstanaClient, register_as_tool

try:
    from instana_client.api.application_topology_api import (
        ApplicationTopologyApi,
    )
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration
except ImportError as e:
    import logging
    import traceback
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}")
    traceback.print_exc()
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationTopologyMCPTools(BaseInstanaClient):
    """Tools for application topology in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Topology MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

        try:

            # Configure the API client with the correct base URL and authentication
            configuration = Configuration()
            configuration.host = base_url
            configuration.api_key['ApiKeyAuth'] = read_token
            configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

            # Create an API client with this configuration
            api_client = ApiClient(configuration=configuration)

            # Initialize the Instana SDK's ApplicationTopologyMCPTools with our configured client
            self.topology_api = ApplicationTopologyApi(api_client=api_client)

        except Exception as e:
            logger.error(f"Error initializing ApplicationTopologyMCPTools: {e}", exc_info=True)
            raise

    @register_as_tool
    async def get_application_topology(self,
                              window_size: Optional[int] = None,
                              to_timestamp: Optional[int] = None,
                              application_id: Optional[str] = None,
                              application_boundary_scope: Optional[str] = None,
                              ctx = None) -> Dict[str, Any]:
        """
        Get the service topology from Instana Server.
        This tool retrieves services and connections (call paths) between them for calls in the scope given by the parameters.

        Args:
            window_size: Size of time window in milliseconds
            to_timestamp: Timestamp since Unix Epoch in milliseconds of the end of the time window
            application_id: Filter by application ID
            application_boundary_scope: Filter by application scope, i.e., INBOUND or ALL. The default value is INBOUND.
            ctx: Context information

        Returns:
            A dictionary containing the service topology data
        """

        try:
            logger.debug("Fetching service topology data")

            # Set default values if not provided
            if not to_timestamp:
                to_timestamp = int(datetime.now().timestamp() * 1000)

            if not window_size:
                window_size = 3600000  # Default to 1 hour in milliseconds

            # Call the API
            # Note: The SDK expects parameters in camelCase, but we use snake_case in Python
            # The SDK will handle the conversion
            result = self.topology_api.get_services_map(
                window_size=window_size,
                to=to_timestamp,
                application_id=application_id,
                application_boundary_scope=application_boundary_scope
            )

            # Ensure we always return a dictionary
            if hasattr(result, "to_dict"):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                # Convert to dictionary using __dict__ or as a fallback, create a new dict with string representation
                result_dict = getattr(result, "__dict__", {"data": str(result)})

            logger.debug("Successfully retrieved service topology data")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_application_topology: {e}", exc_info=True)
            return {"error": f"Failed to get application topology: {e!s}"}
