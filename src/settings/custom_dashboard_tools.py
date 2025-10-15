"""
Custom Dashboard MCP Tools Module

This module provides custom dashboard-specific MCP tools for Instana monitoring.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    register_as_tool,
    with_header_auth,
)

try:
    from instana_client.api.custom_dashboards_api import CustomDashboardsApi
    from instana_client.models.custom_dashboard import CustomDashboard

except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class CustomDashboardMCPTools(BaseInstanaClient):
    """Tools for custom dashboards in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Custom Dashboard MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Custom Dashboards",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def get_custom_dashboards(self,
                                   ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all custom dashboards from Instana server.
        This tool retrieves a list of all custom dashboards configured in your Instana environment.
        Use this tool to see what dashboards are available and their basic information.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing custom dashboards data or error information
        """
        try:
            logger.debug("Getting custom dashboards from Instana SDK")

            # Call the get_custom_dashboards method from the SDK
            result = api_client.get_custom_dashboards()

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            elif isinstance(result, list):
                # If it's a list, wrap it in a dictionary
                result_dict = {"items": result}
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            # Limit the response size
            if "items" in result_dict and isinstance(result_dict["items"], list):
                # Limit items to top 10
                items_list = result_dict["items"]
                original_count = len(items_list)
                if original_count > 10:
                    result_dict["items"] = items_list[:10]
                    logger.debug(f"Limited response items from {original_count} to 10")

            try:
                logger.debug(f"Result from get_custom_dashboards: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from get_custom_dashboards: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in get_custom_dashboards: {e}", exc_info=True)
            return {"error": f"Failed to get custom dashboards: {e!s}"}

    @register_as_tool(
        title="Get Custom Dashboard",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def get_custom_dashboard(self,
                                  dashboard_id: str,
                                  ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get a specific custom dashboard by ID from Instana server.
        This tool retrieves detailed information about a specific custom dashboard including
        its widgets, access rules, and configuration.

        Args:
            dashboard_id: The ID of the custom dashboard to retrieve
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing custom dashboard data or error information
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.debug(f"Getting custom dashboard {dashboard_id} from Instana SDK")

            # Call the get_custom_dashboard method from the SDK
            result = api_client.get_custom_dashboard(dashboard_id=dashboard_id)

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            try:
                logger.debug(f"Result from get_custom_dashboard: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from get_custom_dashboard: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in get_custom_dashboard: {e}", exc_info=True)
            return {"error": f"Failed to get custom dashboard: {e!s}"}

    @register_as_tool(
        title="Add Custom Dashboard",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def add_custom_dashboard(self,
                                  custom_dashboard: Dict[str, Any],
                                  ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Add a new custom dashboard to Instana server.
        This tool creates a new custom dashboard with the specified configuration,
        widgets, and access rules.

        Args:
            custom_dashboard: Dictionary containing dashboard configuration including:
                - title: Dashboard title
                - widgets: List of widget configurations
                - accessRules: List of access rules
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the created custom dashboard data or error information
        """
        try:
            if not custom_dashboard:
                return {"error": "Custom dashboard configuration is required for this operation"}

            logger.debug("Adding custom dashboard to Instana SDK")
            logger.debug(json.dumps(custom_dashboard, indent=2))

            # Create the CustomDashboard object
            dashboard_obj = CustomDashboard(**custom_dashboard)

            # Call the add_custom_dashboard method from the SDK
            result = api_client.add_custom_dashboard(custom_dashboard=dashboard_obj)

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            try:
                logger.debug(f"Result from add_custom_dashboard: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from add_custom_dashboard: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in add_custom_dashboard: {e}", exc_info=True)
            return {"error": f"Failed to add custom dashboard: {e!s}"}

    @register_as_tool(
        title="Update Custom Dashboard",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def update_custom_dashboard(self,
                                     dashboard_id: str,
                                     custom_dashboard: Dict[str, Any],
                                     ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Update an existing custom dashboard in Instana server.
        This tool updates a custom dashboard with new configuration, widgets, or access rules.

        Args:
            dashboard_id: The ID of the custom dashboard to update
            custom_dashboard: Dictionary containing updated dashboard configuration
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the updated custom dashboard data or error information
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            if not custom_dashboard:
                return {"error": "Custom dashboard configuration is required for this operation"}

            logger.debug(f"Updating custom dashboard {dashboard_id} in Instana SDK")
            logger.debug(json.dumps(custom_dashboard, indent=2))

            # Create the CustomDashboard object
            dashboard_obj = CustomDashboard(**custom_dashboard)

            # Call the update_custom_dashboard method from the SDK
            result = api_client.update_custom_dashboard(
                dashboard_id=dashboard_id,
                custom_dashboard=dashboard_obj
            )

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            try:
                logger.debug(f"Result from update_custom_dashboard: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from update_custom_dashboard: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in update_custom_dashboard: {e}", exc_info=True)
            return {"error": f"Failed to update custom dashboard: {e!s}"}

    @register_as_tool(
        title="Delete Custom Dashboard",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
    @with_header_auth(CustomDashboardsApi)
    async def delete_custom_dashboard(self,
                                     dashboard_id: str,
                                     ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Delete a custom dashboard from Instana server.
        This tool removes a custom dashboard from your Instana environment.

        Args:
            dashboard_id: The ID of the custom dashboard to delete
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing deletion status or error information
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.debug(f"Deleting custom dashboard {dashboard_id} from Instana SDK")

            # Call the delete_custom_dashboard method from the SDK
            result = api_client.delete_custom_dashboard(dashboard_id=dashboard_id)

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            try:
                logger.debug(f"Result from delete_custom_dashboard: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from delete_custom_dashboard: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in delete_custom_dashboard: {e}", exc_info=True)
            return {"error": f"Failed to delete custom dashboard: {e!s}"}

    @register_as_tool(
        title="Get Shareable Users",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def get_shareable_users(self,
                                 dashboard_id: str,
                                 ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get shareable users for a custom dashboard from Instana server.
        This tool retrieves the list of users who can be granted access to a specific custom dashboard.

        Args:
            dashboard_id: The ID of the custom dashboard
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing shareable users data or error information
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.debug(f"Getting shareable users for dashboard {dashboard_id} from Instana SDK")

            # Call the get_shareable_users method from the SDK
            result = api_client.get_shareable_users(dashboard_id=dashboard_id)

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            elif isinstance(result, list):
                # If it's a list, wrap it in a dictionary
                result_dict = {"items": result}
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            # Limit the response size
            if "items" in result_dict and isinstance(result_dict["items"], list):
                # Limit items to top 20
                items_list = result_dict["items"]
                original_count = len(items_list)
                if original_count > 20:
                    result_dict["items"] = items_list[:20]
                    logger.debug(f"Limited response items from {original_count} to 20")

            try:
                logger.debug(f"Result from get_shareable_users: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from get_shareable_users: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in get_shareable_users: {e}", exc_info=True)
            return {"error": f"Failed to get shareable users: {e!s}"}

    @register_as_tool(
        title="Get Shareable API Tokens",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(CustomDashboardsApi)
    async def get_shareable_api_tokens(self,
                                      dashboard_id: str,
                                      ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get shareable API tokens for a custom dashboard from Instana server.
        This tool retrieves the list of API tokens that can be used to access a specific custom dashboard.

        Args:
            dashboard_id: The ID of the custom dashboard
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing shareable API tokens data or error information
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.debug(f"Getting shareable API tokens for dashboard {dashboard_id} from Instana SDK")

            # Call the get_shareable_api_tokens method from the SDK
            result = api_client.get_shareable_api_tokens(dashboard_id=dashboard_id)

            # Convert the result to a dictionary
            result_dict: Dict[str, Any] = {}

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            elif isinstance(result, list):
                # If it's a list, wrap it in a dictionary
                result_dict = {"items": result}
            else:
                # For any other type, convert to string and wrap
                result_dict = {"result": str(result)}

            # Limit the response size
            if "items" in result_dict and isinstance(result_dict["items"], list):
                # Limit items to top 10
                items_list = result_dict["items"]
                original_count = len(items_list)
                if original_count > 10:
                    result_dict["items"] = items_list[:10]
                    logger.debug(f"Limited response items from {original_count} to 10")

            try:
                logger.debug(f"Result from get_shareable_api_tokens: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from get_shareable_api_tokens: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in get_shareable_api_tokens: {e}", exc_info=True)
            return {"error": f"Failed to get shareable API tokens: {e!s}"}
