"""
Custom Dashboard MCP Tools Module

This module provides custom dashboard-specific MCP tools for Instana monitoring.
Uses the api/custom-dashboard endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context
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
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Execute Custom Dashboard CRUD operations.
        Called by the custom dashboard smart router tool.

        Args:
            operation: Operation to perform (get_all, get, create, update, delete, get_shareable_users, get_shareable_api_tokens)
            params: Dictionary containing operation-specific parameters:
                - dashboard_id: Dashboard ID (for get, update, delete, get_shareable_users, get_shareable_api_tokens)
                - custom_dashboard: Dashboard configuration payload (for create, update)
                - query: Search query for filtering dashboards (for get_all)
                - page_size: Number of items per page (for get_all)
                - page: Page number (for get_all)
                - with_total_hits: Include total count (for get_all)
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            # Initialize params if not provided
            if params is None:
                params = {}

            # Extract parameters based on operation
            dashboard_id = params.get("dashboard_id")
            custom_dashboard = params.get("custom_dashboard")

            if operation == "get_all":
                # Extract get_all specific parameters
                query = params.get("query")
                page_size = params.get("page_size")
                page = params.get("page")
                with_total_hits = params.get("with_total_hits")

                return await self.get_custom_dashboards(
                    query=query,
                    page_size=page_size,
                    page=page,
                    with_total_hits=with_total_hits,
                    ctx=ctx
                )
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
                # Note: This operation returns ALL shareable users globally, not for a specific dashboard
                return await self.get_shareable_users(ctx=ctx)
            elif operation == "get_shareable_api_tokens":
                # Note: This operation returns ALL shareable API tokens globally, not for a specific dashboard
                return await self.get_shareable_api_tokens(ctx=ctx)
            else:
                return {"error": f"Operation '{operation}' not supported"}

        except Exception as e:
            logger.error(f"Error executing {operation}: {e}", exc_info=True)
            return {"error": f"Error executing {operation}: {e!s}"}

    # Individual operation functions

    @with_header_auth(CustomDashboardsApi)
    async def get_custom_dashboards(self,
                                   query: Optional[str] = None,
                                   page_size: Optional[int] = None,
                                   page: Optional[int] = None,
                                   with_total_hits: Optional[bool] = None,
                                   ctx: Optional[Context] = None,
                                   api_client: Any = None) -> Dict[str, Any]:
        """
        Get all custom dashboards from Instana server.
        Uses api/custom-dashboard endpoint.

        Args:
            query: Search query to filter dashboards
            page_size: Number of dashboards per page
            page: Page number (0-indexed)
            with_total_hits: Include total count in response
            ctx: MCP context
            api_client: API client instance

        Returns:
            Dictionary containing dashboards list and metadata
        """
        try:
            logger.debug(f"Getting custom dashboards from Instana SDK with query={query}, page_size={page_size}, page={page}, with_total_hits={with_total_hits}")

            # Use _without_preload_content to bypass Pydantic validation
            # This handles cases where API returns None for fields that expect strings
            result = api_client.get_custom_dashboards_without_preload_content(
                query=query,
                page_size=page_size,
                page=page,
                with_total_hits=with_total_hits
            )

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Parse the JSON response manually
            response_text = result.data.decode('utf-8')
            dashboards_list = json.loads(response_text)

            # Build result dictionary
            result_dict = {
                "items": dashboards_list if isinstance(dashboards_list, list) else [],
                "count": len(dashboards_list) if isinstance(dashboards_list, list) else 0
            }

            # Add pagination info if provided
            if page is not None:
                result_dict["page"] = page
            if page_size is not None:
                result_dict["page_size"] = page_size

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
                                  ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get a specific custom dashboard by ID from Instana server.
        Uses api/custom-dashboard/{id} endpoint.
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.debug(f"Getting custom dashboard {dashboard_id} from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: SDK expects 'custom_dashboard_id' not 'dashboard_id'
            result = api_client.get_custom_dashboard_without_preload_content(custom_dashboard_id=dashboard_id)

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Parse the JSON response manually
            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

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
                                  ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Add a new custom dashboard to Instana server.
        Uses api/custom-dashboard POST endpoint.
        """
        try:
            if not custom_dashboard:
                return {"error": "Custom dashboard configuration is required for this operation"}

            logger.debug("Adding custom dashboard to Instana SDK")
            logger.debug(json.dumps(custom_dashboard, indent=2))

            # Prepare dashboard config with required fields
            dashboard_config = custom_dashboard.copy()

            # Add temporary ID for validation (will be replaced by server)
            if 'id' not in dashboard_config:
                dashboard_config['id'] = ''

            # Ensure widgets field exists (required by model)
            if 'widgets' not in dashboard_config:
                dashboard_config['widgets'] = []
                logger.debug("Added empty widgets array (required field)")

            # Ensure accessRules field exists (required by model)
            if 'accessRules' not in dashboard_config:
                dashboard_config['accessRules'] = [
                    {"accessType": "READ_WRITE", "relationType": "GLOBAL", "relatedId": None}
                ]
                logger.debug("Added default global READ_WRITE access rule (required field)")

            # Create the CustomDashboard object
            dashboard_obj = CustomDashboard(**dashboard_config)

            # Use _without_preload_content to bypass Pydantic validation on response
            result = api_client.add_custom_dashboard_without_preload_content(custom_dashboard=dashboard_obj)

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Parse the JSON response manually
            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

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
                                     ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
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

            # Prepare dashboard config with required fields
            dashboard_config = custom_dashboard.copy()

            # Ensure widgets field exists (required by model)
            if 'widgets' not in dashboard_config:
                dashboard_config['widgets'] = []
                logger.debug("Added empty widgets array (required field)")

            # Ensure accessRules field exists (required by model)
            if 'accessRules' not in dashboard_config:
                dashboard_config['accessRules'] = [
                    {"accessType": "READ_WRITE", "relationType": "GLOBAL", "relatedId": None}
                ]
                logger.debug("Added default global READ_WRITE access rule (required field)")

            # Create the CustomDashboard object
            dashboard_obj = CustomDashboard(**dashboard_config)

            # Use _without_preload_content to bypass Pydantic validation on response
            # Note: SDK expects 'custom_dashboard_id' not 'dashboard_id'
            result = api_client.update_custom_dashboard_without_preload_content(
                custom_dashboard_id=dashboard_id,
                custom_dashboard=dashboard_obj
            )

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Parse the JSON response manually
            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

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
                                     ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Delete a custom dashboard from Instana server.
        Uses api/custom-dashboard/{id} DELETE endpoint.
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.debug(f"Deleting custom dashboard {dashboard_id} from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: SDK expects 'custom_dashboard_id' not 'dashboard_id'
            result = api_client.delete_custom_dashboard_without_preload_content(custom_dashboard_id=dashboard_id)

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # For DELETE operations, typically returns empty response or success message
            # Parse response if there's content
            if result.data:
                response_text = result.data.decode('utf-8')
                if response_text.strip():
                    result_dict = json.loads(response_text)
                else:
                    result_dict = {"success": True, "message": f"Dashboard {dashboard_id} deleted"}
            else:
                result_dict = {"success": True, "message": f"Dashboard {dashboard_id} deleted"}

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
                                 dashboard_id: Optional[str] = None,
                                 ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get all users that have access to shareable custom dashboards.
        Note: This returns ALL users globally, not for a specific dashboard.
        Uses api/custom-dashboard/shareable-users endpoint.
        """
        try:
            logger.debug("Getting all shareable users from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: This API does not take a dashboard_id - it returns all shareable users globally
            result = api_client.get_shareable_users_without_preload_content()

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Parse the JSON response manually
            response_text = result.data.decode('utf-8')
            users_list = json.loads(response_text)

            # Limit the response size
            original_count = len(users_list) if isinstance(users_list, list) else 0
            if isinstance(users_list, list) and original_count > 20:
                users_list = users_list[:20]
                logger.debug(f"Limited response items from {original_count} to 20")

            result_dict = {"items": users_list, "count": len(users_list)}

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
                                      dashboard_id: Optional[str] = None,
                                      ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get all API tokens that have access to shareable custom dashboards.
        Note: This returns ALL API tokens globally, not for a specific dashboard.
        Uses api/custom-dashboard/shareable-api-tokens endpoint.
        """
        try:
            logger.debug("Getting all shareable API tokens from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: This API does not take a dashboard_id - it returns all shareable tokens globally
            result = api_client.get_shareable_api_tokens_without_preload_content()

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Parse the JSON response manually
            response_text = result.data.decode('utf-8')
            tokens_list = json.loads(response_text)

            # Limit the response size
            original_count = len(tokens_list) if isinstance(tokens_list, list) else 0
            if isinstance(tokens_list, list) and original_count > 10:
                tokens_list = tokens_list[:10]
                logger.debug(f"Limited response items from {original_count} to 10")

            result_dict = {"items": tokens_list, "count": len(tokens_list)}

            try:
                logger.debug(f"Result from get_shareable_api_tokens: {json.dumps(result_dict, indent=2)}")
            except TypeError:
                logger.debug(f"Result from get_shareable_api_tokens: {result_dict} (not JSON serializable)")

            return result_dict

        except Exception as e:
            logger.error(f"Error in get_shareable_api_tokens: {e}", exc_info=True)
            return {"error": f"Failed to get shareable API tokens: {e!s}"}
