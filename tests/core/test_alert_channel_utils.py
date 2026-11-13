"""
Unit and drift tests for Alert Channel Masking Utilities.
"""

from __future__ import annotations

import importlib
import json
import logging
import sys
from typing import Any
from unittest.mock import patch

import pytest

from src.core import alert_channel_utils
from src.core.alert_channel_utils import (
    ALLOWED_EXCEPTIONS,
    ALLOWED_FIELDS_BY_KIND,
    COMMON_SHOWN_FIELDS,
    KNOWN_CREDENTIAL_FIELDS,
    SAFE_URL_KEYS,
    STRUCTURED_CREDENTIAL_FIELDS,
    UNSAFE_URL_KEYS,
    is_known_credential,
    mask_channel,
    mask_header_entry,
    mask_webhook_url,
    normalize_key,
    redact_for_log,
)


@pytest.fixture
def AbstractIntegration():  # noqa: N802
    """Load the *real* SDK model for drift tests without polluting sys.modules.

    Other test modules replace ``instana_client*`` in sys.modules with mocks. The drift
    tests need the real models, so temporarily drop any such mocks, import the real
    package, and restore sys.modules exactly as it was afterwards.
    """
    with patch.dict(sys.modules):
        for name in [m for m in sys.modules if m == "instana_client" or m.startswith("instana_client.")]:
            del sys.modules[name]
        module = importlib.import_module("instana_client.models.abstract_integration")
        yield module.AbstractIntegration


class TestAlertChannelUtils:
    """Test suite for alert channel security masking and drift detection."""

    def test_drift_every_sdk_kind_is_covered(self, AbstractIntegration):
        """1. Every SDK kind in AbstractIntegration discriminator map is in ALLOWED_FIELDS_BY_KIND."""
        discriminator_map = AbstractIntegration._AbstractIntegration__discriminator_value_class_map
        assert set(discriminator_map.keys()) == set(ALLOWED_FIELDS_BY_KIND.keys())

    def test_drift_every_sdk_field_is_classified(self, AbstractIntegration):
        """2. Every field on every SDK integration model is classified."""
        discriminator_map = AbstractIntegration._AbstractIntegration__discriminator_value_class_map
        common_normalized = {normalize_key(f) for f in COMMON_SHOWN_FIELDS}

        import re

        def _to_snake_case(name: str) -> str:
            # Handle acronyms like MS, NS1, ZChat, AIOps, etc.
            s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
            s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
            return s.lower()

        # Custom mappings if standard snake_case conversion differs from openapi generator filename
        module_name_overrides = {
            "ServiceNowEnhancedIntegration": "service_now_enhanced_integration",
            "ServiceNowIntegration": "service_now_integration",
            "NS1Integration": "ns1_integration",
            "Office365Integration": "office365_integration",
            "ZChatOpsIntegration": "z_chat_ops_integration",
            "WatsonAIOpsWebhookIntegration": "watson_ai_ops_webhook_integration",
            "BidirectionalMsTeamsAppIntegration": "bidirectional_ms_teams_app_integration",
            "BidirectionalSlackAppIntegration": "bidirectional_slack_app_integration",
            "WebexTeamsWebhookIntegration": "webex_teams_webhook_integration",
        }

        for kind, class_name in discriminator_map.items():
            module_name = module_name_overrides.get(class_name, _to_snake_case(class_name))
            try:
                mod_pkg = importlib.import_module(f"instana_client.models.{module_name}")
                mod = getattr(mod_pkg, class_name)
            except Exception as e:
                pytest.fail(f"Could not import {class_name} from instana_client.models.{module_name}: {e}")

            # Check model properties / fields
            fields = getattr(mod, "model_fields", {})
            for field_name, field_info in fields.items():
                wire_name = getattr(field_info, "alias", None) or field_name
                norm_wire = normalize_key(wire_name)
                norm_field = normalize_key(field_name)

                # Field must be common, or in allowed set, or in known credentials / structured fields
                allowed_paths = ALLOWED_FIELDS_BY_KIND[kind]
                allowed_norm = {normalize_key(p.split(".")[-1]) for p in allowed_paths}

                is_classified = (
                    norm_wire in common_normalized
                    or norm_field in common_normalized
                    or norm_wire in allowed_norm
                    or norm_field in allowed_norm
                    or is_known_credential(wire_name)
                    or is_known_credential(field_name)
                    or norm_wire in STRUCTURED_CREDENTIAL_FIELDS
                    or norm_field in STRUCTURED_CREDENTIAL_FIELDS
                )
                assert is_classified, (
                    f"Unclassified field '{wire_name}' ({field_name}) in kind '{kind}' ({class_name})"
                )

    def test_drift_allow_list_vs_credential_names(self):
        """3. Leaf key names in shown paths must not contain credential keywords unless in ALLOWED_EXCEPTIONS."""
        cred_substrings = (
            "secret",
            "password",
            "token",
            "apikey",
            "privatekey",
            "credential",
            "authorization",
            "routingkey",
            "integrationkey",
        )

        for kind, paths in ALLOWED_FIELDS_BY_KIND.items():
            for path in paths:
                if path in ALLOWED_EXCEPTIONS:
                    continue
                leaf = path.split(".")[-1]
                norm_leaf = normalize_key(leaf)
                for cred in cred_substrings:
                    assert cred not in norm_leaf, (
                        f"Potentially sensitive leaf key '{leaf}' (matching '{cred}') "
                        f"found in allow-list for kind '{kind}' at path '{path}'. "
                        f"If intentional, add to ALLOWED_EXCEPTIONS."
                    )

    def test_sentinel_round_trip_per_kind(self):
        """4. Sentinel values in secret fields are masked and never appear in output."""
        sentinel = "SENTINEL-SUPER-SECRET-12345"
        test_fixtures: dict[str, dict[str, Any]] = {
            "WEB_HOOK": {
                "id": "wh-1",
                "kind": "WEB_HOOK",
                "name": "Webhook Channel",
                "webhookUrls": [f"https://hooks.example.com/services/{sentinel}"],
                "headers": [f"Authorization: Bearer {sentinel}"],
                "oauth": {
                    "config": {
                        "clientId": "client-id",
                        "clientSecret": sentinel,
                        "password": sentinel,
                    },
                    "token": {
                        "accessToken": sentinel,
                        "refreshToken": sentinel,
                    },
                },
            },
            "SLACK": {
                "id": "slack-1",
                "kind": "SLACK",
                "name": "Slack Channel",
                "channel": "#alerts",
                "webhookUrl": f"https://hooks.slack.com/services/{sentinel}",
            },
            "PAGER_DUTY": {
                "id": "pd-1",
                "kind": "PAGER_DUTY",
                "name": "PagerDuty",
                "serviceIntegrationKey": sentinel,
            },
            "OPS_GENIE": {
                "id": "og-1",
                "kind": "OPS_GENIE",
                "name": "Opsgenie",
                "apiKey": sentinel,
                "region": "US",
            },
            "SERVICE_NOW_WEBHOOK": {
                "id": "snow-1",
                "kind": "SERVICE_NOW_WEBHOOK",
                "name": "ServiceNow",
                "serviceNowUrl": "https://snow.example.com",
                "username": "admin",
                "password": sentinel,
            },
            "SPLUNK": {
                "id": "sp-1",
                "kind": "SPLUNK",
                "name": "Splunk",
                "url": "https://splunk.example.com",
                "token": sentinel,
            },
            "SALESFORCE": {
                "id": "sf-1",
                "kind": "SALESFORCE",
                "name": "Salesforce",
                "salesforceUrl": "https://salesforce.example.com",
                "clientId": "sf-client",
                "bearerToken": sentinel,
                "clientSecret": sentinel,
            },
            "Z_CHATOPS": {
                "id": "zc-1",
                "kind": "Z_CHATOPS",
                "name": "ZChatOps",
                "zchatOpsIncidentsUrl": "https://zchat.example.com",
                "channels": ["chan1"],
                "bearerAuthToken": sentinel,
            },
        }

        for kind, fixture in test_fixtures.items():
            masked = mask_channel(fixture)
            dumped = json.dumps(masked)
            assert sentinel not in dumped, f"Sentinel found in masked output for kind '{kind}': {dumped}"
            # Ensure safe fields are preserved
            assert masked["id"] == fixture["id"]
            assert masked["name"] == fixture["name"]
            assert masked["kind"] == kind

    def test_mixed_type_list_masking(self):
        """Test that mixed-type lists with nested dictionaries/URLs are correctly masked."""
        fixture = {
            "id": "mixed-1",
            "kind": "WEB_HOOK",
            "name": "Mixed List Integration",
            "webhookUrls": [
                None,
                "https://hooks.example.com/services/secret_key_123"
            ]
        }
        masked = mask_channel(fixture)
        assert masked["webhookUrls"][0] is None
        assert masked["webhookUrls"][1] == "***"

    def test_nested_list_items_are_masked_recursively(self):
        """Dicts nested inside lists inside allow-listed lists must still be masked."""
        fixture = {
            "id": "nested-1",
            "kind": "EMAIL",
            "name": "Nested List Integration",
            "emails": [
                "ops@example.com",
                [{"apiKey": "s3cr3t", "unknownField": "hidden"}, ["ok", {"password": "p4ss"}]],
            ],
        }
        masked = mask_channel(fixture)
        assert masked["emails"][0] == "ops@example.com"
        assert masked["emails"][1][0] == {"apiKey": "***", "unknownField": "***"}
        assert masked["emails"][1][1][0] == "ok"
        assert masked["emails"][1][1][1] == {"password": "***"}
        dumped = json.dumps(masked)
        assert "s3cr3t" not in dumped
        assert "p4ss" not in dumped

    def test_unknown_field_fails_closed(self):
        """5. Unknown fields and unknown kinds fail closed (values replaced with ***)."""
        fixture = {
            "id": "unknown-1",
            "kind": "FUTURE_UNKNOWN_INTEGRATION",
            "name": "Future Integration",
            "unrecognizedSecret": "confidential_data_999",
            "nestedObject": {
                "deepSecret": "deep_data_123",
            },
        }

        masked = mask_channel(fixture)
        assert masked["id"] == "unknown-1"
        assert masked["name"] == "Future Integration"
        assert masked["kind"] == "FUTURE_UNKNOWN_INTEGRATION"
        assert masked["unrecognizedSecret"] == "***"
        assert masked["nestedObject"]["deepSecret"] == "***"

    def test_allow_listed_url_fields_strip_embedded_credentials(self):
        """Allow-listed URL fields must not leak credentials in query string or userinfo."""
        sentinel = "URL-SENTINEL-SECRET-777"
        fixtures = [
            {
                "kind": "SERVICE_NOW_WEBHOOK",
                "serviceNowUrl": f"https://dev1.service-now.com/login.do?user_name=admin&user_password={sentinel}",
                "password": sentinel,
            },
            {
                "kind": "SALESFORCE",
                "salesforceUrl": f"https://admin:{sentinel}@example.my.salesforce.com/path?x=1#{sentinel}",
            },
            {
                "kind": "Z_CHATOPS",
                "zchatOpsIncidentsUrl": f"https://webhook.site/{sentinel}",
            },
        ]
        for fixture in fixtures:
            dumped = json.dumps(mask_channel(fixture))
            assert sentinel not in dumped, f"Sentinel leaked for {fixture['kind']}: {dumped}"

        # URL fields are masked completely (host included) to avoid exposing internal URLs
        snow = mask_channel(fixtures[0])
        assert snow["serviceNowUrl"] == "***"
        assert mask_channel(fixtures[1])["salesforceUrl"] == "***"
        assert mask_channel(fixtures[2])["zchatOpsIncidentsUrl"] == "***"
        assert mask_channel({"kind": "SLACK", "iconUrl": "https://x.com/i.png"})["iconUrl"] == "***"
        assert (
            mask_channel({"kind": "SERVICE_NOW_APPLICATION", "instanaUrl": "https://i.example.com/ui?x=1"})["instanaUrl"]
            == "***"
        )
        assert mask_channel({"kind": "SPLUNK", "url": "https://splunk.example.com/services/collector/TOKEN"})[
            "url"
        ] == "***"

    def test_all_url_fields_fully_masked_and_empty_values_pass_through(self):
        """Every allow-listed URL field (incl. nested oauth tokenUrl) is fully masked."""
        url = "https://internal.corp.local:8443/secret/path"
        fixtures = [
            {"kind": "SLACK", "webhookUrl": url, "iconUrl": url},
            {"kind": "WEB_HOOK", "webhookUrls": [url, url], "oauth": {"config": {"tokenUrl": url}}},
            {"kind": "OFFICE_365", "webhookUrl": url},
            {"kind": "GOOGLE_CHAT", "webhookUrl": url},
            {"kind": "WEBEX_TEAMS_WEBHOOK", "webhookUrl": url},
            {"kind": "PROMETHEUS_WEBHOOK", "webhookUrl": url},
            {"kind": "WATSON_AIOPS_WEBHOOK", "webhookUrl": url},
            {"kind": "NS1", "webhookUrls": [url]},
            {"kind": "SPLUNK", "url": url},
            {"kind": "SERVICE_NOW_WEBHOOK", "serviceNowUrl": url},
            {"kind": "SERVICE_NOW_APPLICATION", "serviceNowUrl": url, "instanaUrl": url},
            {"kind": "SALESFORCE", "salesforceUrl": url},
            {"kind": "Z_CHATOPS", "zchatOpsIncidentsUrl": url},
            {"kind": "BIDIRECTIONAL_MS_TEAMS", "instanaUrl": url, "serviceUrl": url},
        ]
        for fixture in fixtures:
            dumped = json.dumps(mask_channel(fixture))
            assert "internal.corp.local" not in dumped, f"Host leaked for {fixture['kind']}: {dumped}"
            assert "secret/path" not in dumped

        webhook = mask_channel(fixtures[1])
        assert webhook["webhookUrls"] == ["***", "***"]
        assert webhook["oauth"]["config"]["tokenUrl"] == "***"

        # Empty values leak nothing and pass through unchanged
        masked = mask_channel({"kind": "SERVICE_NOW_APPLICATION", "instanaUrl": None, "serviceNowUrl": ""})
        assert masked["instanaUrl"] is None
        assert masked["serviceNowUrl"] == ""

    def test_unknown_url_key_fails_closed_and_safe_list_is_empty(self):
        """New *Url keys are masked fully; safe list is empty; unsafe wins over safe."""
        assert not SAFE_URL_KEYS
        assert {"webhookurl", "webhookurls", "iconurl", "url", "serviceurl", "instanaurl", "tokenurl",
                "servicenowurl", "salesforceurl", "zchatopsincidentsurl"} <= UNSAFE_URL_KEYS
        # Unknown kind / unknown field: never exposed
        masked = mask_channel({"kind": "FUTURE", "newEndpointUrl": "https://a.internal/x"})
        assert masked["newEndpointUrl"] == "***"

        # Backup logic: a key in SAFE_URL_KEYS (and not unsafe) uses host-visible display masking
        with patch.object(alert_channel_utils, "SAFE_URL_KEYS", frozenset({"serviceurl"})), \
                patch.object(alert_channel_utils, "UNSAFE_URL_KEYS", frozenset()):
            masked = mask_channel({"kind": "BIDIRECTIONAL_MS_TEAMS", "serviceUrl": "https://s.example.com/p?q=1"})
            assert masked["serviceUrl"] == "https://s.example.com/p"
        # Unsafe takes precedence over safe
        with patch.object(alert_channel_utils, "SAFE_URL_KEYS", frozenset({"serviceurl"})):
            masked = mask_channel({"kind": "BIDIRECTIONAL_MS_TEAMS", "serviceUrl": "https://s.example.com/p"})
            assert masked["serviceUrl"] == "***"

    def test_kind_casing_is_normalized(self):
        """Lower/mixed-case kinds still use the right allow-list; unknown kinds fail closed."""
        masked = mask_channel({"kind": " slack ", "channel": "#alerts", "apiKey": "S"})
        assert masked["channel"] == "#alerts"
        assert masked["apiKey"] == "***"
        masked = mask_channel({"kind": "nope", "channel": "#alerts"})
        assert masked["channel"] == "***"

    def test_enum_kind_is_unwrapped(self):
        """An enum-valued kind (exposing .value) resolves to the same allow-list as its string."""
        import enum

        class Kind(enum.Enum):
            SLACK = "SLACK"

        masked = mask_channel({"kind": Kind.SLACK, "channel": "#alerts", "apiKey": "S"})
        assert masked["channel"] == "#alerts"
        assert masked["apiKey"] == "***"

    def test_non_dict_inputs_fail_closed(self):
        """Bare strings and non-dict list entries are masked, not passed through."""
        assert mask_channel("raw-secret") == "***"
        assert mask_channel(["raw-secret", {"kind": "SLACK", "channel": "#a"}]) == [
            "***",
            {"kind": "SLACK", "channel": "#a"},
        ]
        assert mask_channel(None) is None

    def test_oauth_token_metadata_visible_but_tokens_masked(self):
        """oauth.token status metadata is shown while token secrets remain masked."""
        masked = mask_channel(
            {
                "kind": "WEB_HOOK",
                "oauth": {
                    "token": {
                        "status": "VALID",
                        "tokenType": "Bearer",
                        "accessToken": "SECRET-AT",
                        "refreshToken": "SECRET-RT",
                    }
                },
            }
        )
        token = masked["oauth"]["token"]
        assert token["status"] == "VALID"
        assert token["tokenType"] == "Bearer"
        assert token["accessToken"] == "***"
        assert token["refreshToken"] == "***"

    def test_mask_webhook_url_ipv6_and_no_suffix_shortcut(self):
        """IPv6 literals stay bracketed; a crafted '/***' suffix cannot bypass masking."""
        assert mask_webhook_url("http://[::1]:8080/secret/path") == "http://[::1]:8080/***"
        assert mask_webhook_url("https://[2001:db8::1]/hook") == "https://[2001:db8::1]/***"
        assert mask_webhook_url("https://evil.com/token?x=1/***") == "https://evil.com/***"
        once = mask_webhook_url("http://[::1]:8080/secret")
        assert mask_webhook_url(once) == once

    def test_log_redaction_and_caplog(self, caplog: pytest.LogCaptureFixture):
        """6. Logging data through redact_for_log does not expose secrets."""
        sentinel = "LOG-SENTINEL-SECRET-999"
        payload = {
            "kind": "SLACK",
            "name": "Test Slack",
            "webhookUrl": f"https://hooks.slack.com/services/{sentinel}",
            "apiKey": sentinel,
        }

        with caplog.at_level(logging.DEBUG):
            redacted = redact_for_log(payload)
            logging.getLogger("test").info("Channel details: %s", redacted)

        assert sentinel not in caplog.text
        assert "hooks.slack.com" not in caplog.text

    def test_log_redaction_with_sdk_model(self):
        """Verify that redact_for_log successfully unpacks and redacts class/model instances."""
        class MockSDKModel:
            def to_dict(self):
                return {
                    "kind": "SLACK",
                    "name": "Class Model Slack",
                    "webhookUrl": "https://hooks.slack.com/services/SECRET_TOKEN_456",
                    "apiKey": "SECRET_KEY_789"
                }

        model_instance = MockSDKModel()
        redacted = redact_for_log(model_instance)

        assert isinstance(redacted, dict)
        assert redacted["webhookUrl"] == "***"
        assert redacted["apiKey"] == "***"

    def test_redact_for_log_unified_header_and_url_handling(self):
        """redact_for_log masks dict/list headers and URL lists the same way as mask_channel."""
        payload = {
            "headers": {"Authorization": "Bearer SECRET-H", "X-Api": "SECRET-H2"},
            "webhookUrls": ["https://hooks.example.com/SECRET-U"],
            "nested": {"headers": ["Authorization: Bearer SECRET-H3"]},
        }
        redacted = redact_for_log(payload)
        assert redacted["headers"] == {"Authorization": "***", "X-Api": "***"}
        assert redacted["webhookUrls"] == ["***"]
        assert redacted["nested"]["headers"] == ["Authorization: ***"]
        assert "SECRET" not in json.dumps(redacted)

        channel = {"kind": "WEB_HOOK", "headers": payload["headers"], "webhookUrls": payload["webhookUrls"]}
        masked = mask_channel(channel)
        assert masked["headers"] == redacted["headers"]
        assert masked["webhookUrls"] == redacted["webhookUrls"]

    def test_masking_idempotency(self):
        """7. Masking is idempotent: mask_channel(mask_channel(x)) == mask_channel(x)."""
        fixture = {
            "id": "wh-idempotent",
            "kind": "WEB_HOOK",
            "name": "Webhook Channel",
            "webhookUrls": ["https://hooks.example.com/services/secret123"],
            "headers": ["Authorization: Bearer my-secret-token"],
            "oauth": {
                "config": {
                    "clientId": "client-id",
                    "clientSecret": "super-secret",
                },
            },
        }

        first_pass = mask_channel(fixture)
        second_pass = mask_channel(first_pass)
        assert first_pass == second_pass

    def test_mask_webhook_url_edge_cases(self):
        """Test URL masking edge cases."""
        assert mask_webhook_url(None) is None
        assert mask_webhook_url("") == ""
        assert mask_webhook_url("https://hooks.slack.com/***") == "https://hooks.slack.com/***"
        assert mask_webhook_url("https://hooks.slack.com/services/T1/B2/token") == "https://hooks.slack.com/***"
        assert mask_webhook_url("http://user:pass@internal.service.local:8080/hook") == "http://internal.service.local:8080/***"
        assert mask_webhook_url("not-a-valid-url") == "***"

    def test_mask_url_missing_scheme_fallbacks(self):
        """Test URL masking fallbacks when scheme is missing or atypical."""
        assert mask_webhook_url("hooks.slack.com/services/T1/B2/token") == "hooks.slack.com/***"
        assert mask_webhook_url("localhost:8080/services/token") == "localhost:8080/***"
        assert mask_webhook_url("127.0.0.1/services") == "127.0.0.1/***"

        from src.core.alert_channel_utils import mask_display_url
        assert mask_display_url("dev1.service-now.com/login.do?user=admin&pass=secret") == "dev1.service-now.com/***"
        assert mask_display_url("admin:secret@dev1.service-now.com/login.do") == "dev1.service-now.com/***"
        assert (
            mask_display_url("dev1.service-now.com/login.do?user=admin", keep_path=True)
            == "dev1.service-now.com/login.do"
        )

    def test_mask_header_entry_edge_cases(self):
        """Test header masking edge cases."""
        assert mask_header_entry(None) is None
        assert mask_header_entry("") == ""
        assert mask_header_entry("Authorization: Bearer secret") == "Authorization: ***"
        assert mask_header_entry("X-Custom-Header: value123") == "X-Custom-Header: ***"
        assert mask_header_entry("Authorization: ***") == "Authorization: ***"
        assert mask_header_entry("no-colon-header") == "***"

    def test_nested_allowlist_collision_prevention(self):
        """Ensure nested dictionary fields sharing top-level allowed names are masked unless path-allowed."""
        fixture = {
            "id": "wh-collision",
            "kind": "WEB_HOOK",
            "name": "Webhook Channel",
            "oauth": {
                "config": {
                    "clientId": "client-id",
                    # 'transformationExpression' and 'oauthEnabled' are top-level allowed fields for WEB_HOOK,
                    # but 'oauth.config.transformationExpression' is NOT path-allowed.
                    "transformationExpression": "unvetted-nested-payload",
                    "oauthEnabled": "nested-flag",
                },
            },
        }
        masked = mask_channel(fixture)
        assert masked["oauth"]["config"]["clientId"] == "client-id"
        assert masked["oauth"]["config"]["transformationExpression"] == "***"
        assert masked["oauth"]["config"]["oauthEnabled"] == "***"
