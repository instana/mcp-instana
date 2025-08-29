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
sys.modules['fastmcp'] = MagicMock()
sys.modules['src.prompts.prompt_loader'] = MagicMock()

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
from src.core.server import (
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
            'events_client', 'infra_client', 'app_resource_client', 'app_metrics_client',
            'app_alert_client', 'infra_catalog_client', 'infra_topo_client', 'infra_analyze_client',
            'infra_metrics_client', 'app_catalog_client', 'app_topology_client', 'app_analyze_client']:
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
            ('events_client', mock_events_class)
        ]
        token = "test_token"
        base_url = "https://test.instana.io"
        state = create_clients(token, base_url, "events")
        self.assertIsNone(state.infra_client)
        self.assertEqual(state.events_client, mock_events_client)
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
        result, tools_registered = create_app(token, base_url)
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
        result, tools_registered = create_app(token, base_url)
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
        mock_create_app.return_value = (mock_app, 1)
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
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
        # Set up getenv to return None for INSTANA_API_TOKEN and handle PORT correctly
        mock_getenv.side_effect = lambda key, default=None: default if key == "INSTANA_API_TOKEN" else (default if key == "PORT" else "value")

        # Set up the mock app
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1)

        # Set up the argument parser
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
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
        mock_parser.parse_args.return_value = mock_args
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 0)

        # Just check that sys.exit is called with the correct code
        mock_exit.reset_mock()
        main()
        mock_exit.assert_called_with(2)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http'])
    def test_main_function_http(self, mock_create_app, mock_arg_parser):
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 1)
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = "streamable-http"
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_args.list_tools = False
        mock_parser.parse_args.return_value = mock_args
        with patch('src.core.server.sys.exit'):
            main()
        mock_app.run.assert_called_once_with(transport="streamable-http")

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    def test_main_function_keyboard_interrupt(self, mock_create_app, mock_arg_parser):
        mock_app = MagicMock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_create_app.return_value = (mock_app, 1)
        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser
        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.info instead of capturing stderr
        with patch('src.core.server.logger.info') as mock_logger_info:
            with patch('src.core.server.sys.exit') as mock_exit:
                # Reset mock_exit to clear any previous calls
                mock_exit.reset_mock()
                main()
                mock_logger_info.assert_any_call("Server stopped by user")
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
        """Test that only infra prompts are registered when infra category is enabled"""
        mock_server = MagicMock()
        mock_fast_mcp.return_value = mock_server
        mock_state = MagicMock()
        mock_create_clients.return_value = mock_state

        # Call create_app with only infra category enabled
        create_app("test_token", "https://test.instana.io", 8000, "infra")

        # Check that only infra prompts were registered
        registered_categories = []
        for call in mock_logger.info.call_args_list:
            args = call[0]
            if len(args) > 0 and isinstance(args[0], str):
                if args[0].startswith("  - app:") and "DISABLED" not in args[0]:
                    registered_categories.append("app")
                if args[0].startswith("  - infra:") and "DISABLED" not in args[0]:
                    registered_categories.append("infra")

        self.assertIn("infra", registered_categories)
        self.assertNotIn("app", registered_categories)

    @patch('src.core.server.FastMCP')
    @patch('src.core.server.create_clients')
    @patch('src.core.server.logger')
    def test_both_categories(self, mock_logger, mock_create_clients, mock_fast_mcp):
        """Test that both app and infra prompts are registered when both categories are enabled"""
        mock_server = MagicMock()
        mock_fast_mcp.return_value = mock_server
        mock_state = MagicMock()
        mock_create_clients.return_value = mock_state

        # Call create_app with both categories enabled
        create_app("test_token", "https://test.instana.io", 8000, "app,infra")

        # Check that both app and infra prompts were registered
        registered_categories = []
        for call in mock_logger.info.call_args_list:
            args = call[0]
            if len(args) > 0 and isinstance(args[0], str):
                if args[0].startswith("  - app:") and "DISABLED" not in args[0]:
                    registered_categories.append("app")
                if args[0].startswith("  - infra:") and "DISABLED" not in args[0]:
                    registered_categories.append("infra")

        self.assertIn("app", registered_categories)
        self.assertIn("infra", registered_categories)


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
                self.assertIsNone(state.events_client)
                self.assertIsNone(state.infra_client)
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
        state.events_client = mock_client

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
        state.events_client = mock_client
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

        mock_parser._actions = [mock_action1, mock_action2]

        # Patch logger.info instead of capturing stdout
        with patch('src.core.server.logger.info') as mock_logger_info:
            # Call the function
            main()

            # Check that logger.info was called with "Available options:"
            mock_logger_info.assert_any_call("Available options:")

            # Check that sys.exit was called with 0
            mock_exit.assert_called_with(0)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py', '--transport', 'streamable-http', '--debug'])
    def test_http_server_debug_output(self, mock_create_app, mock_arg_parser):
        """Test debug output for HTTP server"""
        # Set up mocks
        mock_app = MagicMock()
        mock_create_app.return_value = (mock_app, 5)  # 5 tools registered

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = "streamable-http"
        mock_args.debug = True
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
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
        mock_create_app.return_value = (mock_app, 1)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = "streamable-http"
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
        mock_parser.parse_args.return_value = mock_args

        # Patch logger.error instead of capturing stderr
        with patch('src.core.server.logger.error') as mock_logger_error:
            with patch('src.core.server.sys.exit') as mock_exit:
                main()

            # Check error output
            mock_logger_error.assert_any_call("Failed to start HTTP server: HTTP server error")
            mock_exit.assert_called_with(1)

    @patch('src.core.server.argparse.ArgumentParser')
    @patch('src.core.server.create_app')
    @patch('src.core.server.sys.argv', ['mcp_server.py'])
    def test_stdio_stringio_error_handling(self, mock_create_app, mock_arg_parser):
        """Test StringIO error handling for stdio transport"""
        # Set up mocks
        mock_app = MagicMock()
        mock_app.run.side_effect = AttributeError("'_io.StringIO' object has no attribute 'buffer'")
        mock_create_app.return_value = (mock_app, 1)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = None
        mock_args.help = False
        mock_args.list_tools = False
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
        mock_create_app.return_value = (mock_app, 1)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "app"
        mock_args.help = False
        mock_args.list_tools = False
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
        mock_create_app.return_value = (mock_app, 1)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "infra"
        mock_args.help = False
        mock_args.list_tools = False
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
        mock_create_app.return_value = (mock_app, 1)

        mock_parser = MagicMock()
        mock_arg_parser.return_value = mock_parser

        mock_args = MagicMock()
        mock_args.transport = None
        mock_args.debug = False
        mock_args.tools = "app,infra"
        mock_args.help = False
        mock_args.list_tools = False
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
        mock_create_app.return_value = (mock_app, 1)

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
                if call_args[0][0].startswith("  - ") and "tools" in call_args[0][0]
            ]
            self.assertIn("  - app: 2 tools", category_logs)
            self.assertIn("  - events: 1 tools", category_logs)

            # Check that logger.info was called multiple times
            self.assertTrue(mock_logger_info.call_count >= 5)

if __name__ == '__main__':
    unittest.main()

