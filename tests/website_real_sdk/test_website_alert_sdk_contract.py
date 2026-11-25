"""Contract test for ``_raw_call`` against the real instana-client SDK.

``_raw_call`` relies on private SDK methods (``_*_serialize`` and the ``call_api`` tuple shape),
so this fails loudly if an SDK upgrade changes them. It runs in a subprocess so the real SDK
is used regardless of the sys.modules stubs that other test modules install.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_SCRIPT = textwrap.dedent(
    """
    import json
    from unittest.mock import MagicMock, patch

    from instana_client.api.event_settings_api import EventSettingsApi
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration

    from src.website.website_alert import _raw_call

    BASE = "https://x.instana.io/api/events/settings/website-alert-configs"
    payload = {"name": "n", "rules": [{"x": 1}], "futureField": 1}


    def api():
        cfg = Configuration(host="https://x.instana.io")
        cfg.api_key["ApiKeyAuth"], cfg.api_key_prefix["ApiKeyAuth"] = "T", "apiToken"
        return EventSettingsApi(ApiClient(cfg))


    def sent(serialize_name, **kwargs):
        a = api()
        with patch.object(a.api_client.rest_client.pool_manager, "request") as rq:
            rq.return_value = MagicMock(status=200, data=b"{}")
            _raw_call(a, serialize_name, website_alert_config=payload, **kwargs)
        return rq.call_args


    call = sent("_create_website_alert_config_serialize")
    assert call.args == ("POST", BASE), call.args
    assert json.loads(call.kwargs["body"]) == payload
    assert call.kwargs["timeout"] is not None  # HTTP-level timeout is applied

    call = sent("_update_website_alert_config_serialize", id="abc")
    assert call.args == ("POST", BASE + "/abc"), call.args
    assert json.loads(call.kwargs["body"]) == payload
    print("OK")
    """
)


def test_raw_call_matches_real_sdk_serializer():
    result = subprocess.run(
        [sys.executable, "-c", _SCRIPT], cwd=REPO_ROOT, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0 and "OK" in result.stdout, result.stderr or result.stdout
