"""
SLO Alert Configuration MCP Tools Module

This module provides SLO Alert configuration tools for Instana.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

try:
    from instana_client.api.service_levels_alert_configuration_api import (
        ServiceLevelsAlertConfigurationApi,
    )
except ImportError:
    logging.getLogger(__name__).error("Instana SDK not available.", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, with_header_auth

logger = logging.getLogger(__name__)

class SLOAlertConfigMCPTools(BaseInstanaClient):
    """Tools for SLO alert configuration in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the SLO Alert Config MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _validate_alert_config_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate SLO alert configuration payload and return elicitation if fields are missing.

        Args:
            payload: The SLO alert configuration payload to validate

        Returns:
            None if validation passes, elicitation dict if fields are missing
        """
        missing_params = []

        # Check top-level required fields
        if "name" not in payload:
            missing_params.append({
                "name": "name",
                "description": "Name of the SLO alert configuration",
                "type": "string",
                "required": True,
                "example": "High Burn Rate Alert"
            })

        if "description" not in payload:
            missing_params.append({
                "name": "description",
                "description": "Description of the alert (also used as alert message)",
                "type": "string",
                "required": True,
                "example": "Alert when SLO burn rate exceeds threshold"
            })

        if "sloIds" not in payload:
            missing_params.append({
                "name": "sloIds",
                "description": "List of SLO configuration IDs this alert applies to",
                "type": "array of strings",
                "required": True,
                "example": ["slo-abc123", "slo-def456"]
            })

        if "severity" not in payload:
            missing_params.append({
                "name": "severity",
                "description": "Alert severity level",
                "type": "integer",
                "required": True,
                "example": 10,
                "validation": "Must be 5 (warning) or 10 (critical)"
            })
        elif payload["severity"] not in [5, 10]:
            missing_params.append({
                "name": "severity",
                "description": "Alert severity level (invalid value provided)",
                "type": "integer",
                "required": True,
                "example": 10,
                "validation": "Must be 5 (warning) or 10 (critical)",
                "error": f"Invalid severity: {payload['severity']}"
            })

        if "alertChannelIds" not in payload:
            missing_params.append({
                "name": "alertChannelIds",
                "description": "List of alert channel IDs to send notifications to",
                "type": "array of strings",
                "required": True,
                "example": ["channel-123", "channel-456"]
            })

        if "customPayloadFields" not in payload:
            missing_params.append({
                "name": "customPayloadFields",
                "description": "Custom fields to include in alert payload (can be empty list)",
                "type": "array of objects",
                "required": True,
                "example": [{"type": "staticString", "key": "environment", "value": "production"}]
            })

        # Validate rule
        if "rule" not in payload:
            missing_params.append({
                "name": "rule",
                "description": "Alert rule definition",
                "type": "object",
                "required": True,
                "example": {
                    "alertType": "ERROR_BUDGET",
                    "metric": "BURN_RATE"
                },
                "nested_fields": {
                    "alertType": "'ERROR_BUDGET' or 'SERVICE_LEVELS_OBJECTIVE'",
                    "metric": "'BURN_RATE', 'BURNED_PERCENTAGE', or 'BURN_RATE_V2' (for ERROR_BUDGET)"
                }
            })
        else:
            rule = payload["rule"]
            if isinstance(rule, dict):
                if "alertType" not in rule:
                    missing_params.append({
                        "name": "rule.alertType",
                        "description": "Type of alert rule",
                        "type": "string",
                        "required": True,
                        "example": "ERROR_BUDGET",
                        "validation": "Must be 'ERROR_BUDGET' or 'SERVICE_LEVELS_OBJECTIVE'"
                    })
                elif rule["alertType"] == "ERROR_BUDGET":
                    if "metric" not in rule:
                        missing_params.append({
                            "name": "rule.metric",
                            "description": "Metric to monitor for ERROR_BUDGET alerts",
                            "type": "string",
                            "required": True,
                            "example": "BURN_RATE",
                            "validation": "Must be 'BURN_RATE', 'BURNED_PERCENTAGE', or 'BURN_RATE_V2'"
                        })
                    elif rule["metric"] == "BURN_RATE" and "burnRateTimeWindows" not in payload:
                        missing_params.append({
                            "name": "burnRateTimeWindows",
                            "description": "Time windows for burn rate calculation (required for BURN_RATE metric)",
                            "type": "object",
                            "required": True,
                            "example": {
                                "longTimeWindow": {"duration": 1, "durationType": "hour"},
                                "shortTimeWindow": {"duration": 5, "durationType": "minute"}
                            },
                            "nested_fields": {
                                "longTimeWindow": "Long time window configuration",
                                "shortTimeWindow": "Short time window configuration"
                            }
                        })

        # Validate timeThreshold
        if "timeThreshold" not in payload:
            missing_params.append({
                "name": "timeThreshold",
                "description": "Time threshold configuration for the alert",
                "type": "object",
                "required": True,
                "example": {
                    "expiry": 604800000,
                    "timeWindow": 604800000
                },
                "nested_fields": {
                    "expiry": "Expiry time in milliseconds",
                    "timeWindow": "Time window in milliseconds"
                }
            })
        else:
            time_threshold = payload["timeThreshold"]
            if isinstance(time_threshold, dict):
                if "expiry" not in time_threshold:
                    missing_params.append({
                        "name": "timeThreshold.expiry",
                        "description": "Alert expiry time in milliseconds",
                        "type": "integer",
                        "required": True,
                        "example": 604800000
                    })
                if "timeWindow" not in time_threshold:
                    missing_params.append({
                        "name": "timeThreshold.timeWindow",
                        "description": "Time window in milliseconds",
                        "type": "integer",
                        "required": True,
                        "example": 604800000
                    })

        # If any fields are missing, return elicitation
        if missing_params:
            # Group parameters by category
            top_level = [p for p in missing_params if "." not in p["name"] and p["name"] not in ["rule", "timeThreshold", "burnRateTimeWindows"]]
            rule_fields = [p for p in missing_params if p["name"].startswith("rule")]
            time_threshold_fields = [p for p in missing_params if p["name"].startswith("timeThreshold")]
            conditional_fields = [p for p in missing_params if p["name"] == "burnRateTimeWindows"]

            message_parts = ["To create an SLO alert configuration, I need the following information:\n"]

            if top_level:
                message_parts.append("\n**Top-level fields:**")
                for param in top_level:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    validation_str = f" - {param['validation']}" if "validation" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}{validation_str}")

            if rule_fields:
                message_parts.append("\n**Rule fields:**")
                for param in rule_fields:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    validation_str = f" - {param['validation']}" if "validation" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}{validation_str}")

            if time_threshold_fields:
                message_parts.append("\n**Time threshold fields:**")
                for param in time_threshold_fields:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}")

            if conditional_fields:
                message_parts.append("\n**Conditional fields (required for BURN_RATE metric):**")
                for param in conditional_fields:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}")

            return {
                "elicitation_needed": True,
                "message": "\n".join(message_parts),
                "missing_parameters": [p["name"] for p in missing_params],
                "parameter_details": missing_params,
                "user_prompt": "Please provide all the required fields to create the SLO alert configuration."
            }

        return None

    def _validate_id_parameter(self, id: Optional[str], param_name: str = "id") -> Optional[Dict[str, Any]]:
        """
        Validate ID parameter.

        Args:
            id: The ID value to validate
            param_name: Name of the parameter for error messages

        Returns:
            Error dict if validation fails, None if valid
        """
        if not id:
            return {"error": f"{param_name} is required"}
        if not isinstance(id, str):
            return {"error": f"{param_name} must be a string"}
        if not id.strip():
            return {"error": f"{param_name} cannot be empty"}
        return None

    def _parse_payload(self, payload: Union[Dict[str, Any], str]) -> Union[Dict[str, Any], Dict[str, Any]]:
        """
        Parse payload from string or dict.

        Args:
            payload: Payload as dict or JSON string

        Returns:
            Parsed dict if successful, error dict otherwise
        """
        if not payload:
            return {"error": "payload is required"}

        if isinstance(payload, str):
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                try:
                    import ast
                    return ast.literal_eval(payload)
                except (ValueError, SyntaxError) as e:
                    return {"error": f"Invalid payload format: {e!s}"}

        if isinstance(payload, dict):
            return payload

        return {"error": f"Payload must be dict or JSON string, got {type(payload).__name__}"}

    def _clean_alert_config_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Clean alert config data for LLM consumption."""
        cleaned = {
            "id": config.get("id"),
            "name": config.get("name"),
            "description": config.get("description"),
            "sloIds": config.get("sloIds", []),
            "rule": config.get("rule"),
            "severity": config.get("severity"),
            "alertChannelIds": config.get("alertChannelIds", []),
            "timeThreshold": config.get("timeThreshold"),
            "threshold": config.get("threshold"),
            "burnRateConfig": config.get("burnRateConfig"),
            "customPayloadFields": config.get("customPayloadFields", []),
            "triggering": config.get("triggering")
        }
        return {k: v for k, v in cleaned.items() if v is not None}

    def _build_alert_config_object(self, request_body: Dict[str, Any]) -> Union[Dict[str, Any], Any]:
        """
        Build ServiceLevelsAlertConfig object from request body.

        This method contains the common logic for creating alert config objects
        used by both create_alert_config and update_alert_config.

        Args:
            request_body: Validated request body dictionary

        Returns:
            ServiceLevelsAlertConfig object if successful, error dict otherwise
        """
        try:
            # Import models
            from instana_client.models.alerting_time_window import AlertingTimeWindow
            from instana_client.models.error_budget_alert_rule import (
                ErrorBudgetAlertRule,
            )
            from instana_client.models.service_level_objective_alert_rule import (
                ServiceLevelObjectiveAlertRule,
            )
            from instana_client.models.service_levels_alert_config import (
                ServiceLevelsAlertConfig,
            )
            from instana_client.models.service_levels_burn_rate_time_windows import (
                ServiceLevelsBurnRateTimeWindows,
            )
            from instana_client.models.service_levels_time_threshold import (
                ServiceLevelsTimeThreshold,
            )
            from instana_client.models.static_string_field import StaticStringField
            from instana_client.models.static_threshold import StaticThreshold

            # Create rule object based on alertType
            rule_data = request_body.get("rule", {})
            alert_type = rule_data.get("alertType")
            metric = rule_data.get("metric")

            if alert_type == "ERROR_BUDGET":
                if "metric" not in rule_data:
                    return {"error": "rule.metric is required for ERROR_BUDGET alerts (BURN_RATE, BURNED_PERCENTAGE, or BURN_RATE_V2)"}

                # Validate burnRateTimeWindows for BURN_RATE metric
                if metric == "BURN_RATE" and "burnRateTimeWindows" not in request_body:
                    return {"error": "burnRateTimeWindows is required for BURN_RATE metric. Must include longTimeWindow and shortTimeWindow with duration and durationType"}

                rule_object = ErrorBudgetAlertRule(**rule_data)
            elif alert_type == "SERVICE_LEVELS_OBJECTIVE":
                rule_object = ServiceLevelObjectiveAlertRule(**rule_data)
            else:
                return {"error": f"Invalid alertType: {alert_type}. Must be ERROR_BUDGET or SERVICE_LEVELS_OBJECTIVE"}

            # Create time threshold object (requires expiry and timeWindow in milliseconds)
            time_threshold_data = request_body.get("timeThreshold", {})
            if "expiry" not in time_threshold_data or "timeWindow" not in time_threshold_data:
                return {"error": "timeThreshold must include both 'expiry' and 'timeWindow' (in milliseconds)"}
            time_threshold_object = ServiceLevelsTimeThreshold(**time_threshold_data)

            # Create custom payload fields (must use proper discriminated union types)
            custom_payload_objects = []
            for field in request_body.get("customPayloadFields", []):
                if field.get("type") == "staticString":
                    custom_payload_objects.append(StaticStringField(**field))
                # Add other types as needed (dynamic, etc.)

            # Create threshold object if provided
            threshold_object = None
            if request_body.get("threshold"):
                threshold_object = StaticThreshold(**request_body["threshold"])

            # Create burnRateTimeWindows if provided (required for BURN_RATE metric)
            burn_rate_time_windows_object = None
            if request_body.get("burnRateTimeWindows"):
                brw_data = request_body["burnRateTimeWindows"]
                long_window = None
                short_window = None

                if "longTimeWindow" in brw_data:
                    long_window = AlertingTimeWindow(**brw_data["longTimeWindow"])
                if "shortTimeWindow" in brw_data:
                    short_window = AlertingTimeWindow(**brw_data["shortTimeWindow"])

                burn_rate_time_windows_object = ServiceLevelsBurnRateTimeWindows(
                    longTimeWindow=long_window,
                    shortTimeWindow=short_window
                )

            # Create main config object
            config_object = ServiceLevelsAlertConfig(
                name=request_body["name"],
                description=request_body["description"],
                sloIds=request_body["sloIds"],
                rule=rule_object,
                severity=request_body["severity"],
                alertChannelIds=request_body["alertChannelIds"],
                timeThreshold=time_threshold_object,
                customPayloadFields=custom_payload_objects,
                threshold=threshold_object,
                burnRateConfig=request_body.get("burnRateConfig"),
                burnRateTimeWindows=burn_rate_time_windows_object,
                triggering=request_body.get("triggering")
            )

            return config_object

        except Exception as e:
            logger.error(f"Error building alert config object: {e}", exc_info=True)
            return {"error": f"Failed to build alert config object: {e!s}"}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def find_active_alert_configs(self,
        slo_id: Optional[str] = None,
        alert_ids: Optional[List[str]] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Find active SLO alert configurations."""
        try:
            logger.debug(f"find_active_alert_configs called with slo_id: {slo_id}")

            result = api_client.find_active_service_levels_alert_configs_without_preload_content(
                slo_id=slo_id,
                alert_ids=alert_ids
            )

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_list = json.loads(response_text)

            if isinstance(result_list, list):
                cleaned = [self._clean_alert_config_data(cfg) for cfg in result_list]
                return {"success": True, "configs": cleaned, "count": len(cleaned)}

            return {"success": True, "configs": [], "count": 0}

        except Exception as e:
            logger.error(f"Error in find_active_alert_configs: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def find_alert_config(self,
        id: str,
        valid_on: Optional[int] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Find specific SLO alert configuration by ID."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            if valid_on is not None and not isinstance(valid_on, int):
                return {"error": "valid_on must be an integer timestamp"}

            result = api_client.find_service_levels_alert_config_without_preload_content(
                id=id,
                valid_on=valid_on
            )

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            cleaned = self._clean_alert_config_data(result_dict)
            return cleaned

        except Exception as e:
            logger.error(f"Error in find_alert_config: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def find_alert_config_versions(self,
        id: str,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Find all versions of an SLO alert configuration."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            result = api_client.find_service_levels_alert_config_versions_without_preload_content(id=id)

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_list = json.loads(response_text)

            return {"success": True, "versions": result_list, "count": len(result_list)}

        except Exception as e:
            logger.error(f"Error in find_alert_config_versions: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def create_alert_config(self,
        payload: Union[Dict[str, Any], str],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Create new SLO alert configuration."""
        try:
            # Parse payload using helper method
            request_body = self._parse_payload(payload)

            # Check if parsing failed (returns error dict)
            if isinstance(request_body, dict) and "error" in request_body:
                return request_body

            # Comprehensive validation with elicitation
            validation_result = self._validate_alert_config_payload(request_body)
            if validation_result:
                logger.info("SLO alert config validation failed - returning elicitation")
                return validation_result

            # Build config object using common helper method
            config_object = self._build_alert_config_object(request_body)

            # Check if building failed (returns error dict)
            if isinstance(config_object, dict) and "error" in config_object:
                return config_object

            result = api_client.create_service_levels_alert_config_without_preload_content(
                service_levels_alert_config=config_object
            )

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            cleaned = self._clean_alert_config_data(result_dict)
            return {"success": True, "message": "Alert config created", "data": cleaned}

        except Exception as e:
            logger.error(f"Error in create_alert_config: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def update_alert_config(self,
        id: str,
        payload: Union[Dict[str, Any], str],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Update existing SLO alert configuration."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            # Parse payload using helper method
            request_body = self._parse_payload(payload)

            # Check if parsing failed (returns error dict)
            if isinstance(request_body, dict) and "error" in request_body:
                return request_body

            # Comprehensive validation with elicitation
            validation_result = self._validate_alert_config_payload(request_body)
            if validation_result:
                logger.info("SLO alert config validation failed for update - returning elicitation")
                validation_result["message"] = validation_result["message"].replace(
                    "To create an SLO alert configuration",
                    "To update the SLO alert configuration"
                )
                return validation_result

            # Build config object using common helper method
            config_object = self._build_alert_config_object(request_body)

            # Check if building failed (returns error dict)
            if isinstance(config_object, dict) and "error" in config_object:
                return config_object

            result = api_client.update_service_levels_alert_config_without_preload_content(
                id=id,
                service_levels_alert_config=config_object
            )

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            response_text = result.data.decode('utf-8')
            result_dict = json.loads(response_text)

            cleaned = self._clean_alert_config_data(result_dict)
            return {"success": True, "message": "Alert config updated", "data": cleaned}

        except Exception as e:
            logger.error(f"Error in update_alert_config: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def delete_alert_config(self,
        id: str,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Delete SLO alert configuration."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            api_client.delete_service_levels_alert_config(id=id)
            return {"success": True, "message": f"Alert config '{id}' deleted"}

        except Exception as e:
            logger.error(f"Error in delete_alert_config: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def disable_alert_config(self,
        id: str,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Disable SLO alert configuration."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            api_client.disable_service_levels_alert_config(id=id)
            return {"success": True, "message": f"Alert config '{id}' disabled"}

        except Exception as e:
            logger.error(f"Error in disable_alert_config: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def enable_alert_config(self,
        id: str,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Enable SLO alert configuration."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            api_client.enable_service_levels_alert_config(id=id)
            return {"success": True, "message": f"Alert config '{id}' enabled"}

        except Exception as e:
            logger.error(f"Error in enable_alert_config: {e}", exc_info=True)
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsAlertConfigurationApi)
    async def restore_alert_config(self,
        id: str,
        created: int,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Restore SLO alert configuration to a specific version by creation timestamp."""
        try:
            # Validate inputs
            validation_error = self._validate_id_parameter(id)
            if validation_error:
                return validation_error

            if not created:
                return {"error": "created is required"}
            if not isinstance(created, int):
                return {"error": "created must be an integer timestamp"}

            result = api_client.restore_service_levels_alert_config_without_preload_content(
                id=id,
                created=created
            )

            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details"
                return {"error": f"API error (status {result.status}): {error_text}"}

            # Restore returns 204 No Content on success, so no response body to parse
            return {"success": True, "message": f"Alert config '{id}' restored to version created at '{created}'"}

        except Exception as e:
            logger.error(f"Error in restore_alert_config: {e}", exc_info=True)
            return {"error": str(e)}
