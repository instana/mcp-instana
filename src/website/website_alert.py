"""
Website Alert MCP Tools Module

This module provides website alert-specific MCP tools for Instana monitoring.
Uses the api/event-settings endpoints.
"""

import logging
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from src.core.alert_config_utils import (
    parse_alert_config_response,
    parse_single_alert_config_response,
)
from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.event_settings_api import (
        EventSettingsApi,
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import mobile app alert configuration API", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class WebsiteAlertMCPTools(BaseInstanaClient):
    """Tools for website alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(EventSettingsApi)
    async def find_active_website_alert_configs(self,
                                                website_id: str,
                                                alert_ids: Optional[list] = None,
                                                ctx=None, api_client=None,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all Website Smart Alert Configurations for a specific website.

        This tool retrieves all Smart Alert Configurations pertaining to a specific website,
        optionally filtered by specific alert IDs. Configurations are sorted by creation date
        in descending order.

        Args:
            website_id: The ID of the specific Website (required)
            alert_ids: Optional list of Smart Alert Configuration IDs to filter results
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configurations or error information
        """
        try:
            logger.debug(f"find_active_website_alert_configs called with website_id={website_id}, alert_ids={alert_ids}")

            # Validate required parameters
            if not website_id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "website_id",
                            "issue": "website_id is required for find_active_website_alert_configs",
                            "hint": "Use resource_type='configuration', operation='get_all' to list available website IDs"
                        }
                    ],
                    "message": "Missing required parameter 'website_id'. Use configuration/get_all to list available website IDs."
                }

            # Call the find_active_website_alert_configs_without_preload_content method from the SDK
            logger.debug(f"Calling find_active_website_alert_configs_without_preload_content with website_id={website_id}, alert_ids={alert_ids}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.find_active_website_alert_configs_without_preload_content,
                    website_id=website_id,
                    alert_ids=alert_ids),
                ctx=ctx,
                operation_name="find_active_website_alert_configs",
                resource_type=resource_type, tool_name=tool_name,
            )

            return parse_alert_config_response(response, "website", website_id)

        except Exception as e:
            logger.error(f"Error in find_active_website_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to get active website alert configs: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def find_website_alert_config(self,
                                        id: str,
                                        valid_on: Optional[int] = None,
                                        ctx=None, api_client=None,
    resource_type: Optional[str] = None,
    tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets a specific Smart Alert Configuration for websites by ID. This may return a deleted Configuration.

        This tool retrieves a specific Smart Alert Configuration, filtered by id and valid_on timestamp.

        Args:
            id: ID of a specific Website Smart Alert Configuration to retrieve (required)
            valid_on: A Unix timestamp representing a specific time the Configuration was active. If no timestamp is provided, the latest active version will be retrieved.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"find_website_alert_config called with id={id}, valid_on={valid_on}")

            # Validate required parameters
            if not id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "id",
                            "issue": "id is required for find_website_alert_config",
                            "hint": "Use resource_type='alert', operation='find_active_website_alert_configs' to list available alert config IDs"
                        }
                    ],
                    "message": "Missing required parameter 'id'. Use alert/find_active_website_alert_configs to list available IDs."
                }

            # Call the find_website_alert_config_without_preload_content method from the SDK
            # Using _without_preload_content to avoid SDK deserialization issues
            logger.debug(f"Calling find_website_alert_config_without_preload_content with id={id}, valid_on={valid_on}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.find_website_alert_config_without_preload_content,
                    id=id,
                    valid_on=valid_on),
                ctx=ctx,
                operation_name="find_website_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            return parse_single_alert_config_response(response)

        except Exception as e:
            logger.error(f"Error in find_website_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to get website alert config: {e!s}"}
