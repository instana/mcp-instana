"""
Unit tests for the ApplicationTopologyMCPTools class
"""

import builtins
import logging
import os
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, patch


# Create a null handler that will discard all log messages
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Configure root logger to use ERROR level and disable propagation
logging.basicConfig(level=logging.ERROR)

# Get the application logger and replace its handlers
app_logger = logging.getLogger('src.application.application_topology')
app_logger.handlers = []
app_logger.addHandler(NullHandler())
app_logger.propagate = False

# Add src to path before any imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Create a mock for the with_header_auth decorator
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.topology_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Set up mock modules and classes
mock_mcp = MagicMock()
mock_mcp_types = MagicMock()
mock_tool_annotations = MagicMock()
mock_mcp_types.ToolAnnotations = mock_tool_annotations

mock_instana_client = MagicMock()
mock_instana_api = MagicMock()
mock_topology_api_mod = MagicMock()
mock_instana_api_client = MagicMock()
mock_instana_configuration = MagicMock()
mock_fastmcp = MagicMock()
mock_fastmcp_server = MagicMock()
mock_fastmcp_deps = MagicMock()
mock_pydantic = MagicMock()

# Mock the get_http_headers function
mock_get_http_headers = MagicMock(return_value={})
mock_fastmcp_deps.get_http_headers = mock_get_http_headers

# Set up mock classes
mock_configuration = MagicMock()
mock_api_client = MagicMock()
mock_topology_api = MagicMock()

# Add __name__ attribute to mock classes
mock_topology_api.__name__ = "ApplicationTopologyApi"

mock_instana_configuration.Configuration = mock_configuration
mock_instana_api_client.ApiClient = mock_api_client
mock_instana_api.ApplicationTopologyApi = mock_topology_api

# Mock src.prompts
mock_src_prompts = MagicMock()

# Mock src.core and src.core.utils
mock_src_core = MagicMock()
mock_src_core_utils = MagicMock()

class MockBaseInstanaClient:
    def __init__(self, read_token: str, base_url: str):
        self.read_token = read_token
        self.base_url = base_url

mock_src_core_utils.BaseInstanaClient = MockBaseInstanaClient
mock_src_core_utils.register_as_tool = lambda *args, **kwargs: lambda func: func
mock_src_core_utils.with_header_auth = mock_with_header_auth

# Build the full mocks dict for patch.dict
_mocks = {
    'mcp': mock_mcp,
    'mcp.types': mock_mcp_types,
    'instana_client': mock_instana_client,
    'instana_client.api': mock_instana_api,
    'instana_client.api.application_topology_api': mock_topology_api_mod,
    'instana_client.api_client': mock_instana_api_client,
    'instana_client.configuration': mock_instana_configuration,
    'fastmcp': mock_fastmcp,
    'fastmcp.server': mock_fastmcp_server,
    'fastmcp.server.dependencies': mock_fastmcp_deps,
    'pydantic': mock_pydantic,
    'src.prompts': mock_src_prompts,
    'src.core': mock_src_core,
    'src.core.utils': mock_src_core_utils,
}

# Save original modules before mocking
_original_modules = {}
for module_name in _mocks:
    if module_name in sys.modules:
        _original_modules[module_name] = sys.modules[module_name]

# Apply mocks
for module_name, mock_obj in _mocks.items():
    sys.modules[module_name] = mock_obj

# Now import with the decorator patched
with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.application.application_topology import ApplicationTopologyMCPTools

# Clean up mocks from sys.modules to prevent interference with other tests
for module_name in _mocks:
    if module_name in _original_modules:
        # Restore original module
        sys.modules[module_name] = _original_modules[module_name]
    elif module_name in sys.modules:
        # Remove mock if there was no original
        del sys.modules[module_name]


class TestApplicationTopologyMCPTools(unittest.TestCase):
    """Test the ApplicationTopologyMCPTools class"""

    def setUp(self):
        """Set up test fixtures"""
        # Reset all mocks
        mock_configuration.reset_mock()
        mock_api_client.reset_mock()
        mock_topology_api.reset_mock()

        # Store references to the global mocks
        self.mock_configuration = mock_configuration
        self.mock_api_client = mock_api_client
        self.topology_api = MagicMock()

        # Create the client
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"

        # Patch Configuration and ApiClient for initialization
        with patch('src.application.application_topology.Configuration', return_value=mock_configuration), \
             patch('src.application.application_topology.ApiClient', return_value=mock_api_client), \
             patch('src.application.application_topology.ApplicationTopologyApi', return_value=self.topology_api):
            self.client = ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

    def test_init_success(self):
        """Test that the client is initialized with the correct values"""
        self.assertEqual(self.client.read_token, self.read_token)
        self.assertEqual(self.client.base_url, self.base_url)
        self.assertIsNotNone(self.client.topology_api)

    def test_init_with_different_credentials(self):
        """Test initialization with different credentials"""
        different_token = "different_token"
        different_url = "https://different.instana.io"

        with patch('src.application.application_topology.Configuration', return_value=mock_configuration), \
             patch('src.application.application_topology.ApiClient', return_value=mock_api_client), \
             patch('src.application.application_topology.ApplicationTopologyApi', return_value=self.topology_api):
            client = ApplicationTopologyMCPTools(read_token=different_token, base_url=different_url)

        self.assertEqual(client.read_token, different_token)
        self.assertEqual(client.base_url, different_url)

    def test_init_configuration_setup(self):
        """Test that Configuration is set up correctly during initialization"""
        mock_config = MagicMock()
        mock_config.api_key = {}
        mock_config.api_key_prefix = {}

        with patch('src.application.application_topology.create_instana_configuration', return_value=mock_config) as mock_create_config, \
             patch('src.application.application_topology.ApiClient', return_value=mock_api_client), \
             patch('src.application.application_topology.ApplicationTopologyApi', return_value=self.topology_api):
            ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

            # Verify create_instana_configuration was called with the base_url
            mock_create_config.assert_called_once_with(self.base_url)
            # Verify configuration properties were set on the returned config
            self.assertEqual(mock_config.api_key['ApiKeyAuth'], self.read_token)
            self.assertEqual(mock_config.api_key_prefix['ApiKeyAuth'], 'apiToken')

    def test_init_api_client_creation(self):
        """Test that ApiClient is created with the configuration"""
        mock_config = MagicMock()
        mock_config.api_key = {}
        mock_config.api_key_prefix = {}

        with patch('src.application.application_topology.create_instana_configuration', return_value=mock_config), \
             patch('src.application.application_topology.ApiClient', return_value=mock_api_client) as mock_api_client_class, \
             patch('src.application.application_topology.ApplicationTopologyApi', return_value=self.topology_api):
            ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

            # Verify ApiClient was called with the configuration
            mock_api_client_class.assert_called_once_with(configuration=mock_config)

    def test_init_topology_api_creation(self):
        """Test that ApplicationTopologyApi is created with the API client"""
        mock_config = MagicMock()

        with patch('src.application.application_topology.Configuration', return_value=mock_config), \
             patch('src.application.application_topology.ApiClient', return_value=mock_api_client), \
             patch('src.application.application_topology.ApplicationTopologyApi', return_value=self.topology_api) as mock_topology_api_class:
            client = ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

            # Verify ApplicationTopologyApi was called with the API client
            mock_topology_api_class.assert_called_once_with(api_client=mock_api_client)
            # Verify the topology_api attribute was set
            self.assertEqual(client.topology_api, self.topology_api)

    def test_init_exception_handling(self):
        """Test that initialization handles exceptions properly"""
        with patch('src.application.application_topology.create_instana_configuration', side_effect=Exception("Config error")), \
             patch('src.application.application_topology.logger') as mock_logger:
            with self.assertRaises(Exception):
                ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

            # Verify the exception was logged
            mock_logger.error.assert_called_once()
            self.assertIn("Error initializing ApplicationTopologyMCPTools", str(mock_logger.error.call_args))

    def test_init_api_client_exception(self):
        """Test initialization when ApiClient creation fails"""
        mock_config = MagicMock()

        with patch('src.application.application_topology.Configuration', return_value=mock_config), \
             patch('src.application.application_topology.ApiClient', side_effect=Exception("API client error")), \
             patch('src.application.application_topology.logger') as mock_logger:
            with self.assertRaises(Exception):
                ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

            # Verify the exception was logged
            mock_logger.error.assert_called_once()
            self.assertIn("Error initializing ApplicationTopologyMCPTools", str(mock_logger.error.call_args))

    def test_init_topology_api_exception(self):
        """Test initialization when ApplicationTopologyApi creation fails"""
        mock_config = MagicMock()

        with patch('src.application.application_topology.Configuration', return_value=mock_config), \
             patch('src.application.application_topology.ApiClient', return_value=mock_api_client), \
             patch('src.application.application_topology.ApplicationTopologyApi', side_effect=Exception("Topology API error")), \
             patch('src.application.application_topology.logger') as mock_logger:
            with self.assertRaises(Exception):
                ApplicationTopologyMCPTools(read_token=self.read_token, base_url=self.base_url)

            # Verify the exception was logged
            mock_logger.error.assert_called_once()
            self.assertIn("Error initializing ApplicationTopologyMCPTools", str(mock_logger.error.call_args))

    def test_inherits_from_base_instana_client(self):
        """Test that ApplicationTopologyMCPTools inherits from BaseInstanaClient"""
        self.assertIsInstance(self.client, MockBaseInstanaClient)

    def test_import_error_branch_logs_and_raises(self):
        """Test module import error handling when Instana SDK import fails"""
        module_name = 'src.application.application_topology'
        original_module = sys.modules.get(module_name)
        real_import = builtins.__import__

        def failing_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'instana_client.api.application_topology_api':
                raise ImportError("SDK missing")
            return real_import(name, globals, locals, fromlist, level)

        try:
            if module_name in sys.modules:
                del sys.modules[module_name]

            with patch('builtins.__import__', side_effect=failing_import), \
                 patch('logging.getLogger') as mock_get_logger, \
                 patch('traceback.print_exc') as mock_print_exc:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                with self.assertRaises(ImportError) as context:
                    __import__(module_name, fromlist=['ApplicationTopologyMCPTools'])

                self.assertIn("SDK missing", str(context.exception))
                mock_logger.error.assert_called_once()
                self.assertIn("Error importing Instana SDK", mock_logger.error.call_args.args[0])
                mock_print_exc.assert_called_once()
        finally:
            if original_module is not None:
                sys.modules[module_name] = original_module
            elif module_name in sys.modules:
                del sys.modules[module_name]


if __name__ == '__main__':
    unittest.main()

