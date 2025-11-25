# """
# Entities Insight MCP Tools Module

# This module provides application entities insights tools for Instana monitoring.
# Merges functionality from application resources APIs into a single comprehensive tool.
# """
# import logging
# from datetime import datetime
# from typing import Any, Dict, List, Optional

# from mcp.types import ToolAnnotations

# from src.prompts import mcp
# from src.core.utils import BaseInstanaClient, register_as_tool

# # Configure logger for this module
# logger = logging.getLogger(__name__)


# class ApplicationEntitiesInsightMCPTools(BaseInstanaClient):
#     """Tools for application entities insights in Instana MCP."""

#     def __init__(self, read_token: str, base_url: str):
#         """Initialize the Application Entities Insight MCP tools client."""
#         super().__init__(read_token=read_token, base_url=base_url)

#     @register_as_tool(
#         title="Get Application Entities Insights",
#         annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
#     )
#     async def application_entities_insights(
#         self,
#         entity_type: str = "all",
#         name_filter: Optional[str] = None,
#         window_size: Optional[int] = None,
#         to_time: Optional[int] = None,
#         ctx=None,
#     ) -> Dict[str, Any]:
#         """
#         Get application entities insights from Instana based on the requested entity type.
        
#         This intelligent tool retrieves specific application-related entities based on your query:
#         - applications: List of Applications with their IDs
#         - application_services: Services within application perspectives with their IDs and technologies
#         - services: All services across the environment
#         - endpoints: Application endpoints with types and technologies
#         - all: Retrieve all entity types in a single call
        
#         Use this tool when you need to:
#         - Get application perspectives: entity_type="applications"
#         - List services in application perspectives: entity_type="application_services"
#         - View all services across environment: entity_type="services"
#         - Get endpoint information: entity_type="endpoints"
#         - Get comprehensive overview: entity_type="all"
        
#         For example:
#         - "Show me all applications" → entity_type="applications"
#         - "List services in application perspectives" → entity_type="application_services"
#         - "Get all services" → entity_type="services"
#         - "Show me endpoints" → entity_type="endpoints"
#         - "Give me complete application landscape" → entity_type="all"
        
#         Args:
#             entity_type: Type of entities to retrieve. Options: "applications", "application_services", "services", "endpoints", "all" (default: "all")
#             name_filter: Name to filter applications/services/endpoints (optional)
#             window_size: Size of time window in milliseconds (optional, default: 1 hour)
#             to_time: End timestamp in milliseconds (optional, default: now)
#             ctx: The MCP context (optional)
        
#         Returns:
#             Dictionary containing requested entity data with summary statistics
#         """
#         try:
#             logger.debug(f"application_entities_insights called with entity_type={entity_type}, name_filter={name_filter}")

#             # Validate entity_type
#             valid_types = ["applications", "application_services", "services", "endpoints", "all"]
#             if entity_type not in valid_types:
#                 return {
#                     "error": f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(valid_types)}"
#                 }

#             # Set default time range if not provided
#             if not to_time:
#                 to_time = int(datetime.now().timestamp() * 1000)

#             if not window_size:
#                 window_size = 60 * 60 * 1000  # Default to 1 hour

#             # Set internal parameters with default values
#             page = None
#             page_size = None
#             application_boundary_scope = "ALL"
#             include_snapshot_ids = False

#             result: Dict[str, Any] = {
#                 "summary": {
#                     "entity_type": entity_type,
#                     "time_range": {
#                         "window_size_ms": window_size,
#                         "to_time": to_time,
#                         "window_size_hours": window_size / (60 * 60 * 1000)
#                     },
#                     "filters": {
#                         "name_filter": name_filter
#                     }
#                 }
#             }

#             # Store apps_items for reuse in application_services
#             apps_items = []

#             # 1. Get Applications (Application Perspectives)
#             if entity_type in ["applications", "application_services", "all"]:
#                 try:
#                     # Build query parameters
#                     params = {
#                         "windowSize": window_size,
#                         "to": to_time,
#                         "applicationBoundaryScope": application_boundary_scope
#                     }
#                     if name_filter:
#                         params["nameFilter"] = name_filter
#                     if page is not None:
#                         params["page"] = page
#                     if page_size is not None:
#                         params["pageSize"] = page_size

#                     # Make direct API call
#                     apps_result = await self.make_request(
#                         endpoint="/api/application-monitoring/applications",
#                         params=params,
#                         method="GET"
#                     )

#                     if "error" in apps_result:
#                         result["applications_error"] = apps_result["error"]
#                     else:
#                         apps_items = apps_result.get('items', [])

#                         # Only populate applications result if explicitly requested
#                         if entity_type in ["applications", "all"]:
#                             applications = []
#                             for item in apps_items:
#                                 label = item.get('label', '')
#                                 app_id = item.get('id', '')
#                                 if label:
#                                     applications.append({
#                                         'id': app_id,
#                                         'label': label
#                                     })

#                             applications.sort(key=lambda x: x['label'])
#                             result["applications"] = {
#                                 "items": applications,
#                                 "total": len(applications),
#                                 "showing": min(15, len(applications))
#                             }
#                             result["summary"]["total_applications"] = len(applications)
#                             result["summary"]["showing_applications"] = len(applications[:15])

#                 except Exception as e:
#                     logger.error(f"Error getting applications: {e}", exc_info=True)
#                     result["applications_error"] = str(e)

#             # Store all_services_list for reuse in endpoints
#             all_services_list = []

#             # 2. Get Application Services (services within application perspectives)
#             if entity_type in ["application_services", "endpoints", "all"]:
#                 try:
#                     all_services = []
                    
#                     # If apps_items is empty but we need application_services, fetch applications
#                     if not apps_items:
#                         try:
#                             # Build query parameters
#                             params = {
#                                 "windowSize": window_size,
#                                 "to": to_time,
#                                 "applicationBoundaryScope": application_boundary_scope
#                             }
#                             if name_filter:
#                                 params["nameFilter"] = name_filter
#                             if page is not None:
#                                 params["page"] = page
#                             if page_size is not None:
#                                 params["pageSize"] = page_size

#                             # Make direct API call to get applications
#                             apps_result = await self.make_request(
#                                 endpoint="/api/application-monitoring/applications",
#                                 params=params,
#                                 method="GET"
#                             )

#                             if "error" not in apps_result:
#                                 apps_items = apps_result.get('items', [])
#                         except Exception as e:
#                             logger.error(f"Error fetching applications for services: {e}", exc_info=True)
                    
#                     # Use apps_items to fetch services
#                     if apps_items:
#                         # Iterate through each application and get its services
#                         for app in apps_items:
#                             app_id = app.get('id', '')
#                             app_label = app.get('label', '')
#                             if not app_id:
#                                 continue
                            
#                             # Build query parameters for services (without nameFilter for services endpoint)
#                             params = {
#                                 "windowSize": window_size,
#                                 "to": to_time,
#                                 "applicationBoundaryScope": application_boundary_scope,
#                                 "includeSnapshotIds": include_snapshot_ids
#                             }
#                             if page is not None:
#                                 params["page"] = page
#                             if page_size is not None:
#                                 params["pageSize"] = page_size

#                             # Make API call with actual app ID
#                             app_services_result = await self.make_request(
#                                 endpoint=f"/api/application-monitoring/applications;id={app_id}/services",
#                                 params=params,
#                                 method="GET"
#                             )

#                             if "error" not in app_services_result:
#                                 app_services_items = app_services_result.get('items', [])
                                
#                                 for item in app_services_items:
#                                     service_id = item.get('id', '')
#                                     label = item.get('label', '')
#                                     technologies = item.get('technologies', [])
#                                     types = item.get('types', [])
#                                     if label and service_id:
#                                         # Avoid duplicates
#                                         if not any(s['id'] == service_id for s in all_services):
#                                             service_data = {
#                                                 'id': service_id,
#                                                 'label': label,
#                                                 'technologies': technologies,
#                                                 'types': types,
#                                                 'application_id': app_id,
#                                                 'application_label': app_label
#                                             }
#                                             all_services.append(service_data)
#                                             all_services_list.append(service_data)

#                         all_services.sort(key=lambda x: x['label'])
                        
#                         # Only populate application_services result if explicitly requested
#                         if entity_type in ["application_services", "all"]:
#                             result["application_services"] = {
#                                 "services": all_services,
#                                 "total": len(all_services),
#                                 "showing": min(15, len(all_services))
#                             }
#                             result["summary"]["total_application_services"] = len(all_services)
#                             result["summary"]["showing_application_services"] = len(all_services[:15])
#                     else:
#                         if entity_type in ["application_services", "all"]:
#                             result["application_services"] = {
#                                 "services": [],
#                                 "total": 0,
#                                 "showing": 0
#                             }
#                             result["summary"]["total_application_services"] = 0
#                             result["summary"]["showing_application_services"] = 0
#                             if name_filter:
#                                 result["application_services_note"] = f"No applications found matching filter '{name_filter}'"
#                             else:
#                                 result["application_services_note"] = "No applications found"

#                 except Exception as e:
#                     logger.error(f"Error getting application services: {e}", exc_info=True)
#                     result["application_services_error"] = str(e)

#             # 3. Get All Services (across all environments)
#             if entity_type in ["services", "all"]:
#                 try:
#                     # Build query parameters
#                     params = {
#                         "windowSize": window_size,
#                         "to": to_time,
#                         "includeSnapshotIds": include_snapshot_ids
#                     }
#                     if name_filter:
#                         params["nameFilter"] = name_filter
#                     if page is not None:
#                         params["page"] = page
#                     if page_size is not None:
#                         params["pageSize"] = page_size

#                     # Make direct API call
#                     all_services_result = await self.make_request(
#                         endpoint="/api/application-monitoring/services",
#                         params=params,
#                         method="GET"
#                     )

#                     if "error" in all_services_result:
#                         result["services_error"] = all_services_result["error"]
#                     else:
#                         all_services_items = all_services_result.get('items', [])

#                         all_services = []
#                         for item in all_services_items:
#                             label = item.get('label', '')
#                             service_id = item.get('id', '')
#                             if label:
#                                 all_services.append({
#                                     'id': service_id,
#                                     'label': label
#                                 })

#                         all_services.sort(key=lambda x: x['label'])
#                         result["services"] = {
#                             "items": all_services,
#                             "total": len(all_services),
#                             "showing": min(10, len(all_services))
#                         }
#                         result["summary"]["total_services"] = len(all_services)
#                         result["summary"]["showing_services"] = len(all_services[:10])

#                 except Exception as e:
#                     logger.error(f"Error getting all services: {e}", exc_info=True)
#                     result["services_error"] = str(e)

#             # 4. Get Application Endpoints
#             # If name_filter is provided as application name: get services for that app, then query endpoints API with each service name
#             # If name_filter is provided but no apps found: treat it as service name filter
#             if entity_type in ["endpoints", "all"]:
#                 try:
#                     all_endpoints = []
                    
#                     # Case 1: name_filter provided and we have matching applications
#                     # Get services for the application, then query endpoints API with each service label as nameFilter
#                     if name_filter and apps_items:
#                         logger.debug(f"Fetching endpoints for application(s) matching '{name_filter}'")
                        
#                         # Track seen service and endpoint IDs to avoid duplicates
#                         seen_service_ids = set()
#                         seen_endpoint_ids = set()
                        
#                         # Iterate through each matching application
#                         for app in apps_items:
#                             app_id = app.get('id', '')
#                             app_label = app.get('label', '')
#                             if not app_id:
#                                 continue
                            
#                             # Get services for this application
#                             service_params = {
#                                 "windowSize": window_size,
#                                 "to": to_time,
#                                 "applicationBoundaryScope": application_boundary_scope,
#                                 "includeSnapshotIds": include_snapshot_ids
#                             }
#                             if page is not None:
#                                 service_params["page"] = page
#                             if page_size is not None:
#                                 service_params["pageSize"] = page_size
                            
#                             app_services_result = await self.make_request(
#                                 endpoint=f"/api/application-monitoring/applications;id={app_id}/services",
#                                 params=service_params,
#                                 method="GET"
#                             )
                            
#                             if "error" in app_services_result:
#                                 logger.warning(
#                                     f"Failed to retrieve services for application '{app_label}' ({app_id}): {app_services_result['error']}"
#                                 )
#                                 continue
                            
#                             app_services_items = app_services_result.get('items', [])
#                             logger.debug(f"Found {len(app_services_items)} services for application '{app_label}'")
                            
#                             # For each service, query endpoints API using service label as nameFilter
#                             for service in app_services_items:
#                                 service_id = service.get('id', '')
#                                 service_label = service.get('label', '')
                                
#                                 if not service_label or not service_id:
#                                     continue
                                
#                                 # Track this service (avoid duplicate processing)
#                                 if service_id in seen_service_ids:
#                                     continue
#                                 seen_service_ids.add(service_id)
                                
#                                 # Query endpoints API with service label as nameFilter
#                                 # Note: Don't include applicationBoundaryScope for endpoints query
#                                 # as it can filter out valid endpoints
#                                 endpoint_params = {
#                                     "windowSize": window_size,
#                                     "to": to_time,
#                                     "nameFilter": service_label  # Use service label as filter
#                                 }
#                                 if page is not None:
#                                     endpoint_params["page"] = page
#                                 if page_size is not None:
#                                     endpoint_params["pageSize"] = page_size
                                
#                                 logger.debug(
#                                     f"Querying endpoints API for service '{service_label}' with params: {endpoint_params}"
#                                 )
                                
#                                 endpoints_result = await self.make_request(
#                                     endpoint="/api/application-monitoring/applications/services/endpoints",
#                                     params=endpoint_params,
#                                     method="GET"
#                                 )
                                
#                                 if "error" in endpoints_result:
#                                     logger.warning(
#                                         f"Endpoints request failed for service '{service_label}' ({service_id}): {endpoints_result['error']}"
#                                     )
#                                     continue
                                
#                                 service_endpoints = endpoints_result.get('items', [])
#                                 logger.debug(
#                                     f"Service '{service_label}' returned {len(service_endpoints)} endpoint(s) from API"
#                                 )
                                
#                                 # Add each endpoint to the results
#                                 for endpoint in service_endpoints:
#                                     endpoint_id = endpoint.get('id', '')
#                                     endpoint_label = endpoint.get('label', '')
                                    
#                                     if not endpoint_id or not endpoint_label:
#                                         continue
                                    
#                                     # Avoid duplicate endpoints
#                                     if endpoint_id in seen_endpoint_ids:
#                                         continue
#                                     seen_endpoint_ids.add(endpoint_id)
                                    
#                                     endpoint_data = {
#                                         'id': endpoint_id,
#                                         'label': endpoint_label,
#                                         'type': endpoint.get('type', ''),
#                                         'technologies': endpoint.get('technologies', []),
#                                         'service_id': service_id,
#                                         'service_label': service_label,
#                                         'application_id': app_id,
#                                         'application_label': app_label
#                                     }
#                                     all_endpoints.append(endpoint_data)
                        
#                         logger.debug(f"Total endpoints collected: {len(all_endpoints)}")
                    
#                     # Case 2: name_filter provided but no applications found - treat as service name filter
#                     elif name_filter and not apps_items:
#                         logger.debug(f"No applications found for '{name_filter}', treating as service name filter")
                        
#                         # Get all endpoints and filter by service name
#                         # Note: Don't include applicationBoundaryScope for endpoints query
#                         endpoint_params = {
#                             "windowSize": window_size,
#                             "to": to_time
#                         }
#                         if name_filter:
#                             endpoint_params["nameFilter"] = name_filter
#                         if page is not None:
#                             endpoint_params["page"] = page
#                         if page_size is not None:
#                             endpoint_params["pageSize"] = page_size
                        
#                         endpoints_result = await self.make_request(
#                             endpoint="/api/application-monitoring/applications/services/endpoints",
#                             params=endpoint_params,
#                             method="GET"
#                         )
                        
#                         if "error" not in endpoints_result:
#                             all_service_endpoints = endpoints_result.get('items', [])
#                             logger.debug(
#                                 f"Found {len(all_service_endpoints)} total endpoints from API for service filter '{name_filter}'"
#                             )
                            
#                             for endpoint in all_service_endpoints:
#                                 endpoint_id = endpoint.get('id', '')
#                                 endpoint_label = endpoint.get('label', '')
#                                 if endpoint_label and endpoint_id:
#                                     endpoint_data = {
#                                         'id': endpoint_id,
#                                         'label': endpoint_label,
#                                         'type': endpoint.get('type', ''),
#                                         'technologies': endpoint.get('technologies', []),
#                                         'service_label': endpoint.get('serviceLabel', ''),
#                                         'service_id': endpoint.get('serviceId', '')
#                                     }
#                                     all_endpoints.append(endpoint_data)
                    
#                     # Case 3: No name_filter - get all endpoints
#                     else:
#                         # Note: Don't include applicationBoundaryScope for endpoints query
#                         endpoint_params = {
#                             "windowSize": window_size,
#                             "to": to_time
#                         }
#                         if name_filter:
#                             endpoint_params["nameFilter"] = name_filter
#                         if page is not None:
#                             endpoint_params["page"] = page
#                         if page_size is not None:
#                             endpoint_params["pageSize"] = page_size
                        
#                         logger.debug(f"Fetching all endpoints with params: {endpoint_params}")
                        
#                         endpoints_result = await self.make_request(
#                             endpoint="/api/application-monitoring/applications/services/endpoints",
#                             params=endpoint_params,
#                             method="GET"
#                         )
                        
#                         if "error" not in endpoints_result:
#                             service_endpoints = endpoints_result.get('items', [])
#                             logger.debug(f"Found {len(service_endpoints)} endpoints")
                            
#                             for endpoint in service_endpoints:
#                                 endpoint_id = endpoint.get('id', '')
#                                 endpoint_label = endpoint.get('label', '')
#                                 if endpoint_label and endpoint_id:
#                                     endpoint_data = {
#                                         'id': endpoint_id,
#                                         'label': endpoint_label,
#                                         'type': endpoint.get('type', ''),
#                                         'technologies': endpoint.get('technologies', [])
#                                     }
#                                     all_endpoints.append(endpoint_data)
                    
#                     # Sort and prepare result
#                     all_endpoints.sort(key=lambda x: x['label'])
#                     result["endpoints"] = {
#                         "items": all_endpoints,
#                         "total": len(all_endpoints),
#                         "showing": min(10, len(all_endpoints))
#                     }
#                     result["summary"]["total_endpoints"] = len(all_endpoints)
#                     result["summary"]["showing_endpoints"] = len(all_endpoints[:10])
                    
#                     if len(all_endpoints) == 0 and name_filter:
#                         if apps_items:
#                             result["endpoints_note"] = f"No endpoints found for application '{name_filter}'"
#                         else:
#                             result["endpoints_note"] = f"No endpoints found for service '{name_filter}'"

#                 except Exception as e:
#                     logger.error(f"Error getting endpoints: {e}", exc_info=True)
#                     result["endpoints_error"] = str(e)

#             logger.debug(f"Application entities insights result: {result}")
#             return result

#         except Exception as e:
#             logger.error(f"Error in application_entities_insights: {e}", exc_info=True)
#             error_result: Dict[str, Any] = {"error": f"Failed to get application entities insights: {e!s}"}
#             return error_result
