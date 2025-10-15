"""
Application Analyze MCP Tools Module

This module provides application analyze tool functionality for Instana monitoring.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.application_analyze_api import ApplicationAnalyzeApi
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration
    from instana_client.models.get_call_groups import GetCallGroups
    from instana_client.models.get_traces import GetTraces

except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import application analyze API", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationAnalyzeMCPTools(BaseInstanaClient):
    """Tools for application analyze in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Analyze MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

        try:

            # Configure the API client with the correct base URL and authentication
            configuration = Configuration()
            configuration.host = base_url
            configuration.api_key['ApiKeyAuth'] = read_token
            configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

            # Create an API client with this configuration
            api_client = ApiClient(configuration=configuration)

            # Initialize the Instana SDK's ApplicationAnalyzeApi with our configured client
            self.analyze_api = ApplicationAnalyzeApi(api_client=api_client)
        except Exception as e:
            logger.error(f"Error initializing ApplicationAnalyzeApi: {e}", exc_info=True)
            raise

    @register_as_tool(
        title="Get Call Details",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationAnalyzeApi)
    async def get_call_details(
        self,
        trace_id: str,
        call_id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get details of a specific call in a trace.
        This tool is to retrieve a vast information about a call present in a trace.

        Args:
            trace_id (str): The ID of the trace.
            call_id (str): The ID of the call.
            ctx: Optional context for the request.

        Returns:
            Dict[str, Any]: Details of the specified call.
        """
        try:
            if not trace_id or not call_id:
                logger.warning("Both trace_id and call_id must be provided")
                return {"error": "Both trace_id and call_id must be provided"}

            logger.debug(f"Fetching call details for trace_id={trace_id}, call_id={call_id}")
            result = api_client.get_call_details(
                trace_id=trace_id,
                call_id=call_id
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_call_details: {result_dict}")
            # Ensure we return a dictionary
            return dict(result_dict) if not isinstance(result_dict, dict) else result_dict

        except Exception as e:
            logger.error(f"Error getting call details: {e}", exc_info=True)
            return {"error": f"Failed to get call details: {e!s}"}

    @register_as_tool(
        title="Get Trace Details",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationAnalyzeApi)
    async def get_trace_details(
        self,
        id: str,
        retrievalSize: Optional[int] = None,
        offset: Optional[int] = None,
        ingestionTime: Optional[int] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get details of a specific trace.
        This tool is to retrive comprehensive details of a particular trace.
        Args:
            id (str): The ID of the trace.
            retrievalSize (Optional[int]):The number of records to retrieve in a single request.
                                        Minimum value is 1 and maximum value is 10000.
            offset (Optional[int]): The number of records to be skipped from the ingestionTime.
            ingestionTime (Optional[int]): The timestamp indicating the starting point from which data was ingested.
            ctx: Optional context for the request.
        Returns:
            Dict[str, Any]: Details of the specified trace.
        """

        try:
            if not id:
                logger.warning("Trace ID must be provided")
                return {"error": "Trace ID must be provided"}

            if offset is not None and ingestionTime is None:
                logger.warning("If offset is provided, ingestionTime must also be provided")
                return {"error": "If offset is provided, ingestionTime must also be provided"}

            if retrievalSize is not None and (retrievalSize < 1 or retrievalSize > 10000):
                logger.warning(f"retrievalSize must be between 1 and 10000, got: {retrievalSize}")
                return {"error": "retrievalSize must be between 1 and 10000"}

            logger.debug(f"Fetching trace details for id={id}")
            result = api_client.get_trace_download(
                id=id,
                retrieval_size=retrievalSize,
                offset=offset,
                ingestion_time=ingestionTime
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_trace_details: {result_dict}")
            # Ensure we return a dictionary
            return dict(result_dict) if not isinstance(result_dict, dict) else result_dict

        except Exception as e:
            logger.error(f"Error getting trace details: {e}", exc_info=True)
            return {"error": f"Failed to get trace details: {e!s}"}


    @register_as_tool(
        title="Get All Traces",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationAnalyzeApi)
    async def get_all_traces(
        self,
        payload: Optional[Union[Dict[str, Any], str]]=None,
        api_client = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Get all traces.
        This tool endpoint retrieves the metrics for traces.

        Sample payload: {
        "includeInternal": false,
        "includeSynthetic": false,
        "pagination": {
            "retrievalSize": 1
        },
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
            {
                "type": "TAG_FILTER",
                "name": "endpoint.name",
                "operator": "EQUALS",
                "entity": "DESTINATION",
                "value": "GET /"
            },
            {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "EQUALS",
                "entity": "DESTINATION",
                "value": "groundskeeper"
            }
            ]
        },
        "order": {
            "by": "traceLabel",
            "direction": "DESC"
        }
        }

        Returns:
            Dict[str, Any]: List of traces matching the criteria.
        """
        try:
            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    import json
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
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the GetTraces class
            try:
                from instana_client.models.get_traces import (
                    GetTraces,
                )
                from instana_client.models.group import Group
                logger.debug("Successfully imported GetTraces")
            except ImportError as e:
                logger.debug(f"Error importing GetTraces: {e}")
                return {"error": f"Failed to import GetTraces: {e!s}"}

            # Create an GetTraces object from the request body
            try:
                query_params = {}
                if request_body and "tag_filter_expression" in request_body:
                    query_params["tag_filter_expression"] = request_body["tag_filter_expression"]
                logger.debug(f"Creating get_traces with params: {query_params}")
                config_object = GetTraces(**query_params)
                logger.debug("Successfully got traces")
            except Exception as e:
                logger.debug(f"Error creating get_traces: {e}")
                return {"error": f"Failed to get tracest: {e!s}"}

            # Call the get_traces method from the SDK
            logger.debug("Calling get_traces with config object")
            result = api_client.get_traces(
                get_traces=config_object
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Get traces"
                }

            logger.debug(f"Result from get_traces: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_traces: {e}")
            return {"error": f"Failed to get traces: {e!s}"}

    @register_as_tool(
        title="Get Grouped Trace Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationAnalyzeApi)
    async def get_grouped_trace_metrics(
        self,
        payload: Optional[Union[Dict[str, Any], str]]=None,
        fill_time_series: Optional[bool] = None,
        api_client=None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        The API endpoint retrieves metrics for traces that are grouped in the endpoint or service name.
        This tool Get grouped trace metrics (by endpoint or service name).

        Args:
            fillTimeSeries (Optional[bool]): Whether to fill missing data points with zeroes.
            Sample Payload: {
            "group": {
                "groupbyTag": "trace.endpoint.name",
                "groupbyTagEntity": "NOT_APPLICABLE"
            },
            "metrics": [
                {
                "aggregation": "SUM",
                "metric": "latency"
                }
            ],
            "order": {
                "by": "latency",
                "direction": "ASC"
            },
            "pagination": {
                "retrievalSize": 20
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [
                {
                    "type": "TAG_FILTER",
                    "name": "call.type",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "DATABASE"
                },
                {
                    "type": "TAG_FILTER",
                    "name": "service.name",
                    "operator": "EQUALS",
                    "entity": "DESTINATION",
                    "value": "ratings"
                }
                ]
            }
            }
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: Grouped trace metrics result.
        """
        try:
            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    import json
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
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the GetTraceGroups class
            try:
                from instana_client.models.get_trace_groups import (
                    GetTraceGroups,
                )
                from instana_client.models.group import Group
                logger.debug("Successfully imported GetTraceGroups")
            except ImportError as e:
                logger.debug(f"Error importing GetTraceGroups: {e}")
                return {"error": f"Failed to import GetTraceGroups: {e!s}"}

            # Create an GetTraceGroups object from the request body
            try:
                query_params = {}
                if request_body and "group" in request_body:
                    query_params["group"] = request_body["group"]
                if request_body and "metrics" in request_body:
                    query_params["metrics"] = request_body["metrics"]
                if request_body and "tag_filter_expression" in request_body:
                    query_params["tag_filter_expression"] = request_body["tag_filter_expression"]
                logger.debug(f"Creating GetTraceGroups with params: {query_params}")
                config_object = GetTraceGroups(**query_params)
                logger.debug("Successfully created endpoint config object")
            except Exception as e:
                logger.debug(f"Error creating GetTraceGroups: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the create_endpoint_config method from the SDK
            logger.debug("Calling create_endpoint_config with config object")
            result = api_client.get_trace_groups(
                get_trace_groups=config_object
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Grouped trace metrics"
                }

            logger.debug(f"Result from get_grouped_trace_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_grouped_trace_metrics: {e}")
            return {"error": f"Failed to get grouped trace metrics: {e!s}"}

    @register_as_tool(
        title="Get Grouped Calls Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationAnalyzeApi)
    async def get_grouped_calls_metrics(
        self,
        fillTimeSeries: Optional[str] = None,
        payload: Optional[Union[Dict[str, Any], str]]=None,
        api_client = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Get grouped calls metrics.
        This endpoint retrieves the metrics for calls.

        Args:
            fillTimeSeries (Optional[bool]): Whether to fill missing data points with zeroes.
            Sample payload: {
            "group": {
                "groupbyTag": "service.name",
                "groupbyTagEntity": "DESTINATION"
            },
            "metrics": [
                {
                "aggregation": "SUM",
                "metric": "calls"
                },
                {
                "aggregation": "P75",
                "metric": "latency",
                "granularity": 360
                }
            ],
            "includeInternal": false,
            "includeSynthetic": false,
            "order": {
                "by": "calls",
                "direction": "DESC"
            },
            "pagination": {
                "retrievalSize": 20
            },
            "tagFilterExpression": {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": [
                {
                    "type": "TAG_FILTER",
                    "name": "call.type",
                    "operator": "EQUALS",
                    "entity": "NOT_APPLICABLE",
                    "value": "DATABASE"
                },
                {
                    "type": "TAG_FILTER",
                    "name": "service.name",
                    "operator": "EQUALS",
                    "entity": "DESTINATION",
                    "value": "ratings"
                }
                ]
            },
            "timeFrame": {
                "to": "1688366990000",
                "windowSize": "600000"
            }
            }
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: Grouped trace metrics result.
        """
        try:
            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    import json
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
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the GetCallGroups class
            try:
                from instana_client.models.get_call_groups import (
                    GetCallGroups,
                )
                from instana_client.models.group import Group
                logger.debug("Successfully imported GetCallGroups")
            except ImportError as e:
                logger.debug(f"Error importing GetCallGroups: {e}")
                return {"error": f"Failed to import GetCallGroups: {e!s}"}

            # Create an GetCallGroups object from the request body
            try:
                query_params = {}
                if request_body and "group" in request_body:
                    query_params["group"] = request_body["group"]
                if request_body and "metrics" in request_body:
                    query_params["metrics"] = request_body["metrics"]
                logger.debug(f"Creating GetCallGroups with params: {query_params}")
                config_object = GetCallGroups(**query_params)
                logger.debug("Successfully created endpoint config object")
            except Exception as e:
                logger.error(f"Error creating GetCallGroups: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the get_call_groups method from the SDK
            logger.debug("Calling get_call_groups with config object")
            result = api_client.get_call_group(
                get_call_groups=config_object
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Get Grouped call"
                }

            logger.debug(f"Result from get_call_group: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_call_group: {e}")
            return {"error": f"Failed to get grouped call: {e!s}"}


    @register_as_tool(
        title="Get Correlated Traces",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationAnalyzeApi)
    async def get_correlated_traces(
        self,
        correlation_id: str,
        api_client = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Resolve Trace IDs from Monitoring Beacons.
        Resolves backend trace IDs using correlation IDs from website and mobile app monitoring beacons.

        Args:
            correlation_id: Here, the `backendTraceId` is typically used which can be obtained from the `Get all beacons` API endpoint for website and mobile app monitoring. For XHR, fetch, or HTTP beacons, the `beaconId` retrieved from the same API endpoint can also serve as the `correlationId`.(required)
            ctx: Optional execution context.
        Returns:
            Dict[str, Any]: Grouped trace metrics result.
        """
        try:
            logger.debug("Calling backend correlation API")
            if not correlation_id:
                error_msg = "Correlation ID must be provided"
                logger.warning(error_msg)
                return {"error": error_msg}

            result = api_client.get_correlated_traces(
                correlation_id=correlation_id
            )

            result_dict = result.to_dict() if hasattr(result, 'to_dict') else result

            logger.debug(f"Result from get_correlated_traces: {result_dict}")
            # If result is a list, convert it to a dictionary
            if isinstance(result_dict, list):
                return {"traces": result_dict}
            # Otherwise ensure we return a dictionary
            return dict(result_dict) if not isinstance(result_dict, dict) else result_dict

        except Exception as e:
            logger.error(f"Error in get_correlated_traces: {e}", exc_info=True)
            return {"error": f"Failed to get correlated traces: {e!s}"}
