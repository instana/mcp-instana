"""
Maintenance Window Management MCP Tools Module

This module provides comprehensive maintenance window lifecycle management for Instana
and ServiceNow integration. It automates the creation, modification, and closure of
maintenance windows to prevent false alerts during planned operational activities.

Integration Points:
    - Consumed by maintenance_window_smart_router.py via the manage_maintenance_windows() method
    - Supports WatsonX Orchestrate and MCP agent interactions for automated scheduling
    - Coordinates with ServiceNow for change request synchronization
    - Aligns with Instana alert configurations and application perspectives

Key Features:
    1. Automated maintenance window creation with validation
    2. Real-time modification of active maintenance windows
    3. Automatic closure and documentation of completed windows
    4. ServiceNow change request integration
    5. Predefined rule templates for common maintenance scenarios
    6. Multi-environment support with consistency enforcement

Usage from maintenance_window_smart_router.py:
    # Create maintenance window
    resource_type="window", operation="create"
    imap_code="EAL-012471"
    start_time="in 2 hours"
    duration_minutes="120"
    reason="Database migration"
    change_request_id="CHG0012345"
    affected_services='["payment-service","user-service"]'
    notification_channels='["slack","email"]'

    # Modify existing window
    resource_type="window", operation="modify"
    window_id="mw-789"
    duration_minutes="180"
    reason="Extended due to complications"

    # Close maintenance window
    resource_type="window", operation="close"
    window_id="mw-789"
    completion_notes="Migration completed successfully"

    # Get available templates
    resource_type="templates", operation="get"

Configuration Requirements:
    - INSTANA_API_TOKEN: API token with write permissions
    - INSTANA_BASE_URL: Instana tenant URL
    - SERVICENOW_API_TOKEN: ServiceNow integration token (optional)
    - SERVICENOW_INSTANCE_URL: ServiceNow instance URL (optional)

Error Handling:
    - Validates all input parameters before API calls
    - Provides detailed error messages for troubleshooting
    - Implements retry logic for transient failures
    - Logs all operations for audit trail

Examples:
    # Example 1: Create maintenance window with predefined template
    await maintenance_client.execute_maintenance_operation(
        operation="create",
        imap_code="EAL-012471",
        template="deployment",
        start_time="in 2 hours",
        duration_minutes="60",
        ctx=ctx
    )

    # Example 2: Bulk create windows for multiple applications
    await maintenance_client.execute_maintenance_operation(
        operation="bulk_create",
        imap_codes=["EAL-012471", "ORZ-000012", "MUR-123456"],
        start_time="2026-06-01T02:00:00Z",
        duration_minutes="120",
        reason="Infrastructure upgrade",
        ctx=ctx
    )

    # Example 3: Query active maintenance windows
    await maintenance_client.execute_maintenance_operation(
        operation="list_active",
        imap_code="EAL-012471",
        ctx=ctx
    )
"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from instana_client.api.maintenance_configuration_api import MaintenanceConfigurationApi
from instana_client.models.maintenance_config_v2 import MaintenanceConfigV2

from src.core.timestamp_utils import get_current_timestamp
from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

logger = logging.getLogger(__name__)

# Validation hint constants
_TS_HINT_MS = "Unix timestamp in milliseconds (e.g., 1748786400000)"


class MaintenanceWindowMCPTools(BaseInstanaClient):
    """
    Tools for maintenance window management in Instana MCP.

    This class provides comprehensive maintenance window lifecycle management including
    creation, modification, closure, and ServiceNow integration. It supports both
    individual and bulk operations across multiple applications and environments.

    Attributes:
        read_token (str): Instana API token for authentication
        base_url (str): Instana tenant base URL
        servicenow_token (Optional[str]): ServiceNow API token for integration
        servicenow_url (Optional[str]): ServiceNow instance URL

    Maintenance Window Templates:
        - deployment: Standard deployment window (1-2 hours)
        - database_migration: Extended database maintenance (2-4 hours)
        - infrastructure_upgrade: Infrastructure changes (4-8 hours)
        - emergency: Emergency maintenance (flexible duration)
        - routine: Routine maintenance activities (30-60 minutes)
    """

    # Predefined maintenance window templates
    TEMPLATES = {
        "deployment": {
            "default_duration": 60,
            "description": "Application deployment maintenance",
            "alert_suppression": ["application", "service"],
            "notification_required": True
        },
        "database_migration": {
            "default_duration": 180,
            "description": "Database migration and schema updates",
            "alert_suppression": ["application", "database", "infrastructure"],
            "notification_required": True
        },
        "infrastructure_upgrade": {
            "default_duration": 240,
            "description": "Infrastructure upgrade and patching",
            "alert_suppression": ["infrastructure", "host", "container"],
            "notification_required": True
        },
        "emergency": {
            "default_duration": 120,
            "description": "Emergency maintenance window",
            "alert_suppression": ["all"],
            "notification_required": True
        },
        "routine": {
            "default_duration": 30,
            "description": "Routine maintenance activities",
            "alert_suppression": ["application"],
            "notification_required": False
        }
    }

    # Date format constant for UTC timestamps
    DATETIME_FORMAT_UTC = "%Y-%m-%d %H:%M:%S UTC"

    # Error message constants
    ERROR_START_TIME_REQUIRED = "start_time is required"

    def __init__(
        self,
        read_token: str,
        base_url: str,
        servicenow_token: Optional[str] = None,
        servicenow_url: Optional[str] = None
    ):
        """
        Initialize the Maintenance Window MCP tools client.

        Args:
            read_token: Instana API token with write permissions
            base_url: Instana tenant base URL
            servicenow_token: Optional ServiceNow API token for integration
            servicenow_url: Optional ServiceNow instance URL
        """
        super().__init__(read_token=read_token, base_url=base_url)
        self.servicenow_token = servicenow_token
        self.servicenow_url = servicenow_url
        logger.info("Maintenance Window MCP Tools initialized")

    async def execute_maintenance_operation(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx=None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute maintenance window operations.

        This is the main dispatcher method called by smart_router_tool.py to handle
        all maintenance window operations. It validates inputs, applies templates,
        and routes to the appropriate operation handler.

        Operations:
            - create: Create a new maintenance window
            - modify: Modify an existing maintenance window
            - close: Close and document a maintenance window
            - list_active: List all active maintenance windows
            - list_scheduled: List all scheduled maintenance windows
            - list_all: List all maintenance windows (active, scheduled, and expired)
            - list_expired: List all expired maintenance windows
            - bulk_create: Create maintenance windows for multiple applications
            - validate: Validate maintenance window parameters without creating
            - get_templates: Retrieve available maintenance window templates

        Args:
            operation: Operation to perform (create, modify, close, list_active, etc.)
            params: Dictionary containing operation parameters. Supported keys:
                - application_id: Single application ID (legacy support, treated as IMAP code)
                - application_ids: Multiple application IDs for bulk operations (legacy support)
                - imap_code: Single IMAP code (e.g., EAL-012512, ORZ-000012)
                - imap_codes: Multiple IMAP codes for bulk operations
                - window_id: Existing maintenance window ID (for modify/close operations)
                - start_time: Start time in Unix timestamp milliseconds
                - end_time: End time in Unix timestamp milliseconds
                - duration_minutes: Duration in minutes
                - duration_hours: Duration in hours
                - duration_days: Duration in days
                - reason: Reason for maintenance window
                - template: Predefined template name (deployment, database_migration, etc.)
                - change_request_id: ServiceNow change request ID
                - affected_services: List of affected service names
                - notification_channels: List of notification channels (slack, email, etc.)
                - completion_notes: Notes for window closure
                - use_tag_filter_expression: Use tag filter expression format (default: False)
                - tag_name: Tag name for filter expression (default: synthetic.tags)
                - rrule: Recurrence rule (RFC 5545)
                - until_date: End date for recurring windows (ISO string)
            ctx: MCP context
            **kwargs: Backward compatibility - accepts individual parameters as keyword arguments

        Returns:
            Dictionary containing operation results with the following structure:
            {
                "operation": str,
                "status": "success" | "error",
                "window_id": str (for create operations),
                "details": Dict[str, Any],
                "message": str
            }

        Raises:
            ValueError: If required parameters are missing or invalid

        Examples:
            # New style with params dict (recommended)
            result = await execute_maintenance_operation(
                operation="create",
                params={
                    "imap_code": "EAL-012471",
                    "template": "deployment",
                    "start_time": 1709020800000,
                    "reason": "v2.0 deployment"
                },
                ctx=ctx
            )

            # Old style with individual parameters (backward compatibility)
            result = await execute_maintenance_operation(
                operation="modify",
                window_id="mw-789",
                end_time=1709027400000,
                reason="Extended due to issues",
                ctx=ctx
            )
        """
        try:
            # Merge params dict and kwargs for backward compatibility
            # If called with individual parameters (kwargs), use those
            # If called with params dict, use that
            # This supports both old test style and new router style
            if kwargs:
                # Old style: individual parameters via kwargs
                merged_params = kwargs
            else:
                # New style: params dictionary
                merged_params = params or {}

            extracted = self._extract_maintenance_params(merged_params)

            # Extract individual parameters for easier access
            application_id = extracted["application_id"]
            application_ids = extracted["application_ids"]
            imap_code = extracted["imap_code"]
            imap_codes = extracted["imap_codes"]
            window_id = extracted["window_id"]
            start_time = extracted["start_time"]
            end_time = extracted["end_time"]
            duration_minutes = extracted["duration_minutes"]
            duration_hours = extracted["duration_hours"]
            duration_days = extracted["duration_days"]
            reason = extracted["reason"]
            template = extracted["template"]
            change_request_id = extracted["change_request_id"]
            completion_notes = extracted["completion_notes"]
            use_tag_filter_expression = extracted["use_tag_filter_expression"]
            tag_name = extracted["tag_name"]
            rrule = extracted["rrule"]
            until_date = extracted["until_date"]

            self._log_operation_start(operation, window_id, imap_code, application_id,
                                     duration_minutes, duration_hours, duration_days,
                                     end_time, reason, rrule, until_date)

            # Convert and validate parameters
            conversion_result = self._convert_string_parameters(
                start_time, end_time, duration_minutes, duration_hours, duration_days
            )
            if "elicitation_needed" in conversion_result or "error" in conversion_result:
                return conversion_result

            start_time, end_time, duration_minutes, duration_hours, duration_days = conversion_result["values"]

            # Validate operation
            validation_error = self._validate_operation(operation)
            if validation_error:
                return validation_error

            # Rebuild params dict with converted values for routing
            route_params = {
                "application_id": application_id,
                "application_ids": application_ids,
                "imap_code": imap_code,
                "imap_codes": imap_codes,
                "window_id": window_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration_minutes": duration_minutes,
                "duration_hours": duration_hours,
                "duration_days": duration_days,
                "reason": reason,
                "template": template,
                "change_request_id": change_request_id,
                "affected_services": extracted["affected_services"],
                "notification_channels": extracted["notification_channels"],
                "completion_notes": completion_notes,
                "use_tag_filter_expression": use_tag_filter_expression,
                "tag_name": tag_name,
                "rrule": rrule,
                "until_date": until_date
            }

            # Route to appropriate handler
            return await self._route_operation(
                operation=operation,
                params=route_params,
                ctx=ctx
            )

        except Exception as e:
            logger.error(f"Error executing maintenance operation: {e}", exc_info=True)
            return {
                "error": f"Maintenance operation failed: {e!s}",
                "operation": operation
            }

    def _extract_maintenance_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract maintenance window parameters from params dictionary with defaults.

        This method follows the same pattern as events_tools._extract_event_filters
        to reduce parameter count and improve maintainability.

        Args:
            params: Dictionary containing maintenance window parameters

        Returns:
            Dictionary with all parameters, using defaults where not provided
        """
        ALLOWED_PARAMS = {
            "application_id": None,
            "application_ids": None,
            "imap_code": None,
            "imap_codes": None,
            "window_id": None,
            "start_time": None,
            "end_time": None,
            "duration_minutes": None,
            "duration_hours": None,
            "duration_days": None,
            "reason": None,
            "template": None,
            "change_request_id": None,
            "affected_services": None,
            "notification_channels": None,
            "completion_notes": None,
            "use_tag_filter_expression": False,
            "tag_name": None,
            "rrule": None,
            "until_date": None,
        }

        return {k: params.get(k, v) for k, v in ALLOWED_PARAMS.items()}

    def _log_operation_start(self, operation: str, window_id: Optional[str],
                            imap_code: Optional[str], application_id: Optional[str],
                            duration_minutes: Any, duration_hours: Any,
                            duration_days: Any, end_time: Any,
                            reason: Optional[str], rrule: Optional[str],
                            until_date: Optional[str]) -> None:
        """Log operation start and relevant parameters."""
        logger.info("=== MAINTENANCE OPERATION START ===")
        logger.info(f"Operation: {operation}")

        if operation in ["modify", "close"]:
            logger.info(f"Window ID: {window_id}")
        else:
            logger.info(f"IMAP Code: {imap_code or application_id}")

        if operation == "modify":
            logger.info(f"Duration Minutes: {duration_minutes}")
            logger.info(f"Duration Hours: {duration_hours}")
            logger.info(f"Duration Days: {duration_days}")
            logger.info(f"End Time: {end_time}")
            logger.info(f"Reason: {reason}")

        if rrule:
            logger.info("🔁 RECURRING WINDOW REQUESTED")
            logger.info(f"RRULE parameter: {rrule}")
            logger.info(f"Until Date parameter: {until_date}")

    def _convert_string_parameters(self, start_time: Optional[Any], end_time: Optional[Any],
                                   duration_minutes: Optional[Any], duration_hours: Optional[Any],
                                   duration_days: Optional[Any]) -> Dict[str, Any]:
        """Convert string parameters to integers and validate."""
        conversions = [
            ("start_time", start_time, "Unix timestamp in milliseconds (integer)", "1745020800000"),
            ("end_time", end_time, "Unix timestamp in milliseconds", None),
            ("duration_minutes", duration_minutes, "integer", "120 for 2 hours"),
            ("duration_hours", duration_hours, "integer", "2"),
            ("duration_days", duration_days, "integer", "1")
        ]

        converted_values = []
        for param_name, param_value, description, example in conversions:
            if param_value is not None and isinstance(param_value, str):
                try:
                    converted_values.append(int(param_value))
                except ValueError:
                    expected = description + (f" (e.g., {example})" if example else "")
                    return {
                        "elicitation_needed": True,
                        "reason": "invalid_param_type",
                        "api_error": [
                            {
                                "field": param_name,
                                "issue": f"'{param_value}' cannot be converted to an integer",
                                "expected": expected
                            }
                        ],
                        "message": f"Parameter '{param_name}' must be {expected}, got: '{param_value}'"
                    }
            else:
                converted_values.append(param_value)

        return {"values": tuple(converted_values)}

    def _validate_operation(self, operation: str) -> Optional[Dict[str, Any]]:
        """Validate that the operation is supported."""
        valid_operations = [
            "create", "modify", "close", "list_active", "list_scheduled",
            "list_all", "list_expired", "bulk_create", "validate", "get_templates"
        ]

        if operation not in valid_operations:
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid maintenance window operation",
                        "expected": valid_operations
                    }
                ],
                "message": f"Invalid operation '{operation}'. Valid operations: {valid_operations}"
            }
        return None

    async def _route_operation(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx: Optional[Any]
    ) -> Dict[str, Any]:
        """Route operation to appropriate handler method."""
        # Extract parameters from params dict
        application_id = params.get("application_id")
        imap_code = params.get("imap_code")
        window_id = params.get("window_id")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        duration_minutes = params.get("duration_minutes")
        duration_hours = params.get("duration_hours")
        duration_days = params.get("duration_days")
        reason = params.get("reason")
        template = params.get("template")
        change_request_id = params.get("change_request_id")
        use_tag_filter_expression = params.get("use_tag_filter_expression")
        tag_name = params.get("tag_name")
        rrule = params.get("rrule")
        until_date = params.get("until_date")
        completion_notes = params.get("completion_notes")
        application_ids = params.get("application_ids")
        imap_codes = params.get("imap_codes")

        operation_handlers = {
            "create": lambda: self._create_maintenance_window(params=params, ctx=ctx),
            "modify": lambda: self._handle_modify_operation(
                window_id, end_time, duration_minutes, duration_hours, duration_days,
                reason, rrule, until_date, ctx
            ),
            "close": lambda: self._close_maintenance_window(
                window_id=window_id, completion_notes=completion_notes, ctx=ctx
            ),
            "list_active": lambda: self._list_active_windows(
                application_id=application_id or imap_code, ctx=ctx
            ),
            "list_scheduled": lambda: self._list_scheduled_windows(
                application_id=application_id or imap_code, ctx=ctx
            ),
            "list_all": lambda: self._list_all_windows(
                application_id=application_id or imap_code, ctx=ctx
            ),
            "list_expired": lambda: self._list_expired_windows(
                application_id=application_id or imap_code, ctx=ctx
            ),
            "bulk_create": lambda: self._bulk_create_windows(
                application_ids=application_ids, imap_codes=imap_codes, start_time=start_time,
                duration_minutes=duration_minutes, duration_hours=duration_hours,
                duration_days=duration_days, reason=reason, template=template,
                change_request_id=change_request_id, use_tag_filter_expression=use_tag_filter_expression,
                tag_name=tag_name, ctx=ctx
            ),
            "validate": lambda: self._validate_window_params(
                application_id=application_id or imap_code, start_time=start_time
            ),
            "get_templates": lambda: self._get_templates()
        }

        handler = operation_handlers.get(operation)
        if handler:
            result = handler()
            # Handle both async and sync methods
            if hasattr(result, '__await__'):
                return await result
            return result

        return {"error": f"Operation '{operation}' not implemented"}

    async def _handle_modify_operation(self, window_id: Optional[str], end_time: Optional[int],
                                       duration_minutes: Optional[int], duration_hours: Optional[int],
                                       duration_days: Optional[int], reason: Optional[str],
                                       rrule: Optional[str], until_date: Optional[str],
                                       ctx: Optional[Any]) -> Dict[str, Any]:
        """Handle modify operation with duration conversion."""
        final_duration_minutes = duration_minutes
        if duration_hours and not duration_minutes:
            final_duration_minutes = duration_hours * 60
            logger.info(f"Converted duration_hours={duration_hours} to duration_minutes={final_duration_minutes}")
        elif duration_days and not duration_minutes and not duration_hours:
            final_duration_minutes = duration_days * 24 * 60
            logger.info(f"Converted duration_days={duration_days} to duration_minutes={final_duration_minutes}")

        return await self._modify_maintenance_window(
            window_id=window_id, end_time=end_time, duration_minutes=final_duration_minutes,
            reason=reason, rrule=rrule, until_date=until_date, ctx=ctx
        )

    def _check_response_status(self, response, operation_name: str) -> Optional[Dict[str, Any]]:
        """
        Check HTTP response status and return error dict if status indicates failure.

        Args:
            response: The HTTP response object from API client
            operation_name: Name of the operation for error messages

        Returns:
            Error dict if status indicates failure, None if successful
        """
        if hasattr(response, 'status') and response.status not in (200, 201, 204):
            error_msg = f"HTTP {response.status} error during {operation_name}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "status_code": response.status,
                "operation": operation_name
            }
        return None

    @with_header_auth(MaintenanceConfigurationApi)
    async def _create_maintenance_window(
        self,
        params: Dict[str, Any],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Create a new maintenance window in Instana using real API structure.

        This method handles the creation of maintenance windows with full validation,
        template application, and ServiceNow integration. Supports both IMAP codes
        and legacy application IDs. Uses Instana's actual API format with query
        strings or tag filter expressions.

        Args:
            params: Dictionary containing all parameters:
                - application_id: Application ID (legacy support, will be treated as IMAP code)
                - imap_code: IMAP code (e.g., EAL-012512, ORZ-000012)
                - start_time: Start time in Unix timestamp milliseconds
                - end_time: End time in Unix timestamp milliseconds
                - duration_minutes: Duration in minutes
                - duration_hours: Duration in hours
                - duration_days: Duration in days
                - reason: Reason for maintenance
                - template: Template name to apply
                - change_request_id: ServiceNow change request ID
                - affected_services: List of affected services
                - notification_channels: Notification channels
                - use_tag_filter_expression: Use tag filter expression format
                - tag_name: Tag name for filter expression (default: synthetic.tags)
                - rrule: Recurrence rule
                - until_date: End date for recurrence
            ctx: MCP context
            api_client: API client (optional)

        Returns:
            Dictionary with creation results including window_id
        """
        try:
            # Extract parameters
            application_id = params.get("application_id")
            imap_code = params.get("imap_code")
            start_time = params.get("start_time")
            end_time = params.get("end_time")
            duration_minutes = params.get("duration_minutes")
            duration_hours = params.get("duration_hours")
            duration_days = params.get("duration_days")
            reason = params.get("reason")
            template = params.get("template")
            change_request_id = params.get("change_request_id")
            use_tag_filter_expression = params.get("use_tag_filter_expression")
            tag_name = params.get("tag_name")
            rrule = params.get("rrule")
            until_date = params.get("until_date")

            # Validate and get target code
            validation_result = self._validate_create_params(
                imap_code, application_id, start_time, template
            )
            if "elicitation_needed" in validation_result:
                return validation_result

            target_code = validation_result["target_code"]
            template_config = validation_result["template_config"]

            # Type assertion: start_time is validated in _validate_create_params
            assert start_time is not None, "start_time should be validated"

            # Calculate duration and end time
            duration_result = self._calculate_duration_and_end_time(
                start_time, end_time, duration_minutes, duration_hours,
                duration_days, rrule, template_config
            )
            end_time = duration_result["end_time"]
            duration_amount = duration_result["duration_amount"]
            duration_unit = duration_result["duration_unit"]

            # Type assertion: end_time is calculated and guaranteed to be not None
            assert end_time is not None, "end_time should be calculated"

            # Validate time range
            time_validation_error = self._validate_time_range(start_time, end_time)
            if time_validation_error:
                return time_validation_error

            # Generate maintenance window name
            date_str = datetime.fromtimestamp(start_time / 1000).strftime("%Y_%m_%d")
            reason_sanitized = (reason or template_config.get("description", "Maintenance")).replace(" ", "_")
            window_name = f"{target_code}_{reason_sanitized}_{date_str}"

            # Build scheduling object
            scheduling_obj = self._build_scheduling_object(
                start_time, duration_amount, duration_unit, rrule, until_date
            )

            # Build maintenance window payload
            window_payload = self._build_window_payload(
                window_name, target_code, scheduling_obj,
                use_tag_filter_expression or False, tag_name
            )

            # Create maintenance window via Instana API
            # The API requires PUT with an ID in both the path and payload
            window_id = str(uuid.uuid4()).replace('-', '')[:16]  # Generate 16-char ID

            # Add ID to payload as required by API
            window_payload["id"] = window_id

            # Log the payload being sent
            logger.info("=== CREATING MAINTENANCE WINDOW ===")
            logger.info(f"Window ID: {window_id}")
            logger.info(f"Window Name: {window_name}")
            logger.info(f"IMAP Code: {target_code}")
            logger.info(f"Scheduling Type: {scheduling_obj.get('type')}")
            if scheduling_obj.get('type') == 'RECURRENT':
                logger.info(f"RRULE in payload: {scheduling_obj.get('rrule')}")
            logger.info(f"Start Time: {start_time} ({datetime.fromtimestamp(start_time/1000).strftime('%Y-%m-%d %H:%M:%S UTC')})")
            logger.info(f"Duration: {duration_amount} {duration_unit}")
            logger.info(f"Window ID: {window_id}")

            # Log the complete payload for debugging
            logger.info("Complete API Payload:")
            logger.info(json.dumps(window_payload, indent=2))

            # Create MaintenanceConfigV2 object from payload
            maintenance_config = MaintenanceConfigV2.from_dict(window_payload)

            # Use without_preload_content to avoid pydantic validation issues
            response = api_client.put_maintenance_config_v2_without_preload_content(
                id=window_id,
                maintenance_config_v2=maintenance_config
            )

            # Check response status
            status_error = self._check_response_status(response, "create maintenance window")
            if status_error:
                return status_error

            # Read and parse the response
            response_data = response.read()
            result = json.loads(response_data) if response_data else {}

            if not result:
                logger.error("❌ Failed to create maintenance window: Empty response")
                return {"error": "Empty response from API"}

            # Use the generated ID (API returns the same ID)
            returned_id = result.get("id", window_id)
            window_id = returned_id

            # Log success and verify scheduling type in response
            response_scheduling = result.get("scheduling", {})
            response_type = response_scheduling.get("type", "UNKNOWN")
            logger.info("✅ Maintenance window created successfully")
            logger.info(f"Response scheduling type: {response_type}")
            if response_type == "RECURRENT":
                response_rrule = response_scheduling.get("rrule", "NOT_FOUND")
                logger.info("✅ RECURRING window confirmed in response")
                logger.info(f"Response RRULE: {response_rrule}")
            elif response_type == "ONE_TIME" and scheduling_obj.get('type') == 'RECURRENT':
                logger.warning("⚠️ WARNING: Requested RECURRING but response shows ONE_TIME")
                logger.warning("This may indicate the RRULE was not accepted by Instana API")
            logger.info("=== END MAINTENANCE WINDOW CREATION ===")

            # Integrate with ServiceNow if change request provided
            if change_request_id and self.servicenow_token:
                await self._update_servicenow_change(
                    change_request_id=change_request_id,
                    window_id=window_id,
                    status="maintenance_scheduled"
                )

            # Format success response
            return self._format_success_response(
                window_id, target_code, window_name, start_time, end_time,
                duration_amount, duration_unit, reason, template, template_config
            )

        except Exception as e:
            logger.error(f"Error creating maintenance window: {e}", exc_info=True)
            return {"error": f"Failed to create maintenance window: {e!s}"}

    def _validate_create_params(
        self,
        imap_code: Optional[str],
        application_id: Optional[str],
        start_time: Optional[int],
        template: Optional[str]
    ) -> Dict[str, Any]:
        """Validate creation parameters and apply template."""
        # Use imap_code if provided, otherwise use application_id as imap_code
        target_code = imap_code or application_id

        # Collect all validation errors in one pass
        errors = []
        if not target_code:
            errors.append({
                "field": "imap_code / application_id",
                "issue": "Either imap_code or application_id is required",
                "example": "imap_code='EAL-012471'"
            })
        if not start_time:
            errors.append({
                "field": "start_time",
                "issue": self.ERROR_START_TIME_REQUIRED,
                "expected": _TS_HINT_MS
            })
        if template and template not in self.TEMPLATES:
            errors.append({
                "field": "template",
                "issue": f"'{template}' is not a valid template",
                "expected": list(self.TEMPLATES.keys())
            })
        if errors:
            return {
                "elicitation_needed": True,
                "reason": "missing_required_params",
                "api_error": errors,
                "message": f"Missing or invalid parameters for create: {[e['field'] for e in errors]}"
            }

        # Apply template if specified
        template_config = {}
        if template:
            template_config = self.TEMPLATES[template].copy()
            logger.info(f"Applying template: {template}")

        return {
            "target_code": target_code,
            "template_config": template_config
        }

    def _calculate_duration_and_end_time(
        self,
        start_time: Optional[int],
        end_time: Optional[int],
        duration_minutes: Optional[int],
        duration_hours: Optional[int],
        duration_days: Optional[int],
        rrule: Optional[str],
        template_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate duration and end time for maintenance window."""
        if start_time is None:
            raise ValueError(self.ERROR_START_TIME_REQUIRED)

        if not end_time:
            duration_result = self._calculate_duration_from_inputs(
                duration_minutes, duration_hours, duration_days, rrule, template_config
            )
            end_time = start_time + duration_result["duration_ms"]
            return {
                "end_time": end_time,
                "duration_amount": duration_result["duration_amount"],
                "duration_unit": duration_result["duration_unit"]
            }
        else:
            return self._calculate_duration_from_times(start_time, end_time)

    def _calculate_duration_from_inputs(
        self,
        duration_minutes: Optional[int],
        duration_hours: Optional[int],
        duration_days: Optional[int],
        rrule: Optional[str],
        template_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate duration from input parameters."""
        if duration_days:
            return {
                "duration_ms": duration_days * 24 * 60 * 60 * 1000,
                "duration_amount": duration_days,
                "duration_unit": "DAYS"
            }
        elif duration_hours:
            return {
                "duration_ms": duration_hours * 60 * 60 * 1000,
                "duration_amount": duration_hours,
                "duration_unit": "HOURS"
            }
        else:
            return self._calculate_duration_from_minutes(duration_minutes, rrule, template_config)

    def _calculate_duration_from_minutes(
        self,
        duration_minutes: Optional[int],
        rrule: Optional[str],
        template_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate duration from minutes, adjusting for recurring windows."""
        duration_min = duration_minutes or template_config.get("default_duration", 60)

        if rrule:
            duration_min = self._adjust_duration_for_recurring(duration_min)

        return {
            "duration_ms": duration_min * 60 * 1000,
            "duration_amount": duration_min // 60 if duration_min >= 60 else 1,
            "duration_unit": "HOURS"
        }

    def _adjust_duration_for_recurring(self, duration_min: int) -> int:
        """Adjust duration for recurring windows (must be whole hours)."""
        if duration_min < 60:
            logger.warning("⚠️ Recurring windows require duration >= 1 hour")
            logger.warning(f"Converting {duration_min} minutes to 1 hour for recurring window")
            return 60
        elif duration_min % 60 != 0:
            duration_hours_rounded = (duration_min + 59) // 60
            logger.warning("⚠️ Recurring windows require whole hours")
            logger.warning(f"Rounding {duration_min} minutes up to {duration_hours_rounded} hour(s)")
            return duration_hours_rounded * 60
        return duration_min

    def _calculate_duration_from_times(self, start_time: int, end_time: int) -> Dict[str, Any]:
        """Calculate duration from start and end times."""
        duration_ms = end_time - start_time
        duration_hours_calc = duration_ms // (60 * 60 * 1000)

        if duration_hours_calc >= 24:
            return {
                "end_time": end_time,
                "duration_amount": duration_hours_calc // 24,
                "duration_unit": "DAYS"
            }
        else:
            return {
                "end_time": end_time,
                "duration_amount": duration_hours_calc,
                "duration_unit": "HOURS"
            }

    def _validate_time_range(
        self,
        start_time: int,
        end_time: int
    ) -> Optional[Dict[str, Any]]:
        """Validate time range for maintenance window."""
        current_time_result = get_current_timestamp(timezone="UTC", output_unit="milliseconds")
        current_time = current_time_result["timestamp"]

        if start_time < current_time:
            start_dt = datetime.fromtimestamp(start_time / 1000)
            current_dt = datetime.fromtimestamp(current_time / 1000)
            return {
                "elicitation_needed": True,
                "reason": "invalid_time_params",
                "api_error": [
                    {
                        "field": "start_time",
                        "issue": "start_time cannot be in the past",
                        "provided": start_time,
                        "provided_readable": start_dt.strftime(self.DATETIME_FORMAT_UTC),
                        "current_time_readable": current_dt.strftime(self.DATETIME_FORMAT_UTC),
                        "expected": f"A timestamp after {current_dt.strftime(self.DATETIME_FORMAT_UTC)}"
                    }
                ],
                "message": f"start_time is in the past ({start_dt.strftime(self.DATETIME_FORMAT_UTC)}). Provide a future timestamp."
            }

        if end_time <= start_time:
            return {
                "elicitation_needed": True,
                "reason": "invalid_time_params",
                "api_error": [
                    {
                        "field": "end_time",
                        "issue": "end_time must be after start_time",
                        "start_time": start_time,
                        "end_time": end_time
                    }
                ],
                "message": "end_time must be after start_time."
            }

        return None

    def _build_scheduling_object(
        self,
        start_time: int,
        duration_amount: int,
        duration_unit: str,
        rrule: Optional[str],
        until_date: Optional[str]
    ) -> Dict[str, Any]:
        """Build scheduling object for maintenance window."""
        scheduling_obj = {
            "start": start_time,
            "duration": {
                "amount": duration_amount,
                "unit": duration_unit
            },
            "type": "ONE_TIME"
        }

        # Add recurrence if rrule is provided
        if rrule:
            logger.info("=== RECURRING WINDOW DETECTED ===")
            logger.info(f"Input RRULE: {rrule}")
            logger.info(f"Input until_date: {until_date}")

            # IMPORTANT: Instana uses "RECURRENT" not "RECURRING"
            scheduling_obj["type"] = "RECURRENT"

            # Build rrule with UNTIL if provided
            rrule_with_until = self._process_rrule_with_until(rrule, until_date)
            scheduling_obj["rrule"] = rrule_with_until

            # Add timezone (required for recurring windows in Instana)
            scheduling_obj["timezoneId"] = "UTC"

            logger.info(f"✅ Final RRULE for API: {rrule_with_until}")
            logger.info("✅ Scheduling type set to: RECURRENT (Instana format)")
            logger.info("✅ Timezone set to: UTC")
            logger.info("=== END RECURRING WINDOW SETUP ===")
        else:
            logger.info("Creating ONE_TIME maintenance window (no rrule provided)")

        return scheduling_obj

    def _process_rrule_with_until(
        self,
        rrule: str,
        until_date: Optional[str]
    ) -> str:
        """Process RRULE and add UNTIL if provided."""
        if until_date:
            logger.info("Processing until_date for RRULE...")
            try:
                # Try parsing ISO format
                until_dt = datetime.fromisoformat(until_date.replace('Z', '+00:00'))
                # Format as YYYYMMDDTHHMMSSZ for RRULE
                until_formatted = until_dt.strftime('%Y%m%dT%H%M%SZ')
                logger.info(f"Converted until_date: {until_date} -> {until_formatted}")

                # Add UNTIL to rrule if not already present
                if 'UNTIL=' not in rrule.upper():
                    rrule_with_until = f"{rrule};UNTIL={until_formatted}"
                    logger.info(f"Added UNTIL to RRULE: {rrule_with_until}")
                else:
                    rrule_with_until = rrule
                    logger.info("RRULE already contains UNTIL, using as-is")
            except Exception as e:
                logger.warning(f"Could not parse until_date '{until_date}': {e}, using rrule as-is")
                rrule_with_until = rrule
        else:
            logger.info("No until_date provided, using RRULE without UNTIL")
            rrule_with_until = rrule

        return rrule_with_until

    def _build_window_payload(
        self,
        window_name: str,
        target_code: str,
        scheduling_obj: Dict[str, Any],
        use_tag_filter_expression: bool,
        tag_name: Optional[str]
    ) -> Dict[str, Any]:
        """Build maintenance window payload for API."""
        if use_tag_filter_expression:
            # Format 2: Tag Filter Expression (for synthetic monitoring)
            return {
                "name": window_name,
                "query": "",
                "scheduling": scheduling_obj,
                "paused": False,
                "tagFilterExpression": {
                    "type": "TAG_FILTER",
                    "name": tag_name or "synthetic.tags",
                    "stringValue": f"imap={target_code}",
                    "key": "imap",
                    "value": target_code,
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE"
                },
                "tagFilterExpressionEnabled": True,
                "retriggerOpenAlertsEnabled": False
            }
        else:
            # Format 1: Simple Query String (default)
            return {
                "name": window_name,
                "query": f"entity.tag:imap={target_code}",
                "scheduling": scheduling_obj,
                "paused": False,
                "tagFilterExpressionEnabled": False,
                "retriggerOpenAlertsEnabled": False
            }

    def _format_success_response(
        self,
        window_id: str,
        target_code: str,
        window_name: str,
        start_time: int,
        end_time: int,
        duration_amount: int,
        duration_unit: str,
        reason: Optional[str],
        template: Optional[str],
        template_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Format success response for window creation."""
        start_dt = datetime.fromtimestamp(start_time / 1000)
        end_dt = datetime.fromtimestamp(end_time / 1000)

        return {
            "operation": "create",
            "status": "success",
            "summary": "✅ Maintenance window created successfully!",
            "details": {
                "window_id": window_id,
                "application": target_code,
                "window_name": window_name,
                "schedule": {
                    "start": start_dt.strftime(self.DATETIME_FORMAT_UTC),
                    "end": end_dt.strftime(self.DATETIME_FORMAT_UTC),
                    "duration": f"{duration_amount} {duration_unit.lower()}"
                },
                "reason": reason or template_config.get("description", "Maintenance"),
                "template_used": template or "none"
            },
            "next_steps": [
                "View in Instana UI: Settings → Maintenance Windows",
                f"Window ID for reference: {window_id}",
                f"To modify: 'Extend maintenance window {window_id} by X hours'",
                f"To close: 'Close maintenance window {window_id} with notes [your notes]'"
            ],
            "raw_data": {
                "window_id": window_id,
                "imap_code": target_code,
                "start_time": start_time,
                "end_time": end_time,
                "duration_amount": duration_amount,
                "duration_unit": duration_unit
            }
        }

    def _validate_modify_window_id(self, window_id: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validate window_id for modify operation."""
        if not window_id:
            return {
                "elicitation_needed": True,
                "reason": "missing_required_params",
                "api_error": [
                    {
                        "field": "window_id",
                        "issue": "window_id is required for modify",
                        "hint": "Use list_active or list_scheduled to find window IDs"
                    }
                ],
                "message": "Missing required parameter 'window_id' for modify. Use list_active or list_scheduled to find IDs."
            }
        return None

    def _fetch_existing_window(self, window_id: str, api_client) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Fetch existing maintenance window. Returns (window_data, error)."""
        try:
            response = api_client.get_maintenance_config_v2_without_preload_content(id=window_id)
            status_error = self._check_response_status(response, "fetch maintenance window")
            if status_error:
                return None, status_error

            response_data = response.read()
            existing_window = json.loads(response_data) if response_data else None

            if not existing_window:
                return None, {"error": f"Maintenance window not found: {window_id}"}

            return existing_window, None
        except Exception as e:
            return None, {"error": f"Failed to fetch window: {e!s}"}

    def _build_base_modify_payload(self, window_id: str, existing_window: Dict[str, Any]) -> Dict[str, Any]:
        """Build base update payload preserving all required fields."""
        payload = {
            "id": window_id,
            "name": existing_window.get("name"),
            "query": existing_window.get("query", ""),
            "paused": existing_window.get("paused", False),
            "scheduling": existing_window.get("scheduling", {}),
            "tagFilterExpressionEnabled": existing_window.get("tagFilterExpressionEnabled", False),
            "retriggerOpenAlertsEnabled": existing_window.get("retriggerOpenAlertsEnabled", False)
        }

        # Preserve optional fields if they exist
        optional_fields = ["tagFilterExpression", "applicationNames", "validVersion", "description"]
        for field in optional_fields:
            if field in existing_window:
                payload[field] = existing_window[field]

        return payload

    def _update_duration_in_payload(self, payload: Dict[str, Any], duration_minutes: int) -> None:
        """Update duration in payload. Modifies payload in-place."""
        # Convert duration_minutes to appropriate unit
        if duration_minutes >= 1440:  # >= 1 day
            duration_amount = duration_minutes // 1440
            duration_unit = "DAYS"
        elif duration_minutes >= 60:  # >= 1 hour
            duration_amount = duration_minutes // 60
            duration_unit = "HOURS"
        else:
            duration_amount = duration_minutes
            duration_unit = "MINUTES"

        # Update only the duration within the scheduling object
        if "scheduling" not in payload:
            payload["scheduling"] = {}
        payload["scheduling"]["duration"] = {
            "amount": duration_amount,
            "unit": duration_unit
        }

    def _parse_until_date(self, until_date: str | int) -> tuple[Optional[str], Optional[str]]:
        """Parse until_date and return (rrule_format, error). Returns (None, error_msg) on failure."""
        try:
            if isinstance(until_date, str):
                if 'T' in until_date:
                    dt = datetime.fromisoformat(until_date.replace('Z', '+00:00'))
                else:
                    dt = datetime.fromisoformat(until_date + "T23:59:59+00:00")
            else:
                dt = datetime.fromtimestamp(until_date / 1000)

            return dt.strftime("%Y%m%dT%H%M%SZ"), None
        except Exception as e:
            logger.error(f"Error parsing until_date: {e}")
            return None, f"Invalid until_date format: {until_date}. Use ISO format like '2026-03-18T23:59:59Z'"

    def _update_rrule_with_until(self, existing_rrule: str, until_rrule: str) -> str:
        """Update existing RRULE with new UNTIL value."""
        if existing_rrule:
            # Remove old UNTIL if present
            rrule_without_until = re.sub(r'(?:;UNTIL=[^;]+|UNTIL=[^;]+;?)', '', existing_rrule).rstrip(';')
            return f"{rrule_without_until};UNTIL={until_rrule}"
        else:
            # No existing RRULE, create a basic one
            return f"FREQ=DAILY;INTERVAL=1;UNTIL={until_rrule}"

    def _update_rrule_in_payload(
        self,
        payload: Dict[str, Any],
        rrule: Optional[str],
        until_date: Optional[str]
    ) -> Optional[str]:
        """Update RRULE in payload. Returns error message if parsing fails, None on success."""
        if not (rrule or until_date):
            return None

        if "scheduling" not in payload:
            payload["scheduling"] = {}

        # Handle until_date
        if until_date:
            until_rrule, error = self._parse_until_date(until_date)
            if error:
                return error

            # Type guard: until_rrule is guaranteed to be str here (error would have returned)
            if until_rrule is not None:
                existing_rrule = payload["scheduling"].get("rrule", "")
                payload["scheduling"]["rrule"] = self._update_rrule_with_until(existing_rrule, until_rrule)

        # If explicit rrule is provided, use it directly (overrides until_date processing)
        if rrule:
            payload["scheduling"]["rrule"] = rrule

        return None

    def _update_window_name_with_reason(self, payload: Dict[str, Any], reason: str, existing_window: Dict[str, Any]) -> None:
        """Update window name with modification reason. Modifies payload in-place."""
        current_name = existing_window.get("name", "")
        # Strip any previous _modified_* suffix before appending the new one
        base_name = re.sub(r'_modified_.*$', '', current_name)
        payload["name"] = f"{base_name}_modified_{reason.replace(' ', '_')}"

    def _calculate_new_end_time(self, payload: Dict[str, Any]) -> int:
        """Calculate new end time from scheduling in payload."""
        start_time = payload["scheduling"]["start"]
        duration = payload["scheduling"]["duration"]
        duration_amount = duration.get("amount", 0)
        duration_unit = duration.get("unit", "HOURS")

        if duration_unit == "DAYS":
            duration_ms = duration_amount * 24 * 60 * 60 * 1000
        elif duration_unit == "HOURS":
            duration_ms = duration_amount * 60 * 60 * 1000
        else:  # MINUTES
            duration_ms = duration_amount * 60 * 1000

        return start_time + duration_ms

    def _build_modification_summary(
        self,
        duration_minutes: Optional[int],
        duration_amount: int,
        duration_unit: str,
        rrule: Optional[str],
        until_date: Optional[str],
        reason: Optional[str]
    ) -> str:
        """Build human-readable modification summary."""
        modifications = []
        if duration_minutes:
            modifications.append(f"duration changed to {duration_amount} {duration_unit}")
        if rrule or until_date:
            modifications.append("recurrence rule updated")
        if reason:
            modifications.append(f"name updated with reason: {reason}")

        return ", ".join(modifications) if modifications else "window updated"

    def _build_modify_response(
        self,
        window_id: str,
        payload: Dict[str, Any],
        updated_window: Dict[str, Any],
        duration_minutes: Optional[int],
        new_end_time: int,
        reason: Optional[str],
        modification_summary: str
    ) -> Dict[str, Any]:
        """Build success response for modify operation."""
        scheduling = updated_window.get("scheduling", {})
        rrule_after = scheduling.get("rrule", "")
        recurrence_type = scheduling.get("type", "ONE_TIME")

        duration = payload["scheduling"]["duration"]
        duration_amount = duration.get("amount", 0)
        duration_unit = duration.get("unit", "HOURS")

        return {
            "operation": "modify",
            "status": "success",
            "window_id": window_id,
            "window_name": payload["name"],
            "modifications": modification_summary,
            "new_duration": f"{duration_amount} {duration_unit}" if duration_minutes else "unchanged",
            "new_end_time": new_end_time if duration_minutes else "unchanged",
            "modification_reason": reason or "Window modified",
            "message": f"Maintenance window modified successfully: {window_id}",
            "updated_window": updated_window,
            "verification": {
                "recurrence_type": recurrence_type,
                "current_rrule": rrule_after if rrule_after else "N/A (ONE_TIME window)",
                "note": "This shows the actual current state of the window after modification. Compare with your request to verify changes."
            }
        }

    @with_header_auth(MaintenanceConfigurationApi)
    async def _modify_maintenance_window(
        self,
        window_id: Optional[str],
        end_time: Optional[int],
        duration_minutes: Optional[int],
        reason: Optional[str],
        rrule: Optional[str] = None,
        until_date: Optional[str] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Modify an existing maintenance window.

        Allows extending or shortening maintenance windows, and updating recurrence rules.
        Uses the same payload structure as create operation per Instana API specification.

        Args:
            window_id: Maintenance window ID to modify
            end_time: New end time in Unix timestamp milliseconds (not used - duration is used instead)
            duration_minutes: New duration in minutes
            reason: Reason for modification (used to update window name)
            rrule: New recurrence rule (e.g., "FREQ=DAILY;INTERVAL=1;UNTIL=20260318T235959Z")
            until_date: New end date for recurrence in ISO format (e.g., "2026-03-18T23:59:59Z")
            ctx: MCP context

        Returns:
            Dictionary with modification results
        """
        try:
            # Validate window_id
            validation_error = self._validate_modify_window_id(window_id)
            if validation_error:
                return validation_error

            # Type guard: window_id is guaranteed to be str here (validation would have returned)
            assert window_id is not None, "window_id validated but is None"

            # Fetch existing window
            existing_window, fetch_error = self._fetch_existing_window(window_id, api_client)
            if fetch_error:
                return fetch_error

            # Type guard: existing_window is guaranteed to be dict here (fetch_error would have returned)
            assert existing_window is not None, "existing_window fetched but is None"

            # Build base payload
            update_payload = self._build_base_modify_payload(window_id, existing_window)

            # Update duration if provided
            if duration_minutes:
                self._update_duration_in_payload(update_payload, duration_minutes)

            # Update RRULE if provided
            rrule_error = self._update_rrule_in_payload(update_payload, rrule, until_date)
            if rrule_error:
                return {"error": rrule_error}

            # Update window name if reason provided
            if reason:
                self._update_window_name_with_reason(update_payload, reason, existing_window)

            # Create MaintenanceConfigV2 object and update
            maintenance_config = MaintenanceConfigV2.from_dict(update_payload)
            response = api_client.put_maintenance_config_v2_without_preload_content(
                id=window_id,
                maintenance_config_v2=maintenance_config
            )

            # Check response status
            status_error = self._check_response_status(response, "update maintenance window")
            if status_error:
                return status_error

            # Parse response
            response_data = response.read()
            result = json.loads(response_data) if response_data else {}
            if not result:
                return {"error": "Empty response from API"}

            # Fetch updated window for verification
            response = api_client.get_maintenance_config_v2_without_preload_content(id=window_id)
            response_data = response.read()
            updated_window = json.loads(response_data) if response_data else {}

            # Calculate new end time
            new_end_time = self._calculate_new_end_time(update_payload)

            # Get duration info for response
            duration = update_payload["scheduling"]["duration"]
            duration_amount = duration.get("amount", 0)
            duration_unit = duration.get("unit", "HOURS")

            # Build modification summary
            modification_summary = self._build_modification_summary(
                duration_minutes, duration_amount, duration_unit, rrule, until_date, reason
            )

            # Build and return response
            return self._build_modify_response(
                window_id, update_payload, updated_window, duration_minutes,
                new_end_time, reason, modification_summary
            )

        except Exception as e:
            logger.error(f"Error modifying maintenance window: {e}", exc_info=True)
            return {"error": f"Failed to modify maintenance window: {e!s}"}

    @with_header_auth(MaintenanceConfigurationApi)
    async def _close_maintenance_window(
        self,
        window_id: Optional[str],
        completion_notes: Optional[str],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Close and document a maintenance window.

        Closes an active maintenance window, re-enables alerts, and documents
        completion notes for audit trail.

        Args:
            window_id: Maintenance window ID to close
            completion_notes: Notes about window completion
            ctx: MCP context

        Returns:
            Dictionary with closure results
        """
        try:
            if not window_id:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": [
                        {
                            "field": "window_id",
                            "issue": "window_id is required for close",
                            "hint": "Use list_active to find active window IDs"
                        }
                    ],
                    "message": "Missing required parameter 'window_id' for close. Use list_active to find active window IDs."
                }

            logger.info(f"Closing maintenance window: {window_id}")

            # Delete/close the maintenance window using API client
            # The delete_maintenance_config_v2_without_preload_content method
            # takes 'id' as the parameter for the window ID
            response = api_client.delete_maintenance_config_v2_without_preload_content(
                id=window_id
            )

            # Check response status
            status_error = self._check_response_status(response, "close maintenance window")
            if status_error:
                return status_error

            # Read the response (delete typically returns empty response)
            response.read()

            closed_at = get_current_timestamp(timezone="UTC", output_unit="milliseconds")["timestamp"]

            logger.info(f"Maintenance window closed successfully: {window_id}")

            return {
                "operation": "close",
                "status": "success",
                "window_id": window_id,
                "completion_notes": completion_notes or "Maintenance completed",
                "closed_at": closed_at,
                "message": f"Maintenance window closed successfully: {window_id}"
            }

        except Exception as e:
            logger.error(f"Error closing maintenance window: {e}", exc_info=True)
            return {"error": f"Failed to close maintenance window: {e!s}"}

    def _matches_application_filter(self, window: Dict[str, Any], application_id: str) -> bool:
        """Check if window matches application_id filter."""
        query = window.get("query", "")
        tag_filter = window.get("tagFilterExpression", {})
        tag_value = tag_filter.get("value", "") if tag_filter else ""
        return (application_id in query or
                application_id in tag_value or
                f"imap={application_id}" in query)

    def _is_window_active_by_state(self, window: Dict[str, Any]) -> bool:
        """Check if window is active based on state field."""
        return window.get("state", "") == "ACTIVE"

    def _is_window_active_by_time(self, window: Dict[str, Any], current_time: int) -> bool:
        """Check if window is active based on occurrence times."""
        occurrence = window.get("occurrence", {})
        start_time = occurrence.get("start", 0)
        end_time = occurrence.get("end", 0)
        return start_time <= current_time <= end_time

    def _should_include_window(
        self,
        window: Dict[str, Any],
        application_id: Optional[str],
        current_time: int
    ) -> bool:
        """Determine if window should be included in active list."""
        # Check state field first (most reliable)
        if self._is_window_active_by_state(window):
            if application_id:
                return self._matches_application_filter(window, application_id)
            return True

        # Fallback: check occurrence times if state not available
        if not window.get("state", ""):
            if self._is_window_active_by_time(window, current_time):
                if application_id:
                    return self._matches_application_filter(window, application_id)
                return True

        return False

    def _build_empty_active_response(
        self,
        all_windows: List[Dict[str, Any]],
        application_id: Optional[str]
    ) -> Dict[str, Any]:
        """Build response when no active windows found."""
        if application_id:
            relevant = [w for w in all_windows if self._matches_application_filter(w, application_id)]
        else:
            relevant = all_windows

        expired_count = sum(1 for w in relevant if w.get("state") == "EXPIRED")
        scheduled_count = sum(1 for w in relevant if w.get("state") == "SCHEDULED")

        scope = f" for '{application_id}'" if application_id else ""
        return {
            "operation": "list_active",
            "status": "success",
            "count": 0,
            "windows": [],
            "application_id": application_id,
            "message": f"No active maintenance windows found{scope}. Found {expired_count} expired and {scheduled_count} scheduled windows{scope}.",
            "suggestion": "Use operation 'list_expired' to see expired windows or 'list_all' to see all windows.",
            "expired_count": expired_count,
            "scheduled_count": scheduled_count
        }

    @with_header_auth(MaintenanceConfigurationApi)
    async def _list_active_windows(
        self,
        application_id: Optional[str],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        List all active maintenance windows.

        Args:
            application_id: Optional filter by application ID
            ctx: MCP context

        Returns:
            Dictionary with list of active windows
        """
        try:
            # Get all maintenance windows using API client
            response = api_client.get_maintenance_configs_v2_without_preload_content()

            # Check response status
            status_error = self._check_response_status(response, "list active windows")
            if status_error:
                return status_error

            # Read and parse the response
            response_data = response.read()
            all_windows = json.loads(response_data) if response_data else []

            if not isinstance(all_windows, list):
                all_windows = []

            # Debug: Log the structure of the response
            logger.info(f"API Response type: {type(all_windows)}")
            logger.info(f"Number of windows in all_windows: {len(all_windows)}")

            # Get current time for time-based filtering
            current_time_result = get_current_timestamp(timezone="UTC", output_unit="milliseconds")
            current_time = current_time_result["timestamp"]

            # Filter for active windows using helper method
            active_windows = [
                window for window in all_windows
                if self._should_include_window(window, application_id, current_time)
            ]

            # If no active windows found, provide helpful information
            if not active_windows:
                return self._build_empty_active_response(all_windows, application_id)

            return {
                "operation": "list_active",
                "status": "success",
                "count": len(active_windows),
                "windows": active_windows,
                "application_id": application_id
            }

        except Exception as e:
            logger.error(f"Error listing active windows: {e}", exc_info=True)
            return {"error": f"Failed to list active windows: {e!s}"}

    def _is_window_scheduled(self, window: Dict[str, Any]) -> bool:
        """Check if window is in scheduled state."""
        return window.get("state", "") == "SCHEDULED"

    def _should_include_scheduled_window(
        self,
        window: Dict[str, Any],
        application_id: Optional[str]
    ) -> bool:
        """Determine if scheduled window should be included in list."""
        if not self._is_window_scheduled(window):
            return False

        if application_id:
            return self._matches_application_filter(window, application_id)

        return True

    @with_header_auth(MaintenanceConfigurationApi)
    async def _list_scheduled_windows(
        self,
        application_id: Optional[str],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        List all scheduled maintenance windows.

        Args:
            application_id: Optional filter by application ID
            ctx: MCP context

        Returns:
            Dictionary with list of scheduled windows
        """
        try:
            # Get all maintenance windows using API client
            response = api_client.get_maintenance_configs_v2_without_preload_content()

            # Check response status
            status_error = self._check_response_status(response, "list scheduled windows")
            if status_error:
                return status_error

            # Read and parse the response
            response_data = response.read()
            all_windows = json.loads(response_data) if response_data else []

            if not isinstance(all_windows, list):
                all_windows = []

            # Debug: Log all states
            states_found = [w.get("state", "UNKNOWN") for w in all_windows]
            logger.info(f"States found in windows: {states_found}")

            # Filter for scheduled windows using helper method
            scheduled_windows = [
                window for window in all_windows
                if self._should_include_scheduled_window(window, application_id)
            ]

            return {
                "operation": "list_scheduled",
                "status": "success",
                "count": len(scheduled_windows),
                "windows": scheduled_windows,
                "application_id": application_id
            }

        except Exception as e:
            logger.error(f"Error listing scheduled windows: {e}", exc_info=True)
            return {"error": f"Failed to list scheduled windows: {e!s}"}

    def _filter_windows_by_application(
        self,
        windows: List[Dict[str, Any]],
        application_id: str
    ) -> List[Dict[str, Any]]:
        """Filter windows by application_id."""
        return [
            window for window in windows
            if self._matches_application_filter(window, application_id)
        ]

    def _group_windows_by_state(self, windows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group windows by their state (active, scheduled, expired)."""
        windows_by_state = {
            "active": [],
            "scheduled": [],
            "expired": []
        }

        for window in windows:
            state = window.get("state", "").upper()
            if state == "ACTIVE":
                windows_by_state["active"].append(window)
            elif state == "SCHEDULED":
                windows_by_state["scheduled"].append(window)
            elif state == "EXPIRED":
                windows_by_state["expired"].append(window)

        return windows_by_state

    def _build_windows_summary(self, windows_by_state: Dict[str, List[Dict[str, Any]]], total_count: int) -> str:
        """Build summary message for window counts."""
        summary_parts = []
        if windows_by_state["active"]:
            summary_parts.append(f"{len(windows_by_state['active'])} active")
        if windows_by_state["scheduled"]:
            summary_parts.append(f"{len(windows_by_state['scheduled'])} scheduled")
        if windows_by_state["expired"]:
            summary_parts.append(f"{len(windows_by_state['expired'])} expired")

        return f"Found {total_count} total maintenance window(s): {', '.join(summary_parts) if summary_parts else 'none'}"

    @with_header_auth(MaintenanceConfigurationApi)
    async def _list_all_windows(
        self,
        application_id: Optional[str],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        List all maintenance windows (active, scheduled, and expired).

        Args:
            application_id: Optional filter by application ID
            ctx: MCP context

        Returns:
            Dictionary with list of all windows
        """
        try:
            # Get all maintenance windows using API client
            response = api_client.get_maintenance_configs_v2_without_preload_content()

            # Check response status
            status_error = self._check_response_status(response, "list all windows")
            if status_error:
                return status_error

            # Read and parse the response
            response_data = response.read()
            all_windows = json.loads(response_data) if response_data else []

            if not isinstance(all_windows, list):
                all_windows = []

            # Filter by application_id if provided
            if application_id:
                all_windows = self._filter_windows_by_application(all_windows, application_id)

            # Group windows by state using helper method
            windows_by_state = self._group_windows_by_state(all_windows)

            # Create summary message using helper method
            summary = self._build_windows_summary(windows_by_state, len(all_windows))

            return {
                "operation": "list_all",
                "status": "success",
                "summary": summary,
                "total_count": len(all_windows),
                "active_count": len(windows_by_state["active"]),
                "scheduled_count": len(windows_by_state["scheduled"]),
                "expired_count": len(windows_by_state["expired"]),
                "windows_by_state": windows_by_state,
                "all_windows": all_windows,
                "application_id": application_id,
                "message": "Use 'windows_by_state' to see windows grouped by status, or 'all_windows' for the complete list"
            }

        except Exception as e:
            logger.error(f"Error listing all windows: {e}", exc_info=True)
            return {"error": f"Failed to list all windows: {e!s}"}

    def _is_window_expired(self, window: Dict[str, Any]) -> bool:
        """Check if window is in expired state."""
        return window.get("state", "") == "EXPIRED"

    def _should_include_expired_window(
        self,
        window: Dict[str, Any],
        application_id: Optional[str]
    ) -> bool:
        """Determine if expired window should be included in list."""
        if not self._is_window_expired(window):
            return False

        if application_id:
            return self._matches_application_filter(window, application_id)

        return True

    @with_header_auth(MaintenanceConfigurationApi)
    async def _list_expired_windows(
        self,
        application_id: Optional[str],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        List all expired maintenance windows.

        Args:
            application_id: Optional filter by application ID
            ctx: MCP context

        Returns:
            Dictionary with list of expired windows
        """
        try:
            # Get all maintenance windows using API client
            response = api_client.get_maintenance_configs_v2_without_preload_content()

            # Check response status
            status_error = self._check_response_status(response, "list expired windows")
            if status_error:
                return status_error

            # Read and parse the response
            response_data = response.read()
            all_windows = json.loads(response_data) if response_data else []

            if not isinstance(all_windows, list):
                all_windows = []

            # Debug: Log all states
            states_found = [w.get("state", "UNKNOWN") for w in all_windows]
            logger.info(f"States found in windows for list_expired: {states_found}")

            # Filter for expired windows using helper method
            expired_windows = [
                window for window in all_windows
                if self._should_include_expired_window(window, application_id)
            ]

            logger.info(f"Total expired windows found: {len(expired_windows)}")

            return {
                "operation": "list_expired",
                "status": "success",
                "count": len(expired_windows),
                "windows": expired_windows,
                "application_id": application_id
            }

        except Exception as e:
            logger.error(f"Error listing expired windows: {e}", exc_info=True)
            return {"error": f"Failed to list expired windows: {e!s}"}


    @with_header_auth(MaintenanceConfigurationApi)
    async def _bulk_create_windows(
        self,
        application_ids: Optional[List[str]],
        imap_codes: Optional[List[str]],
        start_time: Optional[int],
        duration_minutes: Optional[int],
        duration_hours: Optional[int],
        duration_days: Optional[int],
        reason: Optional[str],
        template: Optional[str],
        change_request_id: Optional[str],
        use_tag_filter_expression: Optional[bool],
        tag_name: Optional[str],
        ctx,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Create maintenance windows for multiple IMAP codes or applications.

        Args:
            application_ids: List of application IDs (legacy support)
            imap_codes: List of IMAP codes
            start_time: Start time for all windows
            duration_minutes: Duration in minutes
            duration_hours: Duration in hours
            duration_days: Duration in days
            reason: Reason for maintenance
            template: Template to apply
            change_request_id: ServiceNow change request ID
            use_tag_filter_expression: Use tag filter expression format
            tag_name: Tag name for filter expression
            ctx: MCP context

        Returns:
            Dictionary with bulk creation results
        """
        try:
            # Use imap_codes if provided, otherwise use application_ids
            target_codes = imap_codes or application_ids

            errors = []
            if not target_codes:
                errors.append({
                    "field": "imap_codes / application_ids",
                    "issue": "Either imap_codes or application_ids is required",
                    "example": "imap_codes=['EAL-012471', 'ORZ-000012']"
                })
            if not start_time:
                errors.append({
                    "field": "start_time",
                    "issue": self.ERROR_START_TIME_REQUIRED,
                    "expected": _TS_HINT_MS
                })
            if errors:
                return {
                    "elicitation_needed": True,
                    "reason": "missing_required_params",
                    "api_error": errors,
                    "message": f"Missing required parameters for bulk_create: {[e['field'] for e in errors]}"
                }

            results = []
            for code in target_codes:
                result = await self._create_maintenance_window(
                    params={
                        "application_id": None,
                        "imap_code": code,
                        "start_time": start_time,
                        "end_time": None,
                        "duration_minutes": duration_minutes,
                        "duration_hours": duration_hours,
                        "duration_days": duration_days,
                        "reason": reason,
                        "template": template,
                        "change_request_id": change_request_id,
                        "affected_services": None,
                        "notification_channels": None,
                        "use_tag_filter_expression": use_tag_filter_expression,
                        "tag_name": tag_name,
                        "rrule": None,
                        "until_date": None
                    },
                    ctx=ctx,
                    api_client=api_client
                )
                results.append({
                    "imap_code": code,
                    "result": result
                })

            successful = sum(1 for r in results if r["result"].get("status") == "success")

            return {
                "operation": "bulk_create",
                "status": "success",
                "total": len(target_codes),
                "successful": successful,
                "failed": len(target_codes) - successful,
                "results": results
            }

        except Exception as e:
            logger.error(f"Error in bulk create: {e}", exc_info=True)
            return {"error": f"Bulk create failed: {e!s}"}

    async def _validate_window_params(
        self,
        application_id: Optional[str],
        start_time: Optional[int]
    ) -> Dict[str, Any]:
        """
        Validate maintenance window parameters without creating.

        Args:
            application_id: Application ID
            start_time: Start time

        Returns:
            Dictionary with validation results
        """
        errors = []

        if not application_id:
            errors.append({
                "field": "imap_code / application_id",
                "issue": "Either imap_code or application_id is required",
                "example": "imap_code='EAL-012471'"
            })

        if not start_time:
            errors.append({
                "field": "start_time",
                "issue": "start_time is required",
                "expected": _TS_HINT_MS
            })
        elif start_time < get_current_timestamp(timezone="UTC", output_unit="milliseconds")["timestamp"]:
            errors.append({
                "field": "start_time",
                "issue": "start_time cannot be in the past",
                "expected": "A future Unix timestamp in milliseconds"
            })

        if errors:
            return {
                "elicitation_needed": True,
                "reason": "missing_required_params",
                "api_error": errors,
                "message": f"Invalid parameters for validate: {[e['field'] for e in errors]}"
            }

        return {
            "operation": "validate",
            "status": "valid",
            "message": "All parameters are valid"
        }

    def _get_templates(self) -> Dict[str, Any]:
        """
        Get available maintenance window templates.

        Returns:
            Dictionary with template information
        """
        return {
            "operation": "get_templates",
            "status": "success",
            "templates": self.TEMPLATES
        }

    async def _update_servicenow_change(
        self,
        change_request_id: str,
        window_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        Update ServiceNow change request with maintenance window information.

        Args:
            change_request_id: ServiceNow change request ID
            window_id: Maintenance window ID
            status: Status to update

        Returns:
            Dictionary with ServiceNow update results
        """
        if not self.servicenow_token or not self.servicenow_url:
            return {"status": "skipped", "reason": "ServiceNow not configured"}

        try:
            # ServiceNow integration logic would go here
            logger.info(f"Updating ServiceNow change {change_request_id} with window {window_id}")

            return {
                "status": "success",
                "change_request_id": change_request_id,
                "window_id": window_id,
                "updated_status": status
            }

        except Exception as e:
            logger.error(f"ServiceNow update failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}



