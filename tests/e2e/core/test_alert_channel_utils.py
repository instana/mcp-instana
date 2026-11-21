"""Mocked e2e tests for src/core/alert_channel_utils.py (credential masking and log redaction)."""

from types import SimpleNamespace

import pytest

from src.core import alert_channel_utils
from src.core.alert_channel_utils import (
    is_known_credential,
    mask_channel,
    mask_display_url,
    mask_header_entry,
    mask_webhook_url,
    normalize_key,
    redact_for_log,
)


class _WithToDict:
    """SDK-style model exposing to_dict()."""

    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return self._data


class _WithModelDump:
    """Pydantic-style model exposing model_dump(by_alias=...)."""

    def __init__(self, data):
        self._data = data
        self.by_alias_seen = None

    def model_dump(self, by_alias=False):
        self.by_alias_seen = by_alias
        return self._data


class TestKeyHelpersE2E:
    """Key normalisation and credential detection."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_normalize_key_strips_separators_and_case(self):
        assert normalize_key("Client_Secret") == "clientsecret"
        assert normalize_key("API-Key") == "apikey"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_is_known_credential(self):
        assert is_known_credential("apiKey") is True
        assert is_known_credential("service_integration_key") is True
        assert is_known_credential("channel") is False


class TestUrlMaskingE2E:
    """mask_webhook_url / mask_display_url."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_webhook_url_path_query_and_userinfo_removed(self):
        masked = mask_webhook_url("https://user:pw@hooks.slack.com:8443/services/T/B/X?token=1#frag")
        assert masked == "https://hooks.slack.com:8443/***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_webhook_url_without_scheme(self):
        assert mask_webhook_url("hooks.example.com/abc/def") == "hooks.example.com/***"
        assert mask_webhook_url("localhost:8080/hook") == "localhost:8080/***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_webhook_url_ipv6_host_is_bracketed(self):
        assert mask_webhook_url("http://[::1]:8080/p") == "http://[::1]:8080/***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_webhook_url_is_idempotent(self):
        once = mask_webhook_url("https://hooks.example.com/secret/path")
        assert mask_webhook_url(once) == once

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unparseable_urls_are_fully_masked(self):
        assert mask_webhook_url("ftp://files.example.com/x") == "***"
        assert mask_webhook_url("notaurl") == "***"
        assert mask_webhook_url("http://") == "***"
        assert mask_webhook_url("http://example.com:notaport/x") == "***"
        assert mask_webhook_url(12345) == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_urls_pass_through(self):
        assert mask_webhook_url(None) is None
        assert mask_webhook_url("") == ""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_display_url_keep_path_option(self):
        assert mask_display_url("https://a.example.com/p/q?x=1") == "https://a.example.com/***"
        assert mask_display_url("https://a.example.com/p/q?x=1", keep_path=True) == "https://a.example.com/p/q"


class TestHeaderMaskingE2E:
    """mask_header_entry."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_header_with_value_keeps_only_name(self):
        assert mask_header_entry("Authorization: Bearer abc") == "Authorization: ***"
        assert mask_header_entry("  X-Key :v") == "X-Key: ***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_header_without_separator_or_non_string(self):
        assert mask_header_entry("justvalue") == "***"
        assert mask_header_entry(42) == "***"
        assert mask_header_entry("") == ""
        assert mask_header_entry(None) is None


class TestMaskChannelE2E:
    """mask_channel behaviour across kinds and shapes."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_none_and_scalars(self):
        assert mask_channel(None) is None
        assert mask_channel("raw-secret") == "***"
        assert mask_channel(123) == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_of_channels_is_masked_per_item(self):
        result = mask_channel([
            {"kind": "SLACK", "id": "1", "webhookUrl": "https://hooks.slack.com/x"},
            "oops",
        ])
        assert result[0]["id"] == "1"
        assert result[0]["webhookUrl"] == "***"
        assert result[1] == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_webhook_channel_masks_urls_headers_and_oauth_secrets(self):
        channel = {
            "kind": "WEB_HOOK",
            "id": "wh-1",
            "name": "Hook",
            "webhookUrls": ["https://h.example.com/a?t=1", "https://h2.example.com/b"],
            "headers": ["X-Key: abc", "plain"],
            "oauthEnabled": True,
            "unlisted": "leak-me",
            "oauth": {
                "config": {
                    "clientId": "cid",
                    "clientSecret": "s3cret",
                    "tokenUrl": "https://auth.example.com/token",
                    "grantType": "client_credentials",
                },
                "token": {"status": "ok", "accessToken": "abc", "tokenType": "Bearer"},
            },
        }
        masked = mask_channel(channel)
        assert masked["id"] == "wh-1"
        assert masked["name"] == "Hook"
        assert masked["webhookUrls"] == ["***", "***"]
        assert masked["headers"] == ["X-Key: ***", "***"]
        assert masked["oauthEnabled"] is True
        assert masked["unlisted"] == "***"
        config = masked["oauth"]["config"]
        assert config["clientId"] == "cid"
        assert config["clientSecret"] == "***"
        assert config["tokenUrl"] == "***"
        assert config["grantType"] == "client_credentials"
        token = masked["oauth"]["token"]
        assert token["status"] == "ok"
        assert token["accessToken"] == "***"
        assert token["tokenType"] == "Bearer"
        # the original object must not be mutated
        assert channel["oauth"]["config"]["clientSecret"] == "s3cret"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_single_string_header_is_masked(self):
        masked = mask_channel({"kind": "NS1", "headers": "X-Key: abc"})
        assert masked["headers"] == "X-Key: ***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_headers_as_dict_mask_all_values(self):
        masked = mask_channel({"kind": "NS1", "headers": {"A": "1", "B": "2"}})
        assert masked["headers"] == {"A": "***", "B": "***"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_slack_channel_masks_url_fields_but_keeps_channel(self):
        masked = mask_channel({
            "kind": "SLACK",
            "channel": "#alerts",
            "emojiRendering": "yes",
            "iconUrl": "https://icons.example.com/i.png?k=1",
            "webhookUrl": "https://hooks.slack.com/services/T/B/X",
            "apiKey": "abc",
        })
        assert masked["channel"] == "#alerts"
        assert masked["emojiRendering"] == "yes"
        assert masked["iconUrl"] == "***"
        assert masked["webhookUrl"] == "***"
        assert masked["apiKey"] == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_kind_argument_and_enum_like_kind_are_used(self):
        masked = mask_channel({"name": "n", "channel": "#c", "token": "t"}, kind="slack")
        assert masked["channel"] == "#c"
        assert masked["token"] == "***"

        enum_like = SimpleNamespace(value="email")
        masked_email = mask_channel({"emails": ["a@b.com"], "password": "p"}, kind=enum_like)
        assert masked_email["emails"] == ["a@b.com"]
        assert masked_email["password"] == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unknown_kind_keeps_only_common_fields(self):
        masked = mask_channel({
            "kind": "BRAND_NEW",
            "id": "x",
            "name": "n",
            "timezone": "UTC",
            "extra": {"a": "b", "c": ["d", ""]},
            "empty": "",
        })
        assert masked["id"] == "x"
        assert masked["name"] == "n"
        assert masked["timezone"] == "UTC"
        assert masked["extra"] == {"a": "***", "c": ["***", ""]}
        assert masked["empty"] == ""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_credential_values_masked_recursively_preserving_empties(self):
        masked = mask_channel({
            "kind": "PAGER_DUTY",
            "serviceIntegrationKey": "abc",
            "credentials": {"user": "u", "pw": ["p", ""], "none": None, "empty": ""},
            "routingKey": "",
        })
        assert masked["serviceIntegrationKey"] == "***"
        assert masked["credentials"] == {"user": "***", "pw": ["***", ""], "none": None, "empty": ""}
        assert masked["routingKey"] == ""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rbac_tags_only_keep_id_and_display_name(self):
        masked = mask_channel({
            "kind": "SLACK",
            "rbacTags": [
                {"id": "t1", "displayName": "Team", "secret": "x"},
                {"id": "t2", "display_name": "T2", "other": 1},
                "raw",
            ],
        })
        assert masked["rbacTags"] == [
            {"id": "t1", "displayName": "Team"},
            {"id": "t2", "display_name": "T2"},
            "raw",
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_list_rbac_tags_are_treated_as_common_field(self):
        masked = mask_channel({"kind": "SLACK", "rbacTags": "none"})
        assert masked["rbacTags"] == "none"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_allowed_list_recurses_into_dicts_and_nested_lists(self):
        masked = mask_channel({
            "kind": "EMAIL",
            "emails": ["a@b.com", {"inner": "v"}, ["x", {"deep": "y"}]],
        })
        assert masked["emails"][0] == "a@b.com"
        assert masked["emails"][1] == {"inner": "***"}
        assert masked["emails"][2][0] == "x"
        assert masked["emails"][2][1] == {"deep": "***"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_service_now_url_fields_are_masked(self):
        masked = mask_channel({
            "kind": "SERVICE_NOW_WEBHOOK",
            "serviceNowUrl": "https://snow.example.com/api",
            "username": "svc",
            "password": "pw",
            "autoCloseIncidents": True,
        })
        assert masked["serviceNowUrl"] == "***"
        assert masked["username"] == "svc"
        assert masked["password"] == "***"
        assert masked["autoCloseIncidents"] is True

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_to_dict_and_model_dump_objects_are_supported(self):
        from_to_dict = mask_channel(_WithToDict({"kind": "SLACK", "id": "1", "webhookUrl": "https://a.example.com/x"}))
        assert from_to_dict == {"kind": "SLACK", "id": "1", "webhookUrl": "***"}

        model = _WithModelDump({"kind": "SLACK", "id": "2", "webhookUrl": "https://a.example.com/x"})
        from_model_dump = mask_channel(model)
        assert model.by_alias_seen is True
        assert from_model_dump["id"] == "2"
        assert from_model_dump["webhookUrl"] == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_safe_url_keys_are_partially_displayed(self, monkeypatch):
        monkeypatch.setattr(alert_channel_utils, "SAFE_URL_KEYS", frozenset({"iconurl", "url"}))
        monkeypatch.setattr(alert_channel_utils, "UNSAFE_URL_KEYS", frozenset())
        masked = mask_channel({
            "kind": "SLACK",
            "iconUrl": "https://icons.example.com/p/i.png?k=1",
            "url": "https://x.example.com/secret",
        })
        # iconUrl is allowed for SLACK and path-visible; "url" is not allow-listed so it stays hidden
        assert masked["iconUrl"] == "https://icons.example.com/p/i.png"
        assert masked["url"] == "***"

        splunk = mask_channel({"kind": "SPLUNK", "url": "https://splunk.example.com/secret?x=1", "empty": ""})
        assert splunk["url"] == "https://splunk.example.com/***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_safe_url_key_marked_unsafe_stays_hidden(self, monkeypatch):
        monkeypatch.setattr(alert_channel_utils, "SAFE_URL_KEYS", frozenset({"url"}))
        monkeypatch.setattr(alert_channel_utils, "UNSAFE_URL_KEYS", frozenset({"url"}))
        masked = mask_channel({"kind": "SPLUNK", "url": "https://splunk.example.com/x"})
        assert masked["url"] == "***"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_url_values_pass_through(self):
        masked = mask_channel({"kind": "SPLUNK", "url": ""})
        assert masked["url"] == ""
        assert mask_channel({"kind": "SLACK", "webhookUrl": None})["webhookUrl"] is None


class TestRedactForLogE2E:
    """redact_for_log for logging payloads."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_none_and_scalars_unchanged(self):
        assert redact_for_log(None) is None
        assert redact_for_log("text") == "text"
        assert redact_for_log(5) == 5

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dict_without_kind_redacts_known_fields(self):
        redacted = redact_for_log({
            "apiKey": "abc",
            "webhookUrl": "https://x.example.com/s",
            "headers": {"A": "b"},
            "nested": {"token": "t", "plain": "v"},
            "plain": "visible",
            "items": [{"password": "p"}, "x"],
        })
        assert redacted["apiKey"] == "***"
        assert redacted["webhookUrl"] == "***"
        assert redacted["headers"] == {"A": "***"}
        assert redacted["nested"] == {"token": "***", "plain": "v"}
        assert redacted["plain"] == "visible"
        assert redacted["items"] == [{"password": "***"}, "x"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_dict_with_kind_uses_channel_masking(self):
        redacted = redact_for_log({"kind": "SLACK", "id": "1", "webhookUrl": "https://a.example.com/x", "other": "o"})
        assert redacted == {"kind": "SLACK", "id": "1", "webhookUrl": "***", "other": "***"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_and_model_objects(self):
        redacted = redact_for_log([{"secret": "s"}, _WithToDict({"token": "t"})])
        assert redacted == [{"secret": "***"}, {"token": "***"}]
