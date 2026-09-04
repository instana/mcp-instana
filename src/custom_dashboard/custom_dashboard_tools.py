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
    call_sdk_fn,
    register_as_tool,
    sdk_call_with_keepalive,
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

# SDK-verified enum values
_VALID_ACCESS_TYPES = {"READ", "READ_WRITE"}
_VALID_RELATION_TYPES = {"USER", "API_TOKEN", "ROLE", "TEAM", "GLOBAL"}


class CustomDashboardMCPTools(BaseInstanaClient):
    """Tools for custom dashboards in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Custom Dashboard MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @staticmethod
    def _validate_access_rule(rule: Any, idx: int, errors: list) -> None:
        """Validate a single accessRule item; append problems to errors."""
        if not isinstance(rule, dict):
            errors.append(f"'accessRules[{idx}]' must be an object.")
            return
        access_type = rule.get("accessType")
        if not access_type:
            errors.append(
                f"'accessRules[{idx}].accessType' is required. "
                f"Must be one of: {sorted(_VALID_ACCESS_TYPES)}"
            )
        elif access_type not in _VALID_ACCESS_TYPES:
            errors.append(
                f"'accessRules[{idx}].accessType' is invalid: {access_type!r}. "
                f"Must be one of: {sorted(_VALID_ACCESS_TYPES)}"
            )
        relation_type = rule.get("relationType")
        if not relation_type:
            errors.append(
                f"'accessRules[{idx}].relationType' is required. "
                f"Must be one of: {sorted(_VALID_RELATION_TYPES)}"
            )
        elif relation_type not in _VALID_RELATION_TYPES:
            errors.append(
                f"'accessRules[{idx}].relationType' is invalid: {relation_type!r}. "
                f"Must be one of: {sorted(_VALID_RELATION_TYPES)}"
            )

    @staticmethod
    def _validate_access_rules(access_rules: Any, errors: list) -> None:
        """Validate the accessRules list; append problems to errors."""
        if not isinstance(access_rules, list) or len(access_rules) == 0:
            errors.append(
                "'accessRules' must be a non-empty list (1-64 items). "
                'Example: [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}]'
            )
            return
        if len(access_rules) > 64:
            errors.append(f"'accessRules' exceeds maximum of 64 items (got {len(access_rules)}).")
        for idx, rule in enumerate(access_rules):
            CustomDashboardMCPTools._validate_access_rule(rule, idx, errors)

    @staticmethod
    def _validate_widget(widget: Any, idx: int, errors: list) -> None:
        """Validate a single widget item; append problems to errors."""
        if not isinstance(widget, dict):
            errors.append(f"'widgets[{idx}]' must be an object.")
            return
        w_id = widget.get("id")
        if w_id is None:
            errors.append(f"'widgets[{idx}].id' is required (string, max 64 chars).")
        elif len(str(w_id)) > 64:
            errors.append(f"'widgets[{idx}].id' exceeds max length of 64 chars.")
        if not widget.get("type") or not str(widget.get("type", "")).strip():
            errors.append(f"'widgets[{idx}].type' is required (non-empty string).")
        w_config = widget.get("config")
        if w_config is None:
            errors.append(f"'widgets[{idx}].config' is required (object).")
        elif not isinstance(w_config, dict):
            errors.append(f"'widgets[{idx}].config' must be an object, got: {type(w_config).__name__}")
        w_width = widget.get("width")
        if w_width is not None and (not isinstance(w_width, int) or not (1 <= w_width <= 12)):
            errors.append(f"'widgets[{idx}].width' must be an integer 1-12, got: {w_width!r}")
        w_x = widget.get("x")
        if w_x is not None and (not isinstance(w_x, int) or not (0 <= w_x <= 11)):
            errors.append(f"'widgets[{idx}].x' must be an integer 0-11, got: {w_x!r}")
        w_y = widget.get("y")
        if w_y is not None and (not isinstance(w_y, int) or w_y < 0):
            errors.append(f"'widgets[{idx}].y' must be a non-negative integer, got: {w_y!r}")
        w_height = widget.get("height")
        if w_height is not None and (not isinstance(w_height, int) or w_height < 1):
            errors.append(f"'widgets[{idx}].height' must be an integer ≥1, got: {w_height!r}")

    @staticmethod
    def _validate_widgets(widgets: Any, errors: list) -> None:
        """Validate the widgets list; append problems to errors."""
        if not isinstance(widgets, list):
            errors.append("'widgets' must be a list (0-128 items).")
            return
        if len(widgets) > 128:
            errors.append(f"'widgets' exceeds maximum of 128 items (got {len(widgets)}).")
        for idx, widget in enumerate(widgets):
            CustomDashboardMCPTools._validate_widget(widget, idx, errors)

    @staticmethod
    def _validate_dashboard_payload(custom_dashboard: dict, operation: str) -> Optional[Dict[str, Any]]:
        """Validate the custom_dashboard payload for create/update operations.

        Validated against SDK models CustomDashboard, AccessRule, Widget:

        CustomDashboard:
          - title       : str, min_length=1 (required)
          - accessRules : list[AccessRule], min_length=1, max_length=64 (required if supplied;
                          defaults are applied before this call so presence is guaranteed)
          - widgets     : list[Widget], max_length=128 (required if supplied; defaults to [])

        AccessRule (per item, if user supplies accessRules):
          - accessType   : "READ" | "READ_WRITE"
          - relationType : "USER" | "API_TOKEN" | "ROLE" | "TEAM" | "GLOBAL"

        Widget (per item, if user supplies widgets):
          - id     : str, max_length=64 (required)
          - type   : str, min_length=1 (required)
          - config : dict (required)
          - width  : int, 1-12 (optional)
          - x      : int, 0-11 (optional)
          - y      : int, ≥0 (optional)
          - height : int, ≥1 (optional)

        Returns None when valid, or the canonical elicitation dict on any failure.
        """
        errors: list = []

        title = custom_dashboard.get("title")
        if not title or not str(title).strip():
            errors.append(
                "'title' is required and must be a non-empty string."
                ' Example: "My Dashboard"'
            )

        access_rules = custom_dashboard.get("accessRules")
        if access_rules is not None:
            CustomDashboardMCPTools._validate_access_rules(access_rules, errors)

        widgets = custom_dashboard.get("widgets")
        if widgets is not None:
            CustomDashboardMCPTools._validate_widgets(widgets, errors)

        if not errors:
            return None

        n = len(errors)
        return {
            "elicitation_needed": True,
            "reason": f"{operation} custom dashboard has {n} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The {operation} custom dashboard request has {n} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    _VALID_OPERATIONS = frozenset({
        "get_all", "get", "create", "update", "delete",
        "get_shareable_users", "get_shareable_api_tokens",
    })

    @staticmethod
    def _preflight_dashboard_operation(
        operation: str,
        dashboard_id: Optional[str],
        custom_dashboard: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Validate required parameters for the given operation; return elicitation dict or None."""
        if operation not in CustomDashboardMCPTools._VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": f"Operation '{operation}' is not supported",
                "api_error": [f"operation: '{operation}' is not valid. Must be one of: {sorted(CustomDashboardMCPTools._VALID_OPERATIONS)}"],
                "message": f"operation '{operation}' is not supported. Valid operations: {sorted(CustomDashboardMCPTools._VALID_OPERATIONS)}",
            }

        errors: list = []
        if operation in ("get", "delete") and not dashboard_id:
            errors.append(f"dashboard_id is required — provide the dashboard UUID to {operation}")
        if operation == "update":
            if not dashboard_id:
                errors.append("dashboard_id is required — provide the dashboard UUID to update")
            if custom_dashboard is None:
                errors.append("custom_dashboard: required — provide the dashboard configuration dict with at least 'title'")
        if operation == "create" and custom_dashboard is None:
            errors.append("custom_dashboard: required — provide the dashboard configuration dict with at least 'title'")

        if not errors:
            return None
        return {
            "elicitation_needed": True,
            "reason": f"{operation} has {len(errors)} missing required parameter(s)",
            "api_error": errors,
            "message": (
                f"Cannot execute '{operation}': {len(errors)} required parameter(s) missing. "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    async def _dispatch_dashboard_operation(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route a validated dashboard operation to the appropriate handler."""
        dashboard_id = params.get("dashboard_id")
        custom_dashboard = params.get("custom_dashboard")
        logger.info(f"Routing to {operation} [resource_type={resource_type}, tool={tool_name}]")
        dispatch = {
            "get_all": lambda: self.get_custom_dashboards(
                query=params.get("query"),
                page_size=params.get("page_size"),
                page=params.get("page"),
                with_total_hits=params.get("with_total_hits"),
                ctx=ctx,
                resource_type=resource_type,
                tool_name=tool_name,
            ),
            "get": lambda: self.get_custom_dashboard(dashboard_id=dashboard_id, ctx=ctx, resource_type=resource_type, tool_name=tool_name),
            "create": lambda: self.add_custom_dashboard(custom_dashboard=custom_dashboard, ctx=ctx, resource_type=resource_type, tool_name=tool_name),
            "update": lambda: self.update_custom_dashboard(dashboard_id=dashboard_id, custom_dashboard=custom_dashboard, ctx=ctx, resource_type=resource_type, tool_name=tool_name),
            "delete": lambda: self.delete_custom_dashboard(dashboard_id=dashboard_id, ctx=ctx, resource_type=resource_type, tool_name=tool_name),
            "get_shareable_users": lambda: self.get_shareable_users(ctx=ctx, resource_type=resource_type, tool_name=tool_name),
            "get_shareable_api_tokens": lambda: self.get_shareable_api_tokens(ctx=ctx, resource_type=resource_type, tool_name=tool_name),
        }
        return await dispatch[operation]()

    # CRUD Operations Dispatcher - called by custom_dashboard_smart_router_tool.py
    async def execute_dashboard_operation(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
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
            resource_type: Resource type identifier for logging
            tool_name: Tool name identifier for logging

        Returns:
            Operation result dictionary
        """
        try:
            params = params or {}
            preflight = self._preflight_dashboard_operation(
                operation, params.get("dashboard_id"), params.get("custom_dashboard")
            )
            if preflight:
                return preflight
            return await self._dispatch_dashboard_operation(operation, params, ctx, resource_type=resource_type, tool_name=tool_name)

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
                                   ctx=None,
                                   api_client=None,
                                   resource_type: Optional[str] = None,
                                   tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all custom dashboards from Instana server.
        Uses api/custom-dashboard endpoint.

        Args:
            query: Search query to filter dashboards
            page_size: Number of dashboards per page
            page: Page number (1-indexed)
            with_total_hits: Include total count in response
            ctx: MCP context
            api_client: API client instance
            resource_type: Resource type identifier for logging
            tool_name: Tool name identifier for logging

        Returns:
            Dictionary containing dashboards list and metadata
        """
        try:
            logger.info(f"[{tool_name}] get_custom_dashboards [resource_type={resource_type}] query={query}, page_size={page_size}, page={page}")
            logger.debug(f"Getting custom dashboards from Instana SDK with query={query}, page_size={page_size}, page={page}, with_total_hits={with_total_hits}")

            # Use _without_preload_content to bypass Pydantic validation
            # This handles cases where API returns None for fields that expect strings
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_custom_dashboards_without_preload_content,
                    query=query,
                    page_size=page_size,
                    page=page,
                    with_total_hits=with_total_hits,
                ),
                ctx=ctx, operation_name="get_custom_dashboards",
                resource_type=resource_type, tool_name=tool_name,
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
                                  ctx=None, api_client=None,
                                  resource_type: Optional[str] = None,
                                  tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a specific custom dashboard by ID from Instana server.
        Uses api/custom-dashboard/{id} endpoint.
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.info(f"[{tool_name}] get_custom_dashboard [resource_type={resource_type}] dashboard_id={dashboard_id}")
            logger.debug(f"Getting custom dashboard {dashboard_id} from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: SDK expects 'custom_dashboard_id' not 'dashboard_id'
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_custom_dashboard_without_preload_content,
                    custom_dashboard_id=dashboard_id,
                ),
                ctx=ctx, operation_name="get_custom_dashboard",
                resource_type=resource_type, tool_name=tool_name,
            )

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
                                  ctx=None, api_client=None,
                                  resource_type: Optional[str] = None,
                                  tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a new custom dashboard to Instana server.
        Uses api/custom-dashboard POST endpoint.
        """
        try:
            if custom_dashboard is None:
                return {"error": "Custom dashboard configuration is required for this operation"}

            logger.info(f"[{tool_name}] add_custom_dashboard [resource_type={resource_type}]")
            logger.debug("Adding custom dashboard to Instana SDK")
            logger.debug(json.dumps(custom_dashboard, indent=2))

            # Pre-flight validation — collect ALL errors before touching the API
            validation_result = self._validate_dashboard_payload(custom_dashboard, "create")
            if validation_result is not None:
                return validation_result

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
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.add_custom_dashboard_without_preload_content,
                    custom_dashboard=dashboard_obj,
                ),
                ctx=ctx, operation_name="add_custom_dashboard",
                resource_type=resource_type, tool_name=tool_name,
            )

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
                                     ctx=None, api_client=None,
                                     resource_type: Optional[str] = None,
                                     tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing custom dashboard in Instana server.
        Uses api/custom-dashboard/{id} PUT endpoint.
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            if custom_dashboard is None:
                return {"error": "Custom dashboard configuration is required for this operation"}

            logger.info(f"[{tool_name}] update_custom_dashboard [resource_type={resource_type}] dashboard_id={dashboard_id}")
            logger.debug(f"Updating custom dashboard {dashboard_id} in Instana SDK")
            logger.debug(json.dumps(custom_dashboard, indent=2))

            # Pre-flight validation — collect ALL errors before touching the API
            validation_result = self._validate_dashboard_payload(custom_dashboard, "update")
            if validation_result is not None:
                return validation_result

            # Prepare dashboard config with required fields
            dashboard_config = custom_dashboard.copy()

            # Inject the dashboard ID into the body — the Instana PUT API
            # requires the 'id' field in the request body to match the URL path ID.
            # Without it the server accepts the request (HTTP 200) but ignores the body.
            dashboard_config['id'] = dashboard_id

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
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.update_custom_dashboard_without_preload_content,
                    custom_dashboard_id=dashboard_id,
                    custom_dashboard=dashboard_obj,
                ),
                ctx=ctx, operation_name="update_custom_dashboard",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Check HTTP status code
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # The PUT endpoint may return an empty or sparse body — re-fetch the full
            # record by ID so the caller always gets complete, non-null data back.
            logger.debug("Update succeeded; re-fetching dashboard to return full record")
            return await self.get_custom_dashboard(
                dashboard_id=dashboard_id,
                ctx=ctx,
                resource_type=resource_type,
                tool_name=tool_name,
            )

        except Exception as e:
            logger.error(f"Error in update_custom_dashboard: {e}", exc_info=True)
            return {"error": f"Failed to update custom dashboard: {e!s}"}

    @with_header_auth(CustomDashboardsApi)
    async def delete_custom_dashboard(self,
                                     dashboard_id: str,
                                     ctx=None, api_client=None,
                                     resource_type: Optional[str] = None,
                                     tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a custom dashboard from Instana server.
        Uses api/custom-dashboard/{id} DELETE endpoint.
        """
        try:
            if not dashboard_id:
                return {"error": "Dashboard ID is required for this operation"}

            logger.info(f"[{tool_name}] delete_custom_dashboard [resource_type={resource_type}] dashboard_id={dashboard_id}")
            logger.debug(f"Deleting custom dashboard {dashboard_id} from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: SDK expects 'custom_dashboard_id' not 'dashboard_id'
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.delete_custom_dashboard_without_preload_content,
                    custom_dashboard_id=dashboard_id,
                ),
                ctx=ctx, operation_name="delete_custom_dashboard",
                resource_type=resource_type, tool_name=tool_name,
            )

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
                                 ctx=None, api_client=None,
                                 resource_type: Optional[str] = None,
                                 tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all users that have access to shareable custom dashboards.
        Note: This returns ALL users globally, not for a specific dashboard.
        Uses api/custom-dashboard/shareable-users endpoint.
        """
        try:
            logger.info(f"[{tool_name}] get_shareable_users [resource_type={resource_type}]")
            logger.debug("Getting all shareable users from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: This API does not take a dashboard_id - it returns all shareable users globally
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_shareable_users_without_preload_content),
                ctx=ctx, operation_name="get_shareable_users",
                resource_type=resource_type, tool_name=tool_name,
            )

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
                                      ctx=None, api_client=None,
                                      resource_type: Optional[str] = None,
                                      tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all API tokens that have access to shareable custom dashboards.
        Note: This returns ALL API tokens globally, not for a specific dashboard.
        Uses api/custom-dashboard/shareable-api-tokens endpoint.
        """
        try:
            logger.info(f"[{tool_name}] get_shareable_api_tokens [resource_type={resource_type}]")
            logger.debug("Getting all shareable API tokens from Instana SDK")

            # Use _without_preload_content to bypass Pydantic validation
            # Note: This API does not take a dashboard_id - it returns all shareable tokens globally
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_shareable_api_tokens_without_preload_content),
                ctx=ctx, operation_name="get_shareable_api_tokens",
                resource_type=resource_type, tool_name=tool_name,
            )

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
