"""
SLO Configuration MCP Tools Module

This module provides SLO (Service Level Objective) configuration tools for Instana.
"""

import ast
import json
import logging
from typing import Any, Dict, List, Optional, Union

# Import the necessary classes from the Instana SDK
try:
    from instana_client.api.service_levels_objective_slo_configurations_api import (
        ServiceLevelsObjectiveSLOConfigurationsApi,
    )
except ImportError:
    logging.getLogger(__name__).error("Instana SDK not available. Please install the Instana SDK.", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    sdk_call_with_keepalive,
    with_header_auth,
)

# Configure logger for this module
logger = logging.getLogger(__name__)

VALID_BOUNDARY_SCOPES = ("ALL", "INBOUND", "DEFAULT")
VALID_INDICATOR_TYPES = ("timeBased", "eventBased")
VALID_BLUEPRINTS = ("latency", "availability", "traffic", "saturation", "custom")
VALID_AGGREGATIONS = (
    "SUM", "MEAN", "MAX", "MIN",
    "P25", "P50", "P75", "P90", "P95", "P98", "P99", "P99_9", "P99_99",
    "DISTINCT_COUNT", "SUM_POSITIVE", "PER_SECOND", "INCREASE",
)
VALID_TIME_WINDOW_TYPES = ("rolling", "fixed")
VALID_DURATION_UNITS = ("millisecond", "second", "minute", "hour", "day", "week", "calendar_month")

class SLOConfigurationMCPTools(BaseInstanaClient):
    """Tools for SLO configuration in Instana MCP."""
    def __init__(self, read_token: str, base_url: str):
        """Initialize the SLO Configuration MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _build_missing_param(self, name: str, description: str, field_type: str, required: bool = True, **extra: Any) -> Dict[str, Any]:
        param = {
            "name": name,
            "description": description,
            "type": field_type,
            "required": required,
        }
        param.update(extra)
        return param

    def _validate_target(self, payload: Dict[str, Any], missing_params: List[Dict[str, Any]]) -> None:
        if "target" not in payload:
            missing_params.append(self._build_missing_param(
                "target",
                "SLO target value (percentage as decimal between 0.0 and 0.9999)",
                "float",
                example=0.95,
                validation="Must be between 0.0 and 0.9999 (e.g., 0.95 for 95%)",
            ))
            return

        target = payload["target"]
        if not isinstance(target, (int, float)) or not (0.0 <= float(target) <= 0.9999):
            missing_params.append(self._build_missing_param(
                "target",
                "SLO target value out of valid range",
                "float",
                example=0.95,
                validation="Must be between 0.0 and 0.9999 (e.g., 0.95 for 95%)",
                error=f"Invalid target value: {target}",
            ))

    def _validate_entity(self, payload: Dict[str, Any], missing_params: List[Dict[str, Any]]) -> None:
        if "entity" not in payload:
            missing_params.append(self._build_missing_param(
                "entity",
                "Entity definition (application, service, etc.)",
                "object",
                example={
                    "type": "application",
                    "applicationId": "app-123",
                    "boundaryScope": "ALL",
                    "includeInternal": False,
                    "includeSynthetic": False,
                },
                nested_fields={
                    "type": "Entity type — currently only 'application' is supported",
                    "applicationId": "Application ID from Instana",
                    "boundaryScope": f"Scope: one of {VALID_BOUNDARY_SCOPES}",
                    "includeInternal": "Whether to include internal calls (boolean)",
                    "includeSynthetic": "Whether to include synthetic calls (boolean)",
                },
            ))
            return

        entity = payload["entity"]
        if not isinstance(entity, dict):
            return

        if "type" not in entity:
            missing_params.append(self._build_missing_param(
                "entity.type",
                "Type of entity for the SLO",
                "string",
                example="application",
                validation="Currently only 'application' is supported",
            ))
        if entity.get("type") != "application":
            return

        if "applicationId" not in entity:
            missing_params.append(self._build_missing_param(
                "entity.applicationId",
                "Application ID from Instana",
                "string",
                example="app-abc123",
            ))
        if "boundaryScope" not in entity:
            missing_params.append(self._build_missing_param(
                "entity.boundaryScope",
                "Boundary scope for the application",
                "string",
                example="ALL",
                validation=f"Must be one of: {', '.join(VALID_BOUNDARY_SCOPES)}",
            ))
        elif entity["boundaryScope"] not in VALID_BOUNDARY_SCOPES:
            missing_params.append(self._build_missing_param(
                "entity.boundaryScope",
                "Invalid boundary scope value",
                "string",
                example="ALL",
                validation=f"Must be one of: {', '.join(VALID_BOUNDARY_SCOPES)}",
                error=f"Invalid boundaryScope: {entity['boundaryScope']}",
            ))
        if "includeInternal" not in entity:
            entity["includeInternal"] = False
        if "includeSynthetic" not in entity:
            entity["includeSynthetic"] = False

    def _validate_indicator(self, payload: Dict[str, Any], missing_params: List[Dict[str, Any]]) -> None:
        if "indicator" not in payload:
            missing_params.append(self._build_missing_param(
                "indicator",
                "Service level indicator defining what to measure",
                "object",
                example={
                    "type": "timeBased",
                    "blueprint": "latency",
                    "threshold": 100,
                    "aggregation": "P90"
                },
                nested_fields={
                    "type": f"One of: {', '.join(VALID_INDICATOR_TYPES)}",
                    "blueprint": f"One of: {', '.join(VALID_BLUEPRINTS)}",
                    "threshold": "Threshold value (e.g., 100 for 100ms)",
                    "aggregation": f"Optional aggregation type; one of: {', '.join(VALID_AGGREGATIONS)}"
                },
            ))
            return

        indicator = payload["indicator"]
        if not isinstance(indicator, dict):
            return

        if "type" not in indicator:
            missing_params.append(self._build_missing_param(
                "indicator.type",
                "Indicator measurement type",
                "string",
                example="timeBased",
                validation=f"Must be one of: {', '.join(VALID_INDICATOR_TYPES)}",
            ))
        elif indicator["type"] not in VALID_INDICATOR_TYPES:
            missing_params.append(self._build_missing_param(
                "indicator.type",
                "Invalid indicator type",
                "string",
                example="timeBased",
                validation=f"Must be one of: {', '.join(VALID_INDICATOR_TYPES)}",
                error=f"Invalid indicator type: {indicator['type']}",
            ))
        if "blueprint" not in indicator:
            missing_params.append(self._build_missing_param(
                "indicator.blueprint",
                "Blueprint type for the indicator",
                "string",
                example="latency",
                validation=f"Must be one of: {', '.join(VALID_BLUEPRINTS)}",
            ))
        elif indicator["blueprint"] not in VALID_BLUEPRINTS:
            missing_params.append(self._build_missing_param(
                "indicator.blueprint",
                "Invalid indicator blueprint",
                "string",
                example="latency",
                validation=f"Must be one of: {', '.join(VALID_BLUEPRINTS)}",
                error=f"Invalid blueprint: {indicator['blueprint']}",
            ))
        if "aggregation" in indicator and indicator["aggregation"] not in VALID_AGGREGATIONS:
            missing_params.append(self._build_missing_param(
                "indicator.aggregation",
                "Invalid aggregation type",
                "string",
                required=False,
                example="P90",
                validation=f"Must be one of: {', '.join(VALID_AGGREGATIONS)}",
                error=f"Invalid aggregation: {indicator['aggregation']}",
            ))

    def _validate_time_window(self, payload: Dict[str, Any], missing_params: List[Dict[str, Any]]) -> None:
        if "timeWindow" not in payload:
            missing_params.append(self._build_missing_param(
                "timeWindow",
                "Time window for SLO evaluation",
                "object",
                example={
                    "type": "rolling",
                    "duration": 1,
                    "durationUnit": "week"
                },
                nested_fields={
                    "type": f"One of: {', '.join(VALID_TIME_WINDOW_TYPES)}",
                    "duration": "Duration value (e.g., 1, 7, 30)",
                    "durationUnit": f"One of: {', '.join(VALID_DURATION_UNITS)}"
                },
            ))
            return

        time_window = payload["timeWindow"]
        if not isinstance(time_window, dict):
            return

        if "type" not in time_window:
            missing_params.append(self._build_missing_param(
                "timeWindow.type",
                "Time window type",
                "string",
                example="rolling",
                validation=f"Must be one of: {', '.join(VALID_TIME_WINDOW_TYPES)}",
            ))
        elif time_window["type"] not in VALID_TIME_WINDOW_TYPES:
            missing_params.append(self._build_missing_param(
                "timeWindow.type",
                "Invalid time window type",
                "string",
                example="rolling",
                validation=f"Must be one of: {', '.join(VALID_TIME_WINDOW_TYPES)}",
                error=f"Invalid timeWindow type: {time_window['type']}",
            ))
        if "duration" not in time_window:
            missing_params.append(self._build_missing_param(
                "timeWindow.duration",
                "Duration value for the time window",
                "integer",
                example=1,
            ))
        elif not isinstance(time_window["duration"], int) or time_window["duration"] <= 0:
            missing_params.append(self._build_missing_param(
                "timeWindow.duration",
                "Invalid duration value",
                "integer",
                example=1,
                validation="Must be a positive integer",
                error=f"Invalid duration: {time_window['duration']}",
            ))
        if "durationUnit" not in time_window:
            missing_params.append(self._build_missing_param(
                "timeWindow.durationUnit",
                "Unit for the duration",
                "string",
                example="week",
                validation=f"Must be one of: {', '.join(VALID_DURATION_UNITS)}",
            ))
        elif time_window["durationUnit"] not in VALID_DURATION_UNITS:
            missing_params.append(self._build_missing_param(
                "timeWindow.durationUnit",
                "Invalid duration unit",
                "string",
                example="week",
                validation=f"Must be one of: {', '.join(VALID_DURATION_UNITS)}",
                error=f"Invalid durationUnit: {time_window['durationUnit']}",
            ))

    def _append_message_section(self, message_parts: List[str], title: str, params: List[Dict[str, Any]]) -> None:
        if not params:
            return
        message_parts.append(title)
        for param in params:
            example_str = f" (e.g., {param['example']})" if "example" in param else ""
            validation_str = f" — {param['validation']}" if "validation" in param else ""
            error_str = f" [current error: {param['error']}]" if "error" in param else ""
            message_parts.append(f"- {param['name']}: {param['description']}{example_str}{validation_str}{error_str}")

    def _build_slo_config_elicitation(self, missing_params: List[Dict[str, Any]]) -> Dict[str, Any]:
        message_parts = ["To create an SLO configuration, I need the following information:\n"]
        self._append_message_section(message_parts, "\n**Top-level fields:**", [p for p in missing_params if "." not in p["name"]])
        self._append_message_section(message_parts, "\n**Entity fields:**", [p for p in missing_params if p["name"].startswith("entity.")])
        self._append_message_section(message_parts, "\n**Indicator fields:**", [p for p in missing_params if p["name"].startswith("indicator.")])
        self._append_message_section(message_parts, "\n**Time window fields:**", [p for p in missing_params if p["name"].startswith("timeWindow.")])
        return {
            "elicitation_needed": True,
            "message": "\n".join(message_parts),
            "missing_parameters": [p["name"] for p in missing_params],
            "parameter_details": missing_params,
            "user_prompt": "Please provide all the required fields to create the SLO configuration."
        }

    def _validate_slo_config_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate SLO configuration payload and return elicitation if fields are missing or invalid.

        Validates all required fields and their allowed values before the API is called so that
        a single consolidated response is returned to the LLM for correction instead of relying
        on the API to reject individual bad values one at a time.

        Args:
            payload: The SLO configuration payload to validate

        Returns:
            None if validation passes, elicitation dict if fields are missing or invalid
        """
        missing_params = []

        if "name" not in payload:
            missing_params.append(self._build_missing_param(
                "name",
                "Name of the SLO configuration",
                "string",
                example="API Response Time SLO",
            ))
        if "tags" not in payload:
            missing_params.append(self._build_missing_param(
                "tags",
                "List of tags for categorizing the SLO",
                "array of strings",
                example=["api", "production", "critical"],
            ))

        self._validate_target(payload, missing_params)
        self._validate_entity(payload, missing_params)
        self._validate_indicator(payload, missing_params)
        self._validate_time_window(payload, missing_params)

        if missing_params:
            return self._build_slo_config_elicitation(missing_params)

        return None

    def _clean_slo_config_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean SLO config data by removing unnecessary fields for LLM consumption.

        Keeps only user-relevant fields:
        - id, name, tags (core identification)
        - entity, indicator, target, timeWindow (SLO definition)

        Removes internal/technical fields:
        - createdDate, lastUpdated (timestamps)
        - rbacTags (internal RBAC details)

        Args:
            config: Raw SLO config dictionary from API

        Returns:
            Cleaned SLO config dictionary optimized for LLM consumption
        """
        cleaned = {
            "id": config.get("id"),
            "name": config.get("name"),
            "tags": config.get("tags", []),
            "target": config.get("target"),
            "entity": config.get("entity"),
            "indicator": config.get("indicator"),
            "timeWindow": config.get("timeWindow")
        }
        return cleaned

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def get_all_slo_configs(self,
        filters: Optional[Dict[str, Any]] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all SLO configurations with optional filtering and pagination.

        Args:
            filters: Dictionary containing all filter/pagination parameters:
                - page_size: Number of items per page
                - page: Page number (1-based)
                - order_by: Field to order by
                - order_direction: Order direction ('asc' or 'desc')
                - query: Search query string
                - tag: Filter by tags
                - entity_type: Filter by entity types
                - infra_entity_types: Filter by infrastructure entity types
                - kubernetes_cluster_uuid: Filter by Kubernetes cluster UUID
                - blueprint: Filter by blueprint
                - slo_ids: Filter by specific SLO IDs
                - slo_status: Filter by SLO status
                - entity_ids: Filter by entity IDs
                - grouped: Group results
                - refresh: Force refresh of data
                - rbac_tags: Filter by RBAC tags
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing paginated SLO configs with metadata
        """
        try:
            logger.debug("get_all_slo_configs called")
            filters = filters or {}

            # Call the API method
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_all_slo_configs_without_preload_content, page_size=filters.get("page_size"), page=filters.get("page"), order_by=filters.get("order_by"), order_direction=filters.get("order_direction"), query=filters.get("query"), tag=filters.get("tag"), entity_type=filters.get("entity_type"), infra_entity_types=filters.get("infra_entity_types"), kubernetes_cluster_uuid=filters.get("kubernetes_cluster_uuid"), blueprint=filters.get("blueprint"), slo_ids=filters.get("slo_ids"), slo_status=filters.get("slo_status"), entity_ids=filters.get("entity_ids"), grouped=filters.get("grouped"), refresh=filters.get("refresh"), rbac_tags=filters.get("rbac_tags")), ctx=ctx, operation_name="get_all_slo_configs", resource_type=resource_type, tool_name=tool_name)

            # Parse the JSON response manually
            try:
                response_text = result.data.decode('utf-8')
                logger.debug(f"Raw response: {response_text}")
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved SLO configs data")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse  response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            # Clean the items if present
            if isinstance(result_dict, dict) and 'items' in result_dict:
                cleaned_items = [self._clean_slo_config_data(item) for item in result_dict["items"]]
                logger.debug(f"Cleaned {len(cleaned_items)} SLO configs")
                return {
                    "success": True,
                    "items": cleaned_items,
                    "page": result_dict.get("page"),
                    "pageSize": result_dict.get("pageSize"),
                    "totalHits": result_dict.get("totalHits")
                }
            else:
                return result_dict
        except Exception as e:
            logger.error(f"Error retrieving SLO configs: {e}")
            return {"error": f"Failed to get SLO configs: {e!s}"}

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def get_slo_config_by_id(self,
        id: str,
        refresh: Optional[bool] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific SLO configuration by ID.

        Args:
            id: SLO configuration ID (required)
            refresh: Force refresh of data
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing the SLO configuration details
        """
        try:
            if not id:
                return {"error": "id is required"}

            logger.debug(f"get_slo_config_by_id called with id: {id}")

            # Call the API method
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_slo_config_by_id_without_preload_content, id=id, refresh=refresh), ctx=ctx, operation_name="get_slo_config_by_id", resource_type=resource_type, tool_name=tool_name)

            # Parse the JSON response manually.
            try:
                response_text = result.data.decode('utf-8')
                logger.debug(f"Raw response: {response_text}")
                result_dict = json.loads(response_text)
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            # Clean the config data
            cleaned_config = self._clean_slo_config_data(result_dict)
            logger.debug("Cleaned SLO config data")
            return cleaned_config
        except Exception as e:
            logger.error(f"Error in get_slo_config_by_id: {e!s}")
            return {"error": str(e)}

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def create_slo_config(self,
                                payload: Union[Dict[str, Any], str],
                                ctx=None,
                                api_client=None,
                                resource_type: Optional[str] = None,
                                tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new SLO configuration.

        Args:
            payload: SLO config payload (dict or JSON string) containing:
                - name: Name of the SLO config (required)
                - entity: Entity definition (required)
                - indicator: Service level indicator (required)
                - target: Target value (0.0-0.9999) (required)
                - timeWindow: Time window definition (required)
                - tags: List of tags (required)
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing the created SLO configuration
        """
        try:
            if not payload:
                return {"error": "payload is required"}

            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    parsed_payload = json.loads(payload)
                    logger.debug("Successfully parsed payload as JSON")
                    request_body = parsed_payload
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON parsing failed: {e}, trying with quotes replaced")
                    fixed_payload = payload.replace("'", "\"")
                    try:
                        parsed_payload = json.loads(fixed_payload)
                        logger.debug("Successfully parsed fixed JSON")
                        request_body = parsed_payload
                    except json.JSONDecodeError:
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
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Comprehensive validation with elicitation
            validation_result = self._validate_slo_config_payload(request_body)
            if validation_result:
                logger.info("SLO config validation failed - returning elicitation")
                return validation_result

            # Import the required model classes
            try:
                from instana_client.models.application_slo_entity import (
                    ApplicationSloEntity,
                )
                from instana_client.models.service_level_indicator import (
                    ServiceLevelIndicator,
                )
                from instana_client.models.slo_config_with_rbac_tag import (
                    SLOConfigWithRBACTag,
                )
                from instana_client.models.time_window import TimeWindow
                logger.debug("Successfully imported model classes")
            except ImportError as e:
                logger.debug(f"Error importing model classes: {e}")
                return {"error": f"Failed to import model classes: {e!s}"}

            # Create the nested objects properly
            try:
                logger.debug(f"Creating SLO config with params: {request_body}")

                # Create entity object based on type
                entity_data = request_body.get("entity", {})
                entity_type = entity_data.get("type", "").lower()

                if entity_type == "application":
                    entity_object = ApplicationSloEntity(**entity_data)
                    logger.debug(f"Created ApplicationSloEntity: {entity_object}")
                else:
                    return {"error": f"Unsupported entity type: {entity_type}. Only 'application' is currently supported."}

                # Create indicator object
                indicator_data = request_body.get("indicator", {})
                indicator_object = ServiceLevelIndicator(**indicator_data)
                logger.debug(f"Created ServiceLevelIndicator: {indicator_object}")

                # Create timeWindow object
                time_window_data = request_body.get("timeWindow", {})
                time_window_object = TimeWindow(**time_window_data)
                logger.debug(f"Created TimeWindow: {time_window_object}")

                # Validate required fields have values
                name = request_body.get("name")
                target = request_body.get("target")
                if not name or target is None:
                    return {"error": "name and target are required fields"}

                # Create the main config object with properly constructed nested objects
                config_object = SLOConfigWithRBACTag(
                    name=name,
                    entity=entity_object,
                    indicator=indicator_object,
                    target=target,
                    timeWindow=time_window_object,
                    tags=request_body.get("tags", [])
                )
                logger.debug("Successfully created SLOConfigWithRBACTag object")
            except Exception as e:
                logger.error(f"Error creating config object: {e}", exc_info=True)
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the API method
            logger.debug("Calling create_slo_config_without_preload_content")
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.create_slo_config_without_preload_content, slo_config_with_rbac_tag=config_object), ctx=ctx, operation_name="create_slo_config", resource_type=resource_type, tool_name=tool_name)

            # Check HTTP status code
            logger.debug(f"API response status: {result.status}")

            # Handle non-success status codes
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details provided"
                logger.error(f"API returned error status {result.status}: {error_text}")
                return {
                    "error": f"API error (status {result.status}): {error_text}",
                    "status_code": result.status
                }

            # Parse the JSON response manually
            try:
                response_text = result.data.decode('utf-8')
                logger.debug(f"Response text: {response_text[:200]}...")  # Log first 200 chars

                if not response_text or response_text.strip() == "":
                    logger.warning("Empty response from API")
                    return {
                        "success": True,
                        "message": "SLO config created successfully (empty response)",
                        "status_code": result.status
                    }

                result_dict = json.loads(response_text)
                logger.debug("Successfully parsed JSON response")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(f"{error_message}. Response text: {response_text if 'response_text' in locals() else 'N/A'}")
                return {
                    "error": error_message,
                    "raw_response": response_text if 'response_text' in locals() else None,
                    "status_code": result.status
                }

            # Clean the config data
            cleaned_config = self._clean_slo_config_data(result_dict)
            logger.debug("Cleaned created SLO config data")
            return {
                "success": True,
                "message": "SLO config created successfully",
                "data": cleaned_config,
                "status_code": result.status
            }

        except Exception as e:
            logger.error(f"Error in create_slo_config: {e}")
            return {"error": f"Failed to create SLO config: {e!s}"}

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def update_slo_config(self,
                                id: str,
                                payload: Union[Dict[str, Any], str],
                                ctx=None,
                                api_client=None,
                                resource_type: Optional[str] = None,
                                tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing SLO configuration.

        Args:
            id: SLO configuration ID (required)
            payload: SLO config payload (dict or JSON string) with fields to update
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing the updated SLO configuration
        """
        try:
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
                        fixed_payload = payload.replace("'", "\"")
                        try:
                            parsed_payload = json.loads(fixed_payload)
                            logger.debug("Successfully parsed fixed JSON")
                            request_body = parsed_payload
                        except json.JSONDecodeError:
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
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the required model classes
            try:
                from instana_client.models.application_slo_entity import (
                    ApplicationSloEntity,
                )
                from instana_client.models.service_level_indicator import (
                    ServiceLevelIndicator,
                )
                from instana_client.models.slo_config_with_rbac_tag import (
                    SLOConfigWithRBACTag,
                )
                from instana_client.models.time_window import TimeWindow
                logger.debug("Successfully imported model classes")
            except ImportError as e:
                logger.debug(f"Error importing model classes: {e}")
                return {"error": f"Failed to import model classes: {e!s}"}

            # Create the nested objects properly
            try:
                logger.debug(f"Updating SLO config with params: {request_body}")

                # Comprehensive validation with elicitation
                validation_result = self._validate_slo_config_payload(request_body)
                if validation_result:
                    logger.info("SLO config validation failed for update - returning elicitation")
                    validation_result["message"] = validation_result["message"].replace(
                        "To create an SLO configuration",
                        "To update the SLO configuration"
                    )
                    return validation_result

                # Create entity object based on type
                entity_data = request_body.get("entity", {})
                entity_type = entity_data.get("type", "").lower()

                if entity_type == "application":
                    entity_object = ApplicationSloEntity(**entity_data)
                    logger.debug(f"Created ApplicationSloEntity: {entity_object}")
                else:
                    return {"error": f"Unsupported entity type: {entity_type}. Only 'application' is currently supported."}

                # Create indicator object
                indicator_data = request_body.get("indicator", {})
                indicator_object = ServiceLevelIndicator(**indicator_data)
                logger.debug(f"Created ServiceLevelIndicator: {indicator_object}")

                # Create timeWindow object
                time_window_data = request_body.get("timeWindow", {})
                time_window_object = TimeWindow(**time_window_data)
                logger.debug(f"Created TimeWindow: {time_window_object}")

                # Validate required fields have values
                name = request_body.get("name")
                target = request_body.get("target")
                if not name or target is None:
                    return {"error": "name and target are required fields"}

                # Create the main config object with properly constructed nested objects
                config_object = SLOConfigWithRBACTag(
                    name=name,
                    entity=entity_object,
                    indicator=indicator_object,
                    target=target,
                    timeWindow=time_window_object,
                    tags=request_body.get("tags", [])
                )
                logger.debug("Successfully created SLOConfigWithRBACTag object for update")
            except Exception as e:
                logger.error(f"Error creating config object: {e}", exc_info=True)
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the API method
            logger.debug(f"Calling update_slo_config_without_preload_content with id: {id}")
            await sdk_call_with_keepalive(call_sdk_fn(api_client.update_slo_config_without_preload_content, id=id, slo_config_with_rbac_tag=config_object), ctx=ctx, operation_name="update_slo_config", resource_type=resource_type, tool_name=tool_name)

            # The update endpoint returns 204 No Content or a sparse body — re-fetch
            # the full record so the caller always gets complete, non-null data back.
            logger.debug("Update succeeded; re-fetching SLO config by id to return full record")
            return await self.get_slo_config_by_id(
                id=id, ctx=ctx, resource_type=resource_type, tool_name=tool_name
            )

        except Exception as e:
            logger.error(f"Error in update_slo_config: {e}")
            return {"error": f"Failed to update SLO config: {e!s}"}

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def delete_slo_config(self,
                                id: str,
                                ctx=None,
                                api_client=None,
                                resource_type: Optional[str] = None,
                                tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete an SLO configuration.

        Args:
            id: SLO configuration ID (required)
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing success/error message
        """
        try:
            if not id:
                return {"error": "id is required"}

            logger.debug(f"delete_slo_config called with id: {id}")

            # Call the API method
            await sdk_call_with_keepalive(call_sdk_fn(api_client.delete_slo_config, id=id), ctx=ctx, operation_name="delete_slo_config", resource_type=resource_type, tool_name=tool_name)

            logger.debug("Successfully deleted SLO config")
            return {
                "success": True,
                "message": f"SLO config {id} deleted successfully"
            }

        except Exception as e:
            logger.error(f"Error in delete_slo_config: {e}")
            return {"error": f"Failed to delete SLO config: {e!s}"}

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def get_all_slo_config_tags(self,
                                  query: Optional[str] = None,
                                  tag: Optional[List[str]] = None,
                                  entity_type: Optional[str] = None,
                                  ctx=None,
                                  api_client=None,
                                  resource_type: Optional[str] = None,
                                  tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all available tags for SLO configurations with optional filtering.

        Args:
            query: Search query string to filter tags
            tag: Filter by specific tags
            entity_type: Filter by entity type (e.g., "APPLICATION", "SERVICE")
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing list of available tags
        """
        try:
            logger.debug(f"get_all_slo_config_tags called with query={query}, tag={tag}, entity_type={entity_type}")

            # Call the API method
            result = await sdk_call_with_keepalive(call_sdk_fn(api_client.get_all_slo_config_tags_without_preload_content, query=query, tag=tag, entity_type=entity_type), ctx=ctx, operation_name="get_all_slo_config_tags", resource_type=resource_type, tool_name=tool_name)

            try:
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved SLO config tags")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            return {
                "success": True,
                "tags": result_dict if isinstance(result_dict, list) else result_dict.get("tags", []),
                "count": len(result_dict) if isinstance(result_dict, list) else len(result_dict.get("tags", []))
            }

        except Exception as e:
            logger.error(f"Error in get_all_slo_config_tags: {e}")
            return {"error": f"Failed to get SLO config tags: {e!s}"}
