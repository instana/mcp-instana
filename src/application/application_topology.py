"""
Application Topology MCP Tools Module

This module provides application topology-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool
from src.prompts import mcp

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

    @register_as_tool(
        title="Get Application Topology",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

            # Call the API with raw JSON response to avoid Pydantic validation issues
            # Note: The SDK expects parameters in camelCase, but we use snake_case in Python
            # The SDK will handle the conversion
            result = self.topology_api.get_services_map_without_preload_content(
                window_size=window_size,
                to=to_timestamp,
                application_id=application_id,
                application_boundary_scope=application_boundary_scope
            )

            # Parse the JSON response manually
            import json
            try:
                # The result from get_services_map_without_preload_content is a response object
                # We need to read the response data and parse it as JSON
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved service topology data")
                return result_dict
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

        except Exception as e:
            logger.error(f"Error in get_application_topology: {e}", exc_info=True)
            return {"error": f"Failed to get application topology: {e!s}"}
