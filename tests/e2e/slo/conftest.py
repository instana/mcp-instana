"""Local fixtures for these e2e tests."""

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _require_real_instana_sdk():
    """Skip when another test module left a mocked ``instana_client`` in ``sys.modules``.

    Some unit tests replace ``instana_client`` with MagicMocks at import time and do not
    restore it. The e2e tests reload the src modules against the real SDK, so they can only
    run reliably when the real SDK package is loaded.
    """
    for name, module in list(sys.modules.items()):
        if name.split(".")[0] == "instana_client" and isinstance(module, MagicMock):
            pytest.skip("instana_client is mocked in sys.modules by another test module")
