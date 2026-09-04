"""
Application Settings MCP Tools Module

This module provides application settings-specific MCP tools for Instana monitoring.

The API endpoints of this group provides a way to create, read, update, delete (CRUD) for various configuration settings.
"""

import ast
import copy
import json
import logging
import sys
import traceback
from typing import Any, Dict, List, Optional, Union

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    parse_payload,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)

logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api import (
        ApplicationSettingsApi,  #type: ignore
    )
    from instana_client.api_client import ApiClient  #type: ignore
    from instana_client.configuration import Configuration  #type: ignore
    from instana_client.models import (
        ApplicationConfig,  #type: ignore
        EndpointConfig,  #type: ignore
        ManualServiceConfig,  #type: ignore
        NewApplicationConfig,  #type: ignore
        NewManualServiceConfig,  #type: ignore
        ServiceConfig,  #type: ignore
        TagFilter,  #type: ignore
        TagFilterExpression,  #type: ignore
    )

    # TagFilterAllOfValue is not exported from models, import directly
    from instana_client.models.tag_filter_all_of_value import (
        TagFilterAllOfValue,  #type: ignore
    )
except ImportError as e:
    print(f"Error importing Instana SDK: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise


# Helper function for debug printing
def debug_print(*args, **kwargs):
    """Print debug information to stderr instead of stdout"""
    print(*args, file=sys.stderr, **kwargs)

# ---------------------------------------------------------------------------
# Enum constants for settings validation
# ---------------------------------------------------------------------------
VALID_SCOPE_VALUES = frozenset({
    "INCLUDE_ALL_DOWNSTREAM",
    "INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING",
    "INCLUDE_NO_DOWNSTREAM",
})
VALID_BOUNDARY_SCOPE_VALUES = frozenset({"ALL", "INBOUND", "DEFAULT"})
VALID_ENDPOINT_CASE_VALUES = frozenset({"ORIGINAL", "LOWER", "UPPER"})


class ApplicationSettingsMCPTools(BaseInstanaClient):
    """Tools for application settings in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Settings MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

        try:

            # Configure the API client with the correct base URL and authentication
            configuration = Configuration()
            configuration.host = base_url
            configuration.api_key['ApiKeyAuth'] = read_token
            configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

            # Create an API client with this configuration
            api_client = ApiClient(configuration=configuration)

            # Initialize the Instana SDK's ApplicationSettingsApi with our configured client
            self.settings_api = ApplicationSettingsApi(api_client=api_client)
        except Exception as e:
            logger.debug(f"Error initializing ApplicationSettingsApi: {e}")
            traceback.print_exc(file=sys.stderr)
            raise

    # CRUD Operations Dispatcher - called by application_smart_router_tool.py
    async def execute_settings_operation(
        self,
        operation: str,
        resource_subtype: str,
        id: Optional[str] = None,
        payload: Optional[Union[Dict[str, Any], str]] = None,
        request_body: Optional[List[str]] = None,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute Application Settings CRUD operations.
        Called by the smart router tool.

        Args:
            operation: Operation to perform (get_all, get, create, update, delete, order, replace_all)
            resource_subtype: Type of settings resource (application, endpoint, service, manual_service)
            id: Resource ID (for get, update, delete operations)
            payload: Configuration payload (for create, update operations)
            request_body: List of IDs (for order, replace_all operations)
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            # --- Pre-flight: collect ALL missing required params in one pass ---
            errors: List[str] = []

            # id is required for get / update / delete
            if operation in ("get", "update", "delete") and not id:
                errors.append(
                    f"id: required for '{operation}' — "
                    "provide the configuration ID (obtain one from 'get_all')"
                )

            # payload is required for create / update
            if operation in ("create", "update") and not payload:
                errors.append(
                    f"payload: required for '{operation}' — "
                    "provide the configuration dictionary"
                )

            if errors:
                return {
                    "elicitation_needed": True,
                    "reason": f"settings '{operation}' has {len(errors)} missing required parameter(s)",
                    "api_error": errors,
                    "message": (
                        f"Cannot execute '{operation}': {len(errors)} required parameter(s) missing. "
                        "Correct all issues below and retry:\n"
                        + "\n".join(f"  - {e}" for e in errors)
                    ),
                }
            # --- End pre-flight ---

            # Route based on resource_subtype and operation
            _rt, _tn = resource_type, tool_name
            if resource_subtype == "application":
                if operation == "get_all":
                    return await self._get_all_applications_configs(ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "get":
                    return await self._get_application_config(id, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "create":
                    return await self._add_application_config(payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "update":
                    return await self._update_application_config(id, payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "delete":
                    return await self._delete_application_config(id, ctx, resource_type=_rt, tool_name=_tn)

            elif resource_subtype == "endpoint":
                if operation == "get_all":
                    return await self._get_all_endpoint_configs(ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "get":
                    return await self._get_endpoint_config(id, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "create":
                    return await self._create_endpoint_config(payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "update":
                    return await self._update_endpoint_config(id, payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "delete":
                    return await self._delete_endpoint_config(id, ctx, resource_type=_rt, tool_name=_tn)

            elif resource_subtype == "service":
                if operation == "get_all":
                    return await self._get_all_service_configs(ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "get":
                    return await self._get_service_config(id, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "create":
                    return await self._add_service_config(payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "update":
                    return await self._update_service_config(id, payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "delete":
                    return await self._delete_service_config(id, ctx, resource_type=_rt, tool_name=_tn)

            elif resource_subtype == "manual_service":
                if operation == "get_all":
                    return await self._get_all_manual_service_configs(ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "create":
                    return await self._add_manual_service_config(payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "update":
                    return await self._update_manual_service_config(id, payload, ctx, resource_type=_rt, tool_name=_tn)
                elif operation == "delete":
                    return await self._delete_manual_service_config(id, ctx, resource_type=_rt, tool_name=_tn)

            return {"error": f"Operation '{operation}' not supported for resource_subtype '{resource_subtype}'"}

        except Exception as e:
            logger.error(f"Error executing {operation} on {resource_subtype}: {e}", exc_info=True)
            return {"error": f"Error executing {operation} on {resource_subtype}: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_applications_configs(self,
                                           ctx=None,
                                           api_client=None,
                                           resource_type: Optional[str] = None,
                                           tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        All Application Perspectives Configuration
        Get a list of all Application Perspectives with their configuration settings.

        Args:
            ctx: The MCP context (optional)

        Returns:
            List of application perspective configs or error information
        """
        try:
            logger.debug("Fetching all applications and their settings")
            # Use raw JSON response to avoid Pydantic validation issues
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_application_configs_without_preload_content),
                ctx=ctx,
                operation_name="get_application_configs",
                resource_type=resource_type, tool_name=tool_name,
            )
            try:
                response_text = decode_response(result)
                json_data = json.loads(response_text)
                # Convert to List[Dict[str, Any]] format
                if isinstance(json_data, list):
                    result_dict = json_data
                else:
                    # If it's a single object, wrap it in a list
                    result_dict = [json_data] if json_data else []
                logger.debug("Successfully retrieved application configs data")
                return result_dict
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.debug(error_message)
                return [{"error": error_message}]

        except Exception as e:
            logger.error(f"Error in get_application_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get all applications: {e!s}"}]

    def _convert_tag_filter_expression(self, tag_expr: dict):
        """
        Recursively convert a tagFilterExpression dict into the appropriate
        SDK model objects (TagFilterExpression / TagFilter).

        Handles:
        - EXPRESSION  → TagFilterExpression, with each element converted recursively
        - TAG_FILTER  → TagFilter, normalising stringValue ↔ value and dropping the
                        API-only 'key' field that the SDK constructor does not accept
        - anything else → returned unchanged (defensive pass-through)
        """
        if not isinstance(tag_expr, dict):
            return tag_expr

        expr_type = tag_expr.get('type')

        if expr_type == 'EXPRESSION':
            converted_elements = [
                self._convert_tag_filter_expression(e)
                for e in tag_expr.get('elements', [])
                if isinstance(e, dict)
            ]
            return TagFilterExpression(**{**tag_expr, 'elements': converted_elements})

        if expr_type == 'TAG_FILTER':
            # Drop 'key' — it is an API response field the SDK constructor rejects
            tag_filter_dict = {k: v for k, v in tag_expr.items() if k != 'key'}
            # Normalise stringValue / value so both are always present
            if 'stringValue' in tag_filter_dict and 'value' not in tag_filter_dict:
                tag_filter_dict['value'] = TagFilterAllOfValue(tag_filter_dict['stringValue'])
            elif 'value' in tag_filter_dict and isinstance(tag_filter_dict['value'], str):
                tag_filter_dict['stringValue'] = tag_filter_dict['value']
                tag_filter_dict['value'] = TagFilterAllOfValue(tag_filter_dict['value'])
            return TagFilter(**tag_filter_dict)

        # Unknown type — pass through unchanged
        return tag_expr

    # --- missing-fields error response (constant — no branching) ---
    _MISSING_LABEL_ERROR: Dict[str, Any] = {
        "error": "Missing required fields for application configuration",
        "missing_fields": ["label"],
        "required_fields": {
            "label": "Application perspective name (string, required, 1-128 chars)",
        },
        "optional_fields": {
            "tagFilterExpression": "Tag filter to match services (dict, optional - defaults to empty EXPRESSION)",
            "scope": "Monitoring scope (string, optional - defaults to 'INCLUDE_ALL_DOWNSTREAM')",
            "boundaryScope": "Boundary scope (string, optional - defaults to 'ALL')",
            "accessRules": "Access control rules (list, optional - defaults to READ_WRITE GLOBAL access)"
        },
        "scope_options": ["INCLUDE_ALL_DOWNSTREAM", "INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING", "INCLUDE_NO_DOWNSTREAM"],
        "boundary_scope_options": ["ALL", "INBOUND", "DEFAULT"],
        "access_rules_options": ["READ_WRITE_GLOBAL", "READ_ONLY_GLOBAL", "CUSTOM"],
        "elicitation_prompt": (
            "Please provide the following configuration options:\n"
            "1. Scope (INCLUDE_ALL_DOWNSTREAM/INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING/INCLUDE_NO_DOWNSTREAM)\n"
            "2. Boundary Scope (ALL/INBOUND/DEFAULT)\n"
            "3. Access Rules (READ_WRITE_GLOBAL/READ_ONLY_GLOBAL/CUSTOM)\n"
            "4. Tag Filter Expression (optional)"
        ),
        "example_minimal": {"label": "My Application"},
        "example_with_options": {
            "label": "My Application",
            "scope": "INCLUDE_ALL_DOWNSTREAM",
            "boundaryScope": "ALL",
            "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}],
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "EQUALS",
                "entity": "DESTINATION",
                "stringValue": "my-service"
            }
        }
    }

    def _apply_application_defaults(self, request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply SDK-required defaults and convert tagFilterExpression in place.

        Returns an error dict if tagFilterExpression conversion fails, else None.
        """
        if 'scope' not in request_body:
            request_body['scope'] = 'INCLUDE_ALL_DOWNSTREAM'
            logger.debug("Applied default scope: INCLUDE_ALL_DOWNSTREAM")

        if 'boundaryScope' not in request_body:
            request_body['boundaryScope'] = 'ALL'
            logger.debug("Applied default boundaryScope: ALL")

        if 'accessRules' not in request_body:
            request_body['accessRules'] = [
                {"accessType": "READ_WRITE", "relationType": "GLOBAL", "relatedId": None}
            ]
            logger.debug("Applied default accessRules: READ_WRITE GLOBAL")

        # businessCriticality is intentionally NOT defaulted here.
        # The SDK model types it as Optional[StrictStr] with enum values like 'NOT_DEFINED',
        # but the Instana API actually stores and returns it as an integer (e.g. 0).
        # Sending any string value causes a 400 from the API. Omitting the field entirely
        # lets the API apply its own default without conflict.
        if 'businessCriticality' in request_body and isinstance(request_body['businessCriticality'], str):
            del request_body['businessCriticality']
            logger.debug("Removed businessCriticality string value — API expects integer; omitting lets API apply default")

        # The API requires either tagFilterExpression OR matchSpecification
        if 'tagFilterExpression' not in request_body and 'matchSpecification' not in request_body:
            request_body['tagFilterExpression'] = TagFilterExpression(
                type="EXPRESSION", logicalOperator="AND", elements=[]
            )
            logger.debug("Applied default tagFilterExpression: empty EXPRESSION model object")
        elif isinstance(request_body.get('tagFilterExpression'), dict):
            try:
                request_body['tagFilterExpression'] = self._convert_tag_filter_expression(
                    request_body['tagFilterExpression']
                )
            except Exception as e:
                logger.debug(f"Error converting tagFilterExpression: {e}", exc_info=True)
                return {"error": f"Invalid tagFilterExpression structure: {e}"}

        return None

    def _validate_and_prepare_application_payload(self, payload: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """
        Validate and prepare application configuration payload with proper defaults.

        Based on SDK NewApplicationConfig model requirements:
        - label: required (1-128 chars)
        - scope, boundaryScope, accessRules: required by SDK — defaults applied
        - tagFilterExpression: optional, converted to SDK model objects

        Returns:
            Dict with either 'payload' (validated) or 'error' and 'missing_fields'
        """
        # Parse / deep-copy — never mutate the caller's object.
        if isinstance(payload, dict):
            request_body = copy.deepcopy(payload)
        else:
            parsed = parse_payload(payload)
            if "error" in parsed:
                return parsed
            request_body = copy.deepcopy(parsed)

        if not request_body.get('label'):
            return self._MISSING_LABEL_ERROR

        error = self._apply_application_defaults(request_body)
        if error:
            return error

        return {"payload": request_body}

    @staticmethod
    def _build_serializable_body(request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a plain dict body, omitting businessCriticality entirely.

        Rationale: the SDK model types businessCriticality as StrictStr ('NOT_DEFINED' etc.)
        but the Instana API actually stores/returns it as an integer (e.g. 0), and rejects any
        string value with HTTP 400.
        """
        serializable_body = {}
        for k, v in request_body.items():
            if k == 'businessCriticality':
                continue  # omit — API rejects any string value for this field
            if hasattr(v, 'to_dict'):
                serializable_body[k] = v.to_dict()
            elif isinstance(v, list):
                serializable_body[k] = [
                    item.to_dict() if hasattr(item, 'to_dict') else item for item in v
                ]
            else:
                serializable_body[k] = v
        return serializable_body

    @staticmethod
    def _build_add_application_response(
        result_dict: Dict[str, Any],
        request_body: Dict[str, Any],
        payload: Union[Dict[str, Any], str, None],
    ) -> Dict[str, Any]:
        """Format the successful response dict for add_application_config."""
        payload_dict = payload if isinstance(payload, dict) else {}
        access_rules = "Custom" if (payload_dict and 'accessRules' in payload_dict) else "READ_WRITE GLOBAL"
        return {
            **result_dict,
            "message": f"Application perspective '{request_body.get('label')}' created successfully",
            "applied_defaults": {
                "scope": request_body.get('scope'),
                "boundaryScope": request_body.get('boundaryScope'),
                "accessRules": access_rules,
            },
        }

    @staticmethod
    def _parse_payload_string(payload: Union[Dict[str, Any], str]) -> Union[Dict[str, Any], Dict[str, str], Any]:
        """Parse string payload to dict, handling both JSON and Python literal dicts."""
        if not isinstance(payload, str):
            return payload
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(payload)
            except (SyntaxError, ValueError) as e:
                return {"error": f"Invalid payload format: {e}"}

    def _prepare_update_application_body(self, payload: Dict[str, Any], id: Optional[str] = None) -> Dict[str, Any]:
        """Prepare and serialize update payload for SDK API call."""
        request_body = dict(payload)  # shallow copy to avoid mutating the original
        # The Instana PUT endpoint requires 'id' in the request body as well as the URL path.
        if id and not request_body.get("id"):
            request_body["id"] = id
        if 'tagFilterExpression' in request_body and isinstance(request_body['tagFilterExpression'], dict):
            request_body['tagFilterExpression'] = self._convert_tag_filter_expression(
                request_body['tagFilterExpression']
            )
        return self._build_serializable_body(request_body)

    # ------------------------------------------------------------------
    # Pre-flight validation helpers (return elicitation dict or None)
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_application_fields(payload: Dict[str, Any], errors: List[str]) -> None:
        """Validate fields specific to the 'application' subtype."""
        if not payload.get("label") or not str(payload.get("label", "")).strip():
            errors.append(
                "'label' (application perspective name) is required and must be a non-empty string"
            )
        scope = payload.get("scope")
        if scope is not None and scope not in VALID_SCOPE_VALUES:
            errors.append(
                f"'scope' value '{scope}' is invalid. "
                f"Must be one of: {sorted(VALID_SCOPE_VALUES)}"
            )
        boundary = payload.get("boundaryScope")
        if boundary is not None and boundary not in VALID_BOUNDARY_SCOPE_VALUES:
            errors.append(
                f"'boundaryScope' value '{boundary}' is invalid. "
                f"Must be one of: {sorted(VALID_BOUNDARY_SCOPE_VALUES)}"
            )
        access_rules = payload.get("accessRules")
        if access_rules is not None and not isinstance(access_rules, list):
            errors.append("'accessRules' must be a list of access rule objects")

    @staticmethod
    def _validate_endpoint_fields(payload: Dict[str, Any], errors: List[str]) -> None:
        """Validate fields specific to the 'endpoint' subtype."""
        endpoint_case = payload.get("endpointCase")
        if not endpoint_case:
            errors.append(
                "'endpointCase' is required. "
                f"Must be one of: {sorted(VALID_ENDPOINT_CASE_VALUES)}"
            )
        elif endpoint_case not in VALID_ENDPOINT_CASE_VALUES:
            errors.append(
                f"'endpointCase' value '{endpoint_case}' is invalid. "
                f"Must be one of: {sorted(VALID_ENDPOINT_CASE_VALUES)}"
            )
        service_id = payload.get("serviceId")
        if not service_id or not str(service_id).strip():
            errors.append("'serviceId' is required for endpoint config")

    @staticmethod
    def _validate_service_fields(payload: Dict[str, Any], errors: List[str]) -> None:
        """Validate fields specific to the 'service' subtype."""
        label = payload.get("label")
        if not label or not str(label).strip():
            errors.append("'label' (display name) is required for service config")
        name = payload.get("name")
        if not name or not str(name).strip():
            errors.append("'name' is required for service config")
        if "enabled" not in payload:
            errors.append("'enabled' (boolean) is required for service config")
        elif not isinstance(payload["enabled"], bool):
            errors.append("'enabled' must be a boolean (true/false)")
        if payload.get("matchSpecification") is None:
            errors.append("'matchSpecification' is required for service config")

    @staticmethod
    def _validate_manual_service_fields(payload: Dict[str, Any], errors: List[str]) -> None:
        """Validate fields specific to the 'manual_service' subtype."""
        tag_filter = payload.get("tagFilterExpression")
        if tag_filter is None:
            errors.append(
                "'tagFilterExpression' is required for manual service config. "
                "Example: {\"type\": \"TAG_FILTER\", \"name\": \"service.name\", "
                "\"operator\": \"EQUALS\", \"entity\": \"NOT_APPLICABLE\", \"value\": \"my-service\"}"
            )
        elif not isinstance(tag_filter, dict):
            errors.append("'tagFilterExpression' must be a dictionary")

    _SUBTYPE_VALIDATORS = {
        "application": _validate_application_fields.__func__,
        "endpoint": _validate_endpoint_fields.__func__,
        "service": _validate_service_fields.__func__,
        "manual_service": _validate_manual_service_fields.__func__,
    }

    @staticmethod
    def _validate_settings_payload(
        subtype: str,
        operation: str,
        payload: Any,
        id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate settings payloads before sending to the API.

        Collects ALL validation errors in a single pass so the LLM gets
        the complete list in one response.

        Args:
            subtype:   'application' | 'endpoint' | 'service' | 'manual_service'
            operation: 'create' | 'update'
            payload:   The raw dict payload (already parsed from string if needed)
            id:        Resource ID (required for 'update')

        Returns:
            None if valid, elicitation dict if there are errors.
        """
        errors: List[str] = []

        if operation == "update" and (not id or (isinstance(id, str) and not id.strip())):
            errors.append("'id' is required for update operations")

        if payload is None or not isinstance(payload, dict):
            errors.append("'payload' must be a non-empty dictionary")
            return {
                "elicitation_needed": True,
                "reason": f"{operation} {subtype} config: payload is missing or invalid",
                "api_error": errors,
                "message": (
                    f"Cannot {operation} {subtype} config — payload is missing or not a dict. "
                    "Please provide a valid configuration dictionary."
                ),
            }

        validator = ApplicationSettingsMCPTools._SUBTYPE_VALIDATORS.get(subtype)
        if validator:
            validator(payload, errors)

        if not errors:
            return None

        count = len(errors)
        return {
            "elicitation_needed": True,
            "reason": f"{operation} {subtype} config has {count} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The {operation} {subtype} config request has {count} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    @with_header_auth(ApplicationSettingsApi)
    async def _add_application_config(self,
                                      payload: Union[Dict[str, Any], str],
                                      ctx=None,
                                      api_client=None,
                                      resource_type: Optional[str] = None,
                                      tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a new Application Perspective configuration.

        Required fields (per SDK NewApplicationConfig model):
        - label: Application perspective name (1-128 chars)
        - accessRules: Access control rules (min 1, max 64 items) - defaults applied
        - boundaryScope: Boundary scope (ALL/INBOUND/DEFAULT) - defaults applied
        - scope: Monitoring scope - defaults applied

        Optional fields:
        - tagFilterExpression: Tag filter (defaults to empty EXPRESSION)
        - matchSpecification: Match specification (optional)
        """
        try:
            # Parse string payload early so validation can inspect the dict
            if isinstance(payload, str):
                import contextlib
                with contextlib.suppress(Exception):
                    payload = json.loads(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("application", "create", payload)
            if _elicitation:
                return _elicitation

            # Validate and prepare payload with SDK-required defaults
            validation_result = self._validate_and_prepare_application_payload(payload)

            if "error" in validation_result:
                return validation_result

            request_body = validation_result["payload"]

            # Build a plain dict body, omitting businessCriticality entirely.
            # Rationale: the SDK model types it as StrictStr ('NOT_DEFINED' etc.) but the
            # Instana API actually stores/returns it as an integer (e.g. 0), and rejects any
            # string value with HTTP 400.  We bypass both the method-level Pydantic validation
            # (which requires a NewApplicationConfig object) and the model's field requirement
            # by calling the internal _serialize + call_api directly with a plain dict.
            serializable_body = self._build_serializable_body(request_body)
            logger.debug(f"serializable_body for add_application_config: {serializable_body}")

            def _do_add_sync(ac=api_client):
                _param = ac._add_application_config_serialize(
                    new_application_config=serializable_body,
                    _request_auth=None,
                    _content_type=None,
                    _headers=None,
                    _host_index=0,
                )
                rest_response = ac.api_client.call_api(*_param)
                rest_response.read()  # populate .data from underlying urllib3 response
                return rest_response

            response = await sdk_call_with_keepalive(
                call_sdk_fn(_do_add_sync),
                ctx=ctx,
                operation_name="add_application_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            result_dict = json.loads(response.data.decode('utf-8'))
            return self._build_add_application_response(result_dict, request_body, payload)
        except Exception as e:
            logger.error(f"Error in _add_application_config: {e}", exc_info=True)
            return {"error": f"Failed to add application config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _get_application_config(self,
                                      id: str,
                                      ctx=None,
                                      api_client=None,
                                      resource_type: Optional[str] = None,
                                      tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get an Application Perspective configuration by ID.

        Note: To get by application name instead of ID, use the smart router tool
        with application_name parameter. The router will automatically resolve
        the name to ID and call this method.

        Args:
            id: Application perspective configuration ID
            ctx: MCP context
            api_client: API client instance

        Returns:
            Application configuration dictionary
        """
        try:
            if not id:
                return {"error": "id is required"}

            # Use _without_preload_content to bypass SDK Pydantic model validation,
            # which fails when the API returns numeric values for string-typed fields
            # such as businessCriticality (returned as int 0 but typed as str).
            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_application_config_without_preload_content,
                    id=id
                ),
                ctx=ctx,
                operation_name="get_application_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            return json.loads(response.data.decode('utf-8'))
        except Exception as e:
            logger.error(f"Error in _get_application_config: {e}", exc_info=True)
            return {"error": f"Failed to get application config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_application_config(self,
                                         id: str,
                                         payload: Union[Dict[str, Any], str],
                                         ctx=None,
                                         api_client=None,
                                         resource_type: Optional[str] = None,
                                         tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing Application Perspective configuration."""
        try:
            parsed = self._parse_payload_string(payload)
            if isinstance(parsed, dict) and "error" in parsed:
                return parsed
            payload = parsed

            _elicitation = self._validate_settings_payload("application", "update", payload, id=id)
            if _elicitation:
                return _elicitation

            serializable_body = self._prepare_update_application_body(payload, id=id)

            def _do_update_sync(ac=api_client, _id=id):
                _param = ac._put_application_config_serialize(
                    id=_id,
                    application_config=serializable_body,
                    _request_auth=None,
                    _content_type=None,
                    _headers=None,
                    _host_index=0,
                )
                rest_response = ac.api_client.call_api(*_param)
                rest_response.read()  # populate .data from underlying urllib3 response
                return rest_response

            response = await sdk_call_with_keepalive(
                call_sdk_fn(_do_update_sync),
                ctx=ctx,
                operation_name="put_application_config",
                resource_type=resource_type, tool_name=tool_name,
            )

            result_dict = json.loads(response.data.decode('utf-8'))
            return result_dict or {"success": True, "message": f"Application config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_application_config: {e}", exc_info=True)
            return {"error": f"Failed to update application config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_application_config(self,
                                         id: str,
                                         ctx=None,
                                         api_client=None,
                                         resource_type: Optional[str] = None,
                                         tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete an Application Perspective configuration."""
        try:
            if not id:
                return {"error": "id is required"}

            await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.delete_application_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="delete_application_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            return {"success": True, "message": f"Application config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_application_config: {e}", exc_info=True)
            return {"error": f"Failed to delete application config: {e!s}"}

    # Endpoint Config Operations
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_endpoint_configs(self,
                                        ctx=None,
                                        api_client=None,
                                        resource_type: Optional[str] = None,
                                        tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all Endpoint Perspectives Configuration."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_endpoint_configs_without_preload_content),
                ctx=ctx,
                operation_name="get_endpoint_configs",
                resource_type=resource_type, tool_name=tool_name,
            )
            response_text = decode_response(result)
            json_data = json.loads(response_text)
            return json_data if isinstance(json_data, list) else [json_data] if json_data else []
        except Exception as e:
            logger.error(f"Error in _get_all_endpoint_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get endpoint configs: {e!s}"}]

    @with_header_auth(ApplicationSettingsApi)
    async def _get_endpoint_config(self,
                                   id: str,
                                   ctx=None,
                                   api_client=None,
                                   resource_type: Optional[str] = None,
                                   tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get an Endpoint configuration by ID."""
        try:
            if not id:
                return {"error": "id is required"}
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_endpoint_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="get_endpoint_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result
        except Exception as e:
            logger.error(f"Error in _get_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to get endpoint config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _create_endpoint_config(self,
                                      payload: Union[Dict[str, Any], str],
                                      ctx=None,
                                      api_client=None,
                                      resource_type: Optional[str] = None,
                                      tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Create or update endpoint configuration for a service."""
        try:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = ast.literal_eval(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("endpoint", "create", payload)
            if _elicitation:
                return _elicitation

            request_body = payload
            config_object = EndpointConfig(**request_body)
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.create_endpoint_config,
                    endpoint_config=config_object
                ),
                ctx=ctx,
                operation_name="create_endpoint_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": "Endpoint config created"}
        except Exception as e:
            logger.error(f"Error in _create_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to create endpoint config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_endpoint_config(self,
                                      id: str,
                                      payload: Union[Dict[str, Any], str],
                                      ctx=None,
                                      api_client=None,
                                      resource_type: Optional[str] = None,
                                      tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Update an endpoint configuration."""
        try:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = ast.literal_eval(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("endpoint", "update", payload, id=id)
            if _elicitation:
                return _elicitation

            request_body = payload
            config_object = EndpointConfig(**request_body)
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.update_endpoint_config,
                    id=id,
                    endpoint_config=config_object
                ),
                ctx=ctx,
                operation_name="update_endpoint_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Endpoint config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to update endpoint config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_endpoint_config(self,
                                      id: str,
                                      ctx=None,
                                      api_client=None,
                                      resource_type: Optional[str] = None,
                                      tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete an endpoint configuration."""
        try:
            if not id:
                return {"error": "id is required"}
            await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.delete_endpoint_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="delete_endpoint_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            return {"success": True, "message": f"Endpoint config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to delete endpoint config: {e!s}"}

    # Service Config Operations
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_service_configs(self,
                                       ctx=None,
                                       api_client=None,
                                       resource_type: Optional[str] = None,
                                       tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all Service configurations."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_service_configs_without_preload_content),
                ctx=ctx,
                operation_name="get_service_configs",
                resource_type=resource_type, tool_name=tool_name,
            )
            response_text = decode_response(result)
            json_data = json.loads(response_text)
            return json_data if isinstance(json_data, list) else [json_data] if json_data else []
        except Exception as e:
            logger.error(f"Error in _get_all_service_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get service configs: {e!s}"}]

    @with_header_auth(ApplicationSettingsApi)
    async def _get_service_config(self,
                                  id: str,
                                  ctx=None,
                                  api_client=None,
                                  resource_type: Optional[str] = None,
                                  tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Get a Service configuration by ID."""
        try:
            if not id:
                return {"error": "id is required"}
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_service_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="get_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result
        except Exception as e:
            logger.error(f"Error in _get_service_config: {e}", exc_info=True)
            return {"error": f"Failed to get service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _add_service_config(self,
                                  payload: Union[Dict[str, Any], str],
                                  ctx=None,
                                  api_client=None,
                                  resource_type: Optional[str] = None,
                                  tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Add a new Service configuration."""
        try:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = ast.literal_eval(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("service", "create", payload)
            if _elicitation:
                return _elicitation

            request_body = payload
            config_object = ServiceConfig(**request_body)
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.add_service_config,
                    service_config=config_object
                ),
                ctx=ctx,
                operation_name="add_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": "Service config created"}
        except Exception as e:
            logger.error(f"Error in _add_service_config: {e}", exc_info=True)
            return {"error": f"Failed to add service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_service_config(self,
                                     id: str,
                                     payload: Union[Dict[str, Any], str],
                                     ctx=None,
                                     api_client=None,
                                     resource_type: Optional[str] = None,
                                     tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Update a Service configuration."""
        try:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = ast.literal_eval(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("service", "update", payload, id=id)
            if _elicitation:
                return _elicitation

            request_body = payload
            config_object = ServiceConfig(**request_body)
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.update_service_config,
                    id=id,
                    service_config=config_object
                ),
                ctx=ctx,
                operation_name="update_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Service config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_service_config: {e}", exc_info=True)
            return {"error": f"Failed to update service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_service_config(self,
                                     id: str,
                                     ctx=None,
                                     api_client=None,
                                     resource_type: Optional[str] = None,
                                     tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete a Service configuration."""
        try:
            if not id:
                return {"error": "id is required"}
            await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.delete_service_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="delete_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            return {"success": True, "message": f"Service config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_service_config: {e}", exc_info=True)
            return {"error": f"Failed to delete service config: {e!s}"}

    # Manual Service Config Operations
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_manual_service_configs(self,
                                              ctx=None,
                                              api_client=None,
                                              resource_type: Optional[str] = None,
                                              tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all Manual Service configurations."""
        try:
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_all_manual_service_configs_without_preload_content),
                ctx=ctx,
                operation_name="get_all_manual_service_configs",
                resource_type=resource_type, tool_name=tool_name,
            )
            response_text = decode_response(result)
            json_data = json.loads(response_text)
            return json_data if isinstance(json_data, list) else [json_data] if json_data else []
        except Exception as e:
            logger.error(f"Error in _get_all_manual_service_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get manual service configs: {e!s}"}]

    @with_header_auth(ApplicationSettingsApi)
    async def _add_manual_service_config(self,
                                         payload: Union[Dict[str, Any], str],
                                         ctx=None,
                                         api_client=None,
                                         resource_type: Optional[str] = None,
                                         tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Add a new Manual Service configuration."""
        try:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = ast.literal_eval(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("manual_service", "create", payload)
            if _elicitation:
                return _elicitation

            request_body = payload
            config_object = NewManualServiceConfig(**request_body)
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.add_manual_service_config,
                    new_manual_service_config=config_object
                ),
                ctx=ctx,
                operation_name="add_manual_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": "Manual service config created"}
        except Exception as e:
            logger.error(f"Error in _add_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to add manual service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_manual_service_config(self,
                                            id: str,
                                            payload: Union[Dict[str, Any], str],
                                            ctx=None,
                                            api_client=None,
                                            resource_type: Optional[str] = None,
                                            tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Update a Manual Service configuration."""
        try:
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = ast.literal_eval(payload)

            # --- Pre-flight validation ---
            _elicitation = self._validate_settings_payload("manual_service", "update", payload, id=id)
            if _elicitation:
                return _elicitation

            request_body = payload
            config_object = ManualServiceConfig(**request_body)
            result = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.update_manual_service_config,
                    id=id,
                    manual_service_config=config_object
                ),
                ctx=ctx,
                operation_name="update_manual_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Manual service config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to update manual service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_manual_service_config(self,
                                            id: str,
                                            ctx=None,
                                            api_client=None,
                                            resource_type: Optional[str] = None,
                                            tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Delete a Manual Service configuration."""
        try:
            if not id:
                return {"error": "id is required"}
            await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.delete_manual_service_config,
                    id=id
                ),
                ctx=ctx,
                operation_name="delete_manual_service_config",
                resource_type=resource_type, tool_name=tool_name,
            )
            return {"success": True, "message": f"Manual service config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to delete manual service config: {e!s}"}
