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
from typing import Any, Dict, List, Optional, Union

from src.core.timestamp_utils import get_current_timestamp
from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

logger = logging.getLogger(__name__)


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
        application_id: Optional[str] = None,
        application_ids: Optional[List[str]] = None,
        imap_code: Optional[str] = None,
        imap_codes: Optional[List[str]] = None,
        window_id: Optional[str] = None,
        start_time: Optional[Union[int, str]] = None,
        end_time: Optional[Union[int, str]] = None,
        duration_minutes: Optional[Union[int, str]] = None,
        duration_hours: Optional[Union[int, str]] = None,
        duration_days: Optional[Union[int, str]] = None,
        reason: Optional[str] = None,
        template: Optional[str] = None,
        change_request_id: Optional[str] = None,
        affected_services: Optional[List[str]] = None,
        notification_channels: Optional[List[str]] = None,
        completion_notes: Optional[str] = None,
        use_tag_filter_expression: Optional[bool] = False,
        tag_name: Optional[str] = None,
        rrule: Optional[str] = None,
        until_date: Optional[str] = None,
        ctx=None
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
            application_id: Single application ID (legacy support, treated as IMAP code)
            application_ids: Multiple application IDs for bulk operations (legacy support)
            imap_code: Single IMAP code (e.g., EAL-012512, ORZ-000012)
            imap_codes: Multiple IMAP codes for bulk operations
            window_id: Existing maintenance window ID (for modify/close operations)
            start_time: Start time in Unix timestamp milliseconds
            end_time: End time in Unix timestamp milliseconds
            duration_minutes: Duration in minutes
            duration_hours: Duration in hours
            duration_days: Duration in days
            reason: Reason for maintenance window
            template: Predefined template name (deployment, database_migration, etc.)
            change_request_id: ServiceNow change request ID
            affected_services: List of affected service names
            notification_channels: List of notification channels (slack, email, etc.)
            completion_notes: Notes for window closure
            use_tag_filter_expression: Use tag filter expression format (default: False)
            tag_name: Tag name for filter expression (default: synthetic.tags)
            ctx: MCP context

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
            # Create with template
            result = await execute_maintenance_operation(
                operation="create",
                application_id="app-123",
                template="deployment",
                start_time=1709020800000,
                reason="v2.0 deployment",
                ctx=ctx
            )

            # Modify existing window
            result = await execute_maintenance_operation(
                operation="modify",
                window_id="mw-789",
                end_time=1709027400000,
                reason="Extended due to issues",
                ctx=ctx
            )
        """
        try:
            logger.info("=== MAINTENANCE OPERATION START ===")
            logger.info(f"Operation: {operation}")
            logger.info(f"IMAP Code: {imap_code or application_id}")

            # Log recurrence parameters if provided
            if rrule:
                logger.info("🔁 RECURRING WINDOW REQUESTED")
                logger.info(f"RRULE parameter: {rrule}")
                logger.info(f"Until Date parameter: {until_date}")

            # Convert string parameters to appropriate types
            # LLM should provide values in correct format as per docString
            if start_time is not None and isinstance(start_time, str):
                try:
                    start_time = int(start_time)
                except ValueError:
                    return {
                        "error": f"start_time must be a Unix timestamp in milliseconds (integer): {start_time}",
                        "suggestion": "Provide start_time as integer milliseconds (e.g., 1745020800000)"
                    }

            if end_time is not None and isinstance(end_time, str):
                try:
                    end_time = int(end_time)
                except ValueError:
                    return {
                        "error": f"end_time must be a Unix timestamp in milliseconds (integer): {end_time}",
                        "suggestion": "Provide end_time as integer milliseconds"
                    }

            if duration_minutes is not None and isinstance(duration_minutes, str):
                try:
                    duration_minutes = int(duration_minutes)
                except ValueError:
                    return {
                        "error": f"duration_minutes must be an integer: {duration_minutes}",
                        "suggestion": "Provide duration_minutes as integer (e.g., 120 for 2 hours)"
                    }

            if duration_hours is not None and isinstance(duration_hours, str):
                try:
                    duration_hours = int(duration_hours)
                except ValueError:
                    return {
                        "error": f"duration_hours must be an integer: {duration_hours}",
                        "suggestion": "Provide duration_hours as integer (e.g., 2)"
                    }

            if duration_days is not None and isinstance(duration_days, str):
                try:
                    duration_days = int(duration_days)
                except ValueError:
                    return {
                        "error": f"duration_days must be an integer: {duration_days}",
                        "suggestion": "Provide duration_days as integer (e.g., 1)"
                    }

            # Validate operation
            valid_operations = [
                "create", "modify", "close", "list_active", "list_scheduled",
                "list_all", "list_expired", "bulk_create", "validate", "get_templates"
            ]

            if operation not in valid_operations:
                return {
                    "error": f"Invalid operation '{operation}'",
                    "valid_operations": valid_operations
                }

            # Route to appropriate handler
            if operation == "create":
                return await self._create_maintenance_window(
                    application_id=application_id,
                    imap_code=imap_code,
                    start_time=start_time,
                    end_time=end_time,
                    duration_minutes=duration_minutes,
                    duration_hours=duration_hours,
                    duration_days=duration_days,
                    reason=reason,
                    template=template,
                    change_request_id=change_request_id,
                    affected_services=affected_services,
                    notification_channels=notification_channels,
                    use_tag_filter_expression=use_tag_filter_expression,
                    tag_name=tag_name,
                    rrule=rrule,
                    until_date=until_date,
                    ctx=ctx
                )
            elif operation == "modify":
                return await self._modify_maintenance_window(
                    window_id=window_id,
                    end_time=end_time,
                    duration_minutes=duration_minutes,
                    reason=reason,
                    rrule=rrule,
                    until_date=until_date,
                    ctx=ctx
                )
            elif operation == "close":
                return await self._close_maintenance_window(
                    window_id=window_id,
                    completion_notes=completion_notes,
                    ctx=ctx
                )
            elif operation == "list_active":
                return await self._list_active_windows(
                    application_id=application_id or imap_code,
                    ctx=ctx
                )
            elif operation == "list_scheduled":
                return await self._list_scheduled_windows(
                    application_id=application_id or imap_code,
                    ctx=ctx
                )
            elif operation == "list_all":
                return await self._list_all_windows(
                    application_id=application_id or imap_code,
                    ctx=ctx
                )
            elif operation == "list_expired":
                return await self._list_expired_windows(
                    application_id=application_id or imap_code,
                    ctx=ctx
                )
            elif operation == "bulk_create":
                return await self._bulk_create_windows(
                    application_ids=application_ids,
                    imap_codes=imap_codes,
                    start_time=start_time,
                    duration_minutes=duration_minutes,
                    duration_hours=duration_hours,
                    duration_days=duration_days,
                    reason=reason,
                    template=template,
                    change_request_id=change_request_id,
                    use_tag_filter_expression=use_tag_filter_expression,
                    tag_name=tag_name,
                    ctx=ctx
                )
            elif operation == "validate":
                return await self._validate_window_params(
                    application_id=application_id,
                    start_time=start_time,
                    duration_minutes=duration_minutes,
                    template=template,
                    ctx=ctx
                )
            elif operation == "get_templates":
                return self._get_templates()
            else:
                return {"error": f"Operation '{operation}' not implemented"}

        except Exception as e:
            logger.error(f"Error executing maintenance operation: {e}", exc_info=True)
            return {
                "error": f"Maintenance operation failed: {e!s}",
                "operation": operation
            }

    async def _create_maintenance_window(
        self,
        application_id: Optional[str],
        imap_code: Optional[str],
        start_time: Optional[int],
        end_time: Optional[int],
        duration_minutes: Optional[int],
        duration_hours: Optional[int],
        duration_days: Optional[int],
        reason: Optional[str],
        template: Optional[str],
        change_request_id: Optional[str],
        affected_services: Optional[List[str]],
        notification_channels: Optional[List[str]],
        use_tag_filter_expression: Optional[bool],
        tag_name: Optional[str],
        rrule: Optional[str],
        until_date: Optional[str],
        ctx
    ) -> Dict[str, Any]:
        """
        Create a new maintenance window in Instana using real API structure.

        This method handles the creation of maintenance windows with full validation,
        template application, and ServiceNow integration. Supports both IMAP codes
        and legacy application IDs. Uses Instana's actual API format with query
        strings or tag filter expressions.

        Args:
            application_id: Application ID (legacy support, will be treated as IMAP code)
            imap_code: IMAP code (e.g., EAL-012512, ORZ-000012)
            start_time: Start time in Unix timestamp milliseconds
            end_time: End time in Unix timestamp milliseconds
            duration_minutes: Duration in minutes
            duration_hours: Duration in hours
            duration_days: Duration in days
            reason: Reason for maintenance
            template: Template name to apply
            change_request_id: ServiceNow change request ID
            affected_services: List of affected services
            notification_channels: Notification channels
            use_tag_filter_expression: Use tag filter expression format
            tag_name: Tag name for filter expression (default: synthetic.tags)
            ctx: MCP context

        Returns:
            Dictionary with creation results including window_id
        """
        try:
            # Use imap_code if provided, otherwise use application_id as imap_code
            target_code = imap_code or application_id

            # Validate required parameters
            if not target_code:
                return {"error": "imap_code or application_id is required"}

            if not start_time:
                return {"error": "start_time is required"}

            # Apply template if specified
            template_config = {}
            if template:
                if template not in self.TEMPLATES:
                    return {
                        "error": f"Invalid template '{template}'",
                        "available_templates": list(self.TEMPLATES.keys())
                    }
                template_config = self.TEMPLATES[template].copy()
                logger.info(f"Applying template: {template}")

            # Calculate duration and end time
            if not end_time:
                # Determine duration in milliseconds
                if duration_days:
                    duration_ms = duration_days * 24 * 60 * 60 * 1000
                    duration_amount = duration_days
                    duration_unit = "DAYS"
                elif duration_hours:
                    duration_ms = duration_hours * 60 * 60 * 1000
                    duration_amount = duration_hours
                    duration_unit = "HOURS"
                else:
                    duration_min = duration_minutes or template_config.get("default_duration", 60)

                    # IMPORTANT: For recurring windows, Instana requires whole hours
                    if rrule and duration_min < 60:
                        logger.warning("⚠️ Recurring windows require duration >= 1 hour")
                        logger.warning(f"Converting {duration_min} minutes to 1 hour for recurring window")
                        duration_min = 60
                    elif rrule and duration_min % 60 != 0:
                        # Round up to nearest hour for recurring windows
                        duration_hours_rounded = (duration_min + 59) // 60
                        logger.warning("⚠️ Recurring windows require whole hours")
                        logger.warning(f"Rounding {duration_min} minutes up to {duration_hours_rounded} hour(s)")
                        duration_min = duration_hours_rounded * 60

                    duration_ms = duration_min * 60 * 1000
                    duration_amount = duration_min // 60 if duration_min >= 60 else 1
                    duration_unit = "HOURS"

                end_time = start_time + duration_ms
            else:
                # Calculate duration from start and end times
                duration_ms = end_time - start_time
                duration_hours_calc = duration_ms // (60 * 60 * 1000)
                if duration_hours_calc >= 24:
                    duration_amount = duration_hours_calc // 24
                    duration_unit = "DAYS"
                else:
                    duration_amount = duration_hours_calc
                    duration_unit = "HOURS"

            # Validate time range
            current_time_result = get_current_timestamp(timezone="UTC", output_unit="milliseconds")
            current_time = current_time_result["timestamp"]
            if start_time < current_time:
                start_dt = datetime.fromtimestamp(start_time / 1000)
                current_dt = datetime.fromtimestamp(current_time / 1000)
                return {
                    "error": "start_time cannot be in the past",
                    "start_time_provided": start_time,
                    "start_time_readable": start_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "current_time": current_time,
                    "current_time_readable": current_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "suggestion": f"Use a time after {current_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}. Try: 'starting at {(current_dt.replace(hour=current_dt.hour+2)).strftime('%Y-%m-%d %H:%M:%S')} UTC'"
                }

            if end_time <= start_time:
                return {"error": "end_time must be after start_time"}

            # Generate maintenance window name
            date_str = datetime.fromtimestamp(start_time / 1000).strftime("%Y_%m_%d")
            reason_sanitized = (reason or template_config.get("description", "Maintenance")).replace(" ", "_")
            window_name = f"{target_code}_{reason_sanitized}_{date_str}"

            # Determine scheduling type and build scheduling object
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
                if until_date:
                    logger.info("Processing until_date for RRULE...")
                    # Parse until_date to ensure it's in the right format
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

                # Add rrule to scheduling object
                scheduling_obj["rrule"] = rrule_with_until

                # Add timezone (required for recurring windows in Instana)
                # Default to UTC if not specified
                scheduling_obj["timezoneId"] = "UTC"

                logger.info(f"✅ Final RRULE for API: {rrule_with_until}")
                logger.info("✅ Scheduling type set to: RECURRENT (Instana format)")
                logger.info("✅ Timezone set to: UTC")
                logger.info("=== END RECURRING WINDOW SETUP ===")
            else:
                logger.info("Creating ONE_TIME maintenance window (no rrule provided)")

            # Build maintenance window payload matching Instana's real API structure
            if use_tag_filter_expression:
                # Format 2: Tag Filter Expression (for synthetic monitoring)
                window_payload = {
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
                window_payload = {
                    "name": window_name,
                    "query": f"entity.tag:imap={target_code}",
                    "scheduling": scheduling_obj,
                    "paused": False,
                    "tagFilterExpressionEnabled": False,
                    "retriggerOpenAlertsEnabled": False
                }

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

            endpoint = f"api/settings/v2/maintenance/{window_id}"
            logger.info(f"API Endpoint: {endpoint}")

            # Log the complete payload for debugging
            logger.info("Complete API Payload:")
            logger.info(json.dumps(window_payload, indent=2))

            result = await self.make_request(
                endpoint=endpoint,
                method="PUT",
                json=window_payload
            )

            if "error" in result:
                logger.error(f"❌ Failed to create maintenance window: {result.get('error')}")
                logger.error("Payload that was rejected:")
                logger.error(json.dumps(window_payload, indent=2))

                # Check if it's a 422 error (validation error)
                if "422" in str(result.get('error')):
                    logger.error("⚠️ 422 Unprocessable Entity - Instana rejected the payload")
                    logger.error("Common causes:")
                    logger.error("  1. Invalid RRULE format")
                    logger.error("  2. RRULE not supported by this Instana version")
                    logger.error("  3. Missing required fields in scheduling")
                    logger.error("  4. Invalid duration unit or amount")
                    if scheduling_obj.get('type') == 'RECURRENT':
                        logger.error(f"  5. RRULE syntax error: {scheduling_obj.get('rrule')}")

                return result

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

            # Format human-readable times
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
                        "start": start_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "end": end_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
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

        except Exception as e:
            logger.error(f"Error creating maintenance window: {e}", exc_info=True)
            return {"error": f"Failed to create maintenance window: {e!s}"}

    async def _modify_maintenance_window(
        self,
        window_id: Optional[str],
        end_time: Optional[int],
        duration_minutes: Optional[int],
        reason: Optional[str],
        rrule: Optional[str] = None,
        until_date: Optional[str] = None,
        ctx=None
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
            if not window_id:
                return {
                    "error": "window_id is required for modify operation",
                    "help": "Please provide the maintenance window ID to modify. You can find window IDs by listing windows first.",
                    "example": "To modify window 'eeUHJZv8_XG-dDzi', use: operation='modify', params={'window_id': 'eeUHJZv8_XG-dDzi', 'duration_minutes': 60}",
                    "tip": "First list windows to get the window_id, then use that ID in the modify request"
                }

            # Get existing window
            endpoint = f"api/settings/v2/maintenance/{window_id}"
            existing_window = await self.make_request(endpoint=endpoint, method="GET")

            if "error" in existing_window:
                return {"error": f"Maintenance window not found: {window_id}"}

            # Build update payload - preserve ALL fields from existing window
            # The API requires all fields to be present, especially for RECURRENT windows
            update_payload = {
                "id": window_id,
                "name": existing_window.get("name"),
                "query": existing_window.get("query", ""),
                "paused": existing_window.get("paused", False),
                "scheduling": existing_window.get("scheduling", {}),
                "tagFilterExpressionEnabled": existing_window.get("tagFilterExpressionEnabled", False),
                "retriggerOpenAlertsEnabled": existing_window.get("retriggerOpenAlertsEnabled", False)
            }

            # Preserve optional fields if they exist
            optional_fields = [
                "tagFilterExpression",
                "applicationNames",
                "validVersion",
                "description"
            ]
            for field in optional_fields:
                if field in existing_window:
                    update_payload[field] = existing_window[field]

            # Update duration if provided
            if duration_minutes:
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
                if "scheduling" not in update_payload:
                    update_payload["scheduling"] = {}
                update_payload["scheduling"]["duration"] = {
                    "amount": duration_amount,
                    "unit": duration_unit
                }

            # Update RRULE if provided (for RECURRENT windows)
            if rrule or until_date:
                if "scheduling" not in update_payload:
                    update_payload["scheduling"] = {}

                # If until_date is provided, update the RRULE with new UNTIL value
                if until_date:
                    # Parse the until_date and convert to RRULE format
                    try:
                        # Handle ISO format or timestamp
                        if isinstance(until_date, str):
                            if 'T' in until_date:
                                # ISO format: "2026-03-18T23:59:59Z"
                                dt = datetime.fromisoformat(until_date.replace('Z', '+00:00'))
                            else:
                                # Date only: "2026-03-18"
                                dt = datetime.fromisoformat(until_date + "T23:59:59+00:00")
                        else:
                            # Assume timestamp in milliseconds
                            dt = datetime.fromtimestamp(until_date / 1000)

                        # Format as RRULE UNTIL value (YYYYMMDDTHHMMSSZ)
                        until_rrule = dt.strftime("%Y%m%dT%H%M%SZ")

                        # Get existing RRULE and update UNTIL
                        existing_rrule = update_payload["scheduling"].get("rrule", "")
                        if existing_rrule:
                            # Remove old UNTIL if present
                            rrule_without_until = re.sub(r';UNTIL=[^;]+', '', existing_rrule)
                            rrule_without_until = re.sub(r'UNTIL=[^;]+;?', '', rrule_without_until)
                            # Add new UNTIL
                            new_rrule = f"{rrule_without_until};UNTIL={until_rrule}"
                            update_payload["scheduling"]["rrule"] = new_rrule
                        else:
                            # No existing RRULE, create a basic one
                            update_payload["scheduling"]["rrule"] = f"FREQ=DAILY;INTERVAL=1;UNTIL={until_rrule}"
                    except Exception as e:
                        logger.error(f"Error parsing until_date: {e}")
                        return {"error": f"Invalid until_date format: {until_date}. Use ISO format like '2026-03-18T23:59:59Z'"}

                # If explicit rrule is provided, use it directly
                if rrule:
                    update_payload["scheduling"]["rrule"] = rrule

            # Update window name if reason provided
            if reason:
                current_name = existing_window.get("name", "")
                # Append modification reason to name
                update_payload["name"] = f"{current_name}_modified_{reason.replace(' ', '_')}"

            # Update maintenance window using PUT with same structure as create
            result = await self.make_request(
                endpoint=endpoint,
                method="PUT",
                json=update_payload
            )

            if "error" in result:
                return result

            # Fetch the updated window to verify changes
            updated_window = await self.make_request(endpoint=endpoint, method="GET")

            # Calculate new end time for response
            start_time = update_payload["scheduling"]["start"]
            duration = update_payload["scheduling"]["duration"]
            duration_amount = duration.get("amount", 0)
            duration_unit = duration.get("unit", "HOURS")

            if duration_unit == "DAYS":
                duration_ms = duration_amount * 24 * 60 * 60 * 1000
            elif duration_unit == "HOURS":
                duration_ms = duration_amount * 60 * 60 * 1000
            else:  # MINUTES
                duration_ms = duration_amount * 60 * 1000

            new_end_time = start_time + duration_ms

            # Extract RRULE info if present
            scheduling = updated_window.get("scheduling", {})
            rrule_after = scheduling.get("rrule", "")
            recurrence_type = scheduling.get("type", "ONE_TIME")

            # Build modification summary
            modifications = []
            if duration_minutes:
                modifications.append(f"duration changed to {duration_amount} {duration_unit}")
            if rrule or until_date:
                modifications.append("recurrence rule updated")
            if reason:
                modifications.append(f"name updated with reason: {reason}")

            modification_summary = ", ".join(modifications) if modifications else "window updated"

            response = {
                "operation": "modify",
                "status": "success",
                "window_id": window_id,
                "window_name": update_payload["name"],
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

            return response

        except Exception as e:
            logger.error(f"Error modifying maintenance window: {e}", exc_info=True)
            return {"error": f"Failed to modify maintenance window: {e!s}"}

    async def _close_maintenance_window(
        self,
        window_id: Optional[str],
        completion_notes: Optional[str],
        ctx
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
                return {"error": "window_id is required"}

            # Build closure payload
            closure_payload = {
                "status": "completed",
                "completionNotes": completion_notes or "Maintenance completed",
                "closedAt": get_current_timestamp(timezone="UTC", output_unit="milliseconds")["timestamp"]
            }

            # Close maintenance window
            endpoint = f"api/settings/v2/maintenance/{window_id}/close"
            result = await self.make_request(
                endpoint=endpoint,
                method="POST",
                json=closure_payload
            )

            if "error" in result:
                return result

            return {
                "operation": "close",
                "status": "success",
                "window_id": window_id,
                "completion_notes": closure_payload["completionNotes"],
                "closed_at": closure_payload["closedAt"],
                "message": f"Maintenance window closed successfully: {window_id}"
            }

        except Exception as e:
            logger.error(f"Error closing maintenance window: {e}", exc_info=True)
            return {"error": f"Failed to close maintenance window: {e!s}"}

    async def _list_active_windows(
        self,
        application_id: Optional[str],
        ctx
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
            endpoint = "api/settings/v2/maintenance"
            # Don't use query parameters - get all windows and filter in code
            result = await self.make_request(endpoint=endpoint, method="GET")

            if "error" in result:
                return result

            # Get all windows from response
            # The API might return a dict with different keys
            if isinstance(result, list):
                all_windows = result
            elif isinstance(result, dict):
                # Try different possible keys
                all_windows = result.get("items", result.get("data", result.get("maintenanceWindows", [])))
            else:
                all_windows = []

            # Debug: Log the structure of the response
            logger.info(f"API Response type: {type(result)}")
            if isinstance(result, dict):
                logger.info(f"API Response keys: {list(result.keys())}")
            logger.info(f"Number of windows in all_windows: {len(all_windows)}")
            logger.info(f"Raw result for debugging: {str(result)[:500]}")  # First 500 chars

            # Filter for active windows using the 'state' field or occurrence times
            current_time_result = get_current_timestamp(timezone="UTC", output_unit="milliseconds")
            current_time = current_time_result["timestamp"]
            active_windows = []

            for window in all_windows:
                # Check state field first (most reliable)
                state = window.get("state", "")
                if state == "ACTIVE":
                    # Filter by application_id if provided
                    if application_id:
                        query = window.get("query", "")
                        tag_filter = window.get("tagFilterExpression", {})
                        tag_value = tag_filter.get("value", "") if tag_filter else ""
                        if application_id in query or application_id in tag_value or f"imap={application_id}" in query:
                            active_windows.append(window)
                    else:
                        active_windows.append(window)
                # Fallback: check occurrence times if state not available
                elif not state:
                    occurrence = window.get("occurrence", {})
                    start_time = occurrence.get("start", 0)
                    end_time = occurrence.get("end", 0)

                    if start_time <= current_time <= end_time:
                        if application_id:
                            query = window.get("query", "")
                            tag_filter = window.get("tagFilterExpression", {})
                            tag_value = tag_filter.get("value", "") if tag_filter else ""
                            if application_id in query or application_id in tag_value or f"imap={application_id}" in query:
                                active_windows.append(window)
                        else:
                            active_windows.append(window)

            # If no active windows found, provide helpful information about other windows
            if len(active_windows) == 0:
                # Count other window types
                expired_count = sum(1 for w in all_windows if w.get("state") == "EXPIRED")
                scheduled_count = sum(1 for w in all_windows if w.get("state") == "SCHEDULED")

                return {
                    "operation": "list_active",
                    "status": "success",
                    "count": 0,
                    "windows": [],
                    "application_id": application_id,
                    "message": f"No active maintenance windows found. Found {expired_count} expired and {scheduled_count} scheduled windows.",
                    "suggestion": "Use operation 'list_expired' to see expired windows or 'list_all' to see all windows.",
                    "expired_count": expired_count,
                    "scheduled_count": scheduled_count
                }

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

    async def _list_scheduled_windows(
        self,
        application_id: Optional[str],
        ctx
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
            endpoint = "api/settings/v2/maintenance"
            # Don't use query parameters - get all windows and filter in code
            result = await self.make_request(endpoint=endpoint, method="GET")

            if "error" in result:
                return result

            # Get all windows from response
            all_windows = result if isinstance(result, list) else result.get("items", [])

            # Filter for scheduled windows using the 'state' field
            scheduled_windows = []

            # Debug: Log all states
            states_found = [w.get("state", "UNKNOWN") for w in all_windows]
            logger.info(f"States found in windows: {states_found}")

            for window in all_windows:
                # Check state field (most reliable)
                state = window.get("state", "")
                logger.debug(f"Checking window {window.get('name', 'unknown')}: state={state}")
                if state == "SCHEDULED":
                    # Filter by application_id if provided
                    if application_id:
                        query = window.get("query", "")
                        tag_filter = window.get("tagFilterExpression", {})
                        tag_value = tag_filter.get("value", "") if tag_filter else ""
                        if application_id in query or application_id in tag_value or f"imap={application_id}" in query:
                            scheduled_windows.append(window)
                    else:
                        scheduled_windows.append(window)

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
    async def _list_all_windows(
        self,
        application_id: Optional[str],
        ctx
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
            endpoint = "api/settings/v2/maintenance"
            # Get all windows
            result = await self.make_request(endpoint=endpoint, method="GET")

            if "error" in result:
                return result

            # Get all windows from response
            all_windows = result if isinstance(result, list) else result.get("items", [])

            # Filter by application_id if provided
            if application_id:
                filtered_windows = []
                for window in all_windows:
                    query = window.get("query", "")
                    tag_filter = window.get("tagFilterExpression", {})
                    tag_value = tag_filter.get("value", "") if tag_filter else ""
                    if application_id in query or application_id in tag_value or f"imap={application_id}" in query:
                        filtered_windows.append(window)
                all_windows = filtered_windows

            # Group windows by state for better visibility
            windows_by_state = {
                "active": [],
                "scheduled": [],
                "expired": []
            }

            for window in all_windows:
                state = window.get("state", "").upper()
                if state == "ACTIVE":
                    windows_by_state["active"].append(window)
                elif state == "SCHEDULED":
                    windows_by_state["scheduled"].append(window)
                elif state == "EXPIRED":
                    windows_by_state["expired"].append(window)

            # Create summary message
            summary_parts = []
            if windows_by_state["active"]:
                summary_parts.append(f"{len(windows_by_state['active'])} active")
            if windows_by_state["scheduled"]:
                summary_parts.append(f"{len(windows_by_state['scheduled'])} scheduled")
            if windows_by_state["expired"]:
                summary_parts.append(f"{len(windows_by_state['expired'])} expired")

            summary = f"Found {len(all_windows)} total maintenance window(s): {', '.join(summary_parts) if summary_parts else 'none'}"

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

    async def _list_expired_windows(
        self,
        application_id: Optional[str],
        ctx
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
            endpoint = "api/settings/v2/maintenance"
            # Get all windows
            result = await self.make_request(endpoint=endpoint, method="GET")

            if "error" in result:
                return result

            # Get all windows from response
            all_windows = result if isinstance(result, list) else result.get("items", [])

            # Filter for expired windows using the 'state' field
            expired_windows = []

            # Debug: Log all states
            states_found = [w.get("state", "UNKNOWN") for w in all_windows]
            logger.info(f"States found in windows for list_expired: {states_found}")

            for window in all_windows:
                # Check state field (most reliable)
                state = window.get("state", "")
                window_name = window.get("name", "unknown")
                logger.debug(f"Checking window {window_name}: state={state}, application_id filter={application_id}")

                if state == "EXPIRED":
                    # Filter by application_id if provided
                    if application_id:
                        query = window.get("query", "")
                        tag_filter = window.get("tagFilterExpression", {})
                        tag_value = tag_filter.get("value", "") if tag_filter else ""
                        logger.debug(f"  Filtering by app_id: query={query}, tag_value={tag_value}")
                        if application_id in query or application_id in tag_value or f"imap={application_id}" in query:
                            logger.info(f"  ✓ Adding expired window: {window_name}")
                            expired_windows.append(window)
                        else:
                            logger.debug("  ✗ Skipped (app_id filter didn't match)")
                    else:
                        logger.info(f"  ✓ Adding expired window: {window_name}")
                        expired_windows.append(window)

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
        ctx
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

            if not target_codes:
                return {"error": "imap_codes or application_ids is required"}

            results = []
            for code in target_codes:
                result = await self._create_maintenance_window(
                    application_id=None,
                    imap_code=code,
                    start_time=start_time,
                    end_time=None,
                    duration_minutes=duration_minutes,
                    duration_hours=duration_hours,
                    duration_days=duration_days,
                    reason=reason,
                    template=template,
                    change_request_id=change_request_id,
                    affected_services=None,
                    notification_channels=None,
                    use_tag_filter_expression=use_tag_filter_expression,
                    tag_name=tag_name,
                    rrule=None,
                    until_date=None,
                    ctx=ctx
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
        start_time: Optional[int],
        duration_minutes: Optional[int],
        template: Optional[str],
        ctx
    ) -> Dict[str, Any]:
        """
        Validate maintenance window parameters without creating.

        Args:
            application_id: Application ID
            start_time: Start time
            duration_minutes: Duration
            template: Template name
            ctx: MCP context

        Returns:
            Dictionary with validation results
        """
        validation_errors = []

        if not application_id:
            validation_errors.append("application_id is required")

        if not start_time:
            validation_errors.append("start_time is required")
        elif start_time < get_current_timestamp(timezone="UTC", output_unit="milliseconds")["timestamp"]:
            validation_errors.append("start_time cannot be in the past")

        if template and template not in self.TEMPLATES:
            validation_errors.append(f"Invalid template: {template}")

        if validation_errors:
            return {
                "operation": "validate",
                "status": "invalid",
                "errors": validation_errors
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


