import sys
from collections import defaultdict

prompts = {}

def debug_print(*args, **kwargs):
    """Print debug information to stderr instead of stdout"""
    print(*args, file=sys.stderr, **kwargs)

def prompt(name, description="", category="", arguments=None):
    if arguments is None:
        arguments = []

    def decorator(fn):
        prompts[name] = {
            "function": fn,
            "description": description,
            "category": category,
            "arguments": arguments
        }
        return fn

    return decorator


# ----------------------------
# Application Alerts Prompts
# ----------------------------

@prompt(
    name="app_alerts_list",
    description="List all application alerts in Instana",
    category="application_alerts",
    arguments=[{
        "name": "name_filter",
        "type": "string",
        "required": False,
        "description": "Filter alerts by application name (supports partial matches)"
    }, {
        "name": "severity",
        "type": "string",
        "required": False,
        "description": "Filter alerts by severity (e.g., 'CRITICAL', 'WARNING', 'INFO')"
    }, {
        "name": "from_time",
        "type": "integer",
        "required": False,
        "description": "Start timestamp in milliseconds (default: last 24 hours)"
    }, {
        "name": "to_time",
        "type": "integer",
        "required": False,
        "description": "End timestamp in milliseconds (default: current time)"
    }]
)

@prompt(
    name="app_alert_details",
    description="Get Smart Alert Configurations details for a specific application",
    category="application_alerts",
    arguments=[{
        "name": "alert_ids",
        "type": "List[str]",
        "required": False,
        "description": "List of alert IDs to retrieve details for"
    },
    {
        "name": "application_id",
        "type": "str",
        "required": False,
        "description": "ID of the application to which the alerts belong"
    }
    ]
)

@prompt(
    name="app_alert_config_delete",
    description="Delete a Smart Alert Configuration by ID",
    category="application_alerts",
    arguments=[{
        "name": "id",
        "type": "string",
        "required": True,
        "description": "ID of the Smart Alert Configuration to delete"
    }]
)

@prompt(
    name="app_alert_config_enable",
    description="Enable a Smart Alert Configuration by ID",
    category="application_alerts",
    arguments=[{
        "name": "id",
        "type": "string",
        "required": True,
        "description": "ID of the Smart Alert Configuration to enable"
    }]
)


# ----------------------------
# Application Resource Prompts
# ----------------------------

@prompt(
    name="application_insights_summary",
    description="Retrieve a list of services within application perspectives from Instana.",
    category="application_resources",
    arguments=[
        {
            "name": "name_filter",
            "type": "string",
            "required": False,
            "description": "Filter applications or services by name (eg)"
        },
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Size of time window in ms (default: 1 hour)"
        },
        {
            "name": "to_time",
            "type": "integer",
            "required": False,
            "description": "End timestamp in ms (default: now)"
        },
        {
            "name": "application_boundary_scope",
            "type": "string",
            "required": False,
            "description": "Scope (e.g., ALL, GROUP, SERVICE)"
        }
    ]
)




# ----------------------------
# Application Metrics Prompts
# ----------------------------

@prompt(
    name="get_application_metrics",
    description="Retrieve metrics for specific applications including latency, error rates, etc., over a given time frame.",
    category="application_metrics",
    arguments=[
        {
            "name": "application_ids",
            "type": "list[str]",
            "required": False,
            "description": "List of application IDs to fetch metrics for"
        },
        {
            "name": "metrics",
            "type": "list[object]",
            "required": False,
            "description": "List of metrics with their aggregations (e.g., [{'metric': 'latency', 'aggregation': 'MEAN'}])"
        },
        {
            "name": "time_frame",
            "type": "object",
            "required": False,
            "description": "Time frame for the query (e.g., {'windowSize': 3600000, 'to': 1750861775680})"
        },
        {
            "name": "fill_time_series",
            "type": "boolean",
            "required": False,
            "description": "Fill missing data points with 0s"
        }
    ]
)

@prompt(
    name="get_application_endpoints_metrics",
    description="Retrieve metrics for endpoints within an application, such as latency, error rates, and call counts.",
    category="application_metrics",
    arguments=[
        {
            "name": "application_ids",
            "type": "list[str]",
            "required": True,
            "description": "List of application IDs whose endpoints should be queried"
        },
        {
            "name": "metrics",
            "type": "list[object]",
            "required": True,
            "description": "List of metric objects (e.g., [{'metric': 'latency', 'aggregation': 'MEAN'}])"
        },
        {
            "name": "time_frame",
            "type": "object",
            "required": True,
            "description": "Time frame for which to get metrics (e.g., {'windowSize': 3600000, 'to': 1750861775680})"
        },
        {
            "name": "order",
            "type": "object",
            "required": False,
            "description": "Sorting options (e.g., {'by': 'latency', 'direction': 'DESC'})"
        },
        {
            "name": "pagination",
            "type": "object",
            "required": False,
            "description": "Pagination info (e.g., {'page': 1, 'pageSize': 50})"
        },
        {
            "name": "filters",
            "type": "object",
            "required": False,
            "description": "Filter criteria like tags, services, endpoints etc."
        },
        {
            "name": "fill_time_series",
            "type": "boolean",
            "required": False,
            "description": "Whether to fill gaps in time series data with default values"
        }
    ]
)

@prompt(
    name="get_application_service_metrics",
    description="Fetchmetrics over a specific time frame for specific services.",
    category="application_metrics",
    arguments=[
        {
            "name": "service_ids",
            "type": "list[string]",
            "required": True,
            "description": "List of service IDs to fetch metrics for."
        },
        {
            "name": "metrics",
            "type": "list[object]",
            "required": False,
            "description": "List of metric definitions, (e.g., [{'metric': 'latency', 'aggregation': 'MEAN'}])"
        },
        {
            "name": "from",
            "type": "integer",
            "required": False,
            "description": "Start timestamp in milliseconds (default: 1 hour ago)"
        },
        {
            "name": "to",
            "type": "integer",
            "required": False,
            "description": "End timestamp in milliseconds (default: now)"
        },
        {
            "name": "fill_time_series",
            "type": "boolean",
            "required": False,
            "description": "Whether to fill missing data points with timestamp (default: true)"
        },
        {
            "name": "include_snapshot_ids",
            "type": "boolean",
            "required": False,
            "description": "Include snapshot IDs in the response (default: false)"
        }
    ]
)



# ----------------------------
# Application Catalog Prompts
# ----------------------------

@prompt(
    name="app_catalog_yesterday",
    description="List 3 available application tag catalog data for yesterday ",
    category="application_catalog",
    arguments=[{
        "name": "use_case",
        "type": "string",
        "required": False,
        "description": "Use case for the tag catalog (e.g., 'GROUPING', 'FILTERING')"
    }, {
        "name": "data_source",
        "type": "string",
        "required": False,
        "description": "Data source for the tag catalog (e.g., 'CALLS', 'TRACES')"
    }, {
        "name": "var_from",
        "type": "integer",
        "required": False,
        "description": "Timestamp from which to get data (default: last 24 hours)"
    }, {
        "name": "limit",
        "type": "integer",
        "required": False,
        "description": "Limit the number of results returned (default: 100)"
    }
    ]
)

# --------------------------------
# Infrastructure Analyze Prompts
# --------------------------------

@prompt(
    name="infra_available_metrics",
    description="Get available infrastructure metrics for a given entity type (e.g., jvmRuntimePlatform)",
    category="infrastructure_analyze",
    arguments=[
        {
            "name": "type",
            "type": "string",
            "required": True,
            "description": "Type of infrastructure entity (e.g., 'jvmRuntimePlatform')"
        },
        {
            "name": "query",
            "type": "string",
            "required": False,
            "description": "Optional search query for narrowing down metrics (e.g., 'java')"
        },
        {
            "name": "from",
            "type": "integer",
            "required": False,
            "description": "Start timestamp for the timeframe (eg., 1743923995000)"
        },
        {
            "name": "to",
            "type": "integer",
            "required": False,
            "description": "End timestamp for the timeframe (eg., 1743920395000)"
        },
        {
            "name": "windowSize",
            "type": "integer",
            "required": False,
            "description": "Window size in milliseconds (e.g., 3600000 for 1 hour)"
        }
    ]
)

@prompt(
    name="infra_get_entities",
    description="Fetch infrastructure entities and their metrics (e.g., memory used, blocked threads)",
    category="infrastructure_analyze",
    arguments=[
        {
            "name": "type",
            "type": "string",
            "required": True,
            "description": "Type of entity (e.g., 'jvmRuntimePlatform')"
        },
        {
            "name": "metrics",
            "type": "string",
            "required": True,
            "description": "List of metric objects as JSON string (e.g., memory.used, threads.blocked)"
        },
        {
            "name": "windowSize",
            "type": "integer",
            "required": False,
            "description": "Start timestamp for the timeframe (e.g., 3600000 for 1 hour)"
        },
        {
            "name": "to",
            "type": "integer",
            "required": False,
            "description": "End timestamp for the timeframe (e.g., 1743920395000)"
        }
    ]
)

@prompt(
    name="infra_available_plugins",
    description="List available infrastructure monitoring plugins (e.g., Java, Docker)",
    category="infrastructure_analyze",
    arguments=[
        {
            "name": "query",
            "type": "string",
            "required": False,
            "description": "Search term to filter plugin types (e.g., 'java')"
        },
        {
            "name": "offline",
            "type": "boolean",
            "required": False,
            "description": "Whether to include offline plugins (default: false)"
        },
        {
            "name": "windowSize",
            "type": "integer",
            "required": False,
            "description": "Start timestamp for the timeframe (e.g., 3600000 for 1 hour)"
        },
        {
            "name": "to",
            "type": "integer",
            "required": False,
            "description": "End timestamp for the timeframe (e.g., 1743923995000)"
        }
    ]
)

# --------------------------------
# Infrastructure Metrics Prompts
# --------------------------------

@prompt(
    name="get_infrastructure_metrics",
    description="Retrieve infrastructure metrics for plugin and query with a given time frame for a rollup interval",
    category="infrastructure_metrics",
    arguments=[
        {
            "name": "plugin",
            "type": "string",
            "required": True,
            "description": "Plugin type to fetch metrics from (e.g., 'host')"
        },
        {
            "name": "query",
            "type": "string",
            "required": True,
            "description": "Query string to filter metrics (e.g., 'entity.selfType:java')"
        },
        {
            "name": "metrics",
            "type": "list",
            "required": True,
            "description": "List of metrics to fetch (e.g., [\"cpu.usage\", \"mem.usage\"])"
        },
        {
            "name": "snapshot_ids",
            "type": "list",
            "required": False,
            "description": "List of snapshot IDs to filter (eg: w1Wx4kqX5EuemG7Iw8N8SJnBC3A) --- if not provided, all snapshots will be considered"
        },
        {
            "name": "offline",
            "type": "boolean",
            "required": False,
            "description": "Include offline snapshots in the result (default: false)"
        },
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Window size in milliseconds (default: 3600000 for 1 hour)"
        },
        {
            "name": "to",
            "type": "integer",
            "required": False,
            "description": "End timestamp in milliseconds (default: current time)"
        },
        {
            "name": "rollup",
            "type": "integer",
            "required": False,
            "description": "Rollup interval in seconds (default: 60)"
        }
    ]
)

# --------------------------------
# Infrastructure Resources Prompts
# --------------------------------

@prompt(
    name="get_infrastructure_monitoring_state",
    description="Get an overview of the current Instana monitoring state, including monitored hosts and serverless entities.",
    category="infrastructure_resources",
)

@prompt(
    name="get_infrastructure_plugin_payload",
    description="Get raw plugin payload data for a specific snapshot entity in Instana.",
    category="infrastructure_resources",
    arguments=[
        {
            "name": "snapshot_id",
            "type": "string",
            "required": True,
            "description": "ID of the snapshot to fetch plugin payload for."
        },
        {
            "name": "payload_key",
            "type": "string",
            "required": True,
            "description": "Key of the payload to retrieve (e.g., 'topqueries')."
        },
        {
            "name": "to_time",
            "type": "integer",
            "required": False,
            "description": "End timestamp in milliseconds (default: current time)."
        },
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Window size in milliseconds (default: 3600000 for 1 hour)."
        }
    ]
)

@prompt(
    name="get_infrastructure_metrics_snapshot",
    description="Get detailed information for a single infrastructure snapshot using its ID.",
    category="infrastructure_resources",
    arguments=[
        {
            "name": "snapshot_id",
            "type": "string",
            "required": True,
            "description": "Snapshot ID to retrieve details for."
        },
        {
            "name": "to_time",
            "type": "integer",
            "required": False,
            "description": "End timestamp in milliseconds (default: current time)."
        },
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Window size in milliseconds (default: 3600000 for 1 hour)."
        }
    ]
)

@prompt(
    name="post_infrastructure_metrics_snapshot",
    description="Fetch details of multiple snapshots by their IDs.",
    category="infrastructure_resources",
    arguments=[
        {
            "name": "snapshot_ids",
            "type": "list",
            "required": True,
            "description": "List of snapshot IDs to retrieve."
        },
        {
            "name": "to_time",
            "type": "integer",
            "required": False,
            "description": "End timestamp in milliseconds (default: current time)."
        },
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Window size in milliseconds (default: 3600000 for 1 hour )."
        },
        {
            "name": "detailed",
            "type": "boolean",
            "required": False,
            "description": "Return detailed/raw data if True; summarized data if False (default: False)."
        }
    ]
)

# --------------------------------
# Infrastructure Topology Prompts
# --------------------------------

@prompt(
    name="get_related_hosts",
    description="Get hosts related to a specific snapshot, helping to understand infrastructure dependencies for a given entity.",
    category="infrastructure_topology",
    arguments=[
        {
            "name": "snapshot_id",
            "type": "string",
            "required": True,
            "description": "The ID of the snapshot to find related hosts for."
        },
        {
            "name": "to_time",
            "type": "integer",
            "required": False,
            "description": "End timestamp in milliseconds (default:  3600000 for 1 hour)."
        },
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Time window in milliseconds for the related hosts query (default: 3600000 for 1 hour ) ."
        }
    ]
)

# --------------------------------
# Application Topology Prompts
# --------------------------------

@prompt(
    name="get_application_topology",
    description="Retrieve the service topology showing connections between services in an application.",
    category="application_topology",
    arguments=[
        {
            "name": "window_size",
            "type": "integer",
            "required": False,
            "description": "Size of time window in milliseconds (default: 3600000 for 1 hour)"
        },
        {
            "name": "to_timestamp",
            "type": "integer",
            "required": False,
            "description": "Timestamp since Unix Epoch in milliseconds of the end of the time window (default: current time)"
        },
        {
            "name": "application_id",
            "type": "string",
            "required": False,
            "description": "Filter by application ID to show topology for a specific application"
        },
        {
            "name": "application_boundary_scope",
            "type": "string",
            "required": False,
            "description": "Filter by application scope, i.e., INBOUND or ALL (default: INBOUND)"
        }
    ]
)

# --------------------------------
# Infrastructure Topology Prompts
# --------------------------------

@prompt(
    name="get_topology",
    description="Retrieve the complete infrastructure topology including nodes and edges, showing relationships and dependencies between monitored entities.",
    category="infrastructure_topology",
    arguments=[
        {
            "name": "include_data",
            "type": "boolean",
            "required": False,
            "description": "Whether to include detailed snapshot data for nodes (default: False)."
        }
    ]
)


# --------------------------------
# Infrastructure Catalog Prompts
# --------------------------------
@prompt(
    name="get_available_payload_keys_by_plugin_id",
    description="Retrieve available payload keys for a specific plugin, used to access detailed monitoring data structures for that technology.",
    category="infrastructure_catalog",
    arguments=[
        {
            "name": "plugin_id",
            "type": "string",
            "required": True,
            "description": "The ID of the plugin to retrieve payload keys for."
        }
    ]
)

@prompt(
    name="get_infrastructure_catalog_metrics",
    description="Get the list of available metrics for a specified plugin (e.g., host, JVM, Kubernetes), supporting metric exploration for dashboards and queries.",
    category="infrastructure_catalog",
    arguments=[
        {
            "name": "plugin",
            "type": "string",
            "required": True,
            "description": "The plugin ID to fetch metrics for."
        },
        {
            "name": "filter",
            "type": "string",
            "required": False,
            "description": "Filter type to apply, (e.g., 'custom' or 'builtin')."
        }
    ]
)

@prompt(
    name="get_tag_catalog",
    description="Get available tags for a specific plugin, useful for grouping, filtering, or customizing visualizations and alerts.",
    category="infrastructure_catalog",
    arguments=[
        {
            "name": "plugin",
            "type": "string",
            "required": True,
            "description": "Plugin ID (e.g., 'host', 'jvm', 'kubernetes') to retrieve tags for."
        }
    ]
)

@prompt(
    name="get_tag_catalog_all",
    description="Retrieve the complete list of tags available across all monitored entities and plugins in your Instana environment.",
    category="infrastructure_catalog",
)


# ----------------------------
# System Utility
# ----------------------------


@prompt(
    name="get_all_application_prompts",
    description="List all available application-related prompts with descriptions and arguments",
    category="system"
)
def get_all_application_prompts():
    try:
        grouped = defaultdict(list)

        for name, data in prompts.items():
            if name == "get_all_application_prompts":
                continue

            if not isinstance(data, dict):
                continue

            # Format arguments with all details
            formatted_args = []
            for arg in data.get("arguments", []):
                arg_line = f"    • {arg['name']} ({arg['type']})"
                if arg.get('required', False):
                    arg_line += " [REQUIRED]"
                if 'description' in arg:
                    arg_line += f" - {arg['description']}"
                if 'default' in arg:
                    arg_line += f" (default: {arg['default']})"
                formatted_args.append(arg_line)

            grouped[data.get("category", "Uncategorized")].append({
                "name": name,
                "description": data.get("description", ""),
                "arguments": formatted_args
            })

        # Build the output
        output = []
        output.append("=== AVAILABLE PROMPTS ===")
        output.append("")

        for category, items in sorted(grouped.items()):
            output.append(f"--- {category.upper()} ---")
            for item in sorted(items, key=lambda x: x['name']):
                output.append(f"\n🔹 {item['name']}")
                output.append(f"   {item['description']}")

                if item["arguments"]:
                    output.append("   Arguments:")
                    output.extend(item["arguments"])
                else:
                    output.append("   No arguments required")

            output.append("")  # Empty line between categories

        return "\n".join(output)

    except Exception as e:
        return f"Error generating prompt list: {e!s}"



@prompt(
    name="get_all_infrastructure_prompts",
    description="List all available infrastructure-related prompts with descriptions and arguments",
    category="system"
)
def get_all_infrastructure_prompts():
    try:
        grouped = defaultdict(list)

        for name, data in prompts.items():
            if name == "get_all_infrastructure_prompts":
                continue

            if not isinstance(data, dict):
                continue

            # Format arguments with all details
            formatted_args = []
            for arg in data.get("arguments", []):
                arg_line = f"    • {arg['name']} ({arg['type']})"
                if arg.get('required', False):
                    arg_line += " [REQUIRED]"
                if 'description' in arg:
                    arg_line += f" - {arg['description']}"
                if 'default' in arg:
                    arg_line += f" (default: {arg['default']})"
                formatted_args.append(arg_line)

            grouped[data.get("category", "Uncategorized")].append({
                "name": name,
                "description": data.get("description", ""),
                "arguments": formatted_args
            })

        # Build the output
        output = []
        output.append("=== AVAILABLE PROMPTS ===")
        output.append("")

        for category, items in sorted(grouped.items()):
            output.append(f"--- {category.upper()} ---")
            for item in sorted(items, key=lambda x: x['name']):
                output.append(f"\n🔹 {item['name']}")
                output.append(f"   {item['description']}")

                if item["arguments"]:
                    output.append("   Arguments:")
                    output.extend(item["arguments"])
                else:
                    output.append("   No arguments required")

            output.append("")  # Empty line between categories

        return "\n".join(output)

    except Exception as e:
        return f"Error generating prompt list: {e!s}"




@prompt(
    name="get_all_prompts",
    description="List all available prompts with descriptions and arguments",
    category="system",
    arguments=[]
)
def get_all_prompts():
    try:
        grouped = defaultdict(list)

        for name, data in prompts.items():
            if name == "get_all_prompts":
                continue

            if not isinstance(data, dict):
                continue

            # Format arguments with all details
            formatted_args = []
            for arg in data.get("arguments", []):
                arg_line = f"    • {arg['name']} ({arg['type']})"
                if arg.get('required', False):
                    arg_line += " [REQUIRED]"
                if 'description' in arg:
                    arg_line += f" - {arg['description']}"
                if 'default' in arg:
                    arg_line += f" (default: {arg['default']})"
                formatted_args.append(arg_line)

            grouped[data.get("category", "Uncategorized")].append({
                "name": name,
                "description": data.get("description", ""),
                "arguments": formatted_args
            })

        # Build the output
        output = []
        output.append("=== AVAILABLE PROMPTS ===")
        output.append("")

        for category, items in sorted(grouped.items()):
            output.append(f"--- {category.upper()} ---")
            for item in sorted(items, key=lambda x: x['name']):
                output.append(f"\n🔹 {item['name']}")
                output.append(f"   {item['description']}")

                if item["arguments"]:
                    output.append("   Arguments:")
                    output.extend(item["arguments"])
                else:
                    output.append("   No arguments required")

            output.append("")  # Empty line between categories

        return "\n".join(output)

    except Exception as e:
        return f"Error generating prompt list: {e!s}"


INSTANA_PROMPTS = prompts

