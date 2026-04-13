"""
SLO Configuration MCP Tools Module

This module provides SLO (Service Level Objective) configuration tools for Instana.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context

# Import the necessary classes from the Instana SDK
try:
    from instana_client.api.service_levels_objective_slo_configurations_api import (
        ServiceLevelsObjectiveSLOConfigurationsApi,
    )
except ImportError:
    logging.getLogger(__name__).error("Instana SDK not available. Please install the Instana SDK.", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class SLOConfigurationMCPTools(BaseInstanaClient):
    """Tools for SLO configuration in Instana MCP."""
    def __init__(self, read_token: str, base_url: str):
        """Initialize the SLO Configuration MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _validate_slo_config_payload(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate SLO configuration payload and return elicitation if fields are missing.

        Args:
            payload: The SLO configuration payload to validate

        Returns:
            None if validation passes, elicitation dict if fields are missing
        """
        missing_params = []

        # Check top-level required fields
        if "name" not in payload:
            missing_params.append({
                "name": "name",
                "description": "Name of the SLO configuration",
                "type": "string",
                "required": True,
                "example": "API Response Time SLO"
            })

        if "tags" not in payload:
            missing_params.append({
                "name": "tags",
                "description": "List of tags for categorizing the SLO",
                "type": "array of strings",
                "required": True,
                "example": ["api", "production", "critical"]
            })

        if "target" not in payload:
            missing_params.append({
                "name": "target",
                "description": "SLO target value (percentage as decimal between 0.0 and 0.9999)",
                "type": "float",
                "required": True,
                "example": 0.95,
                "validation": "Must be between 0.0 and 0.9999 (e.g., 0.95 for 95%)"
            })

        # Validate entity
        if "entity" not in payload:
            missing_params.append({
                "name": "entity",
                "description": "Entity definition (application, service, etc.)",
                "type": "object",
                "required": True,
                "example": {
                    "type": "application",
                    "applicationId": "app-123",
                    "boundaryScope": "ALL"
                },
                "nested_fields": {
                    "type": "Entity type (e.g., 'application')",
                    "applicationId": "Application ID from Instana",
                    "boundaryScope": "Scope: 'ALL' or 'INBOUND'"
                }
            })
        else:
            entity = payload["entity"]
            if isinstance(entity, dict):
                if "type" not in entity:
                    missing_params.append({
                        "name": "entity.type",
                        "description": "Type of entity for the SLO",
                        "type": "string",
                        "required": True,
                        "example": "application"
                    })
                if entity.get("type") == "application":
                    if "applicationId" not in entity:
                        missing_params.append({
                            "name": "entity.applicationId",
                            "description": "Application ID from Instana",
                            "type": "string",
                            "required": True,
                            "example": "app-abc123"
                        })
                    if "boundaryScope" not in entity:
                        missing_params.append({
                            "name": "entity.boundaryScope",
                            "description": "Boundary scope for the application",
                            "type": "string",
                            "required": True,
                            "example": "ALL",
                            "validation": "Must be 'ALL' or 'INBOUND'"
                        })

        # Validate indicator
        if "indicator" not in payload:
            missing_params.append({
                "name": "indicator",
                "description": "Service level indicator defining what to measure",
                "type": "object",
                "required": True,
                "example": {
                    "type": "timeBased",
                    "blueprint": "latency",
                    "threshold": 100,
                    "aggregation": "P90"
                },
                "nested_fields": {
                    "type": "'timeBased' or 'eventBased'",
                    "blueprint": "'latency', 'availability', 'traffic', 'saturation', or 'custom'",
                    "threshold": "Threshold value (e.g., 100 for 100ms)",
                    "aggregation": "Aggregation type (e.g., 'P90', 'P95', 'MEAN')"
                }
            })
        else:
            indicator = payload["indicator"]
            if isinstance(indicator, dict):
                if "type" not in indicator:
                    missing_params.append({
                        "name": "indicator.type",
                        "description": "Indicator measurement type",
                        "type": "string",
                        "required": True,
                        "example": "timeBased",
                        "validation": "Must be 'timeBased' or 'eventBased'"
                    })
                if "blueprint" not in indicator:
                    missing_params.append({
                        "name": "indicator.blueprint",
                        "description": "Blueprint type for the indicator",
                        "type": "string",
                        "required": True,
                        "example": "latency",
                        "validation": "Must be 'latency', 'availability', 'traffic', 'saturation', or 'custom'"
                    })

        # Validate timeWindow
        if "timeWindow" not in payload:
            missing_params.append({
                "name": "timeWindow",
                "description": "Time window for SLO evaluation",
                "type": "object",
                "required": True,
                "example": {
                    "type": "rolling",
                    "duration": 1,
                    "durationUnit": "week"
                },
                "nested_fields": {
                    "type": "'rolling' or 'fixed'",
                    "duration": "Duration value (e.g., 1, 7, 30)",
                    "durationUnit": "'minute', 'hour', 'day', 'week', or 'month'"
                }
            })
        else:
            time_window = payload["timeWindow"]
            if isinstance(time_window, dict):
                if "type" not in time_window:
                    missing_params.append({
                        "name": "timeWindow.type",
                        "description": "Time window type",
                        "type": "string",
                        "required": True,
                        "example": "rolling",
                        "validation": "Must be 'rolling' or 'fixed'"
                    })
                if "duration" not in time_window:
                    missing_params.append({
                        "name": "timeWindow.duration",
                        "description": "Duration value for the time window",
                        "type": "integer",
                        "required": True,
                        "example": 1
                    })
                if "durationUnit" not in time_window:
                    missing_params.append({
                        "name": "timeWindow.durationUnit",
                        "description": "Unit for the duration",
                        "type": "string",
                        "required": True,
                        "example": "week",
                        "validation": "Must be 'minute', 'hour', 'day', 'week', or 'month'"
                    })

        # If any fields are missing, return elicitation
        if missing_params:
            # Group parameters by category
            top_level = [p for p in missing_params if "." not in p["name"]]
            entity_fields = [p for p in missing_params if p["name"].startswith("entity.")]
            indicator_fields = [p for p in missing_params if p["name"].startswith("indicator.")]
            time_window_fields = [p for p in missing_params if p["name"].startswith("timeWindow.")]

            message_parts = ["To create an SLO configuration, I need the following information:\n"]

            if top_level:
                message_parts.append("\n**Top-level fields:**")
                for param in top_level:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}")

            if entity_fields:
                message_parts.append("\n**Entity fields:**")
                for param in entity_fields:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}")

            if indicator_fields:
                message_parts.append("\n**Indicator fields:**")
                for param in indicator_fields:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}")

            if time_window_fields:
                message_parts.append("\n**Time window fields:**")
                for param in time_window_fields:
                    example_str = f" (e.g., {param['example']})" if "example" in param else ""
                    message_parts.append(f"- {param['name']}: {param['description']}{example_str}")

            return {
                "elicitation_needed": True,
                "message": "\n".join(message_parts),
                "missing_parameters": [p["name"] for p in missing_params],
                "parameter_details": missing_params,
                "user_prompt": "Please provide all the required fields to create the SLO configuration."
            }

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
        page_size: Optional[int] = None,
        page: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        query: Optional[str] = None,
        tag: Optional[List[str]] = None,
        entity_type: Optional[List[str]] = None,
        infra_entity_types: Optional[List[str]] = None,
        kubernetes_cluster_uuid: Optional[str] = None,
        blueprint: Optional[List[str]] = None,
        slo_ids: Optional[List[str]] = None,
        slo_status: Optional[str] = None,
        entity_ids: Optional[List[str]] = None,
        grouped: Optional[bool] = None,
        refresh: Optional[bool] = None,
        rbac_tags: Optional[List[str]] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Get all SLO configurations with optional filtering and pagination.

        Args:
            page_size: Number of items per page
            page: Page number (1-based)
            order_by: Field to order by
            order_direction: Order direction ('asc' or 'desc')
            query: Search query string
            tag: Filter by tags
            entity_type: Filter by entity types
            infra_entity_types: Filter by infrastructure entity types
            kubernetes_cluster_uuid: Filter by Kubernetes cluster UUID
            blueprint: Filter by blueprint
            slo_ids: Filter by specific SLO IDs
            slo_status: Filter by SLO status
            entity_ids: Filter by entity IDs
            grouped: Group results
            refresh: Force refresh of data
            rbac_tags: Filter by RBAC tags
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing paginated SLO configs with metadata
        """
        try:
            logger.debug("get_all_slo_configs called")

            # Call the API method
            result = api_client.get_all_slo_configs_without_preload_content(
                page_size=page_size,
                page=page,
                order_by=order_by,
                order_direction=order_direction,
                query=query,
                tag=tag,
                entity_type=entity_type,
                infra_entity_types=infra_entity_types,
                kubernetes_cluster_uuid=kubernetes_cluster_uuid,
                blueprint=blueprint,
                slo_ids=slo_ids,
                slo_status=slo_status,
                entity_ids=entity_ids,
                grouped=grouped,
                refresh=refresh,
                rbac_tags=rbac_tags
            )

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
        ctx = None,
        api_client = None
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
            result = api_client.get_slo_config_by_id_without_preload_content(
                id=id,
                refresh=refresh
            )

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
                                ctx: Optional[Context] = None,
                                api_client: Any = None) -> Dict[str, Any]:
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
                        import ast
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
            result = api_client.create_slo_config_without_preload_content(
                slo_config_with_rbac_tag=config_object
            )

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
                                ctx: Optional[Context] = None,
                                api_client: Any = None) -> Dict[str, Any]:
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
                            import ast
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
            result = api_client.update_slo_config_without_preload_content(
                id=id,
                slo_config_with_rbac_tag=config_object
            )

            # Parse the JSON response manually
            try:
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully updated SLO config")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            # Clean the config data
            cleaned_config = self._clean_slo_config_data(result_dict)
            logger.debug("Cleaned updated SLO config data")
            return {
                "success": True,
                "message": "SLO config updated successfully",
                "data": cleaned_config
            }

        except Exception as e:
            logger.error(f"Error in update_slo_config: {e}")
            return {"error": f"Failed to update SLO config: {e!s}"}

    @with_header_auth(ServiceLevelsObjectiveSLOConfigurationsApi)
    async def delete_slo_config(self,
                                id: str,
                                ctx: Optional[Context] = None,
                                api_client: Any = None) -> Dict[str, Any]:
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
            api_client.delete_slo_config(id=id)

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
                                  ctx: Optional[Context] = None,
                                  api_client: Any = None) -> Dict[str, Any]:
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
            result = api_client.get_all_slo_config_tags_without_preload_content(
                query=query,
                tag=tag,
                entity_type=entity_type
            )

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
