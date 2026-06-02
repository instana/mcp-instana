"""
Mobile App Alert MCP Tools Module

This module provides mobile app alert-specific MCP tools for Instana monitoring.
Uses the api/event-settings endpoints.
"""

import logging
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from src.core.alert_config_utils import (
    parse_alert_config_response,
    parse_single_alert_config_response,
)
from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
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

class MobileAppAlertMCPTools(BaseInstanaClient):
    """Tools for mobile app alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Mobile App Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(EventSettingsApi)
    async def find_active_mobile_app_alert_configs(self,
                                                   mobile_app_id: str,
                                                   alert_ids: Optional[list] = None,
                                                   ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all Mobile Smart Alert Configurations for a specific mobile app.

        This tool retrieves all Smart Alert Configurations pertaining to a specific mobile app,
        optionally filtered by specific alert IDs. Configurations are sorted by creation date
        in descending order.

        Args:
            mobile_app_id: The ID of the specific Mobile Application (required)
            alert_ids: Optional list of Smart Alert Configuration IDs to filter results
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configurations or error information
        """
        try:
            logger.debug(f"find_active_mobile_app_alert_configs called with mobile_app_id={mobile_app_id}, alert_ids={alert_ids}")

            # Validate required parameters
            if not mobile_app_id:
                return {"error": "mobile_app_id is required"}

            # Call the find_active_mobile_app_alert_configs_without_preload_content method from the SDK
            logger.debug(f"Calling find_active_mobile_app_alert_configs_without_preload_content with mobile_app_id={mobile_app_id}, alert_ids={alert_ids}")
            response = api_client.find_active_mobile_app_alert_configs_without_preload_content(
                mobile_app_id=mobile_app_id,
                alert_ids=alert_ids
            )

            return parse_alert_config_response(response, "mobile app", mobile_app_id)

        except Exception as e:
            logger.error(f"Error in find_active_mobile_app_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to get active mobile app alert configs: {e!s}"}

    @with_header_auth(EventSettingsApi)
    async def find_mobile_app_alert_config(self,
                                           id: str,
                                           valid_on: Optional[int] = None,
                                           ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Gets a specific Smart Alert Configuration for mobile apps by ID. This may return a deleted Configuration.

        This tool retrieves a specific Smart Alert Configuration, filtered by id and valid_on timestamp.

        Args:
            id: ID of a specific Mobile Smart Alert Configuration to retrieve (required)
            valid_on: A Unix timestamp representing a specific time the Configuration was active. If no timestamp is provided, the latest active version will be retrieved.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"find_mobile_app_alert_config called with id={id}, valid_on={valid_on}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the find_mobile_app_alert_config_without_preload_content method from the SDK
            # Using _without_preload_content to avoid SDK deserialization issues
            logger.debug(f"Calling find_mobile_app_alert_config_without_preload_content with id={id}, valid_on={valid_on}")
            response = api_client.find_mobile_app_alert_config_without_preload_content(
                id=id,
                valid_on=valid_on
            )

            return parse_single_alert_config_response(response)

        except Exception as e:
            logger.error(f"Error in find_mobile_app_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app alert config: {e!s}"}
