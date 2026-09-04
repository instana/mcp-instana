"""
Application Alert MCP Tools Module

This module provides application alert configuration tools for Instana monitoring.
"""

import ast
import json
import logging
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.global_application_alert_configuration_api import (
        GlobalApplicationAlertConfigurationApi,
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import application alert configuration API", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationGlobalAlertMCPTools(BaseInstanaClient):
    """Tools for application alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    # CRUD Operations Dispatcher - called by application_smart_router_tool.py
    @staticmethod
    def _validate_alert_payload(
        payload: Optional[Any],
        operation: str,
        resource_label: str = "global_alert_config",
    ) -> Optional[Dict[str, Any]]:
        """
        Validate create/update payload against GlobalApplicationsAlertConfig SDK model.

        Confirmed required fields (SDK throws 'Field required' if absent, verified by
        calling model_validate without each field):
          name, description, boundaryScope, evaluationType, granularity,
          applications, tagFilterExpression, timeThreshold
          (alertChannelIds & customPayloadFields are auto-defaulted by the service layer)

        Confirmed optional (have default=None):
          applicationId, alertChannels, enabled, gracePeriod, includeInternal,
          includeSynthetic, rule, rules, severity, tagFilters, threshold, triggering

        Returns a consolidated elicitation dict, or None when valid.
        """
        errors: List[str] = []

        if payload is None or payload == {}:
            return {
                "elicitation_needed": True,
                "reason": f"{resource_label} '{operation}': payload is missing",
                "api_error": ["payload: required — provide the alert configuration object"],
                "message": "Correct all issues below and retry:\n  - payload: required — provide the alert configuration object",
            }

        if not isinstance(payload, dict):
            return {
                "elicitation_needed": True,
                "reason": f"{resource_label} '{operation}': payload must be a dict",
                "api_error": [f"payload: must be a dict, got {type(payload).__name__!r}"],
                "message": f"Correct all issues below and retry:\n  - payload: must be a dict, got {type(payload).__name__!r}",
            }

        # name and description — required strings (min_length=0, so empty string is valid)
        for field, max_len in [("name", 256), ("description", 65536)]:
            val = payload.get(field)
            if val is None:
                errors.append(f"{field}: required — string, max {max_len} chars")
            elif not isinstance(val, str):
                errors.append(f"{field}: must be a string, got {type(val).__name__!r}")
            elif len(val) > max_len:
                errors.append(f"{field}: exceeds maximum length of {max_len} characters")

        # boundaryScope — required StrictStr enum
        boundary_scope = payload.get("boundaryScope")
        if boundary_scope is None:
            errors.append("boundaryScope: required — valid values: 'ALL', 'INBOUND'")
        elif boundary_scope not in ("ALL", "INBOUND"):
            errors.append(f"boundaryScope: '{boundary_scope}' is not valid — must be 'ALL' or 'INBOUND'")

        # evaluationType — required StrictStr enum
        evaluation_type = payload.get("evaluationType")
        _valid_eval = ("PER_AP", "PER_AP_SERVICE", "PER_AP_ENDPOINT")
        if evaluation_type is None:
            errors.append(f"evaluationType: required — valid values: {list(_valid_eval)}")
        elif evaluation_type not in _valid_eval:
            errors.append(f"evaluationType: '{evaluation_type}' is not valid — must be one of {list(_valid_eval)}")

        # granularity — required StrictInt enum (verified: SDK throws 'Field required' if absent,
        # and 'Value error' for values outside the allowed set)
        granularity = payload.get("granularity")
        _valid_granularity = (60000, 300000, 600000, 900000, 1200000, 1800000)
        if granularity is None:
            errors.append(f"granularity: required — valid values in ms: {list(_valid_granularity)}")
        elif not isinstance(granularity, int):
            errors.append(f"granularity: must be an integer, got {type(granularity).__name__!r}")
        elif granularity not in _valid_granularity:
            errors.append(f"granularity: {granularity} is not valid — must be one of {list(_valid_granularity)} ms")

        # applications — required Dict (verified: SDK throws 'Field required' if absent)
        applications = payload.get("applications")
        if applications is None:
            errors.append(
                'applications: required — dict mapping applicationId → node config, e.g. '
                '{"<appId>": {"applicationId": "<appId>", "inclusive": true, "services": {}}}'
            )
        elif not isinstance(applications, dict):
            errors.append(f"applications: must be a dict, got {type(applications).__name__!r}")

        # tagFilterExpression — required (verified: SDK throws 'Field required' if absent)
        if payload.get("tagFilterExpression") is None:
            errors.append(
                'tagFilterExpression: required — e.g. {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}'
            )

        # timeThreshold — required (no default in SDK model)
        if payload.get("timeThreshold") is None:
            errors.append(
                'timeThreshold: required — e.g. {"type": "violationsInSequence", "timeWindow": 600000}'
            )

        # severity — optional but enum-constrained (ge=5, le=10) when present
        severity = payload.get("severity")
        if severity is not None and severity not in (5, 10):
            errors.append(f"severity: {severity} is not valid — must be 5 (Warning) or 10 (Critical)")

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": f"{resource_label} '{operation}' payload has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The '{operation}' payload has {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    @staticmethod
    def _preflight_global_alert_config(
        operation: str,
        application_id: Optional[str],
        id: Optional[str],
        created: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Validate required parameters before executing a global_alert_config operation."""
        errors: List[str] = []

        if operation == "find_active" and not application_id:
            errors.append(
                "application_id: required for 'find_active' — "
                "provide the application perspective ID or use application_name to resolve it automatically"
            )

        if operation in ("find", "find_versions", "update", "delete", "enable", "disable", "restore") and not id:
            errors.append(
                f"id: required for '{operation}' — "
                "provide the alert configuration ID (obtain one from 'find_active')"
            )

        if operation == "restore":
            if not created:
                errors.append(
                    "created: required for 'restore' — "
                    "provide the Unix timestamp (ms) of the version to restore "
                    "(obtain from 'find_versions')"
                )
            elif not isinstance(created, int) or created <= 0:
                errors.append(
                    f"created: must be a positive integer Unix timestamp in milliseconds, got {created!r}"
                )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": f"global_alert_config '{operation}' has {len(errors)} missing required parameter(s)",
            "api_error": errors,
            "message": (
                f"Cannot execute '{operation}': {len(errors)} required parameter(s) missing or invalid. "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    @staticmethod
    def _parse_payload(payload: Optional[Union[Dict[str, Any], str]]) -> Any:
        """Parse a string payload to dict; return non-string payloads unchanged."""
        if not isinstance(payload, str):
            return payload
        try:
            return json.loads(payload)
        except Exception:
            try:
                return ast.literal_eval(payload)
            except Exception:
                return None

    async def _dispatch_global_alert_config(
        self,
        operation: str,
        application_id: Optional[str],
        id: Optional[str],
        alert_ids: Optional[List[str]],
        valid_on: Optional[int],
        created: Optional[int],
        payload: Optional[Union[Dict[str, Any], str]],
        ctx,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Route a validated global_alert_config operation to the appropriate handler."""
        _r = {"resource_type": resource_type, "tool_name": tool_name}
        dispatch = {
            "find_active": lambda: self._find_active_configs(application_id, alert_ids, ctx, **_r),
            "find_versions": lambda: self._find_config_versions(id, ctx, **_r),
            "find": lambda: self._find_config(id, valid_on, ctx, **_r),
            "create": lambda: self._create_config(payload, ctx, **_r),
            "update": lambda: self._update_config(id, payload, ctx, **_r),
            "delete": lambda: self._delete_config(id, ctx, **_r),
            "enable": lambda: self._enable_config(id, ctx, **_r),
            "disable": lambda: self._disable_config(id, ctx, **_r),
            "restore": lambda: self._restore_config(id, created, ctx, **_r),
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {"error": f"Operation '{operation}' not supported"}
        return await handler()

    async def execute_alert_config_operation(
        self,
        operation: str,
        application_id: Optional[str] = None,
        id: Optional[str] = None,
        alert_ids: Optional[List[str]] = None,
        valid_on: Optional[int] = None,
        created: Optional[int] = None,
        payload: Optional[Union[Dict[str, Any], str]] = None,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute Global Application Alert Config CRUD operations.
        Called by the smart router tool.

        Args:
            operation: Operation to perform (find_active, find_versions, find, create, update, delete, enable, disable, restore)
            application_id: Application ID (for find_active)
            id: Alert config ID
            alert_ids: List of alert IDs to filter
            valid_on: Unix timestamp for specific version
            created: Unix timestamp for restore
            payload: Configuration payload
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            preflight = self._preflight_global_alert_config(operation, application_id, id, created)
            if preflight:
                return preflight

            if operation in ("create", "update"):
                elicitation = self._validate_alert_payload(
                    self._parse_payload(payload), operation, "global_alert_config"
                )
                if elicitation:
                    return elicitation

            return await self._dispatch_global_alert_config(
                operation, application_id, id, alert_ids, valid_on, created, payload, ctx,
                resource_type=resource_type, tool_name=tool_name,
            )

        except Exception as e:
            logger.error(f"Error executing {operation}: {e}", exc_info=True)
            return {"error": f"Error executing {operation}: {e!s}"}

    # Individual operation functions

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _find_active_configs(
        self,
        application_id: Optional[str],
        alert_ids: Optional[List[str]],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find active global application alert configs."""
        if not application_id:
            return {"error": "application_id is required for find_active operation"}

        return await self.find_active_global_application_alert_configs(
            application_id=application_id,
            alert_ids=alert_ids,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _find_config_versions(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find all versions of a global application alert config."""
        if not id:
            return {"error": "id is required for find_versions operation"}

        return await self.find_global_application_alert_config_versions(
            id=id,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _find_config(
        self,
        id: Optional[str],
        valid_on: Optional[int],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find a specific global application alert config."""
        return await self.find_global_application_alert_config(
            id=id,
            valid_on=valid_on,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _create_config(
        self,
        payload: Optional[Union[Dict[str, Any], str]],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new global application alert config."""
        if not payload:
            return {"error": "payload is required for create operation"}

        return await self.create_global_application_alert_config(
            payload=payload,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _update_config(
        self,
        id: Optional[str],
        payload: Optional[Union[Dict[str, Any], str]],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing global application alert config."""
        if not id:
            return {"error": "id is required for update operation"}
        if not payload:
            return {"error": "payload is required for update operation"}

        return await self.update_global_application_alert_config(
            id=id,
            payload=payload,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _delete_config(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete a global application alert config."""
        if not id:
            return {"error": "id is required for delete operation"}

        return await self.delete_global_application_alert_config(
            id=id,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _enable_config(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enable a global application alert config."""
        if not id:
            return {"error": "id is required for enable operation"}

        return await self.enable_global_application_alert_config(
            id=id,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _disable_config(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Disable a global application alert config."""
        if not id:
            return {"error": "id is required for disable operation"}

        return await self.disable_global_application_alert_config(
            id=id,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _restore_config(
        self,
        id: Optional[str],
        created: Optional[int],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore a deleted global application alert config."""
        if not id:
            return {"error": "id is required for restore operation"}
        if not created:
            return {"error": "created timestamp is required for restore operation"}

        return await self.restore_global_application_alert_config(
            id=id,
            created=created,
            ctx=ctx,
            api_client=api_client,
            resource_type=resource_type,
            tool_name=tool_name,
        )

    # Original individual methods - no @register_as_tool decorator
    # These are called internally by the operation functions above

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def find_active_global_application_alert_configs(self,
                                            application_id: str,
                                            alert_ids: Optional[List[str]] = None,
                                            ctx=None, api_client=None,
                                            resource_type: Optional[str] = None,
                                            tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get All Global Smart Alert Configuration.

        This tool retrieves all Global Smart Alert Configuration, filtered by application ID and alert IDs.
        This may return a deleted Configuration.

        Configurations are sorted by creation date in descending order.

        Args:
            id: The ID of a specific global application.
            valid_on: A list of Global Smart Alert Configuration IDs. This allows fetching of a specific set of Configurations. This query can be repeated to use multiple IDs.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"find_active_global_application_alert_configs called with application_id={application_id}, alert_ids={alert_ids}")

            # Validate required parameters
            if not application_id:
                return {"error": "application_id is required"}

            # Call the find_active_global_application_alert_configs method from the SDK
            logger.debug(f"Calling find_active_global_application_alert_configs with application_id={application_id}, alert_ids={alert_ids}")
            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.find_active_global_application_alert_configs_without_preload_content,
                    application_id=application_id,
                    alert_ids=alert_ids
                ),
                ctx=ctx,
                operation_name="find_active_global_application_alert_configs",
                resource_type=resource_type, tool_name=tool_name,
            )

            raw_data = response.data.decode('utf-8')
            logger.debug(f"Raw data: {raw_data}")

            try:
                result = json.loads(raw_data)
                logger.debug(f"Parsed JSON result: {result}")

                if isinstance(result, list):
                    configs = result
                else:
                    configs = [result] if result else []

                # Limit to first 10 results
                total_count = len(configs)
                limited_configs = configs[:10]

                # Provide helpful feedback based on the result
                if not configs:
                    return {
                        "configs": [],
                        "count": 0,
                        "total": 0,
                        "showing": 0,
                        "message": f"No active global alert configurations found for application ID: {application_id}",
                        "suggestion": "You can create a new global alert configuration using the 'create' operation."
                    }
                else:
                    return {
                        "configs": limited_configs,
                        "count": len(limited_configs),
                        "total": total_count,
                        "showing": len(limited_configs),
                        "message": f"Found {total_count} active global alert configuration(s) for application ID: {application_id}. Showing first {len(limited_configs)}."
                    }

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse response JSON: {e}"
                logger.error(error_msg)
                return {"error": error_msg}

        except Exception as e:
            logger.error(f"Error in find_active_global_application_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to get active global application alert config: {e!s}"}


    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def find_global_application_alert_config_versions(self,
                                                     id: str,
                                                     ctx=None, api_client=None,
                                                     resource_type: Optional[str] = None,
                                                     tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Global Smart Alert Config Versions . Get all versions of Global Smart Alert Configuration.

        This tool retrievesGets all versions of a Global Smart Alert Configuration.
        This may return deleted Configurations. Configurations are sorted by creation date in descending order.

        Args:
            id: ID of a specific Global Smart Alert Configuration to retrieve.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the Smart Alert Configuration versions or error information
        """
        try:
            logger.debug(f"find_global_application_alert_config_versions called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the find_global_application_alert_config_versions method from the SDK
            logger.debug(f"Calling find_global_application_alert_config_versions with id={id}")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.find_global_application_alert_config_versions,
                    id=id
                ),
                ctx=ctx,
                operation_name="find_global_application_alert_config_versions",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                # If result is a list, convert each item to a dictionary and wrap in a dict
                items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                result_dict = {"versions": items}
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result if isinstance(result, dict) else {"data": result}

            logger.debug(f"Result from find_global_application_alert_config_versions: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in find_global_application_alert_config_versions: {e}", exc_info=True)
            return {"error": f"Failed to get global application alert config versions: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def find_global_application_alert_config(self,
                                            id: Optional[str] = None,
                                            valid_on: Optional[int] = None,
                                            ctx=None, api_client=None,
                                            resource_type: Optional[str] = None,
                                            tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Gets a specific Global Smart Alert Configuration. This may return a deleted Configuration.

        This tool retrieves Global Smart Alert Configurations, filtered by id and valid on.

        Args:
            id: ID of a specific Global Smart Alert Configuration to retrieve
            valid_on: A Unix timestamp representing a specific time the Configuration was active. If no timestamp is provided, the latest active version will be retrieved.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configurations or error information
        """
        try:
            logger.debug(f"get_application_alert_configs called with id={id}, valid_on={valid_on}")

            # Call the find_global_application_alert_config method from the SDK
            logger.debug(f"Calling find_global_application_alert_config with id={id}, valid_on={valid_on}")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.find_global_application_alert_config,
                    id=id,
                    valid_on=valid_on
                ),
                ctx=ctx,
                operation_name="find_global_application_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                # If result is a list, convert each item to a dictionary and wrap in a dict
                items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                result_dict = {"configs": items}
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result if isinstance(result, dict) else {"data": result}

            logger.debug(f"Result from find_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in find_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to get global application alert configs: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def delete_global_application_alert_config(self,
                                              id: str,
                                              ctx=None, api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Deletes a Global Smart Alert Configuration.

        This tool deletes a specific Global Smart Alert Configuration by its ID.
        Once deleted, the configuration will no longer trigger alerts.

        Args:
            id: ID of a specific Global Smart Alert Configuration to delete.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the deletion operation or error information
        """
        try:
            logger.debug(f"delete_global_application_alert_config called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the delete_global_application_alert_config method from the SDK
            logger.debug(f"Calling delete_global_application_alert_config with id={id}")
            await sdk_call_with_keepalive(call_sdk_fn(api_client.delete_global_application_alert_config, id=id), ctx=ctx, operation_name="delete_global_application_alert_config", resource_type=resource_type, tool_name=tool_name)

            # The delete operation doesn't return a result, so we'll create a success message
            result_dict = {
                "success": True,
                "message": f"Global Smart Alert Configuration with ID '{id}' has been successfully deleted"
            }

            logger.debug(f"Result from delete_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in delete_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to delete global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def enable_global_application_alert_config(self,
                                              id: str,
                                              ctx=None, api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Enable a Global Smart Alert Configuration.

        This tool enables a specific Global Smart Alert Configuration by its ID.
        Once enabled, the configuration will start triggering alerts when conditions are met.

        Args:
            id: ID of a specific Global Smart Alert Configuration to enable.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the enable operation or error information
        """
        try:
            logger.debug(f"enable_global_application_alert_config called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the enable_global_application_alert_config method from the SDK
            logger.debug(f"Calling enable_global_application_alert_config with id={id}")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.enable_global_application_alert_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="enable_global_application_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Global Smart Alert Configuration with ID '{id}' has been successfully enabled"
                }

            logger.debug(f"Result from enable_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in enable_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to enable global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def disable_global_application_alert_config(self,
                                               id: str,
                                               ctx=None, api_client=None,
                                               resource_type: Optional[str] = None,
                                               tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Disable a Global Smart Alert Configuration.

        This tool disables a specific Smart Alert Configuration by its ID.
        Once disabled, the configuration will stop triggering alerts even when conditions are met.

        Args:
            id: ID of a specific Global Smart Alert Configuration to disable.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the disable operation or error information
        """
        try:
            logger.debug(f"disable_global_application_alert_config called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the disable_global_application_alert_config method from the SDK
            logger.debug(f"Calling disable_global_application_alert_config with id={id}")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.disable_global_application_alert_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="disable_global_application_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Smart Alert Configuration with ID '{id}' has been successfully disabled"
                }

            logger.debug(f"Result from disable_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in disable_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to disable global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def restore_global_application_alert_config(self,
                                               id: str,
                                               created: int,
                                               ctx=None, api_client=None,
                                               resource_type: Optional[str] = None,
                                               tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Restore a deleted Global Smart Alert Configuration.

        This tool restores a previously deleted Global Smart Alert Configuration by its ID and creation timestamp.
        Once restored, the configuration will be active again and can trigger alerts when conditions are met.

        Args:
            id: ID of a specific Global Smart Alert Configuration to restore.
            created: Unix timestamp representing the creation time of the specific Global Smart Alert Configuration version
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the restore operation or error information
        """
        try:
            logger.debug(f"restore_global_application_alert_config called with id={id}, created={created}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            if not created:
                return {"error": "created timestamp is required"}

            # Call the restore_global_application_alert_config method from the SDK
            logger.debug(f"Calling restore_global_application_alert_config with id={id}, created={created}")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.restore_global_application_alert_config,
                    id=id,
                    created=created
                ),
                ctx=ctx,
                operation_name="restore_global_application_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Global Smart Alert Configuration with ID '{id}' and creation timestamp '{created}' has been successfully restored"
                }

            logger.debug(f"Result from restore_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in restore_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to restore global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def create_global_application_alert_config(self,
                                              payload: Union[Dict[str, Any], str],
                                              ctx=None, api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new Global Smart Alert Configuration.

        This tool creates a new Global Smart Alert Configuration with the provided configuration details.
        Once created, the configuration will be active and can trigger alerts when conditions are met.

        Sample payload:
        {
        "name": "Slow calls than usual",
        "description": "Calls are slower or equal to 2 ms based on latency (90th).",
        "boundaryScope": "INBOUND",
        "applications": {
            "j02SxMRTSf-NCBXf5IdsjQ": {
            "applicationId": "j02SxMRTSf-NCBXf5IdsjQ",
            "inclusive": true,
            "services": {}
            }
        },
        "applicationIds": [
            "j02SxMRTSf-NCBXf5IdsjQ"
        ],
        "severity": 5,
        "triggering": false,
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": []
        },
        "includeInternal": false,
        "includeSynthetic": false,
        "rule": {
            "alertType": "slowness",
            "aggregation": "P90",
            "metricName": "latency"
        },
        "threshold": {
            "type": "staticThreshold",
            "operator": ">=",
            "value": 2,
            "lastUpdated": 0
        },
        "alertChannelIds": [],
        "granularity": 600000,
        "timeThreshold": {
            "type": "violationsInSequence",
            "timeWindow": 600000
        },
        "evaluationType": "PER_AP",
        "customPayloadFields": []
        }

        Args:
            payload: The Global Smart Alert Configuration details as a dictionary or JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the created new Global Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"create_global_application_alert_config called with payload={payload}")

            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    try:
                        parsed_payload = json.loads(payload)
                        logger.debug("Successfully parsed payload as JSON")
                        request_body = parsed_payload
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON parsing failed: {e}, trying with quotes replaced")

                        # Try replacing single quotes with double quotes
                        fixed_payload = payload.replace("'", "\"")
                        try:
                            parsed_payload = json.loads(fixed_payload)
                            logger.debug("Successfully parsed fixed JSON")
                            request_body = parsed_payload
                        except json.JSONDecodeError:
                            # Try as Python literal
                            try:
                                parsed_payload = ast.literal_eval(payload)
                                logger.debug("Successfully parsed payload as Python literal")
                                request_body = parsed_payload
                            except (SyntaxError, ValueError) as e2:
                                logger.debug(f"Failed to parse payload string: {e2}")
                                return {"error": f"Invalid payload format: {e2}", "payload": payload}
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return {"error": f"Failed to parse payload: {e}", "payload": payload}
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Validate the payload
            if not request_body:
                return {"error": "Payload is required"}

            # Import the GlobalApplicationsAlertConfig class
            try:
                from instana_client.models.global_applications_alert_config import (
                    GlobalApplicationsAlertConfig,
                )
                logger.debug("Successfully imported GlobalApplicationsAlertConfig")
            except ImportError as e:
                logger.debug(f"Error importing GlobalApplicationsAlertConfig: {e}")
                return {"error": f"Failed to import GlobalApplicationsAlertConfig: {e!s}"}

            # Add default values for required fields if missing
            # These fields are required by the SDK but may not always be provided
            if 'alertChannelIds' not in request_body:
                request_body['alertChannelIds'] = []
            if 'customPayloadFields' not in request_body:
                request_body['customPayloadFields'] = []

            # Ensure nested 'applications' dict has required 'services' field
            if 'applications' in request_body and isinstance(request_body['applications'], dict):
                for _app_id, app_config in request_body['applications'].items():
                    if isinstance(app_config, dict) and 'services' not in app_config:
                        app_config['services'] = {}

            # Create an GlobalApplicationsAlertConfig object from the request body
            # NOTE: must use from_dict() (not model_validate()) so that discriminated-union
            # fields like threshold/rules[*].thresholds are resolved via their from_dict()
            # dispatcher, which preserves subclass fields (e.g. StaticThreshold.value).
            # model_validate() coerces everything to the base discriminator type and silently
            # drops fields like `value`, causing a 422 from the API.
            try:
                logger.debug(f"Creating GlobalApplicationsAlertConfig with params: {request_body}")
                config_object = GlobalApplicationsAlertConfig.from_dict(request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating GlobalApplicationsAlertConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the create_global_application_alert_config method from the SDK
            logger.debug("Calling create_global_application_alert_config with config object")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.create_global_application_alert_config,
                    global_applications_alert_config=config_object
                ),
                ctx=ctx,
                operation_name="create_global_application_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from create_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in create_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to create global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def update_global_application_alert_config(self,
                                              id: str,
                                              payload: Union[Dict[str, Any], str],
                                              ctx=None, api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing Global Smart Alert Configuration.

        This tool updates an existing Global Smart Alert Configuration with the provided configuration details.
        The configuration is identified by its ID, and the payload contains the updated configuration.

        Sample payload:
        {
        "name": "Slow calls than usual",
        "description": "Calls are slower or equal to 2 ms based on latency (90th).",
        "boundaryScope": "INBOUND",
        "applications": {
            "j02SxMRTSf-NCBXf5IdsjQ": {
            "applicationId": "j02SxMRTSf-NCBXf5IdsjQ",
            "inclusive": true,
            "services": {}
            }
        },
        "applicationIds": [
            "j02SxMRTSf-NCBXf5IdsjQ"
        ],
        "severity": 5,
        "triggering": false,
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": []
        },
        "includeInternal": false,
        "includeSynthetic": false,
        "rule": {
            "alertType": "slowness",
            "aggregation": "P90",
            "metricName": "latency"
        },
        "threshold": {
            "type": "staticThreshold",
            "operator": ">=",
            "value": 2,
            "lastUpdated": 0
        },
        "alertChannelIds": [],
        "granularity": 600000,
        "timeThreshold": {
            "type": "violationsInSequence",
            "timeWindow": 600000
        },
        "evaluationType": "PER_AP",
        "customPayloadFields": []
        }

        Args:
            id: The ID of the Global Smart Alert Configuration to update
            payload: The updated Global Smart Alert Configuration details as a dictionary or JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the updated Global Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"update_global_application_alert_config called with id={id}, payload={payload}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            if not payload:
                return {"error": "payload is required"}

            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    try:
                        parsed_payload = json.loads(payload)
                        logger.debug("Successfully parsed payload as JSON")
                        request_body = parsed_payload
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON parsing failed: {e}, trying with quotes replaced")

                        # Try replacing single quotes with double quotes
                        fixed_payload = payload.replace("'", "\"")
                        try:
                            parsed_payload = json.loads(fixed_payload)
                            logger.debug("Successfully parsed fixed JSON")
                            request_body = parsed_payload
                        except json.JSONDecodeError:
                            # Try as Python literal
                            try:
                                parsed_payload = ast.literal_eval(payload)
                                logger.debug("Successfully parsed payload as Python literal")
                                request_body = parsed_payload
                            except (SyntaxError, ValueError) as e2:
                                logger.debug(f"Failed to parse payload string: {e2}")
                                return {"error": f"Invalid payload format: {e2}", "payload": payload}
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return {"error": f"Failed to parse payload: {e}", "payload": payload}
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the GlobalApplicationsAlertConfig class
            try:
                from instana_client.models.global_applications_alert_config import (
                    GlobalApplicationsAlertConfig,
                )
                logger.debug("Successfully imported GlobalApplicationsAlertConfig")
            except ImportError as e:
                logger.debug(f"Error importing GlobalApplicationsAlertConfig: {e}")
                return {"error": f"Failed to import GlobalApplicationsAlertConfig: {e!s}"}

            # Add default values for required fields if missing
            # These fields are required by the SDK but may not always be provided
            if 'alertChannelIds' not in request_body:
                request_body['alertChannelIds'] = []
            if 'customPayloadFields' not in request_body:
                request_body['customPayloadFields'] = []

            # Ensure nested 'applications' dict has required 'services' field
            if 'applications' in request_body and isinstance(request_body['applications'], dict):
                for _app_id, app_config in request_body['applications'].items():
                    if isinstance(app_config, dict) and 'services' not in app_config:
                        app_config['services'] = {}

            # Create an GlobalApplicationsAlertConfig object from the request body
            # NOTE: must use from_dict() (not model_validate()) — same reason as create above.
            try:
                logger.debug(f"Creating GlobalApplicationsAlertConfig with params: {request_body}")
                config_object = GlobalApplicationsAlertConfig.from_dict(request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating ApplicationAlertConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the update_global_application_alert_config method from the SDK
            logger.debug(f"Calling update_global_application_alert_config with id={id} and config object")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.update_global_application_alert_config,
                    id=id,
                    global_applications_alert_config=config_object
                ),
                ctx=ctx,
                operation_name="update_global_application_alert_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Smart Global Alert Configuration with ID '{id}' has been successfully updated"
                }

            logger.debug(f"Result from update_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in update_global_application_alert_config: {e}")
            return {"error": f"Failed to update global application alert config: {e!s}"}


