"""
Alert Channel Security and Masking Utilities.

This module provides fail-closed allow-list filtering, credential masking,
and log redaction for Instana Alert Channel configurations.
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Known credential field names (normalized: lower-case with '-' and '_' removed)
KNOWN_CREDENTIAL_FIELDS: tuple[str, ...] = (
    "apikey",
    "secret",
    "clientsecret",
    "password",
    "passwd",
    "token",
    "accesstoken",
    "refreshtoken",
    "bearertoken",
    "bearerauthtoken",
    "serviceintegrationkey",
    "routingkey",
    "privatekey",
    "credential",
    "credentials",
    "authorization",
    "apitokenid",
    "additionalparameters",
)

# Structured fields with custom redaction rules
_WEBHOOK_URL_FIELDS: tuple[str, ...] = ("webhookurl", "webhookurls")
_HEADERS_FIELD = "headers"
STRUCTURED_CREDENTIAL_FIELDS: tuple[str, ...] = (*_WEBHOOK_URL_FIELDS, _HEADERS_FIELD)

# Common fields allowed across all alert channel kinds
COMMON_SHOWN_FIELDS: frozenset[str] = frozenset({
    "id",
    "kind",
    "name",
    "timezone",
    "testEventType",
    "testSeverity",
    "testState",
    "test_event_type",
    "test_severity",
    "test_state",
    "rbacTags",
    "rbac_tags",
})

# Per-kind allow-list for non-credential fields
ALLOWED_FIELDS_BY_KIND: dict[str, set[str]] = {
    "WEB_HOOK": {
        "oauthEnabled",
        "oauth_enabled",
        "transformationExpression",
        "transformation_expression",
        "webhookUrls",
        "webhook_urls",
        "headers",
        "oauth",
        "oauth.config",
        "oauth.config.clientId",
        "oauth.config.client_id",
        "oauth.config.tokenUrl",
        "oauth.config.token_url",
        "oauth.config.grantType",
        "oauth.config.grant_type",
        "oauth.config.username",
        "oauth.token",
        "oauth.token.status",
        "oauth.token.valid",
        "oauth.token.tokenType",
        "oauth.token.token_type",
        "oauth.token.createdAt",
        "oauth.token.created_at",
        "oauth.token.expiresAt",
        "oauth.token.expires_at",
    },
    "EMAIL": {
        "emails",
        "transformationExpression",
        "transformation_expression",
        "customEmailSubjectPrefix",
        "custom_email_subject_prefix",
        "customEmailSubjectPrefix.prefix",
        "custom_email_subject_prefix.prefix",
        "customEmailSubjectPrefix.type",
        "custom_email_subject_prefix.type",
    },
    "SLACK": {
        "channel",
        "emojiRendering",
        "emoji_rendering",
        "iconUrl",
        "icon_url",
        "webhookUrl",
        "webhook_url",
    },
    "OFFICE_365": {
        "webhookUrl",
        "webhook_url",
    },
    "GOOGLE_CHAT": {
        "webhookUrl",
        "webhook_url",
    },
    "WEBEX_TEAMS_WEBHOOK": {
        "webhookUrl",
        "webhook_url",
    },
    "PROMETHEUS_WEBHOOK": {
        "receiver",
        "webhookUrl",
        "webhook_url",
    },
    "WATSON_AIOPS_WEBHOOK": {
        "headers",
        "webhookUrl",
        "webhook_url",
    },
    "NS1": {
        "feedLabel",
        "feed_label",
        "webhookUrls",
        "webhook_urls",
        "headers",
    },
    "OPS_GENIE": {
        "alias",
        "region",
        "tags",
    },
    "PAGER_DUTY": set(),
    "VICTOR_OPS": set(),
    "SPLUNK": {
        "url",
    },
    "SERVICE_NOW_WEBHOOK": {
        "serviceNowUrl",
        "service_now_url",
        "username",
        "autoCloseIncidents",
        "auto_close_incidents",
    },
    "SERVICE_NOW_APPLICATION": {
        "serviceNowUrl",
        "service_now_url",
        "instanaUrl",
        "instana_url",
        "tenant",
        "unit",
        "username",
        "autoCloseIncidents",
        "auto_close_incidents",
        "manuallyClosedIncidents",
        "manually_closed_incidents",
        "resolutionOfIncident",
        "resolution_of_incident",
        "snowStatusOnCloseEvent",
        "snow_status_on_close_event",
        "enableSendInstanaNotes",
        "enable_send_instana_notes",
        "enableSendServiceNowActivities",
        "enable_send_service_now_activities",
        "enableSendServiceNowWorkNotes",
        "enable_send_service_now_work_notes",
    },
    "SALESFORCE": {
        "salesforceUrl",
        "salesforce_url",
        "clientId",
        "client_id",
    },
    "Z_CHATOPS": {
        "zchatOpsIncidentsUrl",
        "zchat_ops_incidents_url",
        "channels",
    },
    "BIDIRECTIONAL_SLACK": {
        "appId",
        "app_id",
        "channelId",
        "channel_id",
        "channelName",
        "channel_name",
        "emojiRendering",
        "emoji_rendering",
        "status",
        "teamId",
        "team_id",
        "teamName",
        "team_name",
    },
    "BIDIRECTIONAL_MS_TEAMS": {
        "channelId",
        "channel_id",
        "channelName",
        "channel_name",
        "instanaUrl",
        "instana_url",
        "serviceUrl",
        "service_url",
        "teamId",
        "team_id",
        "teamName",
        "team_name",
        "tenantId",
        "tenant_id",
        "tenantName",
        "tenant_name",
    },
}

ALLOWED_EXCEPTIONS: frozenset[str] = frozenset({
    "oauth.token",
    "oauth.config.tokenUrl",
    "oauth.config.token_url",
    "oauth.token.tokenType",
    "oauth.token.token_type",
})

# URL-valued fields (normalized key) that are known to carry credentials or may expose
# internal hostnames. Their values are replaced entirely with '***'.
UNSAFE_URL_KEYS: frozenset[str] = frozenset({
    "webhookurl",
    "webhookurls",
    "iconurl",
    "url",
    "serviceurl",
    "instanaurl",
    "tokenurl",
    "servicenowurl",
    "salesforceurl",
    "zchatopsincidentsurl",
})

# URL-valued fields (normalized key) reviewed and approved for partial display. Currently
# empty on purpose: every URL is fully masked. A key listed here (and not in UNSAFE_URL_KEYS)
# falls back to the display masking below (scheme://host/*** or, for PATH_VISIBLE_URL_KEYS,
# scheme://host/path). Any URL key in neither list is treated as unsafe (fail-closed).
SAFE_URL_KEYS: frozenset[str] = frozenset()

# Subset of safe URL keys whose path is also known to be non-sensitive. Only consulted for
# keys in SAFE_URL_KEYS.
PATH_VISIBLE_URL_KEYS: frozenset[str] = frozenset({
    "iconurl",
    "instanaurl",
    "tokenurl",
    "serviceurl",
})


def normalize_key(key: str) -> str:
    """Normalize a key string by lowercasing and stripping '_' and '-'."""
    return key.lower().replace("_", "").replace("-", "")


def is_known_credential(key: str) -> bool:
    """Check if normalized key name is in KNOWN_CREDENTIAL_FIELDS."""
    return normalize_key(key) in KNOWN_CREDENTIAL_FIELDS


def _host_port(host: str, port: Optional[int]) -> str:
    """Format host[:port], bracketing IPv6 literals (``[::1]:8080``)."""
    if ":" in host:
        host = f"[{host}]"
    return f"{host}:{port}" if port else host


def _parse_http_url(url: str) -> Optional[tuple[Optional[str], str, str]]:
    """
    Parse an http(s) URL (scheme optional) into ``(scheme, host_port, path)``.

    ``scheme`` is None when the input had no explicit scheme. Userinfo, query and fragment
    are discarded. Returns None when the value is not a recognisable http(s) URL.
    """
    candidate = url.strip()
    has_scheme = "://" in candidate
    try:
        parsed = urlparse(candidate if has_scheme else f"//{candidate}")
        host = parsed.hostname
        port = parsed.port
    except ValueError:
        return None

    if not host:
        return None
    if has_scheme:
        if parsed.scheme not in ("http", "https"):
            return None
    elif not ("." in host or ":" in host or host.lower() == "localhost"):
        return None

    return (parsed.scheme if has_scheme else None, _host_port(host, port), parsed.path)


def _rebuild_url(url: Any, keep_path: bool) -> Any:
    """Rebuild a URL as ``[scheme://]host[:port]`` + (path or ``/***``)."""
    if not url:
        return url
    if not isinstance(url, str):
        return "***"

    parts = _parse_http_url(url)
    if parts is None:
        return "***"
    scheme, host_port, path = parts
    suffix = path if keep_path else "/***"
    return f"{scheme}://{host_port}{suffix}" if scheme else f"{host_port}{suffix}"


def mask_webhook_url(url: Optional[str]) -> Optional[str]:
    """
    Mask a webhook URL to scheme://host/*** while stripping sensitive path/tokens.

    Idempotent by construction: re-parsing an already masked URL yields the same output.
    """
    return _rebuild_url(url, keep_path=False)


def mask_display_url(url: Optional[str], keep_path: bool = False) -> Optional[str]:
    """
    Sanitize a URL field for display.

    Always drops userinfo (user:pass@), query string and fragment. The path is replaced by
    ``/***`` unless ``keep_path`` is True (only for explicitly non-sensitive fields).
    """
    return _rebuild_url(url, keep_path=keep_path)


def mask_header_entry(header: Optional[str]) -> Optional[str]:
    """
    Mask a header entry 'Header-Name: value' to 'Header-Name: ***'.
    """
    if not header:
        return header
    if not isinstance(header, str):
        return "***"
    if ":" in header:
        name, _, _ = header.partition(":")
        return f"{name.strip()}: ***"
    return "***"


def _is_safe_url_key(norm_key: str) -> bool:
    """A URL key may be partially displayed only if explicitly safe and not marked unsafe."""
    return norm_key in SAFE_URL_KEYS and norm_key not in UNSAFE_URL_KEYS


def _mask_url_value(norm_key: str, val: Any) -> Any:
    """
    Mask a URL value (string or list of strings) for the given normalized key.

    Unsafe (default) keys are replaced entirely with '***'; empty values pass through.
    Safe keys fall back to host-visible display masking.
    """
    if isinstance(val, list):
        return [_mask_url_value(norm_key, item) for item in val]
    if val is None or val == "":
        return val
    if _is_safe_url_key(norm_key):
        return mask_display_url(val, keep_path=norm_key in PATH_VISIBLE_URL_KEYS)
    return "***"


def _mask_headers(val: Any) -> Any:
    """Mask header values (list of 'Name: value', dict of name->value, or a single entry)."""
    if isinstance(val, list):
        return [mask_header_entry(h) for h in val]
    if isinstance(val, dict):
        return dict.fromkeys(val, "***")
    return mask_header_entry(val)


def _mask_recursive_leaves(val: Any) -> Any:
    """Recursively mask all scalar leaf values to '***' while keeping keys."""
    if val is None or val == "" or val == []:
        return val
    if isinstance(val, dict):
        return {k: _mask_recursive_leaves(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_mask_recursive_leaves(item) for item in val]
    return "***"


def _mask_allowed_list(items: list[Any], kind: str, prefix: str) -> list[Any]:
    """Mask an allow-listed list, recursing into dicts and nested lists."""
    return [
        _mask_dict(item, kind, prefix=prefix) if isinstance(item, dict)
        else _mask_allowed_list(item, kind, prefix) if isinstance(item, list)
        else copy.deepcopy(item)
        for item in items
    ]


def _mask_rbac_tags(tags: list[Any]) -> list[Any]:
    """Mask items in an rbacTags list, preserving only ID and display names."""
    masked_tags = []
    for tag in tags:
        if isinstance(tag, dict):
            masked_tags.append({
                tk: tv for tk, tv in tag.items()
                if tk in ("id", "displayName", "display_name")
            })
        else:
            masked_tags.append(tag)
    return masked_tags


def _mask_allowed_value(v: Any, norm_k: str, kind: str, curr_path: str) -> Any:
    """Mask allowed values based on type (URL, dict, list, scalar)."""
    if isinstance(v, (str, list)) and (norm_k.endswith("url") or norm_k in UNSAFE_URL_KEYS):
        return _mask_url_value(norm_k, v)
    if isinstance(v, dict):
        return _mask_dict(v, kind, prefix=f"{curr_path}.")
    if isinstance(v, list):
        return _mask_allowed_list(v, kind, prefix=f"{curr_path}[].")
    return copy.deepcopy(v)


def _mask_entry_value(k: str, v: Any, kind: str, prefix: str, allowed_for_kind: set[str]) -> Any:
    """Determine masking strategy for a single dictionary entry."""
    curr_path = f"{prefix}{k}" if prefix else k
    norm_k = normalize_key(k)
    is_exception = curr_path in ALLOWED_EXCEPTIONS and curr_path in allowed_for_kind

    if norm_k in _WEBHOOK_URL_FIELDS:
        return _mask_url_value(norm_k, v)
    if norm_k == _HEADERS_FIELD:
        return _mask_headers(v)
    if not is_exception and is_known_credential(k):
        return _mask_recursive_leaves(v)
    if norm_k in ("rbactags",) and isinstance(v, list):
        return _mask_rbac_tags(v)

    is_allowed = k in COMMON_SHOWN_FIELDS or curr_path in allowed_for_kind
    if is_allowed:
        return _mask_allowed_value(v, norm_k, kind, curr_path)
    return _mask_recursive_leaves(v)


def _mask_dict(data: dict[str, Any], kind: str, prefix: str = "") -> dict[str, Any]:
    """Internal helper to mask dictionary keys recursively based on policy."""
    allowed_for_kind = ALLOWED_FIELDS_BY_KIND.get(kind, set())
    return {
        k: _mask_entry_value(k, v, kind, prefix, allowed_for_kind)
        for k, v in data.items()
    }


def _resolve_kind(raw: Any) -> str:
    """Normalize a kind to its upper-case string form; SDK enums expose ``.value``."""
    return str(getattr(raw, "value", raw) or "").strip().upper()


def _to_dict_or_raw(obj: Any) -> Any:
    """Handle SDK models or objects with to_dict() / model_dump()."""
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return obj.model_dump(by_alias=True)
    return obj


def mask_channel(obj: Any, kind: Optional[str] = None) -> Any:
    """
    Mask an alert channel object or dictionary, replacing sensitive credentials with '***'.

    Fail-closed: anything that is not a dict (or list of such) is replaced by '***'.
    """
    if obj is None:
        return None

    obj = _to_dict_or_raw(obj)

    if isinstance(obj, list):
        return [mask_channel(item, kind=kind) for item in obj]

    if not isinstance(obj, dict):
        return "***"

    detected_kind = _resolve_kind(obj.get("kind") or kind)
    if detected_kind not in ALLOWED_FIELDS_BY_KIND:
        logger.warning("Unrecognized alert channel kind %r; masking all non-common fields", detected_kind)
    return _mask_dict(obj, detected_kind)


def _redact_dict_entry(k: str, v: Any) -> Any:
    """Redact a single key-value entry for logging."""
    norm_k = normalize_key(k)
    if is_known_credential(k):
        return _mask_recursive_leaves(v)
    if norm_k in _WEBHOOK_URL_FIELDS:
        return _mask_url_value(norm_k, v)
    if norm_k == _HEADERS_FIELD:
        return _mask_headers(v)
    return redact_for_log(v)


def _redact_dict(obj: dict[str, Any]) -> dict[str, Any]:
    """Redact secrets from a dictionary before logging."""
    if "kind" in obj:
        return mask_channel(obj)
    return {k: _redact_dict_entry(k, v) for k, v in obj.items()}


def redact_for_log(obj: Any) -> Any:
    """
    Redact secrets from dictionaries, lists, or payloads before logging.
    """
    if obj is None:
        return None

    obj = _to_dict_or_raw(obj)

    if isinstance(obj, list):
        return [redact_for_log(item) for item in obj]
    if isinstance(obj, dict):
        return _redact_dict(obj)
    return obj
