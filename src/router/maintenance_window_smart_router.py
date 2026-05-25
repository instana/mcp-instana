"""
Maintenance Window Smart Router Tool

This module provides a unified MCP tool that routes maintenance window queries
to the appropriate maintenance window management tools.
"""

import json
import logging
from typing import Any, Dict, Optional

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

# Resource type constants
RESOURCE_TYPE_WINDOW = "window"
RESOURCE_TYPE_TEMPLATES = "templates"

# Valid resource types
VALID_RESOURCE_TYPES = [RESOURCE_TYPE_WINDOW, RESOURCE_TYPE_TEMPLATES]

# Operation constants — window resource type
OP_CREATE = "create"
OP_MODIFY = "modify"
OP_CLOSE = "close"
OP_LIST_ACTIVE = "list_active"
OP_LIST_SCHEDULED = "list_scheduled"
OP_LIST_ALL = "list_all"
OP_LIST_EXPIRED = "list_expired"
OP_BULK_CREATE = "bulk_create"
OP_VALIDATE = "validate"

# Operation constants — templates resource type
OP_GET = "get"

# Valid operations per resource type
WINDOW_VALID_OPERATIONS = [
    OP_CREATE,
    OP_MODIFY,
    OP_CLOSE,
    OP_LIST_ACTIVE,
    OP_LIST_SCHEDULED,
    OP_LIST_ALL,
    OP_LIST_EXPIRED,
    OP_BULK_CREATE,
    OP_VALIDATE,
]

TEMPLATES_VALID_OPERATIONS = [OP_GET]

# Parameter name constants
PARAM_APPLICATION_ID = "application_id"
PARAM_APPLICATION_IDS = "application_ids"
PARAM_IMAP_CODE = "imap_code"
PARAM_IMAP_CODES = "imap_codes"
PARAM_WINDOW_ID = "window_id"
PARAM_START_TIME = "start_time"
PARAM_END_TIME = "end_time"
PARAM_DURATION_MINUTES = "duration_minutes"
PARAM_DURATION_HOURS = "duration_hours"
PARAM_DURATION_DAYS = "duration_days"
PARAM_REASON = "reason"
PARAM_TEMPLATE = "template"
PARAM_CHANGE_REQUEST_ID = "change_request_id"
PARAM_AFFECTED_SERVICES = "affected_services"
PARAM_NOTIFICATION_CHANNELS = "notification_channels"
PARAM_COMPLETION_NOTES = "completion_notes"
PARAM_USE_TAG_FILTER_EXPRESSION = "use_tag_filter_expression"
PARAM_TAG_NAME = "tag_name"
PARAM_RRULE = "rrule"
PARAM_UNTIL_DATE = "until_date"


class MaintenanceWindowSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for maintenance window operations.
    Routes queries to Maintenance Window Management tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Maintenance Window Smart Router MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.maintenance_window.maintenance_window_tool import (
            MaintenanceWindowMCPTools,
        )

        # Initialize the maintenance window client
        self.maintenance_window_client = MaintenanceWindowMCPTools(read_token, base_url)

        logger.info("Maintenance Window Smart Router initialized")

    @register_as_tool(
        title="Manage Instana Maintenance Windows",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    async def manage_maintenance_windows(
        self,
        resource_type: Optional[str] = "window",
        operation: Optional[str] = "list_scheduled",
        # ALL PARAMETERS ARE FLAT STRINGS for WatsonX Orchestrate compatibility
        application_id: Optional[str] = None,
        application_ids: Optional[str] = None,
        imap_code: Optional[str] = None,
        imap_codes: Optional[str] = None,
        window_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        duration_minutes: Optional[str] = None,
        duration_hours: Optional[str] = None,
        duration_days: Optional[str] = None,
        reason: Optional[str] = None,
        template: Optional[str] = None,
        change_request_id: Optional[str] = None,
        affected_services: Optional[str] = None,
        notification_channels: Optional[str] = None,
        completion_notes: Optional[str] = None,
        use_tag_filter_expression: Optional[str] = None,
        tag_name: Optional[str] = None,
        rrule: Optional[str] = None,
        until_date: Optional[str] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Unified Instana maintenance window manager for lifecycle management.

        IMPORTANT FOR WATSONX ORCHESTRATE ROUTING:
        - Use this tool for maintenance window questions such as:
          * "Show me scheduled maintenance windows"
          * "List active maintenance windows"
          * "What maintenance windows are planned?"
          * "Create a maintenance window for EAL-012471"
          * "Close maintenance window mw-789"
          * "Show all maintenance windows"
          * "Are there any upcoming maintenance windows?"
          * "Can you give me scheduled maintenance windows applications?"
        - For listing scheduled windows: resource_type="window", operation="list_scheduled"
        - For listing active windows: resource_type="window", operation="list_active"
        - For listing all windows: resource_type="window", operation="list_all"
        - For creating windows: resource_type="window", operation="create"

        ALL PARAMETERS ARE FLAT STRINGS - No nested objects required!

        Resource Types:
        - "window": Create, modify, close, and list maintenance windows
        - "templates": Retrieve available maintenance window templates

        WINDOW (resource_type="window"):
            operations: create, modify, close, list_active, list_scheduled, list_all, list_expired, bulk_create, validate

            create - Create a new maintenance window
                Required: imap_code OR application_id, start_time
                Optional: end_time, duration_minutes, duration_hours, duration_days,
                          reason, template, change_request_id, affected_services,
                          notification_channels, use_tag_filter_expression, tag_name,
                          rrule, until_date

            modify - Modify an existing maintenance window
                Required: window_id
                Optional: end_time, duration_minutes, reason, rrule, until_date

            close - Close and document a maintenance window
                Required: window_id
                Optional: completion_notes

            list_active - List all currently active maintenance windows
                Optional: imap_code, application_id (filter by application)

            list_scheduled - List all upcoming scheduled maintenance windows
                Optional: imap_code, application_id

            list_all - List all maintenance windows (active, scheduled, and expired)
                Optional: imap_code, application_id

            list_expired - List all expired/completed maintenance windows
                Optional: imap_code, application_id

            bulk_create - Create maintenance windows for multiple applications at once
                Required: application_ids (JSON array string) OR imap_codes (JSON array string), start_time
                Optional: duration_minutes, duration_hours, duration_days, reason, template,
                          change_request_id, use_tag_filter_expression, tag_name

            validate - Validate maintenance window parameters without creating
                Required: imap_code OR application_id, start_time
                Optional: duration_minutes, template

        TEMPLATES (resource_type="templates"):
            operations: get

            get - Retrieve all available maintenance window templates
                No parameters required

        Args:
            resource_type: (OPTIONAL) "window" or "templates". Defaults to "window". Do NOT ask the user for this — use "window" unless the user explicitly asks for templates.
            operation: (OPTIONAL) Operation to perform. Defaults to "list_scheduled". Do NOT ask the user for this — infer it from context.
            application_id: Single application ID (legacy support, treated as IMAP code)
            application_ids: JSON array string of application IDs for bulk operations (e.g., '["id1","id2"]')
            imap_code: Single IMAP code (e.g., "EAL-012512", "ORZ-000012", "MUR-123456")
            imap_codes: JSON array string of IMAP codes for bulk operations (e.g., '["EAL-012512","ORZ-000012"]')
            window_id: Existing maintenance window ID (required for modify/close)
            start_time: Start time as Unix timestamp ms, ISO string, or natural language (e.g., "in 2 hours", "tomorrow at 10am")
            end_time: End time as Unix timestamp ms, ISO string, or natural language
            duration_minutes: Duration in minutes as string (e.g., "120")
            duration_hours: Duration in hours as string (e.g., "2")
            duration_days: Duration in days as string (e.g., "1")
            reason: Reason/description for the maintenance window
            template: Predefined template name ("deployment", "database_migration", "infrastructure_upgrade", "emergency", "routine")
            change_request_id: ServiceNow change request ID (e.g., "CHG0012345")
            affected_services: JSON array string of affected service names (e.g., '["payment-api","order-service"]')
            notification_channels: JSON array string of notification channels (e.g., '["slack","email"]')
            completion_notes: Notes to record when closing a window
            use_tag_filter_expression: "true" or "false" — use tag filter expression format
            tag_name: Tag name for filter expression (e.g., "environment:production")
            rrule: Recurrence rule string (RFC 5545, e.g., "FREQ=DAILY;INTERVAL=1")
            until_date: End date for recurring windows as ISO string (e.g., "2026-06-01T23:59:59Z")
            ctx: MCP context (internal)

        Returns:
            Dictionary with results from the appropriate tool

        Examples:
            # Create with template and natural language time
            resource_type="window", operation="create",
            imap_code="EAL-012471", start_time="in 2 hours", template="deployment"

            # Create with custom duration
            resource_type="window", operation="create",
            imap_code="EAL-012471", start_time="2026-06-01T14:00:00Z",
            duration_minutes="120", reason="Scheduled deployment"

            # Create recurring maintenance window
            resource_type="window", operation="create",
            imap_code="ORZ-000012", start_time="in 3 hours",
            duration_minutes="30", rrule="FREQ=DAILY;INTERVAL=1",
            until_date="2026-06-17T23:59:59Z"

            # List all active windows
            resource_type="window", operation="list_active"

            # List windows for specific application
            resource_type="window", operation="list_active", imap_code="EAL-012471"

            # Modify window duration
            resource_type="window", operation="modify",
            window_id="mw-789", duration_minutes="60"

            # Close window with notes
            resource_type="window", operation="close",
            window_id="mw-789", completion_notes="Completed successfully"

            # Bulk create for multiple IMAP codes
            resource_type="window", operation="bulk_create",
            imap_codes='["EAL-012471","ORZ-000012"]',
            start_time="2026-06-02T02:00:00Z", duration_hours="2",
            reason="Coordinated microservices deployment"

            # Get available templates
            resource_type="templates", operation="get"
        """
        try:
            # Apply defaults for optional params (WatsonX may omit them entirely)
            if not resource_type:
                resource_type = RESOURCE_TYPE_WINDOW
            if not operation:
                operation = OP_LIST_SCHEDULED

            logger.info(f"Maintenance Window Router: resource_type={resource_type}, operation={operation}")

            # Build params dict from flat string parameters
            params = {}
            if application_id is not None:
                params[PARAM_APPLICATION_ID] = application_id
            if application_ids is not None:
                params[PARAM_APPLICATION_IDS] = application_ids
            if imap_code is not None:
                params[PARAM_IMAP_CODE] = imap_code
            if imap_codes is not None:
                params[PARAM_IMAP_CODES] = imap_codes
            if window_id is not None:
                params[PARAM_WINDOW_ID] = window_id
            if start_time is not None:
                params[PARAM_START_TIME] = start_time
            if end_time is not None:
                params[PARAM_END_TIME] = end_time
            if duration_minutes is not None:
                params[PARAM_DURATION_MINUTES] = duration_minutes
            if duration_hours is not None:
                params[PARAM_DURATION_HOURS] = duration_hours
            if duration_days is not None:
                params[PARAM_DURATION_DAYS] = duration_days
            if reason is not None:
                params[PARAM_REASON] = reason
            if template is not None:
                params[PARAM_TEMPLATE] = template
            if change_request_id is not None:
                params[PARAM_CHANGE_REQUEST_ID] = change_request_id
            if affected_services is not None:
                params[PARAM_AFFECTED_SERVICES] = affected_services
            if notification_channels is not None:
                params[PARAM_NOTIFICATION_CHANNELS] = notification_channels
            if completion_notes is not None:
                params[PARAM_COMPLETION_NOTES] = completion_notes
            if use_tag_filter_expression is not None:
                params[PARAM_USE_TAG_FILTER_EXPRESSION] = use_tag_filter_expression
            if tag_name is not None:
                params[PARAM_TAG_NAME] = tag_name
            if rrule is not None:
                params[PARAM_RRULE] = rrule
            if until_date is not None:
                params[PARAM_UNTIL_DATE] = until_date

            # Normalise resource_type — accept common aliases WatsonX may produce
            # from cached or inferred tool schemas
            WINDOW_ALIASES = {"window", "maintenance", "maintenance_window", "windows"}
            TEMPLATES_ALIASES = {"templates", "template"}

            if resource_type in WINDOW_ALIASES:
                resource_type = RESOURCE_TYPE_WINDOW
            elif resource_type in TEMPLATES_ALIASES:
                resource_type = RESOURCE_TYPE_TEMPLATES

            # Validate resource_type
            if resource_type not in VALID_RESOURCE_TYPES:
                return {
                    "error": f"Invalid resource_type '{resource_type}'. Must be one of: {VALID_RESOURCE_TYPES}",
                    "suggestion": "Use 'window' for maintenance window lifecycle operations, or 'templates' to retrieve available templates"
                }

            # Route to the appropriate resource handler
            if resource_type == RESOURCE_TYPE_WINDOW:
                return await self._handle_window(operation, params, ctx)
            elif resource_type == RESOURCE_TYPE_TEMPLATES:
                return await self._handle_templates(operation, params, ctx)
            else:
                return {
                    "error": f"Unsupported resource_type: {resource_type}",
                    "supported_types": VALID_RESOURCE_TYPES
                }

        except Exception as e:
            logger.error(f"Error in maintenance window smart router: {e}", exc_info=True)
            return {
                "error": f"Maintenance window router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_window(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle maintenance window lifecycle operations."""
        if operation not in WINDOW_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for resource_type 'window'",
                "valid_operations": WINDOW_VALID_OPERATIONS
            }

        # Parse JSON array strings into lists for the underlying tool
        application_ids = self._parse_json_list(params.get(PARAM_APPLICATION_IDS))
        imap_codes = self._parse_json_list(params.get(PARAM_IMAP_CODES))
        affected_services = self._parse_json_list(params.get(PARAM_AFFECTED_SERVICES))
        notification_channels = self._parse_json_list(params.get(PARAM_NOTIFICATION_CHANNELS))

        # Parse boolean string
        use_tag_filter_raw = params.get(PARAM_USE_TAG_FILTER_EXPRESSION)
        use_tag_filter = (
            str(use_tag_filter_raw).lower() == "true"
            if use_tag_filter_raw is not None
            else False
        )

        logger.info(f"Routing to Maintenance Window client for operation: {operation}")

        result = await self.maintenance_window_client.execute_maintenance_operation(
            operation=operation,
            application_id=params.get(PARAM_APPLICATION_ID),
            application_ids=application_ids,
            imap_code=params.get(PARAM_IMAP_CODE),
            imap_codes=imap_codes,
            window_id=params.get(PARAM_WINDOW_ID),
            start_time=params.get(PARAM_START_TIME),
            end_time=params.get(PARAM_END_TIME),
            duration_minutes=params.get(PARAM_DURATION_MINUTES),
            duration_hours=params.get(PARAM_DURATION_HOURS),
            duration_days=params.get(PARAM_DURATION_DAYS),
            reason=params.get(PARAM_REASON),
            template=params.get(PARAM_TEMPLATE),
            change_request_id=params.get(PARAM_CHANGE_REQUEST_ID),
            affected_services=affected_services,
            notification_channels=notification_channels,
            completion_notes=params.get(PARAM_COMPLETION_NOTES),
            use_tag_filter_expression=use_tag_filter,
            tag_name=params.get(PARAM_TAG_NAME),
            rrule=params.get(PARAM_RRULE),
            until_date=params.get(PARAM_UNTIL_DATE),
            ctx=ctx
        )

        return {
            "resource_type": RESOURCE_TYPE_WINDOW,
            "operation": operation,
            "results": result
        }

    async def _handle_templates(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle maintenance window template retrieval."""
        if operation not in TEMPLATES_VALID_OPERATIONS:
            return {
                "error": f"Invalid operation '{operation}' for resource_type 'templates'",
                "valid_operations": TEMPLATES_VALID_OPERATIONS,
                "hint": "Use 'get' to retrieve all available maintenance window templates"
            }

        logger.info("Routing to Maintenance Window client for get_templates")

        result = await self.maintenance_window_client.execute_maintenance_operation(
            operation="get_templates",
            ctx=ctx
        )

        return {
            "resource_type": RESOURCE_TYPE_TEMPLATES,
            "operation": operation,
            "results": result
        }

    def _parse_json_list(self, value) -> Optional[list]:
        """
        Parse a JSON array string, comma-separated string, or existing list into a Python list.

        Args:
            value: JSON array string (e.g., '["a","b"]'), comma-separated (e.g., "a,b"),
                   or an already-parsed list

        Returns:
            Python list or None if value is None/empty
        """
        if value is None:
            return None
        if isinstance(value, list):
            return value
        value_str = str(value).strip()
        if not value_str:
            return None
        # Try JSON array first
        if value_str.startswith("["):
            try:
                return json.loads(value_str)
            except (json.JSONDecodeError, ValueError):
                pass
        # Fall back to comma-separated
        return [item.strip() for item in value_str.split(",") if item.strip()]

