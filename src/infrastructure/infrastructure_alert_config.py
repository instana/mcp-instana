"""
Infrastructure Smart Alert Configuration MCP Tools Module

This module provides CRUD tools for Instana Infrastructure Smart Alert configurations.
"""

import json
import logging
import ast
from typing import Any, Dict, List, Optional, Union

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    sdk_call_with_keepalive,
    with_header_auth,
)

try:
    from instana_client.api.infrastructure_alert_configuration_api import (
        InfrastructureAlertConfigurationApi,
    )
    from instana_client.models.infra_alert_config import InfraAlertConfig
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("Failed to import required instana_client modules", exc_info=True)
    raise

logger = logging.getLogger(__name__)


class InfrastructureAlertConfigMCPTools(BaseInstanaClient):
    """CRUD tools for Instana Infrastructure Smart Alert configurations."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Alert Config MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Payload field validators (each returns an error string or None)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_name(payload: Dict[str, Any]) -> Optional[str]:
        name = payload.get("name")
        if name is None:
            return "name: required — string, max 256 chars"
        if not isinstance(name, str):
            return f"name: must be a string, got {type(name).__name__!r}"
        if len(name) > 256:
            return "name: exceeds maximum length of 256 characters"
        return None

    @staticmethod
    def _validate_description(payload: Dict[str, Any]) -> Optional[str]:
        desc = payload.get("description")
        if desc is None:
            return "description: required — string, max 65536 chars"
        if not isinstance(desc, str):
            return f"description: must be a string, got {type(desc).__name__!r}"
        return None

    @staticmethod
    def _validate_granularity(payload: Dict[str, Any]) -> Optional[str]:
        _valid_gran = (60000, 300000, 600000, 900000, 1200000, 1800000)
        granularity = payload.get("granularity")
        if granularity is None:
            return f"granularity: required — valid values in ms: {list(_valid_gran)}"
        if not isinstance(granularity, int):
            return f"granularity: must be an integer, got {type(granularity).__name__!r}"
        if granularity not in _valid_gran:
            return f"granularity: {granularity} is not valid — must be one of {list(_valid_gran)} ms"
        return None

    @staticmethod
    def _validate_group_by(payload: Dict[str, Any]) -> Optional[str]:
        group_by = payload.get("groupBy")
        if group_by is None:
            return "groupBy: required — list of tag names (can be empty: [])"
        if not isinstance(group_by, list):
            return f"groupBy: must be a list, got {type(group_by).__name__!r}"
        return None

    @staticmethod
    def _validate_alert_payload(
        payload: Optional[Any],
        operation: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate create/update payload against the InfraAlertConfig SDK model.

        Required fields (SDK throws if absent):
            name, description, granularity, groupBy, customPayloadFields,
            tagFilterExpression, timeThreshold

        Returns a consolidated elicitation dict, or None when valid.
        """
        if payload is None or payload == {}:
            return {
                "elicitation_needed": True,
                "reason": f"infra_alert_config '{operation}': payload is missing",
                "api_error": ["payload: required — provide the alert configuration object"],
                "message": "Correct all issues below and retry:\n  - payload: required — provide the alert configuration object",
            }

        if not isinstance(payload, dict):
            return {
                "elicitation_needed": True,
                "reason": f"infra_alert_config '{operation}': payload must be a dict",
                "api_error": [f"payload: must be a dict, got {type(payload).__name__!r}"],
                "message": f"Correct all issues below and retry:\n  - payload: must be a dict, got {type(payload).__name__!r}",
            }

        errors: List[str] = []

        for validator in (
            InfrastructureAlertConfigMCPTools._validate_name,
            InfrastructureAlertConfigMCPTools._validate_description,
            InfrastructureAlertConfigMCPTools._validate_granularity,
            InfrastructureAlertConfigMCPTools._validate_group_by,
        ):
            error = validator(payload)
            if error:
                errors.append(error)

        if payload.get("tagFilterExpression") is None:
            errors.append(
                'tagFilterExpression: required — e.g. {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []}'
            )

        if payload.get("timeThreshold") is None:
            errors.append(
                'timeThreshold: required — e.g. {"type": "violationsInSequence", "timeWindow": 600000}'
            )

        severity = payload.get("severity")
        if severity is not None and severity not in (5, 10):
            errors.append(f"severity: {severity} is not valid — must be 5 (Warning) or 10 (Critical)")

        eval_type = payload.get("evaluationType")
        if eval_type is not None and eval_type not in ("PER_ENTITY", "CUSTOM"):
            errors.append(f"evaluationType: '{eval_type}' is not valid — must be 'PER_ENTITY' or 'CUSTOM'")

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": f"infra_alert_config '{operation}' payload has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The '{operation}' payload has {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    @staticmethod
    def _preflight(
        operation: str,
        id: Optional[str],
        created: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Validate required parameters before executing an operation."""
        errors: List[str] = []

        if operation in ("find", "find_versions", "update", "delete", "enable", "disable", "restore") and not id:
            errors.append(
                f"id: required for '{operation}' — "
                "provide the Infra Smart Alert configuration ID (obtain from 'find_active')"
            )

        if operation == "restore":
            if not created:
                errors.append(
                    "created: required for 'restore' — "
                    "provide the Unix timestamp (ms) of the version to restore (obtain from 'find_versions')"
                )
            elif not isinstance(created, int) or created <= 0:
                errors.append(
                    f"created: must be a positive integer Unix timestamp in milliseconds, got {created!r}"
                )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": f"infra_alert_config '{operation}' has {len(errors)} missing required parameter(s)",
            "api_error": errors,
            "message": (
                f"Cannot execute '{operation}': {len(errors)} required parameter(s) missing or invalid. "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    @staticmethod
    def _parse_payload(payload: Optional[Union[Dict[str, Any], str]]) -> Any:
        """Parse a string payload to dict; return non-string payloads unchanged.

        Raises:
            ValueError: when a string payload cannot be decoded as JSON or a
                        Python literal, so callers can surface a precise error
                        instead of treating it as a missing payload.
        """
        if not isinstance(payload, str):
            return payload
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(payload)
        except (ValueError, SyntaxError):
            pass
        raise ValueError(
            f"payload could not be parsed: expected a JSON object or Python dict literal, "
            f"got {payload!r:.120}"
        )

    # ------------------------------------------------------------------
    # Public dispatcher — called by the smart router
    # ------------------------------------------------------------------

    async def execute_alert_config_operation(
        self,
        operation: str,
        id: Optional[str] = None,
        alert_ids: Optional[List[str]] = None,
        valid_on: Optional[int] = None,
        created: Optional[int] = None,
        payload: Optional[Union[Dict[str, Any], str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an Infra Smart Alert Config CRUD operation.
        Called by InfrastructureSmartRouterMCPTool.
        """
        try:
            preflight = self._preflight(operation, id, created)
            if preflight:
                return preflight

            if operation in ("create", "update"):
                try:
                    parsed = self._parse_payload(payload)
                except ValueError as exc:
                    return {
                        "elicitation_needed": True,
                        "reason": f"infra_alert_config '{operation}': {exc}",
                        "api_error": [str(exc)],
                        "message": f"Correct all issues below and retry:\n  - {exc}",
                    }
                elicitation = self._validate_alert_payload(parsed, operation)
                if elicitation:
                    return elicitation
                payload = parsed  # use the parsed dict going forward

            _r = {"resource_type": resource_type, "tool_name": tool_name}
            dispatch = {
                "find_active": lambda: self._find_active(alert_ids, page, page_size, ctx, **_r),
                "find": lambda: self._find(id, valid_on, ctx, **_r),
                "find_versions": lambda: self._find_versions(id, ctx, **_r),
                "create": lambda: self._create(payload, ctx, **_r),
                "update": lambda: self._update(id, payload, ctx, **_r),
                "delete": lambda: self._delete(id, ctx, **_r),
                "enable": lambda: self._enable(id, ctx, **_r),
                "disable": lambda: self._disable(id, ctx, **_r),
                "restore": lambda: self._restore(id, created, ctx, **_r),
            }
            handler = dispatch.get(operation)
            if handler is None:
                return {"error": f"Operation '{operation}' not supported"}
            return await handler()

        except Exception as e:
            logger.error(f"Error executing infra alert config operation '{operation}': {e}", exc_info=True)
            return {"error": f"Error executing '{operation}': {e!s}"}

    # ------------------------------------------------------------------
    # Private operation methods
    # ------------------------------------------------------------------

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _find_active(
        self,
        alert_ids: Optional[List[str]],
        page: Optional[int],
        page_size: Optional[int],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all active Infra Smart Alert configurations with pagination."""
        try:
            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.find_active_infra_alert_configs_without_preload_content,
                    alert_ids=alert_ids,
                ),
                ctx=ctx,
                operation_name="find_active_infra_alert_configs",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                return self.handle_api_error_response(response, "find_active_infra_alert_configs", logger)

            raw = decode_response(response)
            result = json.loads(raw)
            if isinstance(result, list):
                configs = result
            elif result:
                configs = [result]
            else:
                configs = []
            
            total = len(configs)
            
            # Apply pagination
            page = page if page is not None else 1
            page_size = page_size if page_size is not None else 50
            
            # Validate pagination parameters
            if page < 1:
                page = 1
            if page_size < 1:
                page_size = 50
            if page_size > 1000:
                page_size = 1000
            
            # Calculate pagination boundaries
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # Slice the results
            paginated_configs = configs[start_idx:end_idx]
            
            # Calculate total pages
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
            
            return {
                "configs": paginated_configs,
                "count": len(paginated_configs),
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
                "message": (
                    "No active Infra Smart Alert configurations found."
                    if not configs
                    else f"Found {total} active configuration(s). Showing page {page} of {total_pages} ({len(paginated_configs)} results)."
                ),
            }
        except Exception as e:
            logger.error(f"Error in _find_active: {e}", exc_info=True)
            return {"error": f"Failed to list active infra alert configs: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _find(
        self,
        id: Optional[str],
        valid_on: Optional[int],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a specific Infra Smart Alert configuration by ID."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.find_infra_alert_config,
                    id=id,
                    valid_on=valid_on,
                ),
                ctx=ctx,
                operation_name="find_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            if hasattr(result, "to_dict"):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                return {"data": result}
        except Exception as e:
            logger.error(f"Error in _find: {e}", exc_info=True)
            return {"error": f"Failed to find infra alert config: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _find_versions(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all versions of an Infra Smart Alert configuration."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.find_infra_alert_config_versions,
                    id=id,
                ),
                ctx=ctx,
                operation_name="find_infra_alert_config_versions",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            if isinstance(result, list):
                return {"versions": [item.to_dict() if hasattr(item, "to_dict") else item for item in result]}
            if hasattr(result, "to_dict"):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                return {"data": result}
        except Exception as e:
            logger.error(f"Error in _find_versions: {e}", exc_info=True)
            return {"error": f"Failed to find infra alert config versions: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _create(
        self,
        payload: Optional[Dict[str, Any]],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new Infra Smart Alert configuration."""
        try:
            # Apply SDK-level defaults for fields the user commonly omits
            if "customPayloadFields" not in payload:
                payload["customPayloadFields"] = []
            if "alertChannelIds" not in payload:
                payload["alertChannelIds"] = []

            # Use from_dict() so discriminated-union fields (threshold, rules) are
            # correctly instantiated as their concrete subclasses.
            try:
                config_object = InfraAlertConfig.from_dict(payload)
            except Exception as model_err:
                return {"error": f"Failed to build InfraAlertConfig model: {model_err!s}"}

            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.create_infra_alert_config_without_preload_content,
                    infra_alert_config=config_object,
                ),
                ctx=ctx,
                operation_name="create_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status not in (200, 201):
                return self.handle_api_error_response(response, "create_infra_alert_config", logger)

            raw = decode_response(response)
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Error in _create: {e}", exc_info=True)
            return {"error": f"Failed to create infra alert config: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _update(
        self,
        id: Optional[str],
        payload: Optional[Dict[str, Any]],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing Infra Smart Alert configuration."""
        try:
            if "customPayloadFields" not in payload:
                payload["customPayloadFields"] = []
            if "alertChannelIds" not in payload:
                payload["alertChannelIds"] = []

            try:
                config_object = InfraAlertConfig.from_dict(payload)
            except Exception as model_err:
                return {"error": f"Failed to build InfraAlertConfig model: {model_err!s}"}

            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.update_infra_alert_config_without_preload_content,
                    id=id,
                    infra_alert_config=config_object,
                ),
                ctx=ctx,
                operation_name="update_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status not in (200, 204):
                return self.handle_api_error_response(response, "update_infra_alert_config", logger)

            raw = decode_response(response)
            return json.loads(raw) if raw.strip() else {"success": True, "message": f"Infra Smart Alert config '{id}' updated successfully."}
        except Exception as e:
            logger.error(f"Error in _update: {e}", exc_info=True)
            return {"error": f"Failed to update infra alert config: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _delete(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete an Infra Smart Alert configuration."""
        try:
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.delete_infra_alert_config, id=id),
                ctx=ctx,
                operation_name="delete_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            if response is not None and response.status not in (200, 204):
                return self.handle_api_error_response(response, "delete_infra_alert_config", logger)

            return {
                "success": True,
                "message": f"Infra Smart Alert config '{id}' deleted successfully.",
            }
        except Exception as e:
            logger.error(f"Error in _delete: {e}", exc_info=True)
            return {"error": f"Failed to delete infra alert config: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _enable(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Enable an Infra Smart Alert configuration."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.enable_infra_alert_config, id=id),
                ctx=ctx,
                operation_name="enable_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            if hasattr(result, "to_dict"):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                return {"success": True, "message": f"Infra Smart Alert config '{id}' enabled."}
        except Exception as e:
            logger.error(f"Error in _enable: {e}", exc_info=True)
            return {"error": f"Failed to enable infra alert config: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _disable(
        self,
        id: Optional[str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Disable an Infra Smart Alert configuration."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.disable_infra_alert_config, id=id),
                ctx=ctx,
                operation_name="disable_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            if hasattr(result, "to_dict"):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                return {"success": True, "message": f"Infra Smart Alert config '{id}' disabled."}
        except Exception as e:
            logger.error(f"Error in _disable: {e}", exc_info=True)
            return {"error": f"Failed to disable infra alert config: {e!s}"}

    @with_header_auth(InfrastructureAlertConfigurationApi)
    async def _restore(
        self,
        id: Optional[str],
        created: Optional[int],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Restore a deleted Infra Smart Alert configuration."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.restore_infra_alert_config, id=id, created=created),
                ctx=ctx,
                operation_name="restore_infra_alert_config",
                resource_type=resource_type,
                tool_name=tool_name,
            )
            if hasattr(result, "to_dict"):
                return result.to_dict()
            elif isinstance(result, dict):
                return result
            else:
                return {
                    "success": True,
                    "message": f"Infra Smart Alert config '{id}' (version created={created}) restored successfully.",
                }
        except Exception as e:
            logger.error(f"Error in _restore: {e}", exc_info=True)
            return {"error": f"Failed to restore infra alert config: {e!s}"}

