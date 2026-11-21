"""
Additional E2E tests for Application Topology MCP Tools
(initialization success path, SDK wiring and import-error handling)
"""

import importlib
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

MODULE_PATH = "src.application.application_topology"


@pytest.fixture(autouse=True)
def _require_real_sdk():
    """Skip when another test module has replaced the SDK with mocks (mixed test runs)."""
    for name in ("instana_client.api", "instana_client.models"):
        if not isinstance(sys.modules.get(name), types.ModuleType):
            pytest.skip(f"{name} is mocked in this session")


def create_application_topology_client(instana_credentials):
    """Dynamically import and create Application Topology client"""
    module = importlib.import_module(MODULE_PATH)
    module = importlib.reload(module)
    return module.ApplicationTopologyMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


class TestApplicationTopologyMoreE2E:
    """Additional end-to-end tests for Application Topology MCP Tools"""

    @pytest.mark.mocked
    def test_initialization_success(self, instana_credentials):
        client = create_application_topology_client(instana_credentials)

        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]
        assert client.topology_api is not None

    @pytest.mark.mocked
    def test_initialization_configures_sdk_client(self, instana_credentials):
        module = importlib.reload(importlib.import_module(MODULE_PATH))
        configuration = MagicMock()
        configuration.api_key = {}
        configuration.api_key_prefix = {}

        with patch.object(module, "Configuration", return_value=configuration), \
                patch.object(module, "ApiClient") as api_client_cls, \
                patch.object(module, "ApplicationTopologyApi") as topology_api_cls:
            client = module.ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"],
            )

        assert configuration.host == instana_credentials["base_url"]
        assert configuration.api_key == {"ApiKeyAuth": instana_credentials["api_token"]}
        assert configuration.api_key_prefix == {"ApiKeyAuth": "apiToken"}
        api_client_cls.assert_called_once_with(configuration=configuration)
        topology_api_cls.assert_called_once_with(api_client=api_client_cls.return_value)
        assert client.topology_api is topology_api_cls.return_value

    @pytest.mark.mocked
    def test_initialization_error_from_api_client(self, instana_credentials):
        module = importlib.reload(importlib.import_module(MODULE_PATH))

        with patch.object(module, "ApiClient", side_effect=Exception("ApiClient Error")), \
                pytest.raises(Exception, match="ApiClient Error"):
            module.ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"],
            )

    @pytest.mark.mocked
    def test_initialization_error_from_configuration(self, instana_credentials):
        module = importlib.reload(importlib.import_module(MODULE_PATH))

        with patch.object(module, "Configuration", side_effect=Exception("Configuration Error")), \
                pytest.raises(Exception, match="Configuration Error"):
            module.ApplicationTopologyMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"],
            )

    @pytest.mark.mocked
    def test_no_tools_are_registered(self, instana_credentials):
        client = create_application_topology_client(instana_credentials)

        assert not hasattr(client, "get_application_topology")

    @pytest.mark.mocked
    def test_import_error_is_logged_and_reraised(self):
        module = importlib.import_module(MODULE_PATH)
        try:
            # A ``None`` entry in sys.modules makes ``from <module> import ...`` raise ImportError.
            with patch.dict(sys.modules, {"instana_client.api.application_topology_api": None}), \
                    pytest.raises(ImportError):
                importlib.reload(module)
        finally:
            # Restore a healthy module so later tests see the real SDK classes.
            importlib.reload(module)

        assert callable(module.ApplicationTopologyMCPTools)
