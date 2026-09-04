"""
SLO Correction Configuration MCP Tools Module

This module provides SLO Correction Window configuration tools for Instana.
"""

import ast
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from instana_client.models.correction_configuration import CorrectionConfiguration
from instana_client.models.correction_scheduling import CorrectionScheduling

try:
    from instana_client.api.slo_correction_configurations_api import (
        SLOCorrectionConfigurationsApi,
    )

except ImportError:
    logging.getLogger(__name__).error("Instana SDK not available.", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    sdk_call_with_keepalive,
    with_header_auth,
)

logger = logging.getLogger(__name__)

VALID_DURATION_UNITS = ("millisecond", "second", "minute", "hour", "day", "week", "calendar_month")

class SLOCorrectionMCPTools(BaseInstanaClient):
    """Tools for SLO correction window configuration in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the SLO Correction MCP tools client."""
        super().__init__(read_token = read_token, base_url = base_url)

    def _build_missing_param(self, name: str, description: str, field_type: str, **extra: Any) -> Dict[str, Any]:
        param = {
            "name": name,
            "description": description,
            "type": field_type,
            "required": True,
        }
        param.update(extra)
        return param

    def _validate_correction_scheduling(self, payload: Dict[str, Any], missing_params: List[Dict[str, Any]]) -> None:
        if "scheduling" not in payload:
            missing_params.append(self._build_missing_param(
                "scheduling",
                "Scheduling configuration for the correction window",
                "object",
                example={
                    "duration": 2,
                    "durationUnit": "hour",
                    "startTime": "2026-03-10 14:00:00|IST"
                },
                nested_fields={
                    "duration": "Duration value (e.g., 2)",
                    "durationUnit": f"One of: {', '.join(VALID_DURATION_UNITS)}",
                    "startTime": "Start time with timezone (e.g., '2026-03-10 14:00:00|IST')"
                }
            ))
            return

        scheduling = payload["scheduling"]
        if not isinstance(scheduling, dict):
            return

        if "duration" not in scheduling:
            missing_params.append(self._build_missing_param(
                "scheduling.duration",
                "Duration value for the correction window",
                "integer",
                example=2,
            ))
        elif not isinstance(scheduling["duration"], int) or scheduling["duration"] <= 0:
            missing_params.append(self._build_missing_param(
                "scheduling.duration",
                "Invalid duration value",
                "integer",
                example=2,
                validation="Must be a positive integer",
                error=f"Invalid duration: {scheduling['duration']}"
            ))

        if "durationUnit" not in scheduling:
            missing_params.append(self._build_missing_param(
                "scheduling.durationUnit",
                "Unit for the duration",
                "string",
                example="hour",
                validation=f"Must be one of: {', '.join(VALID_DURATION_UNITS)}"
            ))
        elif scheduling["durationUnit"] not in VALID_DURATION_UNITS:
            missing_params.append(self._build_missing_param(
                "scheduling.durationUnit",
                "Invalid duration unit",
                "string",
                example="hour",
                validation=f"Must be one of: {', '.join(VALID_DURATION_UNITS)}",
                error=f"Invalid durationUnit: {scheduling['durationUnit']}"
            ))

    def _append_message_section(self, message_parts: List[str], title: str, params: List[Dict[str, Any]], include_validation: bool = False) -> None:
        if not params:
            return
        message_parts.append(title)
        for param in params:
            example_str = f" (e.g., {param['example']})" if "example" in param else ""
            validation_str = f" — {param['validation']}" if include_validation and "validation" in param else ""
            error_str = f" [current error: {param['error']}]" if include_validation and "error" in param else ""
            message_parts.append(f"- {param['name']}: {param['description']}{example_str}{validation_str}{error_str}")

    def _build_correction_elicitation(self, missing_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        top_level = [p for p in missing_params if "." not in p["name"] and p["name"] != "scheduling"]
        scheduling_fields = [p for p in missing_params if p["name"].startswith("scheduling")]
        message_parts = ["To create an SLO correction window, I need the following information:\n"]
        self._append_message_section(message_parts, "\n**Top-level fields:**", top_level)
        self._append_message_section(message_parts, "\n**Scheduling fields:**", scheduling_fields, include_validation=True)
        message_parts.append("\n**Note:** The startTime field should include timezone (e.g., '2026-03-10 14:00:00|IST') for accurate correction window scheduling.")
        return {
            "elicitation_needed": True,
            "message": "\n".join(message_parts),
            "missing_parameters": [p["name"] for p in missing_params],
            "parameter_details": missing_params,
            "user_prompt": "Please provide all the required fields to create the SLO correction window."
        }

    def _validate_correction_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate SLO correction configuration payload and return elicitation if fields are missing
        or invalid.

        Validates all required fields and their allowed enum values before the API is called so
        that a single consolidated response can be returned to the LLM for correction.

        Args:
            payload: The SLO correction configuration payload to validate

        Returns:
            None if validation passes, elicitation dict if fields are missing or invalid
        """
        missing_params = []

        if "name" not in payload:
            missing_params.append(self._build_missing_param(
                "name",
                "Name of the correction window",
                "string",
                example="Maintenance Window - Database Upgrade"
            ))

        if "sloIds" not in payload:
            missing_params.append(self._build_missing_param(
                "sloIds",
                "List of SLO configuration IDs this correction applies to",
                "array of strings",
                example=["slo-abc123", "slo-def456"]
            ))

        self._validate_correction_scheduling(payload, missing_params)

        if missing_params:
            return self._build_correction_elicitation(missing_params)

        return None

    def _clean_correction_data(self, correction: Dict[str, Any]) -> Dict[str, Any]:
        """Clean correction data for LLM consumption."""
        cleaned = {
            "id": correction.get("id"),
            "name": correction.get("name"),
            "description": correction.get("description"),
            "sloIds": correction.get("sloIds", []),
            "scheduling": correction.get("scheduling"),
            "tags": correction.get("tags", []),
            "createdDate": correction.get("createdDate"),
            "lastUpdated": correction.get("lastUpdated")
        }
        return {k: v for k,v in cleaned.items() if v is not None}

    @with_header_auth(SLOCorrectionConfigurationsApi)
    async def get_all_corrections(self,
        page_size: Optional[int]= None,
        page: Optional[int]= None,
        order_by: Optional[str]= None,
        order_direction: Optional[str]= None,
        query: Optional[str]= None,
        tag:  Optional[List[str]]= None,
        id: Optional[List[str]]= None,
        slo_id: Optional[List[str]] = None,
        refresh: Optional[bool] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all SLO correction window configurations with optional filtering."""
        try:
            logger.debug(f"get_all_corrections called with page_size: {page_size}, page: {page}")
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_all_slo_correction_window_configs_without_preload_content, page_size=page_size, page=page, order_by=order_by, order_direction=order_direction, query=query, tag=tag, id=id, slo_id=slo_id, refresh=refresh), ctx=ctx, operation_name="get_all_slo_correction_window_configs", resource_type=resource_type, tool_name=tool_name)
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            # Clean the items in the paginated result
            if "items" in result_dict:
                result_dict["items"] = [self._clean_correction_data(item) for item in result_dict["items"]]
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_all_corrections: {e!s}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(SLOCorrectionConfigurationsApi)
    async def get_correction_by_id(self,
       id: str,
       ctx=None,
       api_client=None,
       resource_type: Optional[str] = None,
       tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get a specific SLO correction window configuration by ID."""
        try:
            if not id:
                return {"error": "ID is required"}
            logger.debug(f"get_correction_by_id called with id: {id}")
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_slo_correction_window_config_by_id_without_preload_content, id=id), ctx=ctx, operation_name="get_slo_correction_window_config_by_id", resource_type=resource_type, tool_name=tool_name)
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}
            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)
            cleaned = self._clean_correction_data(result_dict)
            return cleaned
        except Exception as e:
            logger.error(f"Error in get_correction_by_id: {e!s}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(SLOCorrectionConfigurationsApi)
    async def create_correction(self,
        payload: Union[Dict[str, Any], str],
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create new SLO correction window configuration."""
        try:
            if not payload:
                return {"error": "payload is required"}

            # Parse payload if string
            if isinstance(payload, str):
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            # Comprehensive validation with elicitation
            validation_result = self._validate_correction_payload(request_body)
            if validation_result:
                logger.info("SLO correction config validation failed - returning elicitation")
                return validation_result

            # durationUnit enum is already validated by _validate_correction_payload above;
            # this check is kept as a safety net with the correct SDK-sourced values.
            scheduling_data = request_body.get("scheduling", {})
            valid_units = ['millisecond', 'second', 'minute', 'hour', 'day', 'week', 'calendar_month']
            if scheduling_data.get("durationUnit") not in valid_units:
                return {"error": f"scheduling.durationUnit must be one of: {', '.join(valid_units)}"}
            # Handle startTime conversion if provided as milliseconds
            if "startTime" in scheduling_data and isinstance(scheduling_data["startTime"], (int, float)):
                # Convert milliseconds to UTC datetime
                # CRITICAL: Must use timezone.utc to ensure the timestamp is interpreted correctly
                from datetime import timezone
                scheduling_data["startTime"] = datetime.fromtimestamp(scheduling_data["startTime"] / 1000.0, tz=timezone.utc)

            # Create scheduling object
            scheduling_object = CorrectionScheduling(**scheduling_data)

            # Create main correction object (don't include id, createdDate, lastUpdated)
            correction_object = CorrectionConfiguration(
                name = request_body["name"],
                scheduling = scheduling_object,
                description=request_body.get("description"),
                sloIds = request_body.get("sloIds", []),
                tags = request_body.get("tags", []),
                active = request_body.get("active")
            )

            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.create_slo_correction_window_config_without_preload_content, correction_configuration=correction_object), ctx=ctx, operation_name="create_slo_correction_window_config", resource_type=resource_type, tool_name=tool_name)

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            cleaned = self._clean_correction_data(result_dict)
            return {
                "success": True,
                "message": "Correction window created",
                "data": cleaned
            }
        except Exception as e:
            logger.error(f"Error in create_correction: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(SLOCorrectionConfigurationsApi)
    async def update_correction(
        self,
        id: str,
        payload: Union[Dict[str, Any], str],
        api_client=None,
        ctx=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update existing SLO correction window configuration."""
        try:
            if not id:
                return {"error": "Missing required parameter: id"}
            if not payload:
                return {"error": "Missing required parameter: payload"}

            if isinstance(payload, str):
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            # Comprehensive validation with elicitation
            validation_result = self._validate_correction_payload(request_body)
            if validation_result:
                logger.info("SLO correction config validation failed for update - returning elicitation")
                validation_result["message"] = validation_result["message"].replace(
                    "To create an SLO correction window",
                    "To update the SLO correction window"
                )
                return validation_result

            # Get scheduling data
            scheduling_data = request_body.get("scheduling", {})

            # Handle startTime conversion if provided as milliseconds
            if "startTime" in scheduling_data and isinstance(scheduling_data["startTime"], (int, float)):
                # Convert milliseconds to UTC datetime
                # CRITICAL: Must use timezone.utc to ensure the timestamp is interpreted correctly
                from datetime import timezone
                scheduling_data["startTime"] = datetime.fromtimestamp(scheduling_data["startTime"] / 1000.0, tz=timezone.utc)

            # Create scheduling object
            scheduling_object = CorrectionScheduling(**scheduling_data)

            # Create correction object (don't include id, createdDate, lastUpdated)
            correction_object = CorrectionConfiguration(
                name=request_body["name"],
                scheduling=scheduling_object,
                description=request_body.get("description"),
                sloIds=request_body.get("sloIds", []),
                tags=request_body.get("tags", []),
                active=request_body.get("active")
            )

            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.update_slo_correction_window_config_without_preload_content, id=id, correction_configuration=correction_object), ctx=ctx, operation_name="update_slo_correction_window_config", resource_type=resource_type, tool_name=tool_name)

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            cleaned = self._clean_correction_data(result_dict)
            return {"success": True, "message": "Correction window updated", "data": cleaned}

        except Exception as e:
            logger.error(f"Error in update_correction: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(SLOCorrectionConfigurationsApi)
    async def delete_correction(self,
        id: str,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete SLO correction window configuration."""
        try:
            if not id:
                return {"error": "id is required"}

            await sdk_call_with_keepalive(call_sdk_fn(api_client.delete_slo_correction_window_config, id=id), ctx=ctx, operation_name="delete_slo_correction_window_config", resource_type=resource_type, tool_name=tool_name)
            return {"success": True, "message": f"Correction window '{id}' deleted"}

        except Exception as e:
            logger.error(f"Error in delete_correction: {e}", exc_info=True)
            return {"error": str(e)}
