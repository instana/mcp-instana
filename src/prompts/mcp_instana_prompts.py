import asyncio
import logging
import sys
from typing import Optional

from fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Instana MCP Server")
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

PROMPT_REGISTRY = []

def auto_register_prompt(func):
    """Wrap MCP's @mcp.prompt to also store prompt in a registry."""
    func = mcp.prompt()(func)  # apply MCP's decorator
    PROMPT_REGISTRY.append(func)
    return func


# ----------------------------
# Application Alerts Prompts
# ----------------------------

@auto_register_prompt
def app_alerts_list(from_time: Optional[int]=None , to_time: Optional[int]=None, name_filter: Optional[str] = None, severity: Optional[str] = None, ) -> str:
    """List all application alerts in Instana server"""
    return f"""
    List application alerts with filters:
    - Name filter: {name_filter or 'None'}
    - Severity: {severity or 'None'}
    - Time range: {from_time} to {to_time or 'current time'}
    """

@auto_register_prompt
def app_alert_details(alert_ids: Optional[list] = None, application_id: Optional[str] = None) -> str:
    """Get Smart Alert Configurations details for a specific application"""
    return f"""
    Get alert details for:
    - Alert IDs: {alert_ids or 'None'}
    - Application ID: {application_id or 'None'}
    """

@auto_register_prompt
def app_alert_config_delete(id: str) -> str:
    """Delete a Smart Alert Configuration by ID"""
    return f"Delete alert configuration with ID: {id}"

@auto_register_prompt
def app_alert_config_enable(id: str) -> str:
    """Enable a Smart Alert Configuration by ID"""
    return f"Enable alert configuration with ID: {id}"

# ----------------------------
# Application Resource Prompts
# ----------------------------

@auto_register_prompt
def application_insights_summary(window_size: int, to_time: int, name_filter: Optional[str] = None, application_boundary_scope: Optional[str] = None) -> str:
    """Retrieve a list of services within application perspectives from Instana"""
    return f"""
    Get application insights summary with:
    - Name filter: {name_filter or 'None'}
    - Window size: {window_size or '1 hour'}
    - To time: {to_time or 'now'}
    - Boundary scope: {application_boundary_scope or 'None'}
    """

# ----------------------------
# Application Metrics Prompts
# ----------------------------

@auto_register_prompt
def get_application_metrics(application_ids: Optional[list] = None, metrics: Optional[list] = None, time_frame: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
    """Retrieve metrics for specific applications including latency, error rates, etc., over a given time frame"""
    return f"""
    Get application metrics for:
    - Application IDs: {application_ids or 'None'}
    - Metrics: {metrics or 'None'}
    - Time frame: {time_frame or 'None'}
    - Fill time series: {fill_time_series or 'None'}
    """

@auto_register_prompt
def get_application_endpoints_metrics(application_ids: Optional[list] = None, metrics: Optional[list] = None, time_frame: Optional[dict] = None, order: Optional[dict] = None, pagination: Optional[dict] = None, filters: Optional[dict] = None, fill_time_series: Optional[bool] = None)  -> str:
    """Retrieve metrics for endpoints within an application, such as latency, error rates, and call counts"""
    return f"""
    Get endpoint metrics for applications:
    - Application IDs: {application_ids}
    - Metrics: {metrics}
    - Time frame: {time_frame}
    - Order: {order or 'None'}
    - Pagination: {pagination or 'None'}
    - Filters: {filters or 'None'}
    - Fill time series: {fill_time_series or 'None'}
    """

@auto_register_prompt
def get_application_service_metrics(service_ids: list, metrics: Optional[list] = None, var_from: Optional[int] = None, to: Optional[int] = None, fill_time_series: Optional[bool] = None, include_snapshot_ids: Optional[bool] = None) -> str:
    """Fetch metrics over a specific time frame for specific services"""
    return f"""
    Get service metrics:
    - Service IDs: {service_ids}
    - Metrics: {metrics or 'None'}
    - From: {var_from or '1 hour ago'}
    - To: {to or 'now'}
    - Fill time series: {fill_time_series or 'None'}
    - Include snapshot IDs: {include_snapshot_ids or 'None'}
    """

# ----------------------------
# Application Catalog Prompts
# ----------------------------

@auto_register_prompt
def app_catalog_yesterday(limit: int, use_case: Optional[str] = None, data_source: Optional[str] = None, var_from: Optional[int] = None) -> str:
    """List 3 available application tag catalog data for yesterday"""
    return f"""
    Get application catalog data:
    - Use case: {use_case or 'None'}
    - Data source: {data_source or 'None'}
    - From: {var_from or 'last 24 hours'}
    - Limit: {limit or '100'}
    """

# ----------------------------
# Application Settings Prompts
# ----------------------------

@auto_register_prompt
def get_all_applications_configs() -> str:
    """Get a list of all Application Perspectives with their configuration settings"""
    return "Retrieve all application configurations"

@auto_register_prompt
def get_application_config(id: str) -> str:
    """Get an Application Perspective configuration by ID"""
    return f"Retrieve application configuration with ID: {id}"

@auto_register_prompt
def get_all_endpoint_configs() -> str:
    """Get a list of all Endpoint Perspectives with their configuration settings"""
    return "Retrieve all endpoint configurations"

@auto_register_prompt
def get_endpoint_config(id: str) -> str:
    """Retrieve the endpoint configuration of a service"""
    return f"Get endpoint configuration with ID: {id}"

@auto_register_prompt
def get_all_manual_service_configs() -> str:
    """Get a list of all Manual Service Perspectives with their configuration settings"""
    return "Retrieve all manual service configurations"

@auto_register_prompt
def add_manual_service_config(
    enabled: bool,
    tag_filter_expression: dict,
    unmonitored_service_name: Optional[str] = None,
    existing_service_id: Optional[str] = None,
    description: Optional[str] = None
) -> str:
    """Create a manual service mapping configuration"""
    return f"""
    Add manual service configuration:
    - Tag filter: {tag_filter_expression}
    - Unmonitored service name: {unmonitored_service_name or 'None'}
    - Existing service ID: {existing_service_id or 'None'}
    - Description: {description or 'None'}
    - Enabled: {enabled or 'True'}
    """

@auto_register_prompt
def get_service_config(id: str) -> str:
    """Retrieve the particular custom service configuration"""
    return f"Get service configuration with ID: {id}"

# --------------------------------
# Infrastructure Analyze Prompts
# --------------------------------

@auto_register_prompt
def infra_available_metrics(
    type: str,
    query: Optional[str] = None,
    var_from: Optional[int] = None,
    to: Optional[int] = None,
    windowSize: Optional[int] = None) -> str:
    """Get available infrastructure metrics for a given entity type"""
    return f"""
    Get available infrastructure metrics:
    - Type: {type}
    - Query: {query or 'None'}
    - From: {var_from or 'None'}
    - To: {to or 'None'}
    - Window size: {windowSize or 'None'}
    """

@auto_register_prompt
def infra_get_entities(
    type: str,
    metrics: Optional[str] = None,
    windowSize: Optional[int] = None,
    to: Optional[int] = None) -> str:
    """Fetch infrastructure entities and their metrics"""
    return f"""
    Get infrastructure entities:
    - Type: {type}
    - Metrics: {metrics}
    - Window size: {windowSize or 'None'}
    - To: {to or 'None'}
    """

@auto_register_prompt
def infra_available_plugins(
    offline: bool ,
    query: Optional[str] = None,
    windowSize: Optional[int] = None,
    to: Optional[int] = None) -> str:
    """List available infrastructure monitoring plugins"""
    return f"""
    Get available infrastructure plugins:
    - Query: {query or 'None'}
    - Offline: {offline or 'False'}
    - Window size: {windowSize or 'None'}
    - To: {to or 'None'}
    """

# --------------------------------
# Infrastructure Metrics Prompts
# --------------------------------

@auto_register_prompt
def get_infrastructure_metrics(
    offline: bool,
    rollup: int,
    plugin: str,
    window_size: Optional[int] = None,
    query: Optional[str] = None,
    metrics: Optional[list] = None,
    snapshot_ids: Optional[list] = None,
    to: Optional[int] = None,

) -> str:
    """Retrieve infrastructure metrics for plugin and query with a given time frame"""
    return f"""
    Get infrastructure metrics:
    - Plugin: {plugin}
    - Query: {query}
    - Metrics: {metrics}
    - Snapshot IDs: {snapshot_ids or 'None'}
    - Offline: {offline or 'False'}
    - Window size: {window_size or '1 hour'}
    - To: {to or 'current time'}
    - Rollup: {rollup or '60 seconds'}
    """

# --------------------------------
# Infrastructure Resources Prompts
# --------------------------------

@auto_register_prompt
def get_infrastructure_monitoring_state() -> str:
    """Get an overview of the current Instana monitoring state"""
    return "Get infrastructure monitoring state"

@auto_register_prompt
def get_infrastructure_plugin_payload(
    snapshot_id: str,
    payload_key: str,
    to_time: Optional[int] = None ,
    window_size: Optional[int] = None
) -> str:
    """Get raw plugin payload data for a specific snapshot entity"""
    return f"""
    Get plugin payload:
    - Snapshot ID: {snapshot_id}
    - Payload key: {payload_key}
    - To time: {to_time or 'current time'}
    - Window size: {window_size or '1 hour'}
    """

@auto_register_prompt
def get_infrastructure_metrics_snapshot(
    snapshot_id: str,
    to_time: Optional[int] = None ,
    window_size: Optional[int] = None
) -> str:
    """Get detailed information for a single infrastructure snapshot"""
    return f"""
    Get infrastructure snapshot:
    - Snapshot ID: {snapshot_id}
    - To time: {to_time or 'current time'}
    - Window size: {window_size or '1 hour'}
    """

@auto_register_prompt
def post_infrastructure_metrics_snapshot(
    snapshot_ids: list[str],
    to_time: Optional[int] = None,
    window_size: Optional[int] = None ,
    detailed: Optional[bool] = False,
) -> str:
    """Fetch details of multiple snapshots by their IDs"""
    return f"""
    Get multiple infrastructure snapshots:
    - Snapshot IDs: {snapshot_ids}
    - To time: {to_time or 'current time'}
    - Window size: {window_size or '1 hour'}
    - Detailed: {detailed or 'False'}
    """

# --------------------------------
# Infrastructure Topology Prompts
# --------------------------------

@auto_register_prompt
def get_related_hosts(
    snapshot_id: str,
    to_time: Optional[int] = None ,
    window_size: Optional[int] = None
) -> str:
    """Get hosts related to a specific snapshot"""
    return f"""
    Get related hosts:
    - Snapshot ID: {snapshot_id}
    - To time: {to_time or '1 hour'}
    - Window size: {window_size or '1 hour'}
    """

# --------------------------------
# Application Topology Prompts
# --------------------------------

@auto_register_prompt
def get_application_topology(
    window_size: Optional[int] = None ,
    to_timestamp: Optional[int] = None ,
    application_id: Optional[str] = None,
    application_boundary_scope: Optional[str] = None) -> str:
    """Retrieve the service topology showing connections between services"""
    return f"""
    Get application topology:
    - Window size: {window_size or '1 hour'}
    - To timestamp: {to_timestamp or 'current time'}
    - Application ID: {application_id or 'None'}
    - Boundary scope: {application_boundary_scope or 'INBOUND'}
    """

# --------------------------------
# Infrastructure Topology Prompts
# --------------------------------

@auto_register_prompt
def get_topology(include_data: Optional[bool] = False ) -> str:
    """Retrieve the complete infrastructure topology"""
    return f"Get complete topology with include_data: {include_data or 'False'}"

# --------------------------------
# Infrastructure Catalog Prompts
# --------------------------------

@auto_register_prompt
def get_available_payload_keys_by_plugin_id(plugin_id: str) -> str:
    """Retrieve available payload keys for a specific plugin"""
    return f"Get payload keys for plugin ID: {plugin_id}"

@auto_register_prompt
def get_infrastructure_catalog_metrics(plugin: str, filter: Optional[str] = None) -> str:
    """
    Get the list of available metrics for a specified plugin, supporting metric exploration for dashboards and queries.

    Args:
        plugin (str): Plugin (e.g., host, JVM, Kubernetes)
        filter (Optional[str], optional): Filter string for narrowing down metrics
    """
    return f"""
    Get infrastructure catalog metrics:
    - Plugin: {plugin}
    - Filter: {filter or 'None'}
    """



@auto_register_prompt
def get_tag_catalog(plugin: str) -> str:
    """Get available tags for a specific plugin"""
    return f"Get tag catalog for plugin: {plugin}"

@auto_register_prompt
def get_tag_catalog_all() -> str:
    """Retrieve the complete list of tags available across all monitored entities"""
    return "Get all tag catalogs"

# Main entrypoint
def main() -> None:
    asyncio.run(mcp.run_http_async(
        host="0.0.0.0",
        port=8080,
        log_level="debug",
        path="/mcp"
    ))

if __name__ == "__main__":
    main()

