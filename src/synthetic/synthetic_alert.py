"""
Synthetic Alert MCP Tools Module

This module provides synthetic smart alert-specific MCP tools for Instana monitoring.
Uses the api/synthetic-alert-configuration endpoints.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    parse_payload,
    sdk_call_with_keepalive,
    with_header_auth,
)

try:
    from instana_client.api.synthetic_alert_configuration_api import (
        SyntheticAlertConfigurationApi,
    )
    from instana_client.models.synthetic_alert_config import SyntheticAlertConfig
except ImportError:
    logging.getLogger(__name__).error("Failed to import synthetic alert configuration API", exc_info=True)
    raise

logger = logging.getLogger(__name__)

_NO_ERROR_DETAILS = "No error details available (empty response body)"


def _invalid_payload_error(issues: List[Dict[str, str]]) -> Dict[str, Any]:
    """Build the structured elicitation response for an invalid alert payload."""
    return {
        "elicitation_needed": True,
        "reason": "invalid_payload",
        "api_error": issues,
        "message": "Payload failed SyntheticAlertConfig validation. Fix the listed fields and retry.",
    }


def _convert_nested(field: str, convert, value: Any) -> Tuple[Any, List[Dict[str, str]]]:
    """Run an SDK ``from_dict`` conversion; return (result, issues) instead of raising.

    ``field`` prefixes the reported field path so nested errors identify their
    top-level payload field (e.g. ``tagFilterExpression.operator``).
    """
    try:
        return convert(value), []
    except ValidationError as e:
        return None, [
            {"field": ".".join([field, *(str(p) for p in err["loc"])]), "issue": err["msg"]}
            for err in e.errors()
        ]
    except KeyError as e:
        return None, [{"field": field, "issue": f"missing required key {e}"}]
    except (ValueError, TypeError) as e:
        return None, [{"field": field, "issue": str(e)}]


def _build_config(payload: Any) -> Tuple[Optional[SyntheticAlertConfig], Optional[Dict[str, Any]]]:
    """Return (SyntheticAlertConfig, None) or (None, error_dict)."""
    parsed = parse_payload(payload)
    if not isinstance(parsed, dict):
        return None, {"error": "payload must be a JSON object"}
    if "error" in parsed and len(parsed) == 1:
        return None, parsed
    # Work on a fresh Dict[str, Any] so pyright does not narrow the value type from the
    # parse_payload union return (Dict[str, Any] | Dict[str, str]).
    body: Dict[str, Any] = {}
    body.update(parsed)
    issues: List[Dict[str, str]] = []

    # The tagFilterExpression field is typed as the base TagFilterExpressionElement, so
    # pydantic does not discriminate a plain dict into a TagFilter/TagExpression. Pre-convert
    # it so the nested name/operator/value fields survive serialization to the API.
    tfe = body.get("tagFilterExpression")
    if isinstance(tfe, dict):
        from instana_client.models.tag_filter_expression_element import (
            TagFilterExpressionElement,
        )
        converted, errs = _convert_nested("tagFilterExpression", TagFilterExpressionElement.from_dict, tfe)
        issues.extend(errs)
        body["tag_filter_expression"] = converted
        body.pop("tagFilterExpression", None)

    cpf = body.get("customPayloadFields")
    if isinstance(cpf, list):
        from instana_client.models.custom_payload_field import CustomPayloadField
        fields = []
        for i, item in enumerate(cpf):
            if isinstance(item, dict):
                item, errs = _convert_nested(f"customPayloadFields[{i}]", CustomPayloadField.from_dict, item)
                issues.extend(errs)
            fields.append(item)
        body["custom_payload_fields"] = fields
        body.pop("customPayloadFields", None)

    if issues:
        return None, _invalid_payload_error(issues)

    try:
        return SyntheticAlertConfig(**body), None  # type: ignore[arg-type]
    except ValidationError as e:
        return None, _invalid_payload_error([
            {"field": ".".join(str(p) for p in err["loc"]), "issue": err["msg"]}
            for err in e.errors()
        ])


class SyntheticAlertMCPTools(BaseInstanaClient):
    """Tools for synthetic smart alert configurations in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Synthetic Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    async def _invoke(
        self,
        fn,
        ctx,
        operation_name: str,
        resource_type: Optional[str],
        tool_name: Optional[str],
        *,
        parse_body: bool = True,
        **kwargs,
    ) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
        """Call the SDK; return (parsed_json_or_None, error_dict_or_None).

        Set parse_body=False for operations whose response body is ignored, so a
        successful (2xx) call is never reported as failed due to a non-JSON body.
        """
        response = await sdk_call_with_keepalive(
            call_sdk_fn(fn, **kwargs),
            ctx=ctx,
            operation_name=operation_name,
            resource_type=resource_type,
            tool_name=tool_name,
        )
        # sdk_call_with_keepalive returns an error dict (not a response) on timeout.
        if isinstance(response, dict):
            return None, response
        if response.status >= 400:
            text = decode_response(response) if response.data else _NO_ERROR_DETAILS
            return None, {"error": f"API error (status {response.status}): {text}"}
        if not parse_body:
            return None, None
        raw = decode_response(response) if response.data else ""
        if not raw:
            return None, None
        try:
            return json.loads(raw), None
        except json.JSONDecodeError:
            return None, {"error": "Invalid JSON from API"}

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def find_active_synthetic_alert_configs(
        self,
        synthetic_test_id: Optional[str] = None,
        alert_ids: Optional[List[str]] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all active Synthetic Smart Alert Configurations, optionally filtered by test ID or alert IDs.

        Retrieves synthetic smart alert configurations and applies client-side pagination.

        Args:
            synthetic_test_id: Optional ID of a specific synthetic test to filter by.
            alert_ids: Optional list of Smart Alert Configuration IDs to filter results.
            page: Page number (1-based). Defaults to 1.
            page_size: Number of results per page. Defaults to 50.
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing paginated configurations list, count, total, page metadata, or error information.
        """
        try:
            logger.debug(
                "find_active_synthetic_alert_configs called with synthetic_test_id=%s, alert_ids=%s, page=%s, page_size=%s",
                synthetic_test_id, alert_ids, page, page_size,
            )

            result, err = await self._invoke(
                api_client.find_active_synthetic_alert_configs_without_preload_content,
                ctx,
                "find_active_synthetic_alert_configs",
                resource_type,
                tool_name,
                synthetic_test_id=synthetic_test_id,
                alert_ids=alert_ids,
            )
            if err:
                return err

            configs = result if isinstance(result, list) else ([result] if result else [])
            total_count = len(configs)

            effective_page = page if page is not None and page >= 1 else 1
            effective_page_size = page_size if page_size is not None and page_size >= 1 else 50
            if effective_page_size > 1000:
                effective_page_size = 1000
            total_pages = (total_count + effective_page_size - 1) // effective_page_size if total_count > 0 else 0
            if total_pages > 0 and effective_page > total_pages:
                effective_page = total_pages
            start_idx = (effective_page - 1) * effective_page_size
            end_idx = start_idx + effective_page_size
            paged_configs = configs[start_idx:end_idx]

            return {
                "configs": paged_configs,
                "count": len(paged_configs),
                "total": total_count,
                "page": effective_page,
                "page_size": effective_page_size,
                "total_pages": total_pages,
                "has_next": effective_page < total_pages,
                "has_previous": effective_page > 1,
                "message": (
                    "No active synthetic smart alert configurations found."
                    if not configs
                    else (
                        f"Found {total_count} active synthetic smart alert configuration(s). "
                        f"Showing page {effective_page} of {total_pages} ({len(paged_configs)} item(s))."
                    )
                ),
            }

        except Exception as e:
            logger.error("Error in find_active_synthetic_alert_configs: %s", e, exc_info=True)
            return {"error": f"Failed to get active synthetic alert configs: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def find_synthetic_alert_config(
        self,
        id: str,
        valid_on: Optional[int] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific Synthetic Smart Alert Configuration by ID. May return deleted configurations.

        Args:
            id: ID of a specific Synthetic Smart Alert Configuration to retrieve (required).
            valid_on: Unix timestamp (in milliseconds) representing a specific time the configuration
                      was active. If omitted, the latest active version is retrieved.
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing the Smart Alert Configuration object or error information.
        """
        try:
            logger.debug("find_synthetic_alert_config called with id=%s, valid_on=%s", id, valid_on)

            result, err = await self._invoke(
                api_client.find_synthetic_alert_config_without_preload_content,
                ctx,
                "find_synthetic_alert_config",
                resource_type,
                tool_name,
                id=id,
                valid_on=valid_on,
            )
            if err:
                return err
            if result is None:
                return {"error": f"Empty response from API for config '{id}'"}
            return result

        except Exception as e:
            logger.error("Error in find_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic alert config: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def find_synthetic_alert_config_versions(
        self,
        id: str,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all versions of a Synthetic Smart Alert Configuration.

        Args:
            id: ID of a specific Synthetic Smart Alert Configuration to retrieve versions for (required).
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing a list of versions and total count or error information.
        """
        try:
            logger.debug("find_synthetic_alert_config_versions called with id=%s", id)

            result, err = await self._invoke(
                api_client.find_synthetic_alert_config_versions_without_preload_content,
                ctx,
                "find_synthetic_alert_config_versions",
                resource_type,
                tool_name,
                id=id,
            )
            if err:
                return err
            versions = result if isinstance(result, list) else ([result] if result else [])
            return {"versions": versions, "count": len(versions)}

        except Exception as e:
            logger.error("Error in find_synthetic_alert_config_versions: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic alert config versions: {e!s}"}

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def create_synthetic_alert_config(
        self,
        payload: Any,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Synthetic Smart Alert Configuration.

        Args:
            payload: Dictionary or JSON string containing the synthetic alert configuration fields
                     (e.g., name, description, syntheticTestIds, rule, timeThreshold, tagFilterExpression, etc.).
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing the created Smart Alert Configuration or error information.
        """
        try:
            config_object, err = _build_config(payload)
            if err:
                return err

            result, err = await self._invoke(
                api_client.create_synthetic_alert_config_without_preload_content,
                ctx,
                "create_synthetic_alert_config",
                resource_type,
                tool_name,
                synthetic_alert_config=config_object,
            )
            if err:
                return err
            if result is None:
                return {"success": True, "message": "Synthetic alert config created (no body returned)."}
            return result

        except Exception as e:
            logger.error("Error in create_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to create synthetic alert config: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def update_synthetic_alert_config(
        self,
        id: str,
        payload: Any,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update an existing Synthetic Smart Alert Configuration.

        Args:
            id: ID of the Synthetic Smart Alert Configuration to update (required).
            payload: Dictionary or JSON string containing the full updated synthetic alert configuration.
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing the updated configuration or success/error information.
        """
        try:
            config_object, err = _build_config(payload)
            if err:
                return err

            result, err = await self._invoke(
                api_client.update_synthetic_alert_config_without_preload_content,
                ctx,
                "update_synthetic_alert_config",
                resource_type,
                tool_name,
                id=id,
                synthetic_alert_config=config_object,
            )
            if err:
                return err
            if result is not None:
                return result
            return {"success": True, "message": f"Synthetic alert config '{id}' updated successfully."}

        except Exception as e:
            logger.error("Error in update_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to update synthetic alert config: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def delete_synthetic_alert_config(
        self,
        id: str,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete a Synthetic Smart Alert Configuration.

        Args:
            id: ID of the Synthetic Smart Alert Configuration to delete (required).
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing deletion confirmation message or error information.
        """
        try:
            _, err = await self._invoke(
                api_client.delete_synthetic_alert_config_without_preload_content,
                ctx,
                "delete_synthetic_alert_config",
                resource_type,
                tool_name,
                parse_body=False,
                id=id,
            )
            if err:
                return err
            return {"success": True, "message": f"Synthetic alert config '{id}' deleted successfully."}

        except Exception as e:
            logger.error("Error in delete_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to delete synthetic alert config: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def enable_synthetic_alert_config(
        self,
        id: str,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enable a Synthetic Smart Alert Configuration.

        Args:
            id: ID of the Synthetic Smart Alert Configuration to enable (required).
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing enable status message or error information.
        """
        try:
            _, err = await self._invoke(
                api_client.enable_synthetic_alert_config_without_preload_content,
                ctx,
                "enable_synthetic_alert_config",
                resource_type,
                tool_name,
                parse_body=False,
                id=id,
            )
            if err:
                return err
            return {"success": True, "message": f"Synthetic alert config '{id}' enabled successfully."}

        except Exception as e:
            logger.error("Error in enable_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to enable synthetic alert config: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def disable_synthetic_alert_config(
        self,
        id: str,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Disable a Synthetic Smart Alert Configuration.

        Args:
            id: ID of the Synthetic Smart Alert Configuration to disable (required).
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing disable status message or error information.
        """
        try:
            _, err = await self._invoke(
                api_client.disable_synthetic_alert_config_without_preload_content,
                ctx,
                "disable_synthetic_alert_config",
                resource_type,
                tool_name,
                parse_body=False,
                id=id,
            )
            if err:
                return err
            return {"success": True, "message": f"Synthetic alert config '{id}' disabled successfully."}

        except Exception as e:
            logger.error("Error in disable_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to disable synthetic alert config: {e!s}"}

    @with_header_auth(SyntheticAlertConfigurationApi)
    async def restore_synthetic_alert_config(
        self,
        id: str,
        created: int,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Restore a deleted Synthetic Smart Alert Configuration to a prior version.

        Args:
            id: ID of the deleted Synthetic Smart Alert Configuration to restore (required).
            created: Unix timestamp (in milliseconds) representing the creation time of the prior
                     version to restore (required).
            ctx: The MCP context (optional).
            api_client: Instana API client injected by @with_header_auth.
            resource_type: Optional resource type from smart router (e.g. 'alert').
            tool_name: Optional MCP tool name from smart router (e.g. 'manage_synthetics').

        Returns:
            Dictionary containing restore confirmation message or error information.
        """
        try:
            _, err = await self._invoke(
                api_client.restore_synthetic_alert_config_without_preload_content,
                ctx,
                "restore_synthetic_alert_config",
                resource_type,
                tool_name,
                parse_body=False,
                id=id,
                created=created,
            )
            if err:
                return err
            return {"success": True, "message": f"Synthetic alert config '{id}' restored to version created at '{created}'."}

        except Exception as e:
            logger.error("Error in restore_synthetic_alert_config: %s", e, exc_info=True)
            return {"error": f"Failed to restore synthetic alert config: {e!s}"}
