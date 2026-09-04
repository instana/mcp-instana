"""
SLO Smart Router Tool

This module provides a unified MCP tool that routes SLO (Service Level Objective)
queries to the appropriate specialized tools.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.timestamp_utils import convert_datetime_param_with_required_timezone
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

SLO_ID_HINT = "Use get_all to list available SLO IDs"
PAYLOAD_REQUIRED_FOR_CREATE = "payload is required for create"
ID_REQUIRED_FOR_UPDATE = "id is required for update"
ID_REQUIRED_FOR_DELETE = "id is required for delete"
PAYLOAD_REQUIRED_FOR_UPDATE = "payload is required for update"
MISSING_ID_FOR_DELETE_MESSAGE = "Missing required parameter 'id' for delete."
ALERT_CREATE_REQUIRED_FIELDS = ["name", "description", "sloIds", "rule", "severity", "alertChannelIds", "timeThreshold", "customPayloadFields"]
CORRECTION_CREATE_REQUIRED_FIELDS = ["name", "scheduling"]

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
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False),
        description="""Unified SLO manager for configurations, reports, alerts, and corrections.

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
        REQUIRED FIELDS: name, sloIds (list of SLO config IDs, e.g. ["slo-abc123"]), scheduling (with duration, durationUnit, startTime optional, recurrent optional, recurrentRule optional)
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
    # Response: {"elicitation_needed": True, "message": "I need...", "missing_parameters": [...]}"""
    )
    async def manage_slo(
        self,
        resource_type: str,
        operation: str,
        params: Optional[Dict[str, Any]] = None,
        ctx: Optional[Context] = None,
    ) -> Dict[str, Any]:
        """Unified SLO manager for configurations, reports, alerts, and corrections."""
        try:
            logger.debug(f"[manage_slo] Received: resource_type={resource_type}, operation={operation}")

            # Initialize params if not provided
            if params is None:
                params = {}

            # Validate resource_type
            if resource_type not in VALID_RESOURCE_TYPES:
                logger.warning(f"[manage_slo] Invalid resource_type: {resource_type}")
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

            TOOL_NAME = "manage_slo"

            # Route to the appropriate resource handler
            if resource_type == RESOURCE_TYPE_CONFIGURATION:
                return await self._handle_configuration(operation, params, ctx, resource_type=resource_type, tool_name=TOOL_NAME)
            elif resource_type == RESOURCE_TYPE_REPORT:
                return await self._handle_report(operation, params, ctx, resource_type=resource_type, tool_name=TOOL_NAME)
            elif resource_type == RESOURCE_TYPE_ALERT:
                return await self._handle_alert(operation, params, ctx, resource_type=resource_type, tool_name=TOOL_NAME)
            elif resource_type == RESOURCE_TYPE_CORRECTION:
                return await self._handle_correction(operation, params, ctx, resource_type=resource_type, tool_name=TOOL_NAME)
            else:
                logger.error(f"[manage_slo] Unhandled resource_type: {resource_type}")
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
        except Exception as e:
            logger.error(f"[manage_slo] Error in smart router: {e}", exc_info=True)
            return {
                "error": f"SLO smart router error: {e!s}",
                "resource_type": resource_type,
                "operation": operation
            }

    def _configuration_operation_result(
        self,
        operation: str,
        result: Any,
        slo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        response = {
            "resource_type": RESOURCE_TYPE_CONFIGURATION,
            "operation": operation,
            "results": result
        }
        if slo_id:
            response["id"] = slo_id
        return response

    def _get_all_configuration_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'page_size': params.get(PARAM_PAGE_SIZE, 10),
            'page': params.get(PARAM_PAGE),
            'order_by': params.get(PARAM_ORDER_BY),
            'order_direction': params.get(PARAM_ORDER_DIRECTION),
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

    def _missing_configuration_id_error(self, issue: str, message: str) -> Dict[str, Any]:
        logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_ID}")
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [
                {
                    "field": "id",
                    "issue": issue,
                    "hint": SLO_ID_HINT
                }
            ],
            "message": message
        }

    async def _handle_configuration(
        self,
        operation: str,
        params: Dict[str, Any],
        ctx,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle SLO configuration operations."""
        logger.debug(f"[_handle_configuration] Operation: {operation}, params: {params}")

        if operation not in CONFIG_VALID_OPERATIONS:
            logger.warning(f"[_handle_configuration] Invalid operation: {operation}")
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"'{operation}' is not a valid configuration operation",
                        "expected": CONFIG_VALID_OPERATIONS
                    }
                ],
                "message": f"Invalid operation '{operation}' for resource_type 'configuration'. Valid operations: {CONFIG_VALID_OPERATIONS}"
            }
        try:
            if operation == CONFIG_OP_GET_ALL:
                logger.debug("[_handle_configuration] Routing to get_all_slo_configs")
                result = await self.slo_config_client.get_all_slo_configs(
                    filters=self._get_all_configuration_params(params),
                    ctx=ctx,
                    resource_type=resource_type, tool_name=tool_name,
                )
                return self._configuration_operation_result(operation, result)

            if operation == CONFIG_OP_GET_BY_ID:
                slo_id = params.get(PARAM_ID)
                if not slo_id:
                    return self._missing_configuration_id_error(
                        "id is required for get_by_id",
                        "Missing required parameter 'id' for get_by_id."
                    )
                logger.debug(f"[_handle_configuration] Routing to get_slo_config_by_id with id: {slo_id}")
                result = await self.slo_config_client.get_slo_config_by_id(
                    id=slo_id,
                    refresh=params.get(PARAM_REFRESH),
                    ctx=ctx,
                    resource_type=resource_type, tool_name=tool_name,
                )
                return self._configuration_operation_result(operation, result)

            if operation == CONFIG_OP_CREATE:
                payload = params.get(PARAM_PAYLOAD)
                if not payload:
                    logger.warning(f"[_handle_configuration] Missing required parameter: {PARAM_PAYLOAD}")
                    return {
                        "elicitation_needed": True,
                        "reason": "missing_required_params",
                        "api_error": [
                            {
                                "field": "payload",
                                "issue": PAYLOAD_REQUIRED_FOR_CREATE,
                                "required_fields": ["name", "entity", "indicator", "target", "timeWindow", "tags"]
                            }
                        ],
                        "message": "Missing required parameter 'payload' for create. Required fields: name, entity, indicator, target, timeWindow, tags."
                    }
                logger.debug("[_handle_configuration] Routing to create_slo_config")
                result = await self.slo_config_client.create_slo_config(payload=payload, ctx=ctx, resource_type=resource_type, tool_name=tool_name)
                return self._configuration_operation_result(operation, result)

            if operation == CONFIG_OP_UPDATE:
                slo_id = params.get(PARAM_ID)
                payload = params.get(PARAM_PAYLOAD)
                errors = []
                if not slo_id:
                    errors.append({"field": "id", "issue": ID_REQUIRED_FOR_UPDATE, "hint": SLO_ID_HINT})
                if not payload:
                    errors.append({"field": "payload", "issue": PAYLOAD_REQUIRED_FOR_UPDATE, "required_fields": ["name", "entity", "indicator", "target", "timeWindow"]})
                if errors:
                    logger.warning(f"[_handle_configuration] Missing required parameters for update: {[e['field'] for e in errors]}")
                    return {
                        "elicitation_needed": True,
                        "reason": "missing_required_params",
                        "api_error": errors,
                        "message": f"Missing required parameters for update: {[e['field'] for e in errors]}"
                    }
                logger.debug(f"[_handle_configuration] Routing to update_slo_config with id: {slo_id}")
                result = await self.slo_config_client.update_slo_config(
                    id=slo_id,
                    payload=payload,
                    ctx=ctx,
                    resource_type=resource_type, tool_name=tool_name,
                )
                return self._configuration_operation_result(operation, result, slo_id)

            if operation == CONFIG_OP_DELETE:
                slo_id = params.get(PARAM_ID)
                if not slo_id:
                    return self._missing_configuration_id_error(
                        ID_REQUIRED_FOR_DELETE,
                        MISSING_ID_FOR_DELETE_MESSAGE
                    )

                logger.debug(f"[_handle_configuration] Routing to delete_slo_config with id: {slo_id}")
                result = await self.slo_config_client.delete_slo_config(id=slo_id, ctx=ctx, resource_type=resource_type, tool_name=tool_name)
                return self._configuration_operation_result(operation, result, slo_id)

            if operation == CONFIG_OP_GET_TAGS:
                logger.debug("[_handle_configuration] Routing to get_all_slo_config_tags")
                result = await self.slo_config_client.get_all_slo_config_tags(
                    query=params.get(PARAM_QUERY),
                    tag=params.get(PARAM_TAG),
                    entity_type=params.get(PARAM_ENTITY_TYPE),
                    ctx=ctx,
                    resource_type=resource_type, tool_name=tool_name,
                )
                return self._configuration_operation_result(operation, result)

            logger.error(f"[_handle_configuration] Unhandled operation: {operation}")
            return {
                "elicitation_needed": True,
                "reason": "invalid_operation",
                "api_error": [
                    {
                        "field": "operation",
                        "issue": f"Unhandled configuration operation: {operation}",
                        "expected": CONFIG_VALID_OPERATIONS
                    }
                ],
                "message": f"Unhandled configuration operation '{operation}'. Valid operations: {CONFIG_VALID_OPERATIONS}"
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
        ctx,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
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
                    "elicitation_needed": True,
                    "reason": "invalid_operation",
                    "api_error": [
                        {
                            "field": "operation",
                            "issue": f"'{operation}' is not a valid report operation",
                            "expected": REPORT_VALID_OPERATIONS
                        }
                    ],
                    "message": f"Invalid report operation '{operation}'. Valid operations: {REPORT_VALID_OPERATIONS}"
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
                        "elicitation_needed": True,
                        "reason": "missing_required_params",
                        "api_error": [
                            {
                                "field": "slo_id",
                                "issue": "slo_id is required to generate an SLO report",
                                "hint": "Use resource_type='configuration', operation='get_all' to list available SLO IDs"
                            }
                        ],
                        "message": "Missing required parameter 'slo_id' for get. Use configuration/get_all to list available SLO IDs."
                    }

                # Convert datetime strings to timestamps for var_from and to parameters
                # These parameters require explicit timezone specification
                var_from_result = convert_datetime_param_with_required_timezone(var_from, "var_from")

                # Check for elicitation or error
                if "elicitation_needed" in var_from_result:
                    return var_from_result
                if "error" in var_from_result:
                    return {
                        "error": var_from_result["error"],
                        "resource_type": RESOURCE_TYPE_REPORT,
                        "operation": operation
                    }

                # Convert to string as API expects StrictStr
                if var_from_result["converted"]:
                    var_from = str(var_from_result["value"])

                to_result = convert_datetime_param_with_required_timezone(to, "to")

                # Check for elicitation or error
                if "elicitation_needed" in to_result:
                    return to_result
                if "error" in to_result:
                    return {
                        "error": to_result["error"],
                        "resource_type": RESOURCE_TYPE_REPORT,
                        "operation": operation
                    }

                # Convert to string as API expects StrictStr
                if to_result["converted"]:
                    to = str(to_result["value"])

                logger.debug(f"[_handle_report] Routing to get_slo_report with slo_id: {slo_id}, var_from: {var_from}, to: {to}")
                result = await self.slo_report_client.get_slo_report(
                    slo_id=slo_id,
                    var_from=var_from,
                    to=to,
                    exclude_correction_id=exclude_correction_id,
                    include_correction_id=include_correction_id,
                    ctx=ctx,
                    resource_type=resource_type, tool_name=tool_name,
                )
                return {
                    "resource_type": RESOURCE_TYPE_REPORT,
                    "operation": operation,
                    "results": result
                }
            else:
                logger.error(f"[_handle_report] Unhandled operation: {operation}")
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_operation",
                    "api_error": [
                        {
                            "field": "operation",
                            "issue": f"Unhandled report operation: {operation}",
                            "expected": REPORT_VALID_OPERATIONS
                        }
                    ],
                    "message": f"Unhandled report operation '{operation}'. Valid operations: {REPORT_VALID_OPERATIONS}"
                }
        except Exception as e:
            logger.error(f"[_handle_report] Error handling report operation: {e!s}", exc_info=True)
            return {
                "error": f"Report operation error: {e!s}",
                "resource_type": RESOURCE_TYPE_REPORT,
                "operation": operation
            }

    async def _handle_alert(self, operation: str, params: Dict[str, Any], ctx,
                            resource_type: Optional[str] = None, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Handle alert config operations."""
        try:
            logger.debug(f"[_handle_alert] Operation: {operation}, params: {params}")

            if operation not in ALERT_VALID_OPERATIONS:
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_operation",
                    "api_error": [
                        {
                            "field": "operation",
                            "issue": f"'{operation}' is not a valid alert operation",
                            "expected": ALERT_VALID_OPERATIONS
                        }
                    ],
                    "message": f"Invalid alert operation '{operation}'. Valid operations: {ALERT_VALID_OPERATIONS}"
                }

            result = await self._execute_alert_operation(operation, params, ctx, resource_type=resource_type, tool_name=tool_name)
            if isinstance(result, dict) and result.get("elicitation_needed"):
                return result

            return {"resource_type": RESOURCE_TYPE_ALERT, "operation": operation, "results": result}

        except Exception as e:
            logger.error(f"[_handle_alert] Error: {e}", exc_info=True)
            return {"error": f"Alert operation error: {e!s}", "resource_type": RESOURCE_TYPE_ALERT, "operation": operation}

    def _missing_alert_id_error(self, issue: str, message: str) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [{"field": "id", "issue": issue}],
            "message": message
        }

    def _missing_alert_payload_error(self) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [{"field": "payload", "issue": PAYLOAD_REQUIRED_FOR_CREATE, "required_fields": ALERT_CREATE_REQUIRED_FIELDS}],
            "message": "Missing required parameter 'payload' for create."
        }

    def _validate_alert_update_params(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        errors = []
        if not params.get("id"):
            errors.append({"field": "id", "issue": ID_REQUIRED_FOR_UPDATE})
        if not params.get("payload"):
            errors.append({"field": "payload", "issue": PAYLOAD_REQUIRED_FOR_UPDATE})
        if errors:
            return {
                "elicitation_needed": True,
                "reason": "missing_required_params",
                "api_error": errors,
                "message": f"Missing required parameters for update: {[e['field'] for e in errors]}"
            }
        return None

    def _validate_alert_restore_params(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        errors = []
        if not params.get("id"):
            errors.append({"field": "id", "issue": "id is required for restore"})
        if not params.get("created"):
            errors.append({"field": "created", "issue": "created timestamp is required for restore", "hint": "Provide the version timestamp from find_versions"})
        if errors:
            return {
                "elicitation_needed": True,
                "reason": "missing_required_params",
                "api_error": errors,
                "message": f"Missing required parameters for restore: {[e['field'] for e in errors]}"
            }
        return None

    def _validate_alert_operation(self, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return an error dict if *params* fail validation for *operation*, else None."""
        _id_required_ops = {
            ALERT_OP_FIND:          ("id is required for find",          "Missing required parameter 'id' for find."),
            ALERT_OP_FIND_VERSIONS: ("id is required for find_versions", "Missing required parameter 'id' for find_versions."),
            ALERT_OP_DELETE:        (ID_REQUIRED_FOR_DELETE,             MISSING_ID_FOR_DELETE_MESSAGE),
            ALERT_OP_DISABLE:       ("id is required for disable",       "Missing required parameter 'id' for disable."),
            ALERT_OP_ENABLE:        ("id is required for enable",        "Missing required parameter 'id' for enable."),
        }
        if operation in _id_required_ops:
            issue, message = _id_required_ops[operation]
            return None if params.get("id") else self._missing_alert_id_error(issue, message)
        if operation == ALERT_OP_CREATE:
            return None if params.get("payload") else self._missing_alert_payload_error()
        if operation == ALERT_OP_UPDATE:
            return self._validate_alert_update_params(params)
        if operation == ALERT_OP_RESTORE:
            return self._validate_alert_restore_params(params)
        return None

    async def _call_alert_client(self, operation: str, params: Dict[str, Any], ctx,
                                 resource_type: Optional[str], tool_name: Optional[str]):
        """Dispatch a pre-validated alert *operation* to the appropriate client method."""
        kw = {"ctx": ctx, "resource_type": resource_type, "tool_name": tool_name}
        if operation == ALERT_OP_FIND_ACTIVE:
            return await self.slo_alert_client.find_active_alert_configs(slo_id=params.get("slo_id"), alert_ids=params.get("alert_ids"), **kw)
        if operation == ALERT_OP_FIND:
            return await self.slo_alert_client.find_alert_config(id=params["id"], valid_on=params.get("valid_on"), **kw)
        if operation == ALERT_OP_FIND_VERSIONS:
            return await self.slo_alert_client.find_alert_config_versions(id=params["id"], **kw)
        if operation == ALERT_OP_CREATE:
            return await self.slo_alert_client.create_alert_config(payload=params["payload"], **kw)
        if operation == ALERT_OP_UPDATE:
            return await self.slo_alert_client.update_alert_config(id=params["id"], payload=params["payload"], **kw)
        if operation == ALERT_OP_DELETE:
            return await self.slo_alert_client.delete_alert_config(id=params["id"], **kw)
        if operation == ALERT_OP_DISABLE:
            return await self.slo_alert_client.disable_alert_config(id=params["id"], **kw)
        if operation == ALERT_OP_ENABLE:
            return await self.slo_alert_client.enable_alert_config(id=params["id"], **kw)
        return await self.slo_alert_client.restore_alert_config(id=params["id"], created=params["created"], **kw)

    async def _execute_alert_operation(self, operation: str, params: Dict[str, Any], ctx,
                                       resource_type: Optional[str] = None, tool_name: Optional[str] = None):
        error = self._validate_alert_operation(operation, params)
        if error:
            return error
        return await self._call_alert_client(operation, params, ctx, resource_type, tool_name)

    def _missing_correction_id_error(self, issue: str, message: str) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [{"field": "id", "issue": issue}],
            "message": message
        }

    def _missing_correction_payload_error(self) -> Dict[str, Any]:
        return {
            "elicitation_needed": True,
            "reason": "missing_required_params",
            "api_error": [{"field": "payload", "issue": PAYLOAD_REQUIRED_FOR_CREATE, "required_fields": CORRECTION_CREATE_REQUIRED_FIELDS}],
            "message": "Missing required parameter 'payload' for create. Required fields: name, scheduling."
        }

    def _validate_correction_update_params(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        errors = []
        if not params.get("id"):
            errors.append({"field": "id", "issue": ID_REQUIRED_FOR_UPDATE})
        if not params.get("payload"):
            errors.append({"field": "payload", "issue": PAYLOAD_REQUIRED_FOR_UPDATE})
        if errors:
            return {
                "elicitation_needed": True,
                "reason": "missing_required_params",
                "api_error": errors,
                "message": f"Missing required parameters for update: {[e['field'] for e in errors]}"
            }
        return None

    def _get_all_correction_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'page_size': params.get("page_size", 10),
            'page': params.get("page"),
            'order_by': params.get("order_by"),
            'order_direction': params.get("order_direction"),
            'query': params.get("query"),
            'tag': params.get("tag"),
            'id': params.get("id"),
            'slo_id': params.get("slo_id"),
            'refresh': params.get("refresh")
        }

    def _normalize_correction_start_time(self, scheduling: Dict[str, Any], operation: str) -> Optional[Dict[str, Any]]:
        # If startTime is already a numeric ms timestamp, pass it through directly —
        # no timezone elicitation needed.
        if isinstance(scheduling["startTime"], (int, float)):
            return None

        start_time_result = convert_datetime_param_with_required_timezone(
            scheduling["startTime"],
            "startTime"
        )

        if "elicitation_needed" in start_time_result:
            return start_time_result
        if "error" in start_time_result:
            return {
                "error": start_time_result["error"],
                "resource_type": RESOURCE_TYPE_CORRECTION,
                "operation": operation
            }
        if start_time_result.get("converted"):
            if "value" not in start_time_result:
                return {
                    "error": "Failed to convert startTime: missing value",
                    "resource_type": RESOURCE_TYPE_CORRECTION,
                    "operation": operation
                }
            scheduling["startTime"] = start_time_result["value"]
        return None

    def _validate_create_correction_payload(self, payload) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict) or "scheduling" not in payload:
            return {
                "elicitation_needed": True,
                "message": "To create a correction window, I need the scheduling configuration. Please provide:\n\n- duration: How long should the correction window last? (e.g., 2 hours, 1 day)\n- durationUnit: Unit of time (hour, day, week, month)\n- startTime: When should it start? (e.g., '10 March 2026, 2:00 PM|IST')",
                "missing_parameters": ["scheduling"],
                "user_prompt": "Please specify the scheduling configuration for the correction window including duration, durationUnit, and startTime with timezone."
            }

        if "startTime" not in payload["scheduling"]:
            return {
                "elicitation_needed": True,
                "message": "To create the correction window, I need to know when it should start.\n\nPlease provide the start time with timezone in format: 'datetime|timezone'\n\nExamples:\n- '10 March 2026, 2:00 PM|IST'\n- '2026-03-10 14:00:00|America/New_York'\n- 'March 10, 2026 2 PM|UTC'",
                "missing_parameters": ["startTime"],
                "user_prompt": "When should the correction window start? Please provide the date, time, and timezone."
            }

        return None

    def _validate_correction_create_params(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate CREATE params; return error dict or None."""
        if not params.get("payload"):
            return self._missing_correction_payload_error()
        payload = params["payload"]
        error = self._validate_create_correction_payload(payload)
        if error:
            return error
        return self._normalize_correction_start_time(payload["scheduling"], CORRECTION_OP_CREATE)

    def _validate_correction_update_payload(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalise startTime in an UPDATE payload if present; return error dict or None."""
        payload = params["payload"]
        if not (isinstance(payload, dict) and "scheduling" in payload):
            return None
        scheduling = payload["scheduling"]
        if "startTime" in scheduling and isinstance(scheduling["startTime"], str):
            return self._normalize_correction_start_time(scheduling, CORRECTION_OP_UPDATE)
        return None

    def _validate_correction_operation(self, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return an error dict if *params* fail validation for *operation*, else None."""
        if operation == CORRECTION_OP_GET_BY_ID:
            return None if params.get("id") else self._missing_correction_id_error("id is required for get_by_id", "Missing required parameter 'id' for get_by_id.")
        if operation == CORRECTION_OP_CREATE:
            return self._validate_correction_create_params(params)
        if operation == CORRECTION_OP_UPDATE:
            return self._validate_correction_update_params(params) or self._validate_correction_update_payload(params)
        if operation == CORRECTION_OP_DELETE:
            return None if params.get("id") else self._missing_correction_id_error(ID_REQUIRED_FOR_DELETE, MISSING_ID_FOR_DELETE_MESSAGE)
        return None

    async def _call_correction_client(self, operation: str, params: Dict[str, Any], ctx,
                                      resource_type: Optional[str], tool_name: Optional[str]):
        """Dispatch a pre-validated correction *operation* to the appropriate client method."""
        kw = {"ctx": ctx, "resource_type": resource_type, "tool_name": tool_name}
        if operation == CORRECTION_OP_GET_ALL:
            return await self.slo_correction_client.get_all_corrections(**self._get_all_correction_params(params), **kw)
        if operation == CORRECTION_OP_GET_BY_ID:
            return await self.slo_correction_client.get_correction_by_id(id=params["id"], **kw)
        if operation == CORRECTION_OP_CREATE:
            return await self.slo_correction_client.create_correction(payload=params["payload"], **kw)
        if operation == CORRECTION_OP_UPDATE:
            return await self.slo_correction_client.update_correction(id=params["id"], payload=params["payload"], **kw)
        return await self.slo_correction_client.delete_correction(id=params["id"], **kw)

    async def _execute_correction_operation(self, operation: str, params: Dict[str, Any], ctx,
                                            resource_type: Optional[str] = None, tool_name: Optional[str] = None):
        error = self._validate_correction_operation(operation, params)
        if error:
            return error
        return await self._call_correction_client(operation, params, ctx, resource_type, tool_name)

    async def _handle_correction(self, operation: str, params: Dict[str, Any], ctx,
                                 resource_type: Optional[str] = None, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Handle correction window operations."""
        try:
            logger.debug(f"[_handle_correction] Operation: {operation}, params: {params}")

            if operation not in CORRECTION_VALID_OPERATIONS:
                return {
                    "elicitation_needed": True,
                    "reason": "invalid_operation",
                    "api_error": [
                        {
                            "field": "operation",
                            "issue": f"'{operation}' is not a valid correction operation",
                            "expected": CORRECTION_VALID_OPERATIONS
                        }
                    ],
                    "message": f"Invalid correction operation '{operation}'. Valid operations: {CORRECTION_VALID_OPERATIONS}"
                }

            result = await self._execute_correction_operation(operation, params, ctx, resource_type=resource_type, tool_name=tool_name)
            if isinstance(result, dict) and (result.get("elicitation_needed") or result.get("error")):
                return result

            return {"resource_type": RESOURCE_TYPE_CORRECTION, "operation": operation, "results": result}

        except Exception as e:
            logger.error(f"[_handle_correction] Error: {e}", exc_info=True)
            return {"error": f"Correction operation error: {e!s}", "resource_type": RESOURCE_TYPE_CORRECTION, "operation": operation}
