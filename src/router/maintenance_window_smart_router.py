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

    VALID_TEMPLATES = ["deployment", "database_migration", "infrastructure_upgrade", "emergency", "routine"]

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
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified Instana maintenance window manager for lifecycle management.

Resource Types:
    - "window": Create, modify, close, and list maintenance windows
    - "templates": Retrieve available maintenance window templates

WINDOW (resource_type="window"):
    operations: create, modify, close, list_active, list_scheduled, list_all, list_expired, bulk_create, validate

    create - Create a new maintenance window
        Required: imap_code OR application_id, start_time
        Optional: end_time, duration_minutes, duration_hours, duration_days, reason, template, change_request_id, affected_services, notification_channels, use_tag_filter_expression, tag_name, rrule, until_date

    modify - Modify an existing maintenance window
        Required: window_id
        Optional: end_time, duration_minutes, reason, rrule, until_date

    close - Close and document a maintenance window
        Required: window_id
        Optional: completion_notes

    list_active - List all currently active maintenance windows
        Optional: imap_code, application_id

    list_scheduled - List all upcoming scheduled maintenance windows
        Optional: imap_code, application_id

    list_all - List all maintenance windows (active, scheduled, and expired)
        Optional: imap_code, application_id

    list_expired - List all expired/completed maintenance windows
        Optional: imap_code, application_id

    bulk_create - Create maintenance windows for multiple applications at once
        Required: application_ids OR imap_codes, start_time
        Optional: duration_minutes, duration_hours, duration_days, reason, template, change_request_id, use_tag_filter_expression, tag_name

    validate - Validate maintenance window parameters without creating
        Required: imap_code OR application_id, start_time
        Optional: duration_minutes, template

TEMPLATES (resource_type="templates"):
    operations: get

    get - Retrieve all available maintenance window templates
        No parameters required

Args:
    resource_type: "window" or "templates" (default: "window")
    operation: Operation to perform (default: "list_scheduled")
    application_id: Single application ID (legacy support)
    application_ids: Comma-separated or JSON array of application IDs
    imap_code: Single IMAP code (e.g., "EAL-012512")
    imap_codes: Comma-separated or JSON array of IMAP codes
    window_id: Maintenance window ID (for modify/close)
    start_time: Start time (Unix timestamp ms or ISO string)
    end_time: End time (Unix timestamp ms or ISO string)
    duration_minutes: Duration in minutes (e.g., "120")
    duration_hours: Duration in hours (e.g., "2")
    duration_days: Duration in days (e.g., "1")
    reason: Reason/description for the maintenance window
    template: Template name ("deployment", "database_migration", "infrastructure_upgrade", "emergency", "routine")
    change_request_id: ServiceNow change request ID
    affected_services: Comma-separated or JSON array of service names
    notification_channels: Comma-separated or JSON array of channels
    completion_notes: Notes when closing a window
    use_tag_filter_expression: "true" or "false"
    tag_name: Tag name for filter expression
    rrule: Recurrence rule (RFC 5545)
    until_date: End date for recurring windows (ISO string)
    ctx: MCP context (internal)

Returns:
    Dictionary with results from the appropriate tool

Examples:
    # WINDOW operations - create (covers: imap_code, duration_minutes, duration_hours, template, recurring)
    resource_type="window", operation="create", imap_code="EAL-012471", start_time="1748786400000", duration_minutes="120", reason="Scheduled deployment"
    resource_type="window", operation="create", imap_code="EAL-012471", start_time="1748786400000", duration_hours="2", template="deployment", change_request_id="CHG0012345"
    resource_type="window", operation="create", imap_code="ORZ-000012", start_time="1748786400000", duration_minutes="30", rrule="FREQ=DAILY;INTERVAL=1", until_date="2026-06-17T23:59:59Z"

    # WINDOW operations - modify (covers: duration_minutes, end_time, reason)
    resource_type="window", operation="modify", window_id="mw-789", duration_minutes="60"
    resource_type="window", operation="modify", window_id="mw-789", end_time="1748790000000", reason="Extended maintenance"
    resource_type="window", operation="modify", window_id="mw-789", duration_hours="3", rrule="FREQ=DAILY;INTERVAL=2"

    # WINDOW operations - close (covers: with/without notes)
    resource_type="window", operation="close", window_id="mw-789"
    resource_type="window", operation="close", window_id="mw-789", completion_notes="Completed successfully"
    resource_type="window", operation="close", window_id="mw-789", completion_notes="Completed with issues - rollback performed"

    # WINDOW operations - list_active
    resource_type="window", operation="list_active"
    resource_type="window", operation="list_active", imap_code="EAL-012471"
    resource_type="window", operation="list_active", application_id="app-123"

    # WINDOW operations - list_scheduled
    resource_type="window", operation="list_scheduled"
    resource_type="window", operation="list_scheduled", imap_code="EAL-012471"
    resource_type="window", operation="list_scheduled", application_id="app-123"

    # WINDOW operations - list_all
    resource_type="window", operation="list_all"
    resource_type="window", operation="list_all", imap_code="EAL-012471"
    resource_type="window", operation="list_all", application_id="app-123"

    # WINDOW operations - list_expired
    resource_type="window", operation="list_expired"
    resource_type="window", operation="list_expired", imap_code="EAL-012471"
    resource_type="window", operation="list_expired", application_id="app-123"

    # WINDOW operations - bulk_create
    resource_type="window", operation="bulk_create", imap_codes="EAL-012471,ORZ-000012", start_time="1748786400000", duration_hours="2", reason="Coordinated deployment"
    resource_type="window", operation="bulk_create", application_ids="app-123,app-456", start_time="1748786400000", duration_minutes="120", reason="Multi-app maintenance"
    resource_type="window", operation="bulk_create", imap_codes="EAL-012471,ORZ-000012", start_time="1748786400000", template="deployment", change_request_id="CHG0012345"

    # WINDOW operations - validate
    resource_type="window", operation="validate", imap_code="EAL-012471", start_time="1748786400000", duration_minutes="120"
    resource_type="window", operation="validate", application_id="app-123", start_time="1748786400000", duration_hours="2"
    resource_type="window", operation="validate", imap_code="EAL-012471", start_time="1748786400000", template="deployment"

    # TEMPLATES operations (covers: get templates)
    resource_type="templates", operation="get\""""
    )
    async def manage_maintenance_windows(
        self,
        resource_type: Optional[str] = "window",
        operation: Optional[str] = "list_scheduled",
        params: Optional[Dict[str, Any]] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """Unified Instana maintenance window manager for lifecycle management."""

        TOOL_NAME = "manage_maintenance_windows"

        try:
            # Initialize params if not provided
            if params is None:
                params = {}

            # Apply defaults for optional params (WatsonX may omit them entirely)
            resource_type = resource_type or RESOURCE_TYPE_WINDOW
            operation = operation or OP_LIST_SCHEDULED

            logger.info(f"Received: resource_type={resource_type}, operation={operation}, tool={TOOL_NAME}")

            # Log all incoming parameters for debugging
            self._log_incoming_request(resource_type, operation, params)

            logger.info(f"After defaults: resource_type={resource_type}, operation={operation}")

            # Normalise and validate resource_type
            resource_type = self._normalize_resource_type(resource_type)
            validation_error = self._validate_resource_type(resource_type)
            if validation_error:
                return validation_error

            # Route to the appropriate resource handler
            return await self._route_to_handler(resource_type, operation, params, ctx, tool_name=TOOL_NAME)

        except Exception as e:
            return self._handle_error(e, resource_type, operation, params or {})

    def _log_incoming_request(
        self,
        resource_type: str,
        operation: str,
        params: Dict[str, Any]
    ) -> None:
        """Log incoming request parameters for debugging."""
        logger.info("=== Maintenance Window Router Called ===")
        logger.info(f"resource_type={resource_type}, operation={operation}")
        logger.info(f"window_id={params.get(PARAM_WINDOW_ID)}")
        logger.info(f"imap_code={params.get(PARAM_IMAP_CODE)}, application_id={params.get(PARAM_APPLICATION_ID)}")
        logger.info(f"start_time={params.get(PARAM_START_TIME)}, duration_minutes={params.get(PARAM_DURATION_MINUTES)}")
        logger.info(f"duration_hours={params.get(PARAM_DURATION_HOURS)}, duration_days={params.get(PARAM_DURATION_DAYS)}")
        logger.info(f"template={params.get(PARAM_TEMPLATE)}, reason={params.get(PARAM_REASON)}")

    def _normalize_resource_type(self, resource_type: str) -> str:
        """Normalize resource_type to handle common aliases."""
        WINDOW_ALIASES = {"window", "maintenance", "maintenance_window", "windows"}
        TEMPLATES_ALIASES = {"templates", "template"}

        if resource_type in WINDOW_ALIASES:
            return RESOURCE_TYPE_WINDOW
        elif resource_type in TEMPLATES_ALIASES:
            return RESOURCE_TYPE_TEMPLATES
        return resource_type

    def _validate_resource_type(self, resource_type: str) -> Optional[Dict[str, Any]]:
        """Validate resource_type and return error if invalid."""
        if resource_type not in VALID_RESOURCE_TYPES:
            return {
                "elicitation_needed": True,
                "reason": "invalid_resource_type",
                "api_error": [
                    {
                        "field": "resource_type",
                        "issue": f"'{resource_type}' is not a valid resource type",
                        "expected": VALID_RESOURCE_TYPES
                    }
                ],
                "message": f"Invalid resource_type '{resource_type}'. Must be one of: {VALID_RESOURCE_TYPES}"
            }
        return None

    async def _route_to_handler(
        self,
        resource_type: str,
        operation: str,
        params: Dict[str, Any],
        ctx,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route request to appropriate resource handler."""
        if resource_type == RESOURCE_TYPE_WINDOW:
            return await self._handle_window(operation, params, ctx, tool_name=tool_name)
        elif resource_type == RESOURCE_TYPE_TEMPLATES:
            return await self._handle_templates(operation, ctx, tool_name=tool_name)
        else:
            return {
                "elicitation_needed": True,
                "reason": "invalid_resource_type",
                "api_error": [
                    {
                        "field": "resource_type",
                        "issue": f"Unsupported resource_type: {resource_type}",
                        "expected": VALID_RESOURCE_TYPES
                    }
                ],
                "message": f"Unsupported resource_type '{resource_type}'. Must be one of: {VALID_RESOURCE_TYPES}"
            }

    def _handle_error(
        self,
        error: Exception,
        resource_type: str,
        operation: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle and log errors."""
        logger.error("=== ERROR in Maintenance Window Router ===")
        logger.error(f"Error: {error}", exc_info=True)
        logger.error(f"resource_type={resource_type}, operation={operation}")
        logger.error(f"imap_code={params.get(PARAM_IMAP_CODE)}, application_id={params.get(PARAM_APPLICATION_ID)}")
        return {
            "error": f"Maintenance window router error: {error!s}",
            "error_type": type(error).__name__,
            "resource_type": resource_type,
            "operation": operation,
            "parameters": {
                "imap_code": params.get(PARAM_IMAP_CODE),
                "application_id": params.get(PARAM_APPLICATION_ID),
                "start_time": params.get(PARAM_START_TIME),
                "duration_minutes": params.get(PARAM_DURATION_MINUTES)
            }
        }

    def _window_id_error(self, operation: str, hint: str, message: str) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [
                {
                    "field": "window_id",
                    "issue": f"window_id is required for {operation}",
                    "hint": hint
                }
            ],
            "message": message
        }

    def _create_window_validation_errors(
        self,
        operation: str,
        field: str,
        has_identifier: bool,
        start_time,
        template,
    ) -> list[Dict[str, Any]]:
        errors = []
        if not has_identifier:
            examples = {
                OP_CREATE: "imap_code='EAL-012471'",
                OP_BULK_CREATE: "imap_codes='EAL-012471,ORZ-000012'"
            }
            errors.append({
                "field": field,
                "issue": f"Either {field} is required",
                "example": examples[operation]
            })
        if not start_time:
            errors.append({
                "field": "start_time",
                "issue": "start_time is required",
                "expected": "Unix timestamp in milliseconds (e.g., 1748786400000)"
            })
        if template and template not in self.VALID_TEMPLATES:
            errors.append({
                "field": "template",
                "issue": f"'{template}' is not a valid template",
                "expected": self.VALID_TEMPLATES
            })
        return errors

    def _validate_window_operation(
        self,
        operation: str,
        window_id,
        imap_code,
        application_id,
        imap_codes,
        application_ids,
        start_time,
        template,
    ) -> Optional[Dict[str, Any]]:
        if operation == OP_MODIFY and not window_id:
            return self._window_id_error(
                OP_MODIFY,
                "Use list_active or list_scheduled to find window IDs",
                "Missing required parameter 'window_id' for modify. Use list_active or list_scheduled to find IDs."
            )

        if operation == OP_CLOSE and not window_id:
            return self._window_id_error(
                OP_CLOSE,
                "Use list_active to find active window IDs",
                "Missing required parameter 'window_id' for close. Use list_active to find active window IDs."
            )

        if operation == OP_BULK_CREATE:
            errors = self._create_window_validation_errors(
                operation,
                "imap_codes / application_ids",
                bool(imap_codes or application_ids),
                start_time,
                template,
            )
            if errors:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": errors,
                    "message": f"Missing or invalid parameters for bulk_create: {[e['field'] for e in errors]}"
                }

        if operation == OP_CREATE:
            errors = self._create_window_validation_errors(
                operation,
                "imap_code / application_id",
                bool(imap_code or application_id),
                start_time,
                template,
            )
            if errors:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": errors,
                    "message": f"Missing or invalid parameters for create: {[e['field'] for e in errors]}"
                }

        return None

    async def _handle_window(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle maintenance window lifecycle operations."""
        if operation not in WINDOW_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid window operation",
                        "expected": WINDOW_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'window'. Valid operations: {WINDOW_VALID_OPERATIONS}"
            }

        application_ids = self._parse_json_list(params.get(PARAM_APPLICATION_IDS))
        imap_codes = self._parse_json_list(params.get(PARAM_IMAP_CODES))
        affected_services = self._parse_json_list(params.get(PARAM_AFFECTED_SERVICES))
        notification_channels = self._parse_json_list(params.get(PARAM_NOTIFICATION_CHANNELS))

        use_tag_filter_raw = params.get(PARAM_USE_TAG_FILTER_EXPRESSION)
        use_tag_filter = (
            str(use_tag_filter_raw).lower() == "true"
            if use_tag_filter_raw is not None
            else False
        )

        validation_error = self._validate_window_operation(
            operation=operation,
            window_id=params.get(PARAM_WINDOW_ID),
            imap_code=params.get(PARAM_IMAP_CODE),
            application_id=params.get(PARAM_APPLICATION_ID),
            imap_codes=imap_codes,
            application_ids=application_ids,
            start_time=params.get(PARAM_START_TIME),
            template=params.get(PARAM_TEMPLATE),
        )
        if validation_error:
            return validation_error

        logger.info(f"Routing to Maintenance Window client for operation: {operation} [resource_type={RESOURCE_TYPE_WINDOW}, tool={tool_name}]")

        operation_params = {
            PARAM_APPLICATION_ID: params.get(PARAM_APPLICATION_ID),
            PARAM_APPLICATION_IDS: application_ids,
            PARAM_IMAP_CODE: params.get(PARAM_IMAP_CODE),
            PARAM_IMAP_CODES: imap_codes,
            PARAM_WINDOW_ID: params.get(PARAM_WINDOW_ID),
            PARAM_START_TIME: params.get(PARAM_START_TIME),
            PARAM_END_TIME: params.get(PARAM_END_TIME),
            PARAM_DURATION_MINUTES: params.get(PARAM_DURATION_MINUTES),
            PARAM_DURATION_HOURS: params.get(PARAM_DURATION_HOURS),
            PARAM_DURATION_DAYS: params.get(PARAM_DURATION_DAYS),
            PARAM_REASON: params.get(PARAM_REASON),
            PARAM_TEMPLATE: params.get(PARAM_TEMPLATE),
            PARAM_CHANGE_REQUEST_ID: params.get(PARAM_CHANGE_REQUEST_ID),
            PARAM_AFFECTED_SERVICES: affected_services,
            PARAM_NOTIFICATION_CHANNELS: notification_channels,
            PARAM_COMPLETION_NOTES: params.get(PARAM_COMPLETION_NOTES),
            PARAM_USE_TAG_FILTER_EXPRESSION: use_tag_filter,
            PARAM_TAG_NAME: params.get(PARAM_TAG_NAME),
            PARAM_RRULE: params.get(PARAM_RRULE),
            PARAM_UNTIL_DATE: params.get(PARAM_UNTIL_DATE),
        }

        result = await self.maintenance_window_client.execute_maintenance_operation(
            operation=operation,
            params=operation_params,
            ctx=ctx,
            resource_type=RESOURCE_TYPE_WINDOW,
            tool_name=tool_name,
        )

        return {
            "resource_type": RESOURCE_TYPE_WINDOW,
            "operation": operation,
            "results": result
        }

    async def _handle_templates(
        self,
        operation: str,
        ctx,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle maintenance window template retrieval."""
        if operation not in TEMPLATES_VALID_OPERATIONS:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid templates operation",
                        "expected": TEMPLATES_VALID_OPERATIONS,
                        "hint": "Use 'get' to retrieve all available maintenance window templates"
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'templates'. Valid operations: {TEMPLATES_VALID_OPERATIONS}"
            }

        logger.info(f"Routing to Maintenance Window client for get_templates [resource_type={RESOURCE_TYPE_TEMPLATES}, tool={tool_name}]")

        result = await self.maintenance_window_client.execute_maintenance_operation(
            operation="get_templates",
            params={},
            ctx=ctx,
            resource_type=RESOURCE_TYPE_TEMPLATES,
            tool_name=tool_name,
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
            except json.JSONDecodeError:
                pass
        # Fall back to comma-separated
        return [item.strip() for item in value_str.split(",") if item.strip()]

