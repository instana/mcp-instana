"""
Custom Dashboard MCP Tools Module

This module provides custom dashboard-specific MCP tools for Instana monitoring.
Uses the api/custom-dashboard endpoints.
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

    # CRUD Operations Dispatcher - called by custom_dashboard_smart_router_tool.py
    async def execute_dashboard_operation(
        self,
        operation: str,
        dashboard_id: Optional[str] = None,
        custom_dashboard: Optional[Dict[str, Any]] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Execute Custom Dashboard CRUD operations.
        Called by the custom dashboard smart router tool.

        Args:
            operation: Operation to perform (get_all, get, create, update, delete, get_shareable_users, get_shareable_api_tokens)
            dashboard_id: Dashboard ID
            custom_dashboard: Dashboard configuration payload
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            if operation == "get_all":
                return await self.get_custom_dashboards(ctx=ctx)
            elif operation == "get":
                if not dashboard_id:
                    return {"error": "dashboard_id is required for 'get' operation"}
                return await self.get_custom_dashboard(dashboard_id=dashboard_id, ctx=ctx)
            elif operation == "create":
                if not custom_dashboard:
                    return {"error": "custom_dashboard is required for 'create' operation"}
                return await self.add_custom_dashboard(custom_dashboard=custom_dashboard, ctx=ctx)
            elif operation == "update":
                if not dashboard_id:
                    return {"error": "dashboard_id is required for 'update' operation"}
                if not custom_dashboard:
                    return {"error": "custom_dashboard is required for 'update' operation"}
                return await self.update_custom_dashboard(dashboard_id=dashboard_id, custom_dashboard=custom_dashboard, ctx=ctx)
            elif operation == "delete":
                if not dashboard_id:
                    return {"error": "dashboard_id is required for 'delete' operation"}
                return await self.delete_custom_dashboard(dashboard_id=dashboard_id, ctx=ctx)
            elif operation == "get_shareable_users":
                if not dashboard_id:
                    return {"error": "dashboard_id is required for 'get_shareable_users' operation"}
                return await self.get_shareable_users(dashboard_id=dashboard_id, ctx=ctx)
            elif operation == "get_shareable_api_tokens":
                if not dashboard_id:
                    return {"error": "dashboard_id is required for 'get_shareable_api_tokens' operation"}
                return await self.get_shareable_api_tokens(dashboard_id=dashboard_id, ctx=ctx)
            else:
                return {"error": f"Operation '{operation}' not supported"}

        except Exception as e:
            logger.error(f"Error executing {operation}: {e}", exc_info=True)
            return {"error": f"Error executing {operation}: {e!s}"}

    # Individual operation functions

    @with_header_auth(CustomDashboardsApi)
    async def get_custom_dashboards(self,
                                   ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all custom dashboards from Instana server.
        Uses api/custom-dashboard endpoint.
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

    @with_header_auth(CustomDashboardsApi)
    async def get_custom_dashboard(self,
                                  dashboard_id: str,
                                  ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get a specific custom dashboard by ID from Instana server.
        Uses api/custom-dashboard/{id} endpoint.
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

    @with_header_auth(CustomDashboardsApi)
    async def add_custom_dashboard(self,
                                  custom_dashboard: Dict[str, Any],
                                  ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Add a new custom dashboard to Instana server.
        Uses api/custom-dashboard POST endpoint.
        """
        try:
            if not custom_dashboard:
                return {"error": "Custom dashboard configuration is required for this operation"}

            logger.debug("Adding custom dashboard to Instana SDK")
            logger.debug(json.dumps(custom_dashboard, indent=2))

            # Add a temporary ID for validation (will be replaced by server)
            dashboard_config = custom_dashboard.copy()
            if 'id' not in dashboard_config:
                dashboard_config['id'] = ''  # Empty string as placeholder

            # Create the CustomDashboard object
            dashboard_obj = CustomDashboard(**dashboard_config)

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

    @with_header_auth(CustomDashboardsApi)
    async def update_custom_dashboard(self,
                                     dashboard_id: str,
                                     custom_dashboard: Dict[str, Any],
                                     ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Update an existing custom dashboard in Instana server.
        Uses api/custom-dashboard/{id} PUT endpoint.
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

    @with_header_auth(CustomDashboardsApi)
    async def delete_custom_dashboard(self,
                                     dashboard_id: str,
                                     ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Delete a custom dashboard from Instana server.
        Uses api/custom-dashboard/{id} DELETE endpoint.
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

    @with_header_auth(CustomDashboardsApi)
    async def get_shareable_users(self,
                                 dashboard_id: str,
                                 ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get shareable users for a custom dashboard from Instana server.
        Uses api/custom-dashboard/{id}/shareable-users endpoint.
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

    @with_header_auth(CustomDashboardsApi)
    async def get_shareable_api_tokens(self,
                                      dashboard_id: str,
                                      ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get shareable API tokens for a custom dashboard from Instana server.
        Uses api/custom-dashboard/{id}/shareable-api-tokens endpoint.
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
