"""
Standalone MCP Server for Instana Events and Infrastructure Resources

This module provides a dedicated MCP server that exposes Instana MCP Server.
Supports stdio and Streamable HTTP transports.
"""

import argparse
import logging
import os
import select as _select
import signal
import sys
import threading as _threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, fields
from typing import Any

from dotenv import load_dotenv

from src.prompts import PROMPT_REGISTRY

load_dotenv()

from src.observability import task, workflow

# Configure logging
# Read log level from environment variable (set by start.sh from config.yaml)
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}
log_level = log_level_map.get(log_level_name, logging.INFO)

logging.basicConfig(
    level=log_level,  # Default level from config, can be overridden by --log-level flag
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

def set_log_level(level_name):
    """Set the logging level based on the provided level name"""
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    level = level_map.get(level_name.upper(), logging.INFO)
    logger.setLevel(level)
    logging.getLogger().setLevel(level)
    logger.info(f"Log level set to {level_name.upper()}")

# Add the project root to the Python path
current_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the necessary modules
try:
    from src.core.utils import MCP_TOOLS, _ssl_verify_from_env, register_as_tool
except ImportError:
    logger.error("Failed to import required modules", exc_info=True)
    sys.exit(1)

from fastmcp import FastMCP


@dataclass
class MCPState:
    """State for the MCP server with all tool categories."""
    # Router tools
    smart_router_client: Any = None
    smart_router_custom_dashboard_client: Any = None
    smart_router_events_client: Any = None
    smart_router_website_client: Any = None
    smart_router_mobile_client: Any = None
    smart_router_automation_client: Any = None
    smart_router_slo_client: Any = None
    smart_router_synthetic_client: Any = None
    smart_router_releases_client: Any = None
    smart_router_maintenance_window_client: Any = None

    # Infrastructure - Only the new two-pass elicitation tool
    smart_router_infrastructure_client: Any = None

# Global variables to store credentials for lifespan
_global_token = None
_global_base_url = None

def get_instana_credentials():
    """Get Instana credentials from environment variables for stdio mode."""
    # For stdio mode, use INSTANA_API_TOKEN and INSTANA_BASE_URL
    token = (os.getenv("INSTANA_API_TOKEN") or "")
    base_url = (os.getenv("INSTANA_BASE_URL") or "")

    return token, base_url

def validate_credentials(token: str, base_url: str) -> bool:
    """Validate that Instana credentials are provided for stdio mode."""
    # For stdio mode, validate INSTANA_API_TOKEN and INSTANA_BASE_URL
    return not (not token or not base_url)

def create_clients(token: str, base_url: str, enabled_categories: str = "all") -> MCPState:
    """Create only the enabled Instana clients"""
    state = MCPState()

    # Get enabled client configurations
    enabled_client_configs = get_enabled_client_configs(enabled_categories)

    for attr_name, client_class in enabled_client_configs:
        try:
            client = client_class(read_token=token, base_url=base_url)
            setattr(state, attr_name, client)
        except Exception as e:
            logger.error(f"Failed to create {attr_name}: {e}", exc_info=True)
            setattr(state, attr_name, None)

    return state


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[MCPState]:
    """Set up and tear down the Instana clients."""
    # Get credentials from environment variables
    token, base_url = get_instana_credentials()

    try:
        # For lifespan, we'll create all clients since we don't have access to command line args here
        state = create_clients(token, base_url, "all")

        yield state
    except Exception:
        logger.error("Error during lifespan", exc_info=True)

        # Yield empty state if client creation failed
        yield MCPState()

def create_app(token: str, base_url: str, port: int = int(os.getenv("PORT", "8080")), enabled_categories: str = "all") -> tuple[FastMCP, int, int]:
    """Create and configure the MCP server with the given credentials."""
    try:
        server = FastMCP(name="Instana MCP Server")

        # Only create and register enabled clients/tools
        clients_state = create_clients(token, base_url, enabled_categories)

        tools_registered = 0
        for tool_name, _tool_func in MCP_TOOLS.items():
            try:
                client_attr_names = [field.name for field in fields(MCPState)]
                for attr_name in client_attr_names:
                    client = getattr(clients_state, attr_name, None)
                    if client and hasattr(client, tool_name):
                        bound_method = getattr(client, tool_name)

                        # Use the stored metadata (all tools now have metadata)
                        tool_kwargs = {
                            'title': bound_method._mcp_title,
                            'annotations': bound_method._mcp_annotations
                        }

                        # Add description if available
                        if hasattr(bound_method, '_mcp_description') and bound_method._mcp_description:
                            tool_kwargs['description'] = bound_method._mcp_description

                        server.tool(**tool_kwargs)(bound_method)

                        tools_registered += 1
                        break
            except Exception as e:
                logger.error(f"Failed to register tool {tool_name}: {e}", exc_info=True)

        # Register prompts from the prompt registry
        # Get enabled prompt categories - use the same categories as tools
        prompt_categories = get_prompt_categories()

        # Use the same categories for prompts as for tools
        enabled_prompt_categories = []
        if enabled_categories.lower() == "all" or not enabled_categories:
            enabled_prompt_categories = list(prompt_categories.keys())
            logger.info("Enabling all prompt categories")
        else:
            enabled_prompt_categories = [cat.strip() for cat in enabled_categories.split(",") if cat.strip() in prompt_categories]
            logger.info(f"Enabling prompt categories: {', '.join(enabled_prompt_categories)}")

        # Register prompts to the server
        logger.info("Registering prompts by category:")
        registered_prompts = set()

        for category, prompt_groups in prompt_categories.items():
            if category in enabled_prompt_categories:
                logger.info(f"  - {category}: {len(prompt_groups)} prompt groups")

                for group_name, prompts in prompt_groups:
                    prompt_count = len(prompts)
                    logger.info(f"    - {group_name}: {prompt_count} prompts")

                    for prompt_name, prompt_func in prompts:
                        server.add_prompt(prompt_func)
                        registered_prompts.add(prompt_name)
                        logger.debug(f"      * Registered prompt: {prompt_name}")
            else:
                logger.info(f"  - {category}: DISABLED")

        # Register any remaining prompts that might not be in categories
        uncategorized_count = 0

        # Just log the count of remaining prompts
        remaining_prompts = len(PROMPT_REGISTRY) - len(registered_prompts)
        if remaining_prompts > 0:
            logger.info(f"  - uncategorized: {remaining_prompts} prompts (not registered)")

        if uncategorized_count > 0:
            logger.info(f"  - uncategorized: {uncategorized_count} prompts")


        return server, tools_registered, port

    except Exception:
        logger.error("Error creating app", exc_info=True)
        fallback_server = FastMCP("Instana Tools")
        return fallback_server, 0, port  # Return a tuple with 0 tools registered and port

async def execute_tool(tool_name: str, arguments: dict, clients_state) -> str:
    """Execute a tool and return result"""
    try:
        # Get all field names from MCPState dataclass
        client_attr_names = [field.name for field in fields(MCPState)]

        for attr_name in client_attr_names:
            client = getattr(clients_state, attr_name, None)
            if client and hasattr(client, tool_name):
                method = getattr(client, tool_name)
                result = await method(**arguments)
                return str(result)

        return f"Tool {tool_name} not found"
    except Exception as e:
        return f"Error executing tool {tool_name}: {e!s}"

def get_client_categories():
    """Get client categories with lazy imports to avoid circular dependencies"""
    try:
        from src.router.application_smart_router_tool import (
            ApplicationSmartRouterMCPTool,
        )
        from src.router.automation_smart_router_tool import AutomationSmartRouterMCPTool
        from src.router.custom_dashboard_smart_router_tool import (
            CustomDashboardSmartRouterMCPTool,
        )
        from src.router.events_smart_router_tool import EventsSmartRouterMCPTool
        from src.router.infrastructure_smart_router_tool import (
            InfrastructureSmartRouterMCPTool,
        )
        from src.router.maintenance_window_smart_router import (
            MaintenanceWindowSmartRouterMCPTool,
        )
        from src.router.mobile_app_smart_router import MobileAppSmartRouterMCPTool
        from src.router.releases_smart_router_tool import ReleasesSmartRouterMCPTool
        from src.router.slo_smart_router_tool import SLOSmartRouterMCPTool
        from src.router.synthetic_smart_router_tool import SyntheticSmartRouterMCPTool
        from src.router.website_smart_router import WebsiteSmartRouterMCPTool
    except ImportError as e:
        logger.warning(f"Could not import client classes: {e}")
        return {}

    return {
        "app": [
            ('smart_router_client', ApplicationSmartRouterMCPTool),
        ],
        "infra": [
            ('smart_router_infrastructure_client', InfrastructureSmartRouterMCPTool),
        ],
        "automation": [
            ('smart_router_automation_client', AutomationSmartRouterMCPTool),
        ],
        "website": [
            ('smart_router_website_client', WebsiteSmartRouterMCPTool),
        ],
        "mobile_app": [
            ('smart_router_mobile_client', MobileAppSmartRouterMCPTool),
        ],
        "events": [
            ('smart_router_events_client', EventsSmartRouterMCPTool),
        ],
        "settings": [
            ('smart_router_custom_dashboard_client', CustomDashboardSmartRouterMCPTool),
        ],
        "slo": [
            ('smart_router_slo_client', SLOSmartRouterMCPTool),
        ],
        "synthetic": [
            ('smart_router_synthetic_client', SyntheticSmartRouterMCPTool),
        ],
        "releases": [
            ('smart_router_releases_client', ReleasesSmartRouterMCPTool),
        ],
        "maintenance": [
            ('smart_router_maintenance_window_client', MaintenanceWindowSmartRouterMCPTool),
        ]
    }

def get_prompt_categories():
    """Get prompt categories organized by functionality"""
    # Import the class-based prompts
    try:
        from src.prompts.application.application_alerts import ApplicationAlertsPrompts
        from src.prompts.application.application_metrics import (
            ApplicationMetricsPrompts,
        )
        from src.prompts.application.application_resources import (
            ApplicationResourcesPrompts,
        )
        from src.prompts.application.application_settings import (
            ApplicationSettingsPrompts,
        )
        from src.prompts.application.application_topology import (
            ApplicationTopologyPrompts,
        )
        from src.prompts.events.events_tools import EventsPrompts
        from src.prompts.infrastructure.infrastructure_analyze import (
            InfrastructureAnalyzePrompts,
        )
        from src.prompts.infrastructure.infrastructure_catalog import (
            InfrastructureCatalogPrompts,
        )
        from src.prompts.maintenance_window.maintenance_window_prompts import (
            MaintenanceWindowPrompts,
        )
        from src.prompts.mobile_app.mobile_app_alert import MobileAppAlertPrompts
        from src.prompts.mobile_app.mobile_app_analyze import MobileAppAnalyzePrompts
        from src.prompts.mobile_app.mobile_app_catalog import MobileAppCatalogPrompts
        from src.prompts.mobile_app.mobile_app_configuration import (
            MobileAppConfigurationPrompts,
        )
        from src.prompts.settings.custom_dashboard import CustomDashboardPrompts
        from src.prompts.synthetic.synthetic_catalog import SyntheticCatalogPrompts
        from src.prompts.synthetic.synthetic_metrics import SyntheticMetricsPrompts
        from src.prompts.synthetic.synthetic_settings import SyntheticSettingsPrompts
        from src.prompts.synthetic.synthetic_test_playback_results import (
            SyntheticTestPlaybackResultsPrompts,
        )
        from src.prompts.website.website_alert import WebsiteAlertPrompts
        from src.prompts.website.website_analyze import WebsiteAnalyzePrompts
        from src.prompts.website.website_catalog import WebsiteCatalogPrompts
        from src.prompts.website.website_configuration import (
            WebsiteConfigurationPrompts,
        )
        from src.prompts.website.website_metrics import WebsiteMetricsPrompts
    except ImportError as e:
        logger.warning(f"Could not import prompt classes: {e}")
        return {}

    # Get prompts from each class
    app_alerts_prompts = ApplicationAlertsPrompts.get_prompts()
    app_metrics_prompts = ApplicationMetricsPrompts.get_prompts()
    app_resources_prompts = ApplicationResourcesPrompts.get_prompts()
    app_settings_prompts = ApplicationSettingsPrompts.get_prompts()
    app_topology_prompts = ApplicationTopologyPrompts.get_prompts()
    events_prompts = EventsPrompts.get_prompts()
    infra_analyze_prompts = InfrastructureAnalyzePrompts.get_prompts()
    infra_catalog_prompts = InfrastructureCatalogPrompts.get_prompts()
    custom_dashboard_prompts = CustomDashboardPrompts.get_prompts()
    website_analyze_prompts = WebsiteAnalyzePrompts.get_prompts()
    maintenance_window_prompts = MaintenanceWindowPrompts.get_prompts()
    website_catalog_prompts = WebsiteCatalogPrompts.get_prompts()
    website_configuration_prompts = WebsiteConfigurationPrompts.get_prompts()
    website_metrics_prompts = WebsiteMetricsPrompts.get_prompts()
    mobile_app_analyze_prompts = MobileAppAnalyzePrompts.get_prompts()
    mobile_app_catalog_prompts = MobileAppCatalogPrompts.get_prompts()
    mobile_app_configuration_prompts = MobileAppConfigurationPrompts.get_prompts()
    mobile_app_alert_prompts = MobileAppAlertPrompts.get_prompts()
    website_alert_prompts = WebsiteAlertPrompts.get_prompts()
    synthetic_catalog_prompts: list[Any]= SyntheticCatalogPrompts.get_prompts()
    synthetic_metrics_prompts: list[Any]= SyntheticMetricsPrompts.get_prompts()
    synthetic_settings_prompts: list[Any]= SyntheticSettingsPrompts.get_prompts()
    synthetic_test_playback_prompts: list[Any] = SyntheticTestPlaybackResultsPrompts.get_prompts()

    return {
        "app": [
            ("Application Alerts", app_alerts_prompts),
            ("Application Metrics", app_metrics_prompts),
            ("Application Resources", app_resources_prompts),
            ("Application Settings", app_settings_prompts),
            ("Application Topology", app_topology_prompts),
        ],
        "events": [
            ("Events Tools", events_prompts),
        ],
        "infra": [
            ("Infrastructure Analyze", infra_analyze_prompts),
            ("Infrastructure Catalog", infra_catalog_prompts),
        ],
        "website": [
            ("Website Analyze", website_analyze_prompts),
            ("Website Catalog", website_catalog_prompts),
            ("Website Configuration", website_configuration_prompts),
            ("Website Metrics", website_metrics_prompts),
            ("Website Alerts", website_alert_prompts),
        ],
        "settings": [
            ("Custom Dashboard", custom_dashboard_prompts),
        ],
        "synthetic": [
            ("Synthetic Catalog", synthetic_catalog_prompts),
            ("Synthetic Metrics", synthetic_metrics_prompts),
            ("Synthetic Settings", synthetic_settings_prompts),
            ("Synthetic Playback", synthetic_test_playback_prompts),
        ],
        "mobile_app": [
            ("Mobile App Analyze", mobile_app_analyze_prompts),
            ("Mobile App Catalog", mobile_app_catalog_prompts),
            ("Mobile App Configuration", mobile_app_configuration_prompts),
            ("Mobile App Alerts", mobile_app_alert_prompts),
        ],
        "maintenance": [
            ("Maintenance Window", maintenance_window_prompts),
        ]
    }

def get_enabled_client_configs(enabled_categories: str):
    """Get client configurations based on enabled categories"""
    # Get client categories with lazy imports
    client_categories = get_client_categories()

    if not enabled_categories or enabled_categories.lower() == "all":
        all_configs = []
        for category_clients in client_categories.values():
            all_configs.extend(category_clients)
        return all_configs
    categories = [cat.strip() for cat in enabled_categories.split(",")]
    enabled_configs = []
    for category in categories:
        if category in client_categories:
            enabled_configs.extend(client_categories[category])
        else:
            logger.warning(f"Unknown category '{category}'")
    return enabled_configs

@workflow(name="instana_mcp_workflow")
def main():
    """Main entry point for the MCP server."""
    try:
        # Register signal handlers immediately — before create_app() or any other
        # blocking work — so a SIGTERM that arrives during startup (e.g. Kubernetes
        # rolling restart firing before the server is fully up) is captured and logged
        # rather than killing the process silently with no record.
        _shutdown_reason: list[str] = ["unknown"]

        # _pipe_w holds the write-end of the stdin proxy pipe used in stdio mode.
        # Closing it delivers EOF to anyio's readline thread immediately on any signal.
        _pipe_w: list[int] = [-1]
        _pipe_w_lock = _threading.Lock()

        def _close_pipe_write_end():
            """Close the write end of the stdin pipe so anyio's readline unblocks."""
            with _pipe_w_lock:
                w = _pipe_w[0]
                if w != -1:
                    _pipe_w[0] = -1
            if w != -1:
                with suppress(OSError):
                    os.close(w)

        def _handle_sigterm(signum, frame):
            _shutdown_reason[0] = "SIGTERM (Kubernetes asked the pod to stop — rolling restart, scale-down, or node pressure)"
            logger.info("[server] Received SIGTERM — beginning graceful shutdown")
            _close_pipe_write_end()
            sys.exit(0)

        def _handle_sigint(signum, frame):
            _shutdown_reason[0] = "SIGINT (keyboard interrupt or container stop)"
            logger.info("[server] Received SIGINT — beginning graceful shutdown")
            _close_pipe_write_end()
            # Re-raise as KeyboardInterrupt so the event loop unwinds normally.
            raise KeyboardInterrupt

        # SIGTERM has no Python default handler — it would be silently ignored.
        signal.signal(signal.SIGTERM, _handle_sigterm)
        # SIGINT: install our handler *before* anyio.run() so anyio doesn't replace it.
        # We raise KeyboardInterrupt ourselves which anyio handles correctly.
        signal.signal(signal.SIGINT, _handle_sigint)

        # Create and configure the MCP server
        parser = argparse.ArgumentParser(description="Instana MCP Server", add_help=False)
        parser.add_argument(
                "-h", "--help",
                action="store_true",
                dest="help",
                help="show this help message and exit"
            )
        parser.add_argument(
            "--transport",
            type=str,
            choices=["streamable-http","stdio"],
            metavar='<mode>',
            help="Transport mode. Choose from: streamable-http, stdio."
        )
        parser.add_argument(
            "--log-level",
            type=str,
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default=os.getenv("LOG_LEVEL", "INFO"),
            help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is read from config file via LOG_LEVEL env var."
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Enable debug mode with additional logging (shortcut for --log-level DEBUG)"
        )
        parser.add_argument(
            "--tools",
            type=str,
            metavar='<categories>',
            help="Comma-separated list of tool categories to enable (--tools infra, app, events, automation, mobile_app, website, settings, slo, releases, maintenance, synthetic). Also controls which prompts are enabled. If not provided, all tools and prompts are enabled. Use 'router' for smart routing across app and infra metrics."
        )
        parser.add_argument(
            "--list-tools",
            action="store_true",
            help="List all available tool categories and exit."
        )
        parser.add_argument(
            "--port",
            type=int,
            default=int(os.getenv("PORT", "8080")),
            help="Port to listen on (default: 8080, can be overridden with PORT env var)"
        )
        parser.add_argument(
            "--api-token",
            type=str,
            help="Instana API token (overrides INSTANA_API_TOKEN env var)"
        )
        parser.add_argument(
            "--base-url",
            type=str,
            help="Instana base URL (overrides INSTANA_BASE_URL env var)"
        )
        parser.add_argument(
            "--verify-ssl",
            action="store_true",
            default=False,
            help="Enable SSL certificate verification. Equivalent to INSTANA_SSL_VERIFY=true."
        )
        # Check for help arguments before parsing
        if len(sys.argv) > 1 and any(arg in ['-h', '--help'] for arg in sys.argv[1:]):
            # Check if help is combined with other arguments
            help_args = ['-h', '--help']
            other_args = [arg for arg in sys.argv[1:] if arg not in help_args]

            if other_args:
                logger.error("Argument -h/--help: not allowed with other arguments")
                sys.exit(2)

            # Show help and exit
            try:
                logger.info("Available options:")
                for action in parser._actions:
                    # Only print options that start with '--' and have a help string
                    if any(opt.startswith('--') for opt in action.option_strings) and action.help:
                        # Find the first long option
                        long_opt = next((opt for opt in action.option_strings if opt.startswith('--')), None)
                        metavar = action.metavar or ''
                        opt_str = f"{long_opt} {metavar}".strip()
                        logger.info(f"{opt_str:<24} {action.help}")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error displaying help: {e}")
                sys.exit(0)  # Still exit with 0 for help

        args = parser.parse_args()

        # Set log level based on command line arguments
        if args.debug:
            set_log_level("DEBUG")
        else:
            set_log_level(args.log_level)

        all_categories = {"app", "infra", "events", "automation", "website", "mobile_app", "settings", "slo", "releases", "maintenance", "synthetic"}

        # Handle --list-tools option
        if args.list_tools:
            logger.info("Available tool categories:")
            client_categories = get_client_categories()
            for category, tools in client_categories.items():
                tool_names = [cls.__name__ for _, cls in tools]
                count = len(tool_names)
                label = "tool" if count == 1 else "tools"
                logger.info(f"  {category}: {count} {label}")
                for tool_name in tool_names:
                    logger.info(f"    - {tool_name}")
            sys.exit(0)

        # By default, enable all categories
        enabled = set(all_categories)
        invalid = set()

        # Enable only specified categories if --tools is provided
        if args.tools:
            specified_tools = {cat.strip() for cat in args.tools.split(",")}
            invalid = specified_tools - all_categories
            enabled = specified_tools & all_categories

            # If no valid tools specified, default to all
            if not enabled:
                enabled = set(all_categories)

        if invalid:
            logger.error(f"Error: Unknown category/categories: {', '.join(invalid)}. Available categories: app, infra, events, automation, mobile_app, website, settings, slo, releases, maintenance, synthetic")
            sys.exit(2)

        # Print enabled tools for user information
        enabled_tool_classes = []
        client_categories = get_client_categories()

        # Log enabled categories and tools
        logger.info(f"Enabled tool categories: {', '.join(enabled)}")

        for category in enabled:
            if category in client_categories:
                category_tools = [cls.__name__ for _, cls in client_categories[category]]
                enabled_tool_classes.extend(category_tools)
                count = len(category_tools)
                label = "tool" if count == 1 else "tools"
                logger.info(f"  - {category}: {count} {label}")
                for tool_name in category_tools:
                    logger.info(f"    * {tool_name}")

        if enabled_tool_classes:
            logger.info(
                f"Total enabled tools: {len(enabled_tool_classes)}"
            )

        # Get credentials from command line args or environment variables
        INSTANA_API_TOKEN = args.api_token if args.api_token else os.getenv("INSTANA_API_TOKEN", "")
        INSTANA_BASE_URL = args.base_url if args.base_url else os.getenv("INSTANA_BASE_URL", "")

        # --verify-ssl flag overrides INSTANA_SSL_VERIFY env var
        if args.verify_ssl:
            os.environ["INSTANA_SSL_VERIFY"] = "true"

        if args.transport == "stdio" or args.transport is None:
            if not validate_credentials(INSTANA_API_TOKEN, INSTANA_BASE_URL):
                logger.error("Error: Instana credentials are required for stdio mode but not provided. Please set INSTANA_API_TOKEN and INSTANA_BASE_URL environment variables.")
                sys.exit(1)

        # Log SSL verification state at startup so it's always visible
        if _ssl_verify_from_env():
            logger.info("SSL verification is ENABLED")
        else:
            logger.warning("SSL verification is DISABLED. Set INSTANA_SSL_VERIFY=true or pass --verify-ssl to enable.")

        # Create and configure the MCP server
        try:
            enabled_categories = ",".join(enabled)
            # Ensure create_app is always called, even if credentials are missing
            # This is needed for test_main_function_missing_token
            app, registered_tool_count, port = create_app(INSTANA_API_TOKEN, INSTANA_BASE_URL, args.port, enabled_categories)
        except Exception as e:
            print(f"Failed to create MCP server: {e}", file=sys.stderr)
            sys.exit(1)

        # Run the server with the appropriate transport
        if args.transport == "streamable-http":
            if args.debug:
                logger.info(f"FastMCP instance: {app}")
                logger.info(f"Registered tools: {registered_tool_count}")

            try:
                app.run(
                    transport="streamable-http",
                    host="0.0.0.0",
                    port=port,
                    stateless_http=True,
                    # Use JSON responses instead of SSE streaming.
                    # The SSE path uses a zero-buffer MemoryObjectStream; under
                    # simultaneous stateless requests, the _run_sse_writer.send()
                    # call blocks waiting for uvicorn to pull the next SSE chunk,
                    # causing multi-minute hangs when two tool calls race.
                    # json_response=True switches to a buffered (size=16) channel
                    # and returns the result as one atomic JSON HTTP response body,
                    # eliminating the zero-buffer deadlock entirely.
                    json_response=True,
                )
                # app.run() returns normally on graceful shutdown (e.g. SIGTERM).
                # sys.exit(0) gets caught by the except in SystemExit block below
                # and duplicates the "stopped cleanly" log.
                logger.info(f"[server] HTTP server stopped cleanly. Reason: {_shutdown_reason[0]}")
            except SystemExit as e:
                # uvicorn calls sys.exit() internally on fatal errors (e.g. port already in
                # use exits with code 3). SystemExit is not an Exception so it bypasses a
                # plain `except Exception` block — catch it explicitly so we can log the
                # reason before re-raising with the original exit code.
                exit_code = e.code if isinstance(e.code, int) else 1
                if exit_code == 0:
                    logger.info(f"[server] HTTP server stopped cleanly. Reason: {_shutdown_reason[0]}")
                else:
                    logger.error(
                        f"[server] HTTP server stopped with an error (exit code: {exit_code}). "
                        f"Reason: {_shutdown_reason[0]}. "
                        f"Check the uvicorn output above for details (e.g. 'address already in use')."
                    )
                sys.exit(exit_code)
            except Exception as e:
                logger.error(f"[server] HTTP server stopped with an error: {e}", exc_info=True)
                sys.exit(1)
        else:
            logger.info("Starting stdio transport")
            # ----------------------------------------------------------------
            # Stdin pipe proxy — makes Ctrl+C / SIGTERM exit instantly.
            #
            # anyio wraps fd 0 in a worker thread via to_thread.run_sync with
            # abandon_on_cancel=False (shielded), so task cancellation cannot
            # interrupt it.  The only way to unblock it immediately is EOF on
            # fd 0.  We splice a pipe onto fd 0: our signal handlers close the
            # write end → EOF on the read end → readline returns immediately.
            #
            # We guard with hasattr(sys.stdout, 'buffer') to skip the proxy in
            # test environments where stdout is a StringIO (no real fds), which
            # avoids corrupting the test runner's file descriptors.
            # ----------------------------------------------------------------
            # Only install the pipe proxy when stdout is backed by the real
            # fd 1 — i.e. we are running as a proper MCP server process, not
            # under a test runner (which may have real fds but not fd 1 = stdout).
            try:
                _proxy_active = (
                    hasattr(sys.stdout, 'buffer') and
                    hasattr(sys.stdout.buffer, 'raw') and
                    getattr(sys.stdout.buffer.raw, 'fileno', lambda: -1)() == 1
                )
            except Exception:
                _proxy_active = False
            r_fd = -1
            _fwd = None
            _fwd_stop = _threading.Event()
            try:
                if _proxy_active:
                    r_fd, w_fd = os.pipe()
                    _pipe_w[0] = w_fd
                    orig_stdin_fd = os.dup(0)   # save real stdin fd
                    os.dup2(r_fd, 0)            # replace fd 0 with pipe read-end
                    os.close(r_fd)
                    r_fd = -1

                    def _forward_stdin(in_fd: int, out_fd: int) -> None:
                        try:
                            while not _fwd_stop.is_set():
                                ready, _, _ = _select.select([in_fd], [], [], 0.1)
                                if not ready:
                                    continue
                                chunk = os.read(in_fd, 4096)
                                if not chunk:  # EOF on real stdin
                                    break
                                try:
                                    os.write(out_fd, chunk)
                                except OSError:
                                    break
                        except OSError:
                            pass
                        finally:
                            with suppress(OSError):
                                os.close(in_fd)
                            # Real stdin EOF → also close write end so anyio exits
                            _close_pipe_write_end()

                    _fwd = _threading.Thread(
                        target=_forward_stdin,
                        args=(orig_stdin_fd, w_fd),
                        daemon=True,
                    )
                    _fwd.start()

                logger.info("[server] Instana MCP Server is ready and listening on stdio")
                app.run(transport="stdio")
                logger.info("[server] stdio transport stopped cleanly. Reason: %s", _shutdown_reason[0])
            except (SystemExit, KeyboardInterrupt):
                if _shutdown_reason[0] == "unknown":
                    _shutdown_reason[0] = "SIGINT (keyboard interrupt or container stop)"
                logger.info("[server] stdio transport stopped cleanly. Reason: %s", _shutdown_reason[0])
                raise
            except AttributeError as e:
                # Handle the case where sys.stdout is a StringIO object (in tests)
                if "'_io.StringIO' object has no attribute 'buffer'" in str(e):
                    logger.info("Running in test mode, skipping stdio server")
                else:
                    raise
            finally:
                # Signal the forwarder to stop and close the write end.
                # The forwarder wakes within 0.1 s (select timeout) and exits.
                _fwd_stop.set()
                _close_pipe_write_end()
                if _fwd is not None:
                    _fwd.join(timeout=0.5)  # give the forwarder time to exit cleanly
                if r_fd != -1:
                    with suppress(OSError):
                        os.close(r_fd)

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.error("Unhandled exception in main", exc_info=True)
        sys.exit(1)
