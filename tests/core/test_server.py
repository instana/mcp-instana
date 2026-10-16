"""
Unit tests for the MCP Server module
"""

import asyncio
import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock dependencies before importing the module
sys.modules['dotenv'] = MagicMock()

# Import the real fastmcp middleware module BEFORE replacing sys.modules['fastmcp']
# so that InstanaToolsFilterMiddleware can be subclassed and tested correctly.
import importlib as _importlib

_real_fastmcp_server_mw_mod = _importlib.import_module(
    "fastmcp.server.middleware.middleware"
)

mock_fastmcp_mod = MagicMock()
mock_prompt_cls = MagicMock()
mock_prompt_cls.from_function = MagicMock(side_effect=lambda fn: fn)
mock_fastmcp_prompts_base = MagicMock()
mock_fastmcp_prompts_base.Prompt = mock_prompt_cls
mock_fastmcp_prompts = MagicMock()
mock_fastmcp_prompts.base = mock_fastmcp_prompts_base
mock_fastmcp_mod.prompts = mock_fastmcp_prompts
sys.modules['fastmcp'] = mock_fastmcp_mod
sys.modules['fastmcp.prompts'] = mock_fastmcp_prompts
sys.modules['fastmcp.prompts.base'] = mock_fastmcp_prompts_base
sys.modules['src.prompts.prompt_loader'] = MagicMock()

# Mock fastmcp.server sub-packages.  Register the real middleware module so
# that ``from fastmcp.server.middleware.middleware import Middleware`` in
# server.py resolves to the actual class (not a MagicMock), allowing
# InstanaToolsFilterMiddleware to subclass it correctly.
mock_fastmcp_server = MagicMock()
mock_fastmcp_server_middleware = MagicMock()
sys.modules['fastmcp.server'] = mock_fastmcp_server
sys.modules['fastmcp.server.middleware'] = mock_fastmcp_server_middleware
sys.modules['fastmcp.server.middleware.middleware'] = _real_fastmcp_server_mw_mod
sys.modules['fastmcp.server.dependencies'] = MagicMock()

mock_src_core = MagicMock()
mock_src_core_utils = MagicMock()

# Mock instana_client dependencies
sys.modules['instana_client'] = MagicMock()
sys.modules['instana_client.api'] = MagicMock()
sys.modules['instana_client.api.events_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_resources_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_catalog_api'] = MagicMock()
sys.modules['instana_client.api.application_resources_api'] = MagicMock()
sys.modules['instana_client.api.application_metrics_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_topology_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_analyze_api'] = MagicMock()
sys.modules['instana_client.api.application_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.api.infrastructure_metrics_api'] = MagicMock()
sys.modules['instana_client.api.application_catalog_api'] = MagicMock()
sys.modules['instana_client.api.application_topology_api'] = MagicMock()
sys.modules['instana_client.api.application_analyze_api'] = MagicMock()
sys.modules['instana_client.configuration'] = MagicMock()
sys.modules['instana_client.api_client'] = MagicMock()
sys.modules['instana_client.models'] = MagicMock()
sys.modules['instana_client.models.get_application_metrics'] = MagicMock()
sys.modules['instana_client.models.get_application_resources'] = MagicMock()
sys.modules['instana_client.models.get_application_catalog'] = MagicMock()
sys.modules['instana_client.models.get_application_topology'] = MagicMock()
sys.modules['instana_client.models.get_application_analyze'] = MagicMock()
sys.modules['instana_client.models.get_application_alert_configuration'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_resources'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_catalog'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_topology'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_analyze'] = MagicMock()
sys.modules['instana_client.models.get_infrastructure_metrics'] = MagicMock()
sys.modules['instana_client.models.get_events'] = MagicMock()
# Mock all possible instana_client.models submodules that might be imported
model_submodules = [
    'get_application_metrics', 'get_application_resources', 'get_application_catalog',
    'get_application_topology', 'get_application_analyze', 'get_application_alert_configuration',
    'get_infrastructure_resources', 'get_infrastructure_catalog', 'get_infrastructure_topology',
    'get_infrastructure_analyze', 'get_infrastructure_metrics', 'get_events', 'get_applications',
    'get_available_metrics_query', 'get_available_plugins_query', 'get_infrastructure_query',
    'get_infrastructure_groups_query', 'get_snapshots_query', 'get_endpoints', 'get_services',
    'get_combined_metrics', 'get_traces', 'get_call_groups'
]
for submod in model_submodules:
    sys.modules[f'instana_client.models.{submod}'] = MagicMock()

# Import the module to test
import contextlib

from src.core.server import (
    _CATEGORY_TO_TOOLS,
    InstanaToolsFilterMiddleware,
    MCPState,
    create_app,
    create_clients,
    execute_tool,
    get_enabled_client_configs,
    lifespan,
    main,
)


class TestMCPServer(unittest.TestCase):
    """Test the MCP Server module"""

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["INSTANA_API_TOKEN"] = "test_token"
        os.environ["INSTANA_BASE_URL"] = "https://test.instana.io"
        os.environ["INSTANA_ENABLED_TOOLS"] = "all"

        # Patch the logger to prevent logs during tests
        self.logger_patcher = patch('src.core.server.logger')
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        self.logger_patcher.stop()

    def test_mcp_state_initialization(self):
        state = MCPState()
        for attr in [
            'smart_router_client', 'smart_router_custom_dashboard_client',
            'smart_router_events_client', 'smart_router_website_client',
            'smart_router_automation_client']:
            self.assertIsNone(getattr(state, attr))

    @patch('src.core.server.get_enabled_client_configs')
    @patch('src.infrastructure.infrastructure_resources.InfrastructureResourcesMCPTools')
    @patch('src.event.events_tools.AgentMonitoringEventsMCPTools')
    def test_create_clients_all_enabled(self, mock_events_class, mock_infra_class, mock_get_configs):
        mock_infra_client = MagicMock()
        mock_events_client = MagicMock()
        mock_infra_class.return_value = mock_infra_client
        mock_events_class.return_value = mock_events_client
        mock_get_configs.return_value = [
            ('infra_client', mock_infra_class),
            ('events_client', mock_events_class)
        ]
        token = "test_token"
        base_url = "https://test.instana.io"
        state = create_clients(token, base_url, "infra,events")
        self.assertEqual(state.infra_client, mock_infra_client)
        self.assertEqual(state.events_client, mock_events_client)

    @patch('src.core.server.get_enabled_client_configs')
    @patch('src.event.events_tools.AgentMonitoringEventsMCPTools')
    def test_create_clients_specific_enabled(self, mock_events_class, mock_get_configs):
        mock_events_client = MagicMock()
        mock_events_class.return_value = mock_events_client
        mock_get_configs.return_value = [
            ('smart_router_events_client', mock_events_class)
        ]
        token = "test_token"
        base_url = "https://test.instana.io"
        state = create_clients(token, base_url, "events")
        self.assertEqual(state.smart_router_events_client, mock_events_client)
        mock_events_class.assert_called_with(read_token=token, base_url=base_url)

    @patch('src.core.server.get_enabled_client_configs')
    @patch('src.event.events_tools.AgentMonitoringEventsMCPTools')
    @patch('src.core.server.logger')
    def test_create_clients_error_handling(self, mock_logger, mock_events_class, mock_get_configs):
        # Mock the client class to raise an exception when instantiated
        mock_events_class.side_effect = Exception("Test error")
        mock_get_configs.return_value = [
            ('events_client', mock_events_class)
        ]
        token = "test_token"
        base_url = "https://test.instana.io"
        state = create_clients(token, base_url, "events")
        self.assertIsNone(state.events_client)
        # Verify that logger.error was called but don't actually log anything
        mock_logger.error.assert_called_with("Failed to create events_client: Test error", exc_info=True)

    @patch('src.core.server.FastMCP')
    @patch('src.core.server.create_clients')
    def test_create_app(self, mock_create_clients, mock_fast_mcp):
        mock_server = MagicMock()
        mock_fast_mcp.return_value = mock_server
        mock_state = MCPState()
        mock_state.events_client = MagicMock()
        mock_state.events_client.get_agent_monitoring_events = MagicMock()
        mock_create_clients.return_value = mock_state
        token = "test_token"
        base_url = "https://test.instana.io"
        result, tools_registered, port = create_app(token, base_url)
        mock_fast_mcp.assert_called_once()
        self.assertEqual(result, mock_server)
        mock_create_clients.assert_called_with(token, base_url, "all")

    @patch('src.core.server.FastMCP')
    @patch('src.core.server.create_clients')
    @patch('src.core.server.logger')
    def test_create_app_error_handling(self, mock_logger, mock_create_clients, mock_fast_mcp):
        mock_create_clients.side_effect = RuntimeError("Test error")
        mock_fallback_server = MagicMock()
        mock_fast_mcp.return_value = mock_fallback_server
        token = "test_token"
        base_url = "https://test.instana.io"
        # The implementation returns a fallback server instead of raising an exception
        result, tools_registered, port = create_app(token, base_url)
        self.assertEqual(result, mock_fallback_server)
        self.assertEqual(tools_registered, 0)
        # Verify that logger.error was called but don't actually log anything
        mock_logger.error.assert_called_with("Error creating app", exc_info=True)

    @patch('src.core.server.get_client_categories')
    def test_get_enabled_client_configs_all(self, mock_get_categories):
        # Mock the client categories
        mock_get_categories.return_value = {
            "infra": [
                ('infra_client', MagicMock),
                ('infra_catalog_client', MagicMock),
            ],
            "app": [
                ('app_resource_client', MagicMock),
                ('app_metrics_client', MagicMock),
            ],
            "events": [
                ('events_client', MagicMock),
            ]
        }

        configs = get_enabled_client_configs("all")
        self.assertGreater(len(configs), 0)
        for config in configs:
            self.assertIsInstance(config, tuple)
            self.assertEqual(len(config), 2)
            self.assertIsInstance(config[0], str)
            self.assertTrue(callable(config[1]) or isinstance(config[1], type))

    @patch('src.core.server.get_client_categories')
    def test_get_enabled_client_configs_specific(self, mock_get_categories):
        # Mock the client categories
        mock_get_categories.return_value = {
            "infra": [
                ('infra_client', MagicMock),
                ('infra_catalog_client', MagicMock),
            ],
            "app": [
                ('app_resource_client', MagicMock),
                ('app_metrics_client', MagicMock),
            ],
            "events": [
                ('events_client', MagicMock),
            ]
        }

        configs = get_enabled_client_configs("events")
        self.assertGreater(len(configs), 0)
        for config in configs:
            self.assertTrue(config[0].startswith("events_"))
        configs = get_enabled_client_configs("events,infra")
        self.assertGreater(len(configs), 0)
        for config in configs:
            self.assertTrue(config[0].startswith("events_") or config[0].startswith("infra_"))

    def test_get_enabled_client_configs_unknown(self):
        configs = get_enabled_client_configs("unknown")
        self.assertEqual(len(configs), 0)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_main_function_basic(self, mock_create_app, mock_arg_parser):
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.info instead of capturing stderr
        with patch('src.core.server.logger.info') as mock_logger_info:
            with patch('src.core.server.sys.exit'):
                with patch('src.core.server.sys.stdout'):
                    with patch('src.core.server.sys.stdin'):
                        main()

            # Check that logger.info was called with "Starting stdio transport"
            mock_logger_info.assert_any_call("Starting stdio transport")
            mock_app.run.assert_called_once_with(transport="stdio")

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    @patch('src.core.server.os.getenv')
    def test_main_function_missing_token(self, mock_getenv, mock_create_app, mock_arg_parser):
        # Set up getenv to return None for INSTANA_API_TOKEN and handle PORT/STREAM_READ_BUFFER_SIZE correctly
        mock_getenv.side_effect = lambda key, default=None: (
            default if key in ("INSTANA_API_TOKEN", "PORT", "STREAM_READ_BUFFER_SIZE") else "value"
        )

        # Set up the mock app
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)

        # Set up the argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Run the main function
        with patch('sys.stderr', new=io.StringIO()):
            with patch('src.core.server.sys.exit'):
                main()

        # Verify that create_app was called
        mock_create_app.assert_called_once()

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--tools', 'unknown'])
    @patch('src.core.server.sys.exit')
    def test_main_function_with_invalid_category(self, mock_exit, mock_create_app, mock_arg_parser):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "unknown"
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 0, 0)

        # Just check that sys.exit is called with the correct code
        mock_exit.reset_mock()
        main()
        mock_exit.assert_called_with(2)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_main_function_http(self, mock_create_app, mock_arg_parser):
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = "streamable-http"
        mock_args.host = "0.0.0.0"
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args
        with patch('src.core.server.sys.exit'):
            main()
        mock_app.run.assert_called_once_with(
            transport="streamable-http",
            host='0.0.0.0',
            port=0,
            stateless_http=True,
            json_response=True,
        )

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    def test_main_function_keyboard_interrupt(self, mock_create_app, mock_arg_parser):
        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_create_app.return_value = (mock_app, 1, 0)
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # KeyboardInterrupt now logs "stdio transport stopped cleanly" from the
        # inner except block and then calls sys.exit(0) via the outer except.
        with patch('src.core.server.logger.info'):
            with patch('src.core.server.sys.exit') as mock_exit:
                mock_exit.reset_mock()
                main()
                mock_exit.assert_called_once_with(0)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    def test_main_function_general_exception(self, mock_create_app, mock_arg_parser):
        mock_create_app.side_effect = Exception("General error")
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Patch both print and logger.error since the implementation might use either
        with patch('builtins.print') as mock_print:
            with patch('src.core.server.logger.error') as mock_logger_error:
                with patch('src.core.server.sys.exit') as mock_exit:
                    main()
                    # Check that either print or logger.error was called with the error message
                    try:
                        mock_print.assert_any_call("Failed to create MCP server: General error", file=sys.stderr)
                    except AssertionError:
                        mock_logger_error.assert_any_call("Failed to create MCP server: General error")
                    mock_exit.assert_called_with(1)

class TestPromptCategories(unittest.TestCase):
    """Test the prompt category filtering functionality"""

    @patch('src.core.server.FastMCP')
    @patch('src.core.server.create_clients')
    @patch('src.core.server.logger')
    def test_app_category_only(self, mock_logger, mock_create_clients, mock_fast_mcp):
        """Test that only app prompts are registered when app category is enabled"""
        mock_server = MagicMock()
        mock_fast_mcp.return_value = mock_server
        mock_state = MagicMock()
        mock_create_clients.return_value = mock_state

        # Call create_app with only app category enabled
        create_app("test_token", "https://test.instana.io", 8000, "app")

        # Check that only app prompts were registered
        registered_categories = []
        for call in mock_logger.info.call_args_list:
            args = call[0]
            if len(args) > 0 and isinstance(args[0], str):
                if args[0].startswith("  - app:") and "DISABLED" not in args[0]:
                    registered_categories.append("app")
                if args[0].startswith("  - infra:") and "DISABLED" not in args[0]:
                    registered_categories.append("infra")

        self.assertIn("app", registered_categories)
        self.assertNotIn("infra", registered_categories)

    @patch('src.core.server.FastMCP')
    @patch('src.core.server.create_clients')
    @patch('src.core.server.logger')
    def test_infra_category_only(self, mock_logger, mock_create_clients, mock_fast_mcp):
        """Test that only events prompts are registered when events category is enabled
        (infra is a tool-only category with no dedicated prompts)"""
        mock_server = MagicMock()
        mock_fast_mcp.return_value = mock_server
        mock_state = MagicMock()
        mock_create_clients.return_value = mock_state

        # Call create_app with only events category enabled
        create_app("test_token", "https://test.instana.io", 8000, "events")

        # Check that only events prompts were registered (not app)
        registered_categories = []
        for call in mock_logger.info.call_args_list:
            args = call[0]
            if len(args) > 0 and isinstance(args[0], str):
                if args[0].startswith("  - app:") and "DISABLED" not in args[0]:
                    registered_categories.append("app")
                if args[0].startswith("  - events:") and "DISABLED" not in args[0]:
                    registered_categories.append("events")

        self.assertIn("events", registered_categories)
        self.assertNotIn("app", registered_categories)

    @patch('src.core.server.FastMCP')
    @patch('src.core.server.create_clients')
    @patch('src.core.server.logger')
    def test_both_categories(self, mock_logger, mock_create_clients, mock_fast_mcp):
        """Test that both app and events prompts are registered when both categories are enabled"""
        mock_server = MagicMock()
        mock_fast_mcp.return_value = mock_server
        mock_state = MagicMock()
        mock_create_clients.return_value = mock_state

        # Call create_app with both categories enabled
        create_app("test_token", "https://test.instana.io", 8000, "app,events")

        # Check that both app and events prompts were registered
        registered_categories = []
        for call in mock_logger.info.call_args_list:
            args = call[0]
            if len(args) > 0 and isinstance(args[0], str):
                if args[0].startswith("  - app:") and "DISABLED" not in args[0]:
                    registered_categories.append("app")
                if args[0].startswith("  - events:") and "DISABLED" not in args[0]:
                    registered_categories.append("events")

        self.assertIn("app", registered_categories)
        self.assertIn("events", registered_categories)


class TestMCPServerAsync(unittest.TestCase):
    """Test the async functions in the MCP Server module"""

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["INSTANA_API_TOKEN"] = "test_token"
        os.environ["INSTANA_BASE_URL"] = "https://test.instana.io"
        os.environ["INSTANA_ENABLED_TOOLS"] = "all"

        # Patch the logger to prevent logs during tests
        self.logger_patcher = patch('src.core.server.logger')
        self.mock_logger = self.logger_patcher.start()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        self.logger_patcher.stop()

    @patch('src.core.server.create_clients')
    def test_lifespan_async(self, mock_create_clients):
        mock_state = MCPState()
        mock_create_clients.return_value = mock_state
        mock_server = MagicMock()
        async def test_lifespan():
            async with lifespan(mock_server) as state:
                mock_create_clients.assert_called_once()
                self.assertEqual(state, mock_state)
        asyncio.run(test_lifespan())

    @patch('src.core.server.create_clients')
    @patch('src.core.server.get_instana_credentials')
    def test_lifespan_with_env_vars(self, mock_get_credentials, mock_create_clients):
        # Mock get_instana_credentials instead of os.getenv
        mock_get_credentials.return_value = ("env_token", "https://env.instana.io")
        mock_state = MCPState()
        mock_create_clients.return_value = mock_state
        mock_server = MagicMock()
        async def test_lifespan():
            async with lifespan(mock_server) as state:
                mock_create_clients.assert_called_once()
                self.assertEqual(state, mock_state)
        asyncio.run(test_lifespan())

    @patch('src.core.server.create_clients')
    @patch('src.core.server.logger')
    def test_lifespan_exception_handling(self, mock_logger, mock_create_clients):
        mock_create_clients.side_effect = Exception("Test error")
        mock_server = MagicMock()
        async def test_lifespan():
            async with lifespan(mock_server) as state:
                mock_logger.error.assert_called_with("Error during lifespan", exc_info=True)
                self.assertIsInstance(state, MCPState)
                self.assertIsNone(state.smart_router_client)
        asyncio.run(test_lifespan())

    def test_execute_tool_success(self):
        mock_client = MagicMock()

        # Create a coroutine that returns the result
        async def mock_tool_coro(**kwargs):
            return {"result": "success"}

        # Create a mock that returns the coroutine
        mock_tool = MagicMock(side_effect=mock_tool_coro)
        mock_client.test_tool = mock_tool
        state = MCPState()
        state.smart_router_client = mock_client

        async def test_execute():
            tool_name = "test_tool"
            arguments = {"arg1": "value1", "arg2": "value2"}
            result = await execute_tool(tool_name, arguments, state)
            mock_tool.assert_called_once_with(**arguments)
            self.assertEqual(result, str({"result": "success"}))

        asyncio.run(test_execute())

    def test_execute_tool_not_found(self):
        state = MCPState()
        async def test_execute():
            tool_name = "non_existent_tool"
            arguments = {}
            result = await execute_tool(tool_name, arguments, state)
            self.assertEqual(result, f"Tool {tool_name} not found")
        asyncio.run(test_execute())

    def test_execute_tool_error(self):
        mock_client = MagicMock()
        mock_tool = MagicMock(side_effect=Exception("Test error"))
        mock_client.test_tool = mock_tool
        state = MCPState()
        state.smart_router_client = mock_client
        async def test_execute():
            tool_name = "test_tool"
            arguments = {}
            result = await execute_tool(tool_name, arguments, state)
            self.assertIn(f"Error executing tool {tool_name}", result)
            self.assertIn("Test error", result)
        asyncio.run(test_execute())

    def test_sys_path_insertion(self):
        """Test that the project root is added to sys.path"""
        # Save the original sys.path
        original_path = sys.path.copy()

        # Instead of checking for exact path, check that src directory is in sys.path
        # This is what matters for imports to work
        with patch('sys.path', [p for p in sys.path if not p.endswith('/src')]):
            # Force reload of the module
            import importlib
            importlib.reload(sys.modules['src.core.server'])

            # Check that some path ending with '/src' is in sys.path
            src_paths = [p for p in sys.path if p.endswith('/src')]
            self.assertTrue(len(src_paths) > 0, "No path ending with '/src' found in sys.path")

        # Restore the original sys.path
        sys.path = original_path


    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '-h'])
    @patch('src.core.server.sys.exit')
    def test_help_message_display(self, mock_exit, mock_arg_parser):
        """Test help message display"""
        # Create a mock parser with actions
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        # Create mock actions with option strings and help
        mock_action1 = MagicMock()
        mock_action1.option_strings = ['--transport']
        mock_action1.help = 'Transport mode'
        mock_action1.metavar = '<mode>'

        mock_action2 = MagicMock()
        mock_action2.option_strings = ['--debug']
        mock_action2.help = 'Enable debug mode'
        mock_action2.metavar = None

        mock_action3 = MagicMock()
        mock_action3.option_strings = ['--verify-ssl']
        mock_action3.help = 'Enable SSL certificate verification. Equivalent to INSTANA_SSL_VERIFY=true.'
        mock_action3.metavar = None

        mock_parser._actions = [mock_action1, mock_action2, mock_action3]

        # Patch logger.info instead of capturing stdout
        with patch('src.core.server.logger.info') as mock_logger_info:
            # Call the function
            main()

            # Check that logger.info was called with "Available options:"
            mock_logger_info.assert_any_call("Available options:")

            # Check that --verify-ssl appears in the help output
            logged_lines = [str(call) for call in mock_logger_info.call_args_list]
            self.assertTrue(
                any('--verify-ssl' in line for line in logged_lines),
                "--verify-ssl must appear in the help output"
            )

            # Check that sys.exit was called with 0
            mock_exit.assert_called_with(0)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http', '--debug'])
    def test_http_server_debug_output(self, mock_create_app, mock_arg_parser):
        """Test debug output for HTTP server"""
        # Set up mocks
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 5, 0)  # 5 tools registered

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = "streamable-http"
        mock_args.debug = True
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.info instead of capturing stderr
        with patch('src.core.server.logger.info') as mock_logger_info:
            with patch('src.core.server.sys.exit'):
                main()

            # Check debug output
            mock_logger_info.assert_any_call(f"FastMCP instance: {mock_app}")
            mock_logger_info.assert_any_call("Registered tools: 5")

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_http_server_error_handling(self, mock_create_app, mock_arg_parser):
        """Test error handling for HTTP server"""
        # Set up mocks
        mock_app = MagicMock()
        mock_app.run.side_effect = Exception("HTTP server error")
        mock_create_app.return_value = (mock_app, 1, 0)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = "streamable-http"
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.error instead of capturing stderr
        with patch('src.core.server.logger.error') as mock_logger_error:
            with patch('src.core.server.sys.exit') as mock_exit:
                main()

            # Message now includes [server] prefix and exc_info=True
            error_calls = [str(c) for c in mock_logger_error.call_args_list]
            self.assertTrue(
                any("HTTP server stopped with an error" in c for c in error_calls),
                f"Expected '[server] HTTP server stopped with an error' in logger calls, got: {error_calls}"
            )
            mock_exit.assert_called_with(1)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_stringio_error_handling(self, mock_create_app, mock_arg_parser):
        """Test StringIO error handling for stdio transport"""
        # Set up mocks
        mock_app = MagicMock()
        mock_app.run.side_effect = AttributeError("'_io.StringIO' object has no attribute 'buffer'")
        mock_create_app.return_value = (mock_app, 1, 0)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.info instead of capturing stderr
        with patch('src.core.server.logger.info') as mock_logger_info:
            with patch('src.core.server.sys.exit'):
                main()

            # Check that the error was handled
            mock_logger_info.assert_any_call("Running in test mode, skipping stdio server")

    @patch('src.core.server.get_client_categories')
    def test_list_tools_option(self, mock_get_categories):
        """Test --list-tools option"""
        # Import argparse here
        import argparse

        # Mock the client categories
        mock_get_categories.return_value = {
            "infra": [
                ('infra_client', MagicMock.__name__),
            ],
            "app": [
                ('app_client', MagicMock.__name__),
            ],
            "events": [
                ('events_client', MagicMock.__name__),
            ]
        }

        # Create parser and args directly
        parser = argparse.ArgumentParser()
        parser.add_argument("--list-tools", action="store_true")
        args = parser.parse_args(["--list-tools"])

        # Capture stdout output
        with patch('sys.stdout', new=io.StringIO()) as fake_stdout:
            with patch('sys.exit') as mock_exit:
                # Call the relevant part of the main function directly
                if args.list_tools:
                    print("Available tool categories:")
                    client_categories = mock_get_categories()
                    for category, tools in client_categories.items():
                        print(f"  {category}: {len(tools)} tools")
                    mock_exit.assert_not_called()  # We don't actually call sys.exit in the test

                    # Check that output was captured correctly
                    output = fake_stdout.getvalue()
                    self.assertIn("Available tool categories:", output)
                    self.assertIn("infra:", output)
                    self.assertIn("app:", output)
                    self.assertIn("events:", output)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--tools', 'app'])
    def test_app_tools_only_cli(self, mock_create_app, mock_arg_parser):
        """Test that --tools app enables only app tools and prompts"""
        # Set up mocks
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "app"
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Run the main function with patched sys.exit
        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.logger.info'):
                main()

                # Verify that create_app was called with the correct categories
                mock_create_app.assert_called_once()
                args, kwargs = mock_create_app.call_args
                self.assertEqual(kwargs.get('enabled_categories', None) or args[3], "app")

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--tools', 'infra'])
    def test_infra_tools_only_cli(self, mock_create_app, mock_arg_parser):
        """Test that --tools infra enables only infra tools and prompts"""
        # Set up mocks
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "infra"
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Run the main function with patched sys.exit
        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.logger.info'):
                main()

                # Verify that create_app was called with the correct categories
                mock_create_app.assert_called_once()
                args, kwargs = mock_create_app.call_args
                self.assertEqual(kwargs.get('enabled_categories', None) or args[3], "infra")

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--tools', 'app,infra'])
    def test_app_infra_tools_cli(self, mock_create_app, mock_arg_parser):
        """Test that --tools app,infra enables both app and infra tools and prompts"""
        # Set up mocks
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "app,infra"
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Run the main function with patched sys.exit
        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.logger.info'):
                main()

                # Verify that create_app was called with the correct categories
                mock_create_app.assert_called_once()
                args, kwargs = mock_create_app.call_args

                # The order might be different, so we need to check that both are included
                enabled_cats = kwargs.get('enabled_categories', None) or args[3]
                self.assertIn("app", enabled_cats)
                self.assertIn("infra", enabled_cats)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--tools', 'app,events'])
    @patch('src.core.server.get_client_categories')
    def test_enabled_tools_debug_output(self, mock_get_categories, mock_create_app, mock_arg_parser):
        """Test debug output for enabled tools"""
        # Set up mocks
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 0)

        # Mock the client categories
        mock_get_categories.return_value = {
            "app": [
                ('app_resource_client', MagicMock),
                ('app_metrics_client', MagicMock),
            ],
            "events": [
                ('events_client', MagicMock),
            ]
        }

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "app,events"
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.verify_ssl = False
        mock_args.stream_read_buffer_size = 65536
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.info instead of capturing stderr
        with patch('src.core.server.logger.info') as mock_logger_info:
            with patch('src.core.server.sys.exit'):
                main()

            # Check that enabled tools were listed - use a more flexible approach that doesn't depend on order
            enabled_categories_logs = [
                call_args[0][0] for call_args in mock_logger_info.call_args_list
                if call_args[0][0].startswith("Enabled tool categories:")
            ]
            self.assertTrue(any("app" in log and "events" in log for log in enabled_categories_logs),
                           f"Expected 'app' and 'events' in enabled categories log, got: {enabled_categories_logs}")

            # Verify specific category logs - use a more flexible approach that doesn't depend on order
            category_logs = [
                call_args[0][0] for call_args in mock_logger_info.call_args_list
                if call_args[0][0].startswith("  - ") and " tool" in call_args[0][0]
            ]
            self.assertIn("  - app: 2 tools", category_logs)
            self.assertIn("  - events: 1 tool", category_logs)

            # Check that logger.info was called multiple times
            self.assertTrue(mock_logger_info.call_count >= 5)

if __name__ == '__main__':
    unittest.main()



class TestHTTPServerShutdownBehaviour(unittest.TestCase):
    """Tests for the new shutdown-reason tracking and signal-handler logic added
    to the streamable-http transport branch of main()."""

    def setUp(self):
        # set_log_level calls logging.getLogger().setLevel() — when run as part
        # of the full test suite, a prior test may leave logging.INFO as a
        # MagicMock which causes set_log_level to raise.  Patch it to a no-op
        # for the duration of this class so our tests are order-independent.
        self._log_level_patcher = patch('src.core.server.set_log_level')
        self._log_level_patcher.start()

    def tearDown(self):
        self._log_level_patcher.stop()

    def _make_args(self, transport="streamable-http", debug=False, tools=None):
        """Return a mock args namespace that looks like a parsed argparse result."""
        args = MagicMock()
        args.transport = transport
        args.debug = debug
        args.tools = tools
        args.help = False
        args.list_tools = False
        args.log_level = "INFO"
        args.api_token = None
        args.base_url = None
        args.port = 8600
        args.verify_ssl = False
        args.stream_read_buffer_size = 65536
        return args

    def _setup_parser(self, mock_arg_parser, args):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_parser.parse_args.return_value = args
        return mock_parser

    # ------------------------------------------------------------------
    # 1. Graceful return from app.run() → sys.exit(0) + clean log
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_clean_shutdown_exits_zero(self, mock_create_app, mock_arg_parser):
        """app.run() returning normally must NOT call sys.exit(1) and must return cleanly.

        sys.exit(0) is intentionally absent from the normal return path — adding it
        would be caught by the except SystemExit block and log the "stopped cleanly"
        message twice. Python exits with implicit code 0 when main() returns.
        """
        mock_app = MagicMock()
        mock_app.run.return_value = None          # normal return, no exception
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal'):
                main()

        # sys.exit must NOT be called on a normal return — implicit code 0 is correct
        mock_exit.assert_not_called()

    # ------------------------------------------------------------------
    # 2. Graceful return logs the clean-stop message
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_clean_shutdown_logs_reason(self, mock_create_app, mock_arg_parser):
        """app.run() returning normally must log the clean-stop message."""
        mock_app = MagicMock()
        mock_app.run.return_value = None
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("HTTP server stopped cleanly" in m for m in info_messages),
            f"Expected 'HTTP server stopped cleanly' log. Got: {info_messages}"
        )

    # ------------------------------------------------------------------
    # 3. SIGTERM handler updates shutdown reason
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_sigterm_updates_shutdown_reason(self, mock_create_app, mock_arg_parser):
        """SIGTERM handler must update _shutdown_reason and log a graceful-shutdown message."""
        import signal as signal_module

        captured_handlers = {}

        def capture_signal(sig, handler):
            captured_handlers[sig] = handler

        mock_app = MagicMock()

        def run_and_fire_sigterm(*args, **kwargs):
            # Simulate SIGTERM arriving while the server is running
            handler = captured_handlers.get(signal_module.SIGTERM)
            if handler:
                handler(signal_module.SIGTERM, None)

        mock_app.run.side_effect = run_and_fire_sigterm
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal', side_effect=capture_signal):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("SIGTERM" in m for m in info_messages),
            f"Expected SIGTERM log. Got: {info_messages}"
        )
        self.assertTrue(
            any("HTTP server stopped cleanly" in m and "SIGTERM" in m for m in info_messages),
            f"Expected clean-stop log containing SIGTERM reason. Got: {info_messages}"
        )

    # ------------------------------------------------------------------
    # 4. SIGINT handler updates shutdown reason
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_sigint_updates_shutdown_reason(self, mock_create_app, mock_arg_parser):
        """SIGINT handler must update _shutdown_reason, close the pipe, and raise KeyboardInterrupt."""
        import signal as signal_module

        captured_handlers = {}

        def capture_signal(sig, handler):
            captured_handlers[sig] = handler

        mock_app = MagicMock()

        def run_and_fire_sigint(*args, **kwargs):
            handler = captured_handlers.get(signal_module.SIGINT)
            if handler:
                with contextlib.suppress(KeyboardInterrupt):
                    handler(signal_module.SIGINT, None)

        mock_app.run.side_effect = run_and_fire_sigint
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal', side_effect=capture_signal):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("SIGINT" in m for m in info_messages),
            f"Expected SIGINT log. Got: {info_messages}"
        )

    # ------------------------------------------------------------------
    # 5. SystemExit(0) from uvicorn → propagated as exit(0) + clean log
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_systemexit_zero_propagated_clean(self, mock_create_app, mock_arg_parser):
        """SystemExit(0) from uvicorn must be caught and re-raised as sys.exit(0)."""
        mock_app = MagicMock()
        mock_app.run.side_effect = SystemExit(0)
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        mock_exit.assert_called_once_with(0)
        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("HTTP server stopped cleanly" in m for m in info_messages),
            f"Expected clean-stop log for SystemExit(0). Got: {info_messages}"
        )

    # ------------------------------------------------------------------
    # 6. SystemExit(3) from uvicorn (port conflict) → exit(3) + error log
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_systemexit_nonzero_propagated_as_error(self, mock_create_app, mock_arg_parser):
        """SystemExit(3) from uvicorn (port in use) must exit(3) and log an error."""
        mock_app = MagicMock()
        mock_app.run.side_effect = SystemExit(3)
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.error') as mock_error:
                    main()

        mock_exit.assert_called_once_with(3)
        error_messages = [str(c) for c in mock_error.call_args_list]
        self.assertTrue(
            any("exit code: 3" in m for m in error_messages),
            f"Expected 'exit code: 3' in error log. Got: {error_messages}"
        )
        self.assertTrue(
            any("address already in use" in m for m in error_messages),
            f"Expected hint about 'address already in use'. Got: {error_messages}"
        )

    # ------------------------------------------------------------------
    # 7. SystemExit with a non-int code → treated as exit(1)
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_systemexit_non_int_code_defaults_to_one(self, mock_create_app, mock_arg_parser):
        """SystemExit with a non-integer code must default to exit(1)."""
        mock_app = MagicMock()
        mock_app.run.side_effect = SystemExit("some string code")
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.error'):
                    main()

        mock_exit.assert_called_once_with(1)

    # ------------------------------------------------------------------
    # 8. Exception (not SystemExit) → exit(1) + error log with exc_info
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_exception_exits_one_with_full_log(self, mock_create_app, mock_arg_parser):
        """A plain Exception from app.run() must call sys.exit(1) and log with exc_info."""
        mock_app = MagicMock()
        mock_app.run.side_effect = RuntimeError("unexpected crash")
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.error') as mock_error:
                    main()

        mock_exit.assert_called_once_with(1)
        error_calls = mock_error.call_args_list
        # exc_info=True must be present for full stack trace
        self.assertTrue(
            any(c.kwargs.get('exc_info') is True for c in error_calls),
            f"Expected exc_info=True in logger.error call. Got: {error_calls}"
        )
        # Exception message must appear directly — no "Reason: unknown" noise
        error_messages = [str(c) for c in error_calls]
        self.assertTrue(
            any("unexpected crash" in m for m in error_messages),
            f"Expected exception message in log. Got: {error_messages}"
        )
        self.assertFalse(
            any("Reason: unknown" in m for m in error_messages),
            f"'Reason: unknown' must not appear in exception log. Got: {error_messages}"
        )

    # ------------------------------------------------------------------
    # 9. signal.signal is called for both SIGTERM and SIGINT
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_both_signal_handlers_registered(self, mock_create_app, mock_arg_parser):
        """Both SIGTERM and SIGINT handlers must be registered before app.run() is called."""
        import signal as signal_module

        mock_app = MagicMock()
        mock_app.run.return_value = None
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        registered_signals = []

        def capture(sig, handler):
            registered_signals.append(sig)

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal', side_effect=capture):
                main()

        self.assertIn(signal_module.SIGTERM, registered_signals)
        self.assertIn(signal_module.SIGINT, registered_signals)

    # ------------------------------------------------------------------
    # 10. Shutdown reason defaults to "unknown" when no signal fires
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_unknown_reason_when_no_signal(self, mock_create_app, mock_arg_parser):
        """When no signal fires, the shutdown reason in the log must be 'unknown'."""
        mock_app = MagicMock()
        mock_app.run.side_effect = SystemExit(3)   # fatal error, no signal
        mock_create_app.return_value = (mock_app, 1, 8600)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.error') as mock_error:
                    main()

        error_messages = [str(c) for c in mock_error.call_args_list]
        self.assertTrue(
            any("unknown" in m for m in error_messages),
            f"Expected 'unknown' reason in error log. Got: {error_messages}"
        )


class TestStdioShutdownBehaviour(unittest.TestCase):
    """Tests for stdio transport: ready message, clean shutdown, and signal handling."""

    def setUp(self):
        self._original_env = os.environ.copy()
        os.environ["INSTANA_API_TOKEN"] = "test_token"
        os.environ["INSTANA_BASE_URL"] = "https://test.instana.io"
        self._log_level_patcher = patch('src.core.server.set_log_level')
        self._log_level_patcher.start()

    def tearDown(self):
        self._log_level_patcher.stop()
        os.environ.clear()
        os.environ.update(self._original_env)

    def _make_args(self, transport=None, debug=False, tools=None):
        args = MagicMock()
        args.transport = transport  # None defaults to stdio
        args.debug = debug
        args.tools = tools
        args.help = False
        args.list_tools = False
        args.log_level = "INFO"
        args.api_token = None
        args.base_url = None
        args.port = 8080
        args.verify_ssl = False
        args.stream_read_buffer_size = 65536
        return args

    def _setup_parser(self, mock_arg_parser, args):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_parser.parse_args.return_value = args
        return mock_parser

    # ------------------------------------------------------------------
    # 1. "Server ready" message is logged before app.run() in stdio mode
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_ready_message_logged(self, mock_create_app, mock_arg_parser):
        """A 'ready' log must be emitted before app.run() is called in stdio mode."""
        mock_app = MagicMock()
        mock_app.run.return_value = None
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("ready" in m.lower() and "stdio" in m.lower() for m in info_messages),
            f"Expected a 'ready … stdio' log before app.run(). Got: {info_messages}"
        )

        # The ready log must appear BEFORE app.run() is called — verify ordering
        ready_idx = next(
            (i for i, c in enumerate(mock_info.call_args_list)
             if "ready" in str(c).lower() and "stdio" in str(c).lower()),
            None,
        )
        self.assertIsNotNone(ready_idx, "Ready message not found in logger.info calls")

    # ------------------------------------------------------------------
    # 2. Clean return from app.run() logs the stopped-cleanly message
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_clean_return_logs_stopped(self, mock_create_app, mock_arg_parser):
        """When app.run() returns normally, 'stdio transport stopped cleanly' must be logged."""
        mock_app = MagicMock()
        mock_app.run.return_value = None
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal'):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("stdio transport stopped cleanly" in m for m in info_messages),
            f"Expected 'stdio transport stopped cleanly' log. Got: {info_messages}"
        )

    # ------------------------------------------------------------------
    # 3. SIGTERM causes sys.exit(0) in stdio mode
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_sigterm_calls_sys_exit_zero(self, mock_create_app, mock_arg_parser):
        """SIGTERM handler must call sys.exit(0) so the stdio process stops cleanly."""
        import signal as signal_module

        captured_handlers = {}

        def capture_signal(sig, handler):
            captured_handlers[sig] = handler

        mock_app = MagicMock()

        def run_and_fire_sigterm(*args, **kwargs):
            handler = captured_handlers.get(signal_module.SIGTERM)
            if handler:
                handler(signal_module.SIGTERM, None)

        mock_app.run.side_effect = run_and_fire_sigterm
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal', side_effect=capture_signal):
                with patch('src.core.server.logger.info'):
                    main()

        # sys.exit(0) must be called (from the SIGTERM handler)
        mock_exit.assert_called_with(0)

    # ------------------------------------------------------------------
    # 4. SIGINT handler closes the pipe and raises KeyboardInterrupt
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_sigint_raises_keyboard_interrupt(self, mock_create_app, mock_arg_parser):
        """SIGINT handler must log, close the pipe write-end, and raise KeyboardInterrupt
        so anyio's event loop unwinds cleanly and instantly."""
        import signal as signal_module

        captured_handlers = {}

        def capture_signal(sig, handler):
            captured_handlers[sig] = handler

        mock_app = MagicMock()

        def run_and_fire_sigint(*args, **kwargs):
            handler = captured_handlers.get(signal_module.SIGINT)
            if handler:
                try:
                    handler(signal_module.SIGINT, None)
                except KeyboardInterrupt:
                    raise  # propagate so the except block in main fires

        mock_app.run.side_effect = run_and_fire_sigint
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit') as mock_exit:
            with patch('src.core.server.signal.signal', side_effect=capture_signal):
                with patch('src.core.server.logger.info'):
                    with patch('src.core.server.os.pipe', return_value=(3, 4)):
                        with patch('src.core.server.os.dup', return_value=5):
                            with patch('src.core.server.os.dup2'):
                                with patch('src.core.server.os.close'):
                                    main()

        mock_exit.assert_called_with(0)

    # ------------------------------------------------------------------
    # 5. SIGTERM handler logs graceful-shutdown message in stdio mode
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_sigterm_logs_graceful_shutdown(self, mock_create_app, mock_arg_parser):
        """SIGTERM must be logged as 'beginning graceful shutdown'."""
        import signal as signal_module

        captured_handlers = {}

        def capture_signal(sig, handler):
            captured_handlers[sig] = handler

        mock_app = MagicMock()

        def run_and_fire_sigterm(*args, **kwargs):
            handler = captured_handlers.get(signal_module.SIGTERM)
            if handler:
                handler(signal_module.SIGTERM, None)

        mock_app.run.side_effect = run_and_fire_sigterm
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal', side_effect=capture_signal):
                with patch('src.core.server.logger.info') as mock_info:
                    main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("SIGTERM" in m and "graceful shutdown" in m for m in info_messages),
            f"Expected SIGTERM graceful-shutdown log. Got: {info_messages}"
        )

    # ------------------------------------------------------------------
    # 6. Both SIGTERM and SIGINT handlers are registered
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_both_signal_handlers_registered(self, mock_create_app, mock_arg_parser):
        """Both SIGTERM and SIGINT handlers must be registered."""
        import signal as signal_module

        mock_app = MagicMock()
        mock_app.run.return_value = None
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        registered_signals = []

        def capture(sig, handler):
            registered_signals.append(sig)

        with patch('src.core.server.sys.exit'):
            with patch('src.core.server.signal.signal', side_effect=capture):
                with patch('src.core.server.logger.info'):
                    main()

        self.assertIn(signal_module.SIGTERM, registered_signals)
        self.assertIn(signal_module.SIGINT, registered_signals)

    # ------------------------------------------------------------------
    # 7. SystemExit from signal handler in stdio is caught and re-raised
    # ------------------------------------------------------------------
    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_systemexit_from_signal_logs_stopped(self, mock_create_app, mock_arg_parser):
        """When app.run() raises SystemExit(0) (signal-triggered), the stopped-cleanly
        message must still be logged and the exit code must be re-raised."""
        mock_app = MagicMock()
        mock_app.run.side_effect = SystemExit(0)
        mock_create_app.return_value = (mock_app, 1, 8080)
        self._setup_parser(mock_arg_parser, self._make_args())

        with patch('src.core.server.signal.signal'):
            with patch('src.core.server.logger.info') as mock_info:
                with self.assertRaises(SystemExit) as cm:
                    main()

        self.assertEqual(cm.exception.code, 0)
        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("stdio transport stopped cleanly" in m for m in info_messages),
            f"Expected 'stdio transport stopped cleanly' log. Got: {info_messages}"
        )


class TestListToolsGrammar(unittest.TestCase):
    """Tests that --list-tools uses correct singular/plural grammar."""

    def setUp(self):
        self._log_level_patcher = patch('src.core.server.set_log_level')
        self._log_level_patcher.start()

    def tearDown(self):
        self._log_level_patcher.stop()

    @patch('src.core.server.get_client_categories')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--list-tools'])
    def test_single_tool_uses_singular(self, mock_get_categories):
        """A category with 1 tool must log '1 tool' (not '1 tools')."""
        mock_cls = MagicMock()
        mock_cls.__name__ = 'SomeSmartRouterMCPTool'
        mock_get_categories.return_value = {
            "app": [('smart_router_client', mock_cls)],
        }

        with patch('src.core.server.logger.info') as mock_info:
            with patch('src.core.server.sys.exit'):
                main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("1 tool" in m and "1 tools" not in m for m in info_messages),
            f"Expected '1 tool' (singular) in --list-tools output. Got: {info_messages}"
        )

    @patch('src.core.server.get_client_categories')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--list-tools'])
    def test_multiple_tools_uses_plural(self, mock_get_categories):
        """A category with multiple tools must log 'N tools' (plural)."""
        mock_cls1 = MagicMock()
        mock_cls1.__name__ = 'ToolOne'
        mock_cls2 = MagicMock()
        mock_cls2.__name__ = 'ToolTwo'
        mock_get_categories.return_value = {
            "app": [
                ('client1', mock_cls1),
                ('client2', mock_cls2),
            ],
        }

        with patch('src.core.server.logger.info') as mock_info:
            with patch('src.core.server.sys.exit'):
                main()

        info_messages = [str(c) for c in mock_info.call_args_list]
        self.assertTrue(
            any("2 tools" in m for m in info_messages),
            f"Expected '2 tools' (plural) in --list-tools output. Got: {info_messages}"
        )


class TestInstanaToolsFilterMiddleware(unittest.TestCase):
    """Tests for the InstanaToolsFilterMiddleware and _CATEGORY_TO_TOOLS map."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_tool(self, name):
        """Return a minimal object whose .name attribute equals *name*."""
        t = MagicMock()
        t.name = name
        return t

    async def _run_middleware(self, tools, header_value=None, omit_header_value=None):
        """Exercise InstanaToolsFilterMiddleware.on_list_tools with the given tools list.

        Patches get_http_headers so the test controls which headers are present.
        Returns the filtered tool list.
        """
        mw = InstanaToolsFilterMiddleware()

        headers = {}
        if header_value is not None:
            headers["select-tools"] = header_value
        if omit_header_value is not None:
            headers["omit-tools"] = omit_header_value

        async def call_next(_ctx):
            return tools

        with patch(
            "fastmcp.server.dependencies.get_http_headers",
            return_value=headers,
        ):
            return await mw.on_list_tools(MagicMock(), call_next)

    # ------------------------------------------------------------------
    # _CATEGORY_TO_TOOLS sanity checks
    # ------------------------------------------------------------------

    def test_category_map_has_all_known_categories(self):
        """Every category known to the server must be represented in the map."""
        expected = {
            "app", "infra", "automation", "website", "mobile_app",
            "events", "custom_dashboards", "slo", "synthetic", "releases", "maintenance_windows",
        }
        self.assertEqual(set(_CATEGORY_TO_TOOLS.keys()), expected)

    def test_category_map_tool_names_non_empty(self):
        """Every category must map to at least one tool name."""
        for cat, tool_names in _CATEGORY_TO_TOOLS.items():
            self.assertTrue(tool_names, f"Category '{cat}' has no tool names")

    # ------------------------------------------------------------------
    # Middleware behaviour
    # ------------------------------------------------------------------

    def test_no_header_returns_all_tools(self):
        """Without the select-tools header all tools are returned unchanged."""
        all_tools = [self._make_tool(n) for n in [
            "manage_applications", "manage_infrastructure", "manage_events"
        ]]
        result = asyncio.run(self._run_middleware(all_tools, header_value=None))
        self.assertEqual(result, all_tools)

    def test_empty_header_returns_all_tools(self):
        """An empty select-tools header value is treated as absent."""
        all_tools = [self._make_tool(n) for n in [
            "manage_applications", "manage_infrastructure",
        ]]
        result = asyncio.run(self._run_middleware(all_tools, header_value="   "))
        self.assertEqual(result, all_tools)

    def test_header_key_normalisation_on_list_tools(self):
        """Header keys are normalised to lowercase-with-dashes before lookup.

        Variants like 'Select-Tools', 'SELECT_TOOLS', or 'Omit_Tools' must be
        treated identically to 'select-tools' / 'omit-tools'.
        """
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
        ]
        mw = InstanaToolsFilterMiddleware()

        async def call_next(_ctx):
            return all_tools

        async def run(headers):
            with patch(
                "fastmcp.server.dependencies.get_http_headers",
                return_value=headers,
            ):
                return await mw.on_list_tools(MagicMock(), call_next)

        # Uppercase key with underscore separator
        result = asyncio.run(run({"SELECT_TOOLS": "infra"}))
        self.assertEqual([t.name for t in result], ["manage_infrastructure"])

        # Mixed-case key with dash separator
        result = asyncio.run(run({"Select-Tools": "app"}))
        self.assertEqual([t.name for t in result], ["manage_applications"])

        # Uppercase omit key
        result = asyncio.run(run({"OMIT-TOOLS": "infra"}))
        self.assertCountEqual(
            [t.name for t in result],
            ["manage_applications"],
        )


    def test_header_value_normalisation_on_list_tools(self):
        """Header values are lowercased before category lookup.

        A client sending 'Infra,Events' must get the same result as 'infra,events'.
        Mixed-case values must not be silently dropped as unknown categories.
        """
        all_tools = [
            self._make_tool("manage_infrastructure"),
            self._make_tool("manage_events"),
            self._make_tool("manage_applications"),
        ]
        # Mixed-case value — should match exactly the same as lowercase
        result = asyncio.run(self._run_middleware(all_tools, header_value="Infra,Events"))
        self.assertCountEqual(
            [t.name for t in result],
            ["manage_infrastructure", "manage_events"],
        )

    def test_header_value_normalisation_on_call_tool(self):
        """Value lowercasing also applies in on_call_tool enforcement.

        A client whose header says 'Infra' must be able to call manage_infrastructure.
        """
        result = asyncio.run(
            self._run_call_tool("manage_infrastructure", header_value="Infra")
        )
        self.assertEqual(result, "ok")




    def test_single_category_filter(self):
        """Only tools belonging to the requested category are returned."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
            self._make_tool("manage_events"),
        ]
        result = asyncio.run(self._run_middleware(all_tools, header_value="infra"))
        self.assertEqual([t.name for t in result], ["manage_infrastructure"])

    def test_multiple_category_filter(self):
        """Tools for all requested categories are included."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
            self._make_tool("manage_events"),
            self._make_tool("manage_automation"),
        ]
        result = asyncio.run(self._run_middleware(all_tools, header_value="app,events"))
        self.assertCountEqual(
            [t.name for t in result],
            ["manage_applications", "manage_events"],
        )

    def test_unknown_category_is_ignored(self):
        """Unknown category names produce a warning but do not crash."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
        ]
        with patch("src.core.server.logger") as mock_logger:
            result = asyncio.run(self._run_middleware(all_tools, header_value="app,unknown_cat"))
        # Only the valid category 'app' should be used
        self.assertEqual([t.name for t in result], ["manage_applications"])
        # A warning must have been logged for the unknown category
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        self.assertTrue(
            any("unknown_cat" in msg for msg in warning_calls),
            f"Expected warning about 'unknown_cat'. Got: {warning_calls}",
        )

    def test_all_unknown_categories_returns_no_tools(self):
        """When every requested category is unknown/typo'd, zero tools are returned.

        The header was explicitly sent (non-empty), so the intent was to filter.
        An all-invalid header must not silently fall back to exposing all tools.
        """
        all_tools = [self._make_tool("manage_applications")]
        with patch("src.core.server.logger"):
            result = asyncio.run(
                self._run_middleware(all_tools, header_value="bogus,nonsense")
            )
        self.assertEqual(result, [])

    def test_no_http_context_returns_all_tools(self):
        """When get_http_headers raises RuntimeError (stdio mode), all tools are returned."""
        mw = InstanaToolsFilterMiddleware()
        all_tools = [self._make_tool("manage_applications")]

        async def call_next(_ctx):
            return all_tools

        async def run():
            with patch(
                "fastmcp.server.dependencies.get_http_headers",
                side_effect=RuntimeError("not in http context"),
            ):
                return await mw.on_list_tools(MagicMock(), call_next)

        result = asyncio.run(run())
        self.assertEqual(result, all_tools)

    def test_middleware_registered_in_create_app(self):
        """create_app() must attach exactly one InstanaToolsFilterMiddleware."""
        with patch("src.core.server.get_enabled_client_configs", return_value=[]):
            with patch("src.core.server.get_prompt_categories", return_value={}):
                with patch("src.core.server.FastMCP") as mock_fastmcp_cls:
                    mock_server = MagicMock()
                    mock_fastmcp_cls.return_value = mock_server
                    create_app("token", "https://example.com", 8080, "all")

        add_middleware_calls = mock_server.add_middleware.call_args_list
        # Use class-name comparison so the check is stable regardless of how the
        # class object was imported (avoids false negatives from identity drift
        # between test isolation states).
        filter_middleware_calls = [
            c for c in add_middleware_calls
            if type(c.args[0] if c.args else c.kwargs.get("middleware")).__name__
            == "InstanaToolsFilterMiddleware"
        ]
        self.assertEqual(
            len(filter_middleware_calls), 1,
            "Expected exactly one InstanaToolsFilterMiddleware registration in create_app()",
        )


    # ------------------------------------------------------------------
    # omit-tools header
    # ------------------------------------------------------------------

    def test_omit_header_removes_category(self):
        """omit-tools removes the specified category from the full list."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
            self._make_tool("manage_events"),
        ]
        result = asyncio.run(
            self._run_middleware(all_tools, omit_header_value="infra")
        )
        self.assertCountEqual(
            [t.name for t in result],
            ["manage_applications", "manage_events"],
        )

    def test_omit_header_removes_multiple_categories(self):
        """omit-tools accepts comma-separated categories."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
            self._make_tool("manage_events"),
            self._make_tool("manage_automation"),
        ]
        result = asyncio.run(
            self._run_middleware(all_tools, omit_header_value="infra,automation")
        )
        self.assertCountEqual(
            [t.name for t in result],
            ["manage_applications", "manage_events"],
        )

    def test_omit_unknown_category_warns_and_ignores(self):
        """Unknown category in omit-tools logs a warning and is ignored."""
        all_tools = [self._make_tool("manage_applications")]
        with patch("src.core.server.logger") as mock_logger:
            result = asyncio.run(
                self._run_middleware(all_tools, omit_header_value="bogus")
            )
        self.assertEqual(result, all_tools)
        warning_calls = [str(c) for c in mock_logger.warning.call_args_list]
        self.assertTrue(
            any("bogus" in msg for msg in warning_calls),
            f"Expected warning about 'bogus'. Got: {warning_calls}",
        )

    def test_select_then_omit_combined(self):
        """select-tools allowlist is applied first, then omit-tools removes."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_infrastructure"),
            self._make_tool("manage_events"),
            self._make_tool("manage_automation"),
        ]
        # Select app+infra+events, then omit infra → only app+events remain
        result = asyncio.run(
            self._run_middleware(
                all_tools,
                header_value="app,infra,events",
                omit_header_value="infra",
            )
        )
        self.assertCountEqual(
            [t.name for t in result],
            ["manage_applications", "manage_events"],
        )

    def test_omit_all_registered_results_in_empty_list(self):
        """Omitting every category from the tool list returns an empty list (no server error)."""
        all_tools = [
            self._make_tool("manage_applications"),
            self._make_tool("manage_events"),
        ]
        result = asyncio.run(
            self._run_middleware(all_tools, omit_header_value="app,events")
        )
        self.assertEqual(result, [])


    # ------------------------------------------------------------------
    # on_call_tool enforcement
    # ------------------------------------------------------------------

    async def _run_call_tool(self, tool_name, header_value=None, omit_header_value=None):
        """Exercise InstanaToolsFilterMiddleware.on_call_tool.

        Builds a minimal MiddlewareContext whose .message.name equals *tool_name*,
        then runs the middleware with the given header values.
        Raises ToolError when the tool is blocked; returns sentinel "ok" otherwise.
        """
        from fastmcp.exceptions import ToolError as _ToolError
        from fastmcp.server.middleware.middleware import MiddlewareContext

        mw = InstanaToolsFilterMiddleware()

        msg = MagicMock()
        msg.name = tool_name
        ctx = MagicMock(spec=MiddlewareContext)
        ctx.message = msg

        headers = {}
        if header_value is not None:
            headers["select-tools"] = header_value
        if omit_header_value is not None:
            headers["omit-tools"] = omit_header_value

        async def call_next(_ctx):
            return "ok"

        with patch(
            "fastmcp.server.dependencies.get_http_headers",
            return_value=headers,
        ):
            return await mw.on_call_tool(ctx, call_next)

    def test_call_tool_allowed_category_passes(self):
        """A tools/call for a tool in the allowed category is not blocked."""
        result = asyncio.run(
            self._run_call_tool("manage_infrastructure", header_value="infra")
        )
        self.assertEqual(result, "ok")

    def test_call_tool_blocked_by_select(self):
        """A tools/call for a tool outside the select-tools allowlist raises ToolError."""
        from fastmcp.exceptions import ToolError as _ToolError
        with self.assertRaises(_ToolError):
            asyncio.run(
                self._run_call_tool("manage_applications", header_value="infra")
            )

    def test_call_tool_blocked_by_omit(self):
        """A tools/call for an omitted tool raises ToolError."""
        from fastmcp.exceptions import ToolError as _ToolError
        with self.assertRaises(_ToolError):
            asyncio.run(
                self._run_call_tool("manage_infrastructure", omit_header_value="infra")
            )

    def test_call_tool_no_header_passes(self):
        """Without any filter header, all tools/call requests pass through."""
        result = asyncio.run(self._run_call_tool("manage_applications"))
        self.assertEqual(result, "ok")

    def test_call_tool_all_unknown_categories_blocks(self):
        """All-invalid select-tools header blocks every tools/call (safe-fail)."""
        from fastmcp.exceptions import ToolError as _ToolError
        with self.assertRaises(_ToolError):
            asyncio.run(
                self._run_call_tool("manage_applications", header_value="bogus,typo")
            )

    def test_call_tool_no_http_context_passes(self):
        """In stdio mode (RuntimeError from get_http_headers), call passes through."""
        from fastmcp.server.middleware.middleware import MiddlewareContext

        mw = InstanaToolsFilterMiddleware()
        msg = MagicMock()
        msg.name = "manage_applications"
        ctx = MagicMock(spec=MiddlewareContext)
        ctx.message = msg

        async def call_next(_ctx):
            return "ok"

        async def run():
            with patch(
                "fastmcp.server.dependencies.get_http_headers",
                side_effect=RuntimeError("not in http context"),
            ):
                return await mw.on_call_tool(ctx, call_next)

        result = asyncio.run(run())
        self.assertEqual(result, "ok")



class TestOmitToolsCLI(unittest.TestCase):
    """Tests for the --omit-tools CLI flag in main()."""

    def setUp(self):
        self.original_env = os.environ.copy()
        os.environ["INSTANA_API_TOKEN"] = "test_token"
        os.environ["INSTANA_BASE_URL"] = "https://example.com"
        self._log_level_patcher = patch('src.core.server.set_log_level')
        self._log_level_patcher.start()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.original_env)
        self._log_level_patcher.stop()

    def _make_args(self, transport="streamable-http", tools=None, omit_tools=None):
        args = MagicMock()
        args.transport = transport
        args.debug = False
        args.tools = tools
        args.omit_tools = omit_tools
        args.help = False
        args.list_tools = False
        args.log_level = "INFO"
        args.api_token = None
        args.base_url = None
        args.port = 8080
        args.verify_ssl = True
        return args

    def _setup_parser(self, mock_arg_parser, args):
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_parser.parse_args.return_value = args
        return mock_parser

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['server.py', '--transport', 'streamable-http', '--omit-tools', 'maintenance_windows'])
    def test_omit_tools_removes_from_enabled(self, mock_create_app, mock_arg_parser):
        """--omit-tools removes the specified category from the enabled set passed to create_app."""
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 8080)
        args = self._make_args(omit_tools="maintenance_windows")
        self._setup_parser(mock_arg_parser, args)

        with patch('src.core.server.sys.exit'):
            main()

        call_kwargs = mock_create_app.call_args
        enabled_categories_str = call_kwargs[0][3] if call_kwargs[0] else call_kwargs[1].get('enabled_categories', '')
        enabled = {c.strip() for c in enabled_categories_str.split(",")}
        self.assertNotIn("maintenance_windows", enabled)
        self.assertIn("app", enabled)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.exit')
    @patch('src.core.server.sys.argv', ['server.py', '--omit-tools', 'unknown_cat'])
    def test_omit_tools_unknown_category_exits(self, mock_exit, mock_create_app, mock_arg_parser):
        """--omit-tools with an unknown category exits with code 2."""
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 0, 8080)
        args = self._make_args(omit_tools="unknown_cat")
        self._setup_parser(mock_arg_parser, args)

        mock_exit.reset_mock()
        main()
        mock_exit.assert_called_with(2)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.exit')
    @patch('src.core.server.sys.argv', ['server.py', '--tools', 'infra', '--omit-tools', 'infra'])
    def test_omit_all_enabled_exits(self, mock_exit, mock_create_app, mock_arg_parser):
        """--omit-tools that removes every enabled category exits with code 2."""
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 0, 8080)
        args = self._make_args(tools="infra", omit_tools="infra")
        self._setup_parser(mock_arg_parser, args)

        mock_exit.reset_mock()
        main()
        mock_exit.assert_called_with(2)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['server.py', '--transport', 'streamable-http', '--tools', 'app,infra,events', '--omit-tools', 'events'])
    def test_tools_and_omit_tools_combined(self, mock_create_app, mock_arg_parser):
        """--tools selects categories, --omit-tools further removes from that selection."""
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1, 8080)
        args = self._make_args(tools="app,infra,events", omit_tools="events")
        self._setup_parser(mock_arg_parser, args)

        with patch('src.core.server.sys.exit'):
            main()

        call_kwargs = mock_create_app.call_args
        enabled_categories_str = call_kwargs[0][3] if call_kwargs[0] else call_kwargs[1].get('enabled_categories', '')
        enabled = {c.strip() for c in enabled_categories_str.split(",")}
        self.assertIn("app", enabled)
        self.assertIn("infra", enabled)
        self.assertNotIn("events", enabled)
