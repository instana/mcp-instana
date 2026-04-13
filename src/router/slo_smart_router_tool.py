"""
SLO Smart Router Tool

This module provides a unified MCP tool that routes SLO (Service Level Objective)
queries to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_to_timestamp
from src.core.utils import BaseInstanaClient, register_as_tool

logger = logging.getLogger(__name__)

RESOURCE_TYPE_CONFIGURATION = "configuration"
RESOURCE_TYPE_REPORT = "report"
RESOURCE_TYPE_ALERT = "alert"
RESOURCE_TYPE_CORRECTION = "correction"

VALID_RESOURCE_TYPES = [
    RESOURCE_TYPE_CONFIGURATION,
    RESOURCE_TYPE_REPORT,
    RESOURCE_TYPE_ALERT,
    RESOURCE_TYPE_CORRECTION
]

# Configuration operation constants
CONFIG_OP_GET_ALL = "get_all"
CONFIG_OP_GET_BY_ID = "get_by_id"
CONFIG_OP_CREATE = "create"
CONFIG_OP_UPDATE = "update"
CONFIG_OP_DELETE = "delete"
CONFIG_OP_GET_TAGS = "get_tags"

# Valid configuration operations
CONFIG_VALID_OPERATIONS = [
    CONFIG_OP_GET_ALL,
    CONFIG_OP_GET_BY_ID,
    CONFIG_OP_CREATE,
    CONFIG_OP_UPDATE,
    CONFIG_OP_DELETE,
    CONFIG_OP_GET_TAGS
]

# Report operation constants
REPORT_OP_GET = "get"

# Valid report operations
REPORT_VALID_OPERATIONS = [
    REPORT_OP_GET
]

# Parameter name constants
PARAM_ID = "id"
PARAM_PAYLOAD = "payload"
PARAM_PAGE_SIZE = "page_size"
PARAM_PAGE = "page"
PARAM_ORDER_BY = "order_by"
PARAM_ORDER_DIRECTION = "order_direction"
PARAM_QUERY = "query"
PARAM_TAG = "tag"
PARAM_ENTITY_TYPE = "entity_type"
PARAM_INFRA_ENTITY_TYPES = "infra_entity_types"
PARAM_KUBERNETES_CLUSTER_UUID = "kubernetes_cluster_uuid"
PARAM_BLUEPRINT = "blueprint"
PARAM_SLO_IDS = "slo_ids"
PARAM_SLO_STATUS = "slo_status"
PARAM_ENTITY_IDS = "entity_ids"
PARAM_GROUPED = "grouped"
PARAM_REFRESH = "refresh"
PARAM_RBAC_TAGS = "rbac_tags"

# Alert Config operation constants
ALERT_OP_FIND_ACTIVE = "find_active"
ALERT_OP_FIND = "find"
ALERT_OP_FIND_VERSIONS = "find_versions"
ALERT_OP_CREATE = "create"
ALERT_OP_UPDATE = "update"
ALERT_OP_DELETE = "delete"
ALERT_OP_DISABLE = "disable"
ALERT_OP_ENABLE = "enable"
ALERT_OP_RESTORE = "restore"

# Valid alert config operations
ALERT_VALID_OPERATIONS = [
    ALERT_OP_FIND_ACTIVE,
    ALERT_OP_FIND,
    ALERT_OP_FIND_VERSIONS,
    ALERT_OP_CREATE,
    ALERT_OP_UPDATE,
    ALERT_OP_DELETE,
    ALERT_OP_DISABLE,
    ALERT_OP_ENABLE,
    ALERT_OP_RESTORE
]

# Correction operation constants
CORRECTION_OP_GET_ALL = "get_all"
CORRECTION_OP_GET_BY_ID = "get_by_id"
CORRECTION_OP_CREATE = "create"
CORRECTION_OP_UPDATE = "update"
CORRECTION_OP_DELETE = "delete"

# Valid correction operations
CORRECTION_VALID_OPERATIONS = [
    CORRECTION_OP_GET_ALL,
    CORRECTION_OP_GET_BY_ID,
    CORRECTION_OP_CREATE,
    CORRECTION_OP_UPDATE,
    CORRECTION_OP_DELETE
]

class SLOSmartRouterMCPTool(BaseInstanaClient):
    """
    Smart router for Instana SLO operations.
    Routes queries to SLO Configuration and Report tools.
    """

    def __init__(self, read_token: str, base_url: str):
        """Initialize the SLO Smart Router MCP tool."""
        super().__init__(read_token=read_token, base_url=base_url)

        # Lazy import to avoid circular dependencies
        from src.slo.slo_alert_config import SLOAlertConfigMCPTools
        from src.slo.slo_configuration import SLOConfigurationMCPTools
        from src.slo.slo_correction_configuration import SLOCorrectionMCPTools
        from src.slo.slo_report import SLOReportMCPTools

        self.slo_config_client = SLOConfigurationMCPTools(read_token, base_url)
        self.slo_report_client = SLOReportMCPTools(read_token, base_url)
        self.slo_alert_client = SLOAlertConfigMCPTools(read_token, base_url)
        self.slo_correction_client = SLOCorrectionMCPTools(read_token, base_url)

        logger.info("SLO Smart Router initialized with Configuration, Report, Alert, and Correction tools")

    @register_as_tool(
        title="Manage Instana SLO Resources",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    async def manage_slo(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Unified SLO manager for configurations, reports, alerts, and corrections.

        CONFIGURATION (resource_type="configuration") - Operations: get_all, get_by_id, create, update, delete, get_tags
            get_all: List/filter configs - params: page_size (default: 10), page, order_by, order_direction, query, tag, entity_type, infra_entity_types, kubernetes_cluster_uuid, blueprint, slo_ids, slo_status, entity_ids, grouped, refresh, rbac_tags
                page_size: Number of items per page (default: 10)
                query: Filter by name or matching names (e.g., query="my-slo" to find SLOs with "my-slo" in name)
            get_by_id: Get config by ID - params: id (required), refresh
            create: Create config - params: payload (required) with name, entity, indicator, target (0.0-0.9999), timeWindow, tags
                entity: {type: "application", applicationId: "...", boundaryScope: "ALL"/"INBOUND"/"DEFAULT"} (boundaryScope REQUIRED)
                indicator: {type: "timeBased"/"eventBased", blueprint: "latency"/"availability", threshold: 100, aggregation: "P90"/"P95"}
                timeWindow: {type: "rolling"/"fixed", duration: 1, durationUnit: "week"/"day"/"hour"/"minute"}
            update: Update config (requires ALL fields) - params: id (required), payload (required, same as create)
                CRITICAL: MUST use ID (not name). Fetch via get_by_id first, merge changes, then update with complete payload
            delete: Delete config - params: id (required)
            get_tags: List tags - params: query, tag, entity_type

        REPORT (resource_type="report") - Operations: get
            get: Generate SLO report - params: slo_id (required), var_from, to, exclude_correction_id, include_correction_id
                Returns: SLI value, SLO target, error budget (remaining/spent/total), burn rate, time range, charts
                Time params: var_from/to can be provided as:
                    - Unix timestamp in milliseconds (e.g., 1741604400000)
                    - Human-readable datetime string (e.g., "10 March 2026, 2:00 PM")
                    - Datetime with timezone (e.g., "10 March 2026, 2:00 PM|IST")
                    - If no timezone specified, UTC is assumed
                Supported datetime formats: "10 March 2026, 2:00 PM", "2026-03-10 14:00:00", "March 10, 2026 2 PM", etc.

        ALERT (resource_type="alert") - Operations: find_active, find, find_versions, create, update, delete, disable, enable, restore
            find_active: Find active alerts - params: slo_id, alert_ids
            find: Get alert by ID - params: id (required), valid_on
            find_versions: Get alert versions - params: id (required)
            create: Create alert - params: payload (required) with name, description, sloIds, rule, severity, alertChannelIds, timeThreshold, customPayloadFields
                REQUIRED FIELDS: name, description, sloIds (list), rule, severity (5 or 10 ONLY), alertChannelIds (list), timeThreshold, customPayloadFields (list, can be empty)
                rule: {alertType: "ERROR_BUDGET", metric: "BURN_RATE"/"BURNED_PERCENTAGE"/"BURN_RATE_V2"} OR {alertType: "SERVICE_LEVELS_OBJECTIVE"}
                timeThreshold: {expiry: 604800000, timeWindow: 604800000} (values in milliseconds - NOT type/value format)
                customPayloadFields: [{type: "staticString", key: "foo", value: "bar"}] (use proper discriminated union types)
                threshold (optional): {type: "staticThreshold", operator: ">=", value: 20.0} (required for some alert types)
                burnRateTimeWindows (REQUIRED for BURN_RATE metric): {longTimeWindow: {duration: 1, durationType: "hour"}, shortTimeWindow: {duration: 5, durationType: "minute"}}
            update: Update alert (requires ALL fields) - params: id (required), payload (required, same as create)
                CRITICAL: MUST use ID (not name). Fetch via find first, merge changes, then update with complete payload
            delete: Delete alert - params: id (required)
            disable: Disable alert - params: id (required)
            enable: Enable alert - params: id (required)
            restore: Restore alert to version - params: id (required), created (required - timestamp from version)

        CORRECTION (resource_type="correction") - Operations: get_all, get_by_id, create, update, delete
            get_all: List correction windows - params: page_size (default: 10), page, order_by, order_direction, query, tag, id, slo_id, refresh
                page_size: Number of items per page (default: 10)
                query: Filter by name or matching names (e.g., query="maintenance" to find corrections with "maintenance" in name)
            get_by_id: Get correction by ID - params: id (required)
            create: Create correction window - params: payload (required) with name, scheduling, sloIds, description, tags, active
                REQUIRED FIELDS: name, scheduling (with duration, durationUnit, startTime optional, recurrent optional, recurrentRule optional)
                scheduling: {duration: 1, durationUnit: "hour"/"day"/"week"/"month", startTime: <timestamp_or_datetime>, recurrent: true/false, recurrentRule: "..."}
                durationUnit: Must be one of: millisecond, second, minute, hour, day, week, month
                startTime: Can be provided as:
                    - Unix timestamp in milliseconds (e.g., 1741604400000)
                    - Human-readable datetime string (e.g., "10 March 2026, 2:00 PM")
                    - Datetime with timezone (e.g., "10 March 2026, 2:00 PM|IST")
                    - If no timezone specified, UTC is assumed
                    - CRITICAL: Always include timezone for correction windows to ensure accurate time context
            update: Update correction window - params: id (required), payload (required, same as create)
                CRITICAL: MUST use ID (not name). Always update by ID only
            delete: Delete correction window - params: id (required)

        Examples:
            # Config: List all
            resource_type="configuration", operation="get_all"

            # Config: Get by ID
            resource_type="configuration", operation="get_by_id", params={"id": "slo-123"}

            # Config: Create
            resource_type="configuration", operation="create", params={"payload": {"name": "API SLO", "entity": {"type": "application", "applicationId": "app-123", "boundaryScope": "ALL"}, "indicator": {"type": "timeBased", "blueprint": "latency", "threshold": 100, "aggregation": "P90"}, "target": 0.95, "timeWindow": {"type": "rolling", "duration": 1, "durationUnit": "week"}, "tags": ["api"]}}

            # Report: Get with datetime
            resource_type="report", operation="get", params={"slo_id": "slo-123", "var_from": "10 March 2026, 2:00 PM|IST", "to": "17 March 2026, 2:00 PM|IST"}

            # Alert: Find active
            resource_type="alert", operation="find_active", params={"slo_id": "slo-123"}

            # Alert: Create (all required fields)
            resource_type="alert", operation="create", params={"payload": {"name": "Burn Rate Alert", "description": "High burn rate", "sloIds": ["slo-123"], "rule": {"alertType": "ERROR_BUDGET", "metric": "BURN_RATE"}, "severity": 10, "alertChannelIds": ["ch-123"], "timeThreshold": {"expiry": 604800000, "timeWindow": 604800000}, "customPayloadFields": [{"type": "staticString", "key": "env", "value": "prod"}], "threshold": {"type": "staticThreshold", "operator": ">=", "value": 2.0}, "burnRateTimeWindows": {"longTimeWindow": {"duration": 1, "durationType": "hour"}, "shortTimeWindow": {"duration": 5, "durationType": "minute"}}}}

            # Correction: List all
            resource_type="correction", operation="get_all"

            # Correction: Create with datetime
            resource_type="correction", operation="create", params={"payload": {"name": "Maintenance", "scheduling": {"duration": 2, "durationUnit": "hour", "startTime": "12 March 2026, 1:47 AM|IST"}, "sloIds": ["slo-123"], "description": "Planned maintenance", "tags": ["maint"], "active": True}}

            # Elicitation: Missing timezone
            # Input: resource_type="report", operation="get", params={"slo_id": "abc", "var_from": "10 March 2026, 2:00 PM"}
            # Response: {"elicitation_needed": True, "message": "I need timezone...", "missing_parameters": ["timezone"]}

            # Elicitation: Missing alert fields
            # Input: resource_type="alert", operation="create", params={"payload": {"name": "Alert"}}
            # Response: {"elicitation_needed": True, "message": "I need...", "missing_parameters": [...]}
        """
        try:
            logger.debug(f"[manage_slo] Received: resource_type={resource_type}, operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            if resource_type not in VALID_RESOURCE_TYPES:
                logger.warning(f"[manage_slo] Invalid resource_type: {resource_type}")
                return {
                    "error": f"Invalid resource_type '{resource_type}'",
                    "valid_resource_types": VALID_RESOURCE_TYPES,
                    "suggestion": f"Use '{RESOURCE_TYPE_CONFIGURATION}' for SLO configuration management"
                }

            # Route to the appropriate resource handler
            if resource_type == RESOURCE_TYPE_CONFIGURATION:
                return await self._handle_configuration(operation, params, ctx)
            elif resource_type == RESOURCE_TYPE_REPORT:
                return await self._handle_report(operation, params, ctx)
            elif resource_type == RESOURCE_TYPE_ALERT:
                return await self._handle_alert(operation, params, ctx)
            elif resource_type == RESOURCE_TYPE_CORRECTION:
                return await self._handle_correction(operation, params, ctx)
            else:
                logger.error(f"[manage_slo] Unhandled resource_type: {resource_type}")
                return {
                    "error": f"Unsupported resource_type: {resource_type}",
                    "supported_types": VALID_RESOURCE_TYPES
                }
        except Exception as e:
            logger.error(f"[manage_slo] Error in smart router: {e}", exc_info=True)
            return {
                "error": f"SLO smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    async def _handle_configuration(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """Handle SLO configuration operations."""
        logger.debug(f"[_handle_configuration] Operation: {operation}, params: {params}")

        # Extract required parameters
        if operation not in CONFIG_VALID_OPERATIONS:
            logger.warning(f"[_handle_configuration] Invalid operation: {operation}")
            return {
                "error": f"Invalid operation '{operation}' for configuration",
                "valid_operations": CONFIG_VALID_OPERATIONS
            }
        try:
            # Route to specific configuration operation
            if operation == CONFIG_OP_GET_ALL:
                logger.debug("[_handle_configuration] Routing to get_all_slo_configs")

                # Group related parameters for clarity
                pagination_params = {
                    'page_size': params.get(PARAM_PAGE_SIZE, 10),
                    'page': params.get(PARAM_PAGE),
                    'order_by': params.get(PARAM_ORDER_BY),
                    'order_direction': params.get(PARAM_ORDER_DIRECTION)
                }

                filter_params = {
                    'query': params.get(PARAM_QUERY),
                    'tag': params.get(PARAM_TAG),
                    'entity_type': params.get(PARAM_ENTITY_TYPE),
                    'infra_entity_types': params.get(PARAM_INFRA_ENTITY_TYPES),
                    'kubernetes_cluster_uuid': params.get(PARAM_KUBERNETES_CLUSTER_UUID),
                    'blueprint': params.get(PARAM_BLUEPRINT),
                    'slo_ids': params.get(PARAM_SLO_IDS),
                    'slo_status': params.get(PARAM_SLO_STATUS),
                    'entity_ids': params.get(PARAM_ENTITY_IDS),
                    'grouped': params.get(PARAM_GROUPED),
                    'refresh': params.get(PARAM_REFRESH),
                    'rbac_tags': params.get(PARAM_RBAC_TAGS)
                }

                result = await self.slo_config_client.get_all_slo_configs(
                    **pagination_params,
                    **filter_params,
                    ctx=ctx
                )

                return {
                    "resource_type": RESOURCE_TYPE_CONFIGURATION,
                    "operation": operation,
                    "results": result
                }
            elif operation == CONFIG_OP_GET_BY_ID:
                slo_id = params.get(PARAM_ID)
                refresh = params.get(PARAM_REFRESH)

                if not slo_id:
                    logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_ID}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_ID}'",
                        "resource_type": RESOURCE_TYPE_CONFIGURATION,
                        "operation": operation
                    }
                logger.debug(f"[_handle_configuration] Routing to get_slo_config_by_id with id: {slo_id}")
                result = await self.slo_config_client.get_slo_config_by_id(
                    id=slo_id,
                    refresh=refresh,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_CONFIGURATION,
                    "operation": operation,
                    "results": result
                }
            elif operation == CONFIG_OP_CREATE:
                payload = params.get(PARAM_PAYLOAD)
                if not payload:
                    logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_PAYLOAD}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_PAYLOAD}'",
                        "resource_type": RESOURCE_TYPE_CONFIGURATION,
                        "operation": operation,
                        "required_fields": ["name", "entity", "indicator", "target", "timeWindow", "tags"]
                    }
                logger.debug("[_handle_configuration] Routing to create_slo_config")
                result = await self.slo_config_client.create_slo_config(
                    payload=payload,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_CONFIGURATION,
                    "operation": operation,
                    "results": result
                }
            elif operation == CONFIG_OP_UPDATE:
                slo_id = params.get(PARAM_ID)
                payload = params.get(PARAM_PAYLOAD)
                if not slo_id:
                    logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_ID}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_ID}'",
                        "resource_type": RESOURCE_TYPE_CONFIGURATION,
                        "operation": operation
                    }
                if not payload:
                    logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_PAYLOAD}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_PAYLOAD}'",
                        "resource_type": RESOURCE_TYPE_CONFIGURATION,
                        "operation": operation
                    }
                logger.debug(f"[_handle_configuration] Routing to update_slo_config with id: {slo_id}")
                result = await self.slo_config_client.update_slo_config(
                    id=slo_id,
                    payload=payload,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_CONFIGURATION,
                    "operation": operation,
                    "id": slo_id,
                    "results": result
                }
            elif operation == CONFIG_OP_DELETE:
                slo_id = params.get(PARAM_ID)
                if not slo_id:
                    logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_ID}")
                    return {
                        "error": f"Missing required parameter: '{PARAM_ID}'",
                        "resource_type": RESOURCE_TYPE_CONFIGURATION,
                        "operation": operation
                    }

                logger.debug(f"[_handle_configuration] Routing to delete_slo_config with id: {slo_id}")
                result = await self.slo_config_client.delete_slo_config(
                    id=slo_id,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_CONFIGURATION,
                    "operation": operation,
                    "id": slo_id,
                    "results": result
                }
            elif operation == CONFIG_OP_GET_TAGS:

                logger.debug("[_handle_configuration] Routing to get_all_slo_config_tags")

                query = params.get(PARAM_QUERY)
                tag = params.get(PARAM_TAG)
                entity_type = params.get(PARAM_ENTITY_TYPE)

                result = await self.slo_config_client.get_all_slo_config_tags(query=query,
                    tag=tag,
                    entity_type=entity_type,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_CONFIGURATION,
                    "operation": operation,
                    "results": result
                }
            else:
                logger.error(f"[_handle_configuration] Unhandled operation: {operation}")
                return {
                    "error": f"Unhandled configuration operation: {operation}",
                    "valid_operations": CONFIG_VALID_OPERATIONS
                }
        except Exception as e:
            logger.error(f"[_handle_configuration] Error handling configuration operation: {e!s}", exc_info=True)
            return {
                "error": f"Configuration operation error: {e!s}",
                "resource_type": RESOURCE_TYPE_CONFIGURATION,
                "operation": operation
            }

    async def _handle_report(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx
    ) -> Dict[str, Any]:
        """
        Handle report resource operations.

        Args:
            operation: The operation to perform (get)
            params: Operation parameters
            ctx: MCP context

        Returns:
            Dict containing operation results
        """
        try:
            logger.debug(f"[_handle_report] Operation: {operation}, params: {params}")

            # Validate operation
            if operation not in REPORT_VALID_OPERATIONS:
                logger.warning(f"[_handle_report] Invalid operation: {operation}")
                return {
                    "error": f"Invalid report operation: '{operation}'",
                    "valid_operations": REPORT_VALID_OPERATIONS,
                    "resource_type": RESOURCE_TYPE_REPORT
                }

            if operation == REPORT_OP_GET:
                slo_id = params.get("slo_id")
                var_from = params.get("var_from")
                to = params.get("to")
                exclude_correction_id = params.get("exclude_correction_id")
                include_correction_id = params.get("include_correction_id")

                if not slo_id:
                    logger.warning("[_handle_report] Missing required parameter: slo_id")
                    return {
                        "error": "Missing required parameter: 'slo_id'",
                        "resource_type": RESOURCE_TYPE_REPORT,
                        "operation": operation
                    }

                # Handle datetime string conversion for var_from and to parameters
                # If the value is a string (datetime), convert it to timestamp
                # If it's already a number (timestamp), use it as-is
                if var_from is not None and isinstance(var_from, str):
                    logger.debug(f"[_handle_report] Converting var_from datetime string: {var_from}")
                    # Check if timezone is provided
                    if "|" not in var_from:
                        # Elicit timezone from user
                        return {
                            "elicitation_needed": True,
                            "message": f"I see you want to start the report from '{var_from}', but I need to know which timezone.\n\nPlease specify the timezone:\n- IST (India Standard Time)\n- America/New_York (Eastern Time)\n- UTC (Coordinated Universal Time)\n- Europe/London (GMT/BST)\n- Asia/Tokyo (Japan Standard Time)\n\nOr any other IANA timezone name.",
                            "missing_parameters": ["timezone"],
                            "user_prompt": f"What timezone should be used for the start time '{var_from}'?"
                        }

                    # Extract timezone if provided in format "datetime|timezone"
                    datetime_str, timezone = var_from.split("|", 1)

                    conversion_result = convert_to_timestamp(datetime_str.strip(), timezone.strip(), "milliseconds")
                    if "error" in conversion_result:
                        return {
                            "error": f"Failed to convert var_from datetime: {conversion_result['error']}",
                            "resource_type": RESOURCE_TYPE_REPORT,
                            "operation": operation
                        }
                    var_from = str(conversion_result["timestamp"])  # Convert to string as API expects StrictStr
                    logger.info(f"[_handle_report] Converted var_from to timestamp string: {var_from}")

                if to is not None and isinstance(to, str):
                    logger.debug(f"[_handle_report] Converting to datetime string: {to}")
                    # Check if timezone is provided
                    if "|" not in to:
                        # Elicit timezone from user
                        return {
                            "elicitation_needed": True,
                            "message": f"I see you want to end the report at '{to}', but I need to know which timezone.\n\nPlease specify the timezone:\n- IST (India Standard Time)\n- America/New_York (Eastern Time)\n- UTC (Coordinated Universal Time)\n- Europe/London (GMT/BST)\n- Asia/Tokyo (Japan Standard Time)\n\nOr any other IANA timezone name.",
                            "missing_parameters": ["timezone"],
                            "user_prompt": f"What timezone should be used for the end time '{to}'?"
                        }

                    # Extract timezone if provided in format "datetime|timezone"
                    datetime_str, timezone = to.split("|", 1)

                    conversion_result = convert_to_timestamp(datetime_str.strip(), timezone.strip(), "milliseconds")
                    if "error" in conversion_result:
                        return {
                            "error": f"Failed to convert to datetime: {conversion_result['error']}",
                            "resource_type": RESOURCE_TYPE_REPORT,
                            "operation": operation
                        }
                    to = str(conversion_result["timestamp"])  # Convert to string as API expects StrictStr
                    logger.info(f"[_handle_report] Converted to to timestamp string: {to}")

                logger.debug(f"[_handle_report] Routing to get_slo_report with slo_id: {slo_id}, var_from: {var_from}, to: {to}")
                result = await self.slo_report_client.get_slo_report(
                    slo_id=slo_id,
                    var_from=var_from,
                    to=to,
                    exclude_correction_id=exclude_correction_id,
                    include_correction_id=include_correction_id,
                    ctx=ctx
                )
                return {
                    "resource_type": RESOURCE_TYPE_REPORT,
                    "operation": operation,
                    "results": result
                }
            else:
                logger.error(f"[_handle_report] Unhandled operation: {operation}")
                return {
                    "error": f"Unhandled report operation: {operation}",
                    "valid_operations": REPORT_VALID_OPERATIONS
                }
        except Exception as e:
            logger.error(f"[_handle_report] Error handling report operation: {e!s}", exc_info=True)
            return {
                "error": f"Report operation error: {e!s}",
                "resource_type": RESOURCE_TYPE_REPORT,
                "operation": operation
            }

    async def _handle_alert(self, operation: str, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        """Handle alert config operations."""
        try:
            logger.debug(f"[_handle_alert] Operation: {operation}, params: {params}")

            if operation not in ALERT_VALID_OPERATIONS:
                return {"error": f"Invalid alert operation: '{operation}'", "valid_operations": ALERT_VALID_OPERATIONS}

            if operation == ALERT_OP_FIND_ACTIVE:
                result = await self.slo_alert_client.find_active_alert_configs(
                    slo_id=params.get("slo_id"),
                    alert_ids=params.get("alert_ids"),
                    ctx=ctx
                )
            elif operation == ALERT_OP_FIND:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_alert_client.find_alert_config(
                    id=params["id"],
                    valid_on=params.get("valid_on"),
                    ctx=ctx
                )
            elif operation == ALERT_OP_FIND_VERSIONS:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_alert_client.find_alert_config_versions(id=params["id"], ctx=ctx)
            elif operation == ALERT_OP_CREATE:
                if not params.get("payload"):
                    return {"error": "Missing required parameter: 'payload'"}
                result = await self.slo_alert_client.create_alert_config(payload=params["payload"], ctx=ctx)
            elif operation == ALERT_OP_UPDATE:
                if not params.get("id") or not params.get("payload"):
                    return {"error": "Missing required parameters: 'id' and 'payload'"}
                result = await self.slo_alert_client.update_alert_config(
                    id=params["id"],
                    payload=params["payload"],
                    ctx=ctx
                )
            elif operation == ALERT_OP_DELETE:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_alert_client.delete_alert_config(id=params["id"], ctx=ctx)
            elif operation == ALERT_OP_DISABLE:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_alert_client.disable_alert_config(id=params["id"], ctx=ctx)
            elif operation == ALERT_OP_ENABLE:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_alert_client.enable_alert_config(id=params["id"], ctx=ctx)
            elif operation == ALERT_OP_RESTORE:
                if not params.get("id") or not params.get("created"):
                    return {"error": "Missing required parameters: 'id' and 'created' (timestamp)"}
                result = await self.slo_alert_client.restore_alert_config(
                    id=params["id"],
                    created=params["created"],
                    ctx=ctx
                )

            return {"resource_type": RESOURCE_TYPE_ALERT, "operation": operation, "results": result}

        except Exception as e:
            logger.error(f"[_handle_alert] Error: {e}", exc_info=True)
            return {"error": f"Alert operation error: {e!s}", "resource_type": RESOURCE_TYPE_ALERT, "operation": operation}

    async def _handle_correction(self, operation: str, params: Dict[str, Any], ctx) -> Dict[str, Any]:
        """Handle correction window operations."""
        try:
            logger.debug(f"[_handle_correction] Operation: {operation}, params: {params}")

            if operation not in CORRECTION_VALID_OPERATIONS:
                return {"error": f"Invalid correction operation: '{operation}'", "valid_operations": CORRECTION_VALID_OPERATIONS}

            if operation == CORRECTION_OP_GET_ALL:
                # Group related parameters for clarity
                pagination_params = {
                    'page_size': params.get("page_size", 10),
                    'page': params.get("page"),
                    'order_by': params.get("order_by"),
                    'order_direction': params.get("order_direction")
                }

                filter_params = {
                    'query': params.get("query"),
                    'tag': params.get("tag"),
                    'id': params.get("id"),
                    'slo_id': params.get("slo_id"),
                    'refresh': params.get("refresh")
                }

                result = await self.slo_correction_client.get_all_corrections(
                    **pagination_params,
                    **filter_params,
                    ctx=ctx
                )
            elif operation == CORRECTION_OP_GET_BY_ID:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_correction_client.get_correction_by_id(id=params["id"], ctx=ctx)
            elif operation == CORRECTION_OP_CREATE:
                if not params.get("payload"):
                    return {"error": "Missing required parameter: 'payload'"}

                payload = params["payload"]

                # Check if scheduling exists
                if not isinstance(payload, dict) or "scheduling" not in payload:
                    return {
                        "elicitation_needed": True,
                        "message": "To create a correction window, I need the scheduling configuration. Please provide:\n\n- duration: How long should the correction window last? (e.g., 2 hours, 1 day)\n- durationUnit: Unit of time (hour, day, week, month)\n- startTime: When should it start? (e.g., '10 March 2026, 2:00 PM|IST')",
                        "missing_parameters": ["scheduling"],
                        "user_prompt": "Please specify the scheduling configuration for the correction window including duration, durationUnit, and startTime with timezone."
                    }

                scheduling = payload["scheduling"]

                # Check if startTime is missing
                if "startTime" not in scheduling:
                    return {
                        "elicitation_needed": True,
                        "message": "To create the correction window, I need to know when it should start.\n\nPlease provide the start time with timezone in format: 'datetime|timezone'\n\nExamples:\n- '10 March 2026, 2:00 PM|IST'\n- '2026-03-10 14:00:00|America/New_York'\n- 'March 10, 2026 2 PM|UTC'",
                        "missing_parameters": ["startTime"],
                        "user_prompt": "When should the correction window start? Please provide the date, time, and timezone."
                    }

                # Handle datetime string conversion for startTime
                if isinstance(scheduling["startTime"], str):
                    logger.debug(f"[_handle_correction] Converting startTime datetime string: {scheduling['startTime']}")

                    # Check if timezone is provided
                    if "|" not in scheduling["startTime"]:
                        # Elicit timezone from user
                        return {
                            "elicitation_needed": True,
                            "message": f"I see you want the correction window to start at '{scheduling['startTime']}', but I need to know which timezone.\n\nPlease specify the timezone:\n- IST (India Standard Time)\n- America/New_York (Eastern Time)\n- UTC (Coordinated Universal Time)\n- Europe/London (GMT/BST)\n- Asia/Tokyo (Japan Standard Time)\n\nOr any other IANA timezone name.",
                            "missing_parameters": ["timezone"],
                            "user_prompt": f"What timezone should be used for '{scheduling['startTime']}'?"
                        }

                    # Extract timezone
                    datetime_str, timezone = scheduling["startTime"].split("|", 1)

                    conversion_result = convert_to_timestamp(datetime_str.strip(), timezone.strip(), "milliseconds")
                    if "error" in conversion_result:
                        return {
                            "error": f"Failed to convert startTime datetime: {conversion_result['error']}",
                            "resource_type": RESOURCE_TYPE_CORRECTION,
                            "operation": operation
                        }
                    # Store as integer milliseconds - the correction client will convert to datetime
                    scheduling["startTime"] = conversion_result["timestamp"]
                    logger.info(f"[_handle_correction] Converted startTime to timestamp: {scheduling['startTime']}")

                result = await self.slo_correction_client.create_correction(payload=payload, ctx=ctx)
            elif operation == CORRECTION_OP_UPDATE:
                if not params.get("id") or not params.get("payload"):
                    return {"error": "Missing required parameters: 'id' and 'payload'"}

                payload = params["payload"]

                # Handle datetime string conversion for startTime in scheduling
                if isinstance(payload, dict) and "scheduling" in payload:
                    scheduling = payload["scheduling"]

                    # Check if startTime exists and is a string (datetime)
                    if "startTime" in scheduling and isinstance(scheduling["startTime"], str):
                        logger.debug(f"[_handle_correction] Converting startTime datetime string: {scheduling['startTime']}")

                        # Check if timezone is provided
                        if "|" not in scheduling["startTime"]:
                            # Elicit timezone from user
                            return {
                                "elicitation_needed": True,
                                "message": f"I see you want to update the correction window start time to '{scheduling['startTime']}', but I need to know which timezone.\n\nPlease specify the timezone:\n- IST (India Standard Time)\n- America/New_York (Eastern Time)\n- UTC (Coordinated Universal Time)\n- Europe/London (GMT/BST)\n- Asia/Tokyo (Japan Standard Time)\n\nOr any other IANA timezone name.",
                                "missing_parameters": ["timezone"],
                                "user_prompt": f"What timezone should be used for '{scheduling['startTime']}'?"
                            }

                        # Extract timezone if provided in format "datetime|timezone"
                        datetime_str, timezone = scheduling["startTime"].split("|", 1)

                        conversion_result = convert_to_timestamp(datetime_str.strip(), timezone.strip(), "milliseconds")
                        if "error" in conversion_result:
                            return {
                                "error": f"Failed to convert startTime datetime: {conversion_result['error']}",
                                "resource_type": RESOURCE_TYPE_CORRECTION,
                                "operation": operation
                            }
                        # Store as integer milliseconds - the correction client will convert to datetime
                        scheduling["startTime"] = conversion_result["timestamp"]
                        logger.info(f"[_handle_correction] Converted startTime to timestamp: {scheduling['startTime']}")

                result = await self.slo_correction_client.update_correction(
                    id=params["id"],
                    payload=payload,
                    ctx=ctx
                )
            elif operation == CORRECTION_OP_DELETE:
                if not params.get("id"):
                    return {"error": "Missing required parameter: 'id'"}
                result = await self.slo_correction_client.delete_correction(id=params["id"], ctx=ctx)

            return {"resource_type": RESOURCE_TYPE_CORRECTION, "operation": operation, "results": result}

        except Exception as e:
            logger.error(f"[_handle_correction] Error: {e}", exc_info=True)
            return {"error": f"Correction operation error: {e!s}", "resource_type": RESOURCE_TYPE_CORRECTION, "operation": operation}
