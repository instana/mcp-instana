"""
Tests for SyntheticAlertConfig against the real SDK Pydantic model.

This test file is placed in a separate directory outside tests/synthetic/ to avoid
sys.modules stubs from tests/synthetic/conftest.py.
"""

import importlib
import sys
from unittest.mock import MagicMock

import pytest

# Restore real modules for synthetic_alert_config and pydantic if sibling tests mocked them
for mod in ["instana_client.models.synthetic_alert_config", "src.synthetic.synthetic_alert"]:
    if mod in sys.modules and isinstance(sys.modules[mod], MagicMock):
        del sys.modules[mod]

if "pydantic" in sys.modules and isinstance(sys.modules["pydantic"], MagicMock):
    del sys.modules["pydantic"]

pytest.importorskip("instana_client.models.synthetic_alert_config")

sac_module = importlib.import_module("instana_client.models.synthetic_alert_config")
SyntheticAlertConfig = sac_module.SyntheticAlertConfig

from pydantic import ValidationError

import src.synthetic.synthetic_alert as sa_module

_build_config = sa_module._build_config

GOOD_PAYLOAD = {
    "name": "Login test failing",
    "description": "Fails in 2+ locations",
    "syntheticTestIds": ["CVkDqtbdHMR4pqms7K5N"],
    "alertChannelIds": [],
    "customPayloadFields": [],
    "rule": {"alertType": "failure", "metricName": "synthetic.metricsStatus", "aggregation": "SUM"},
    "timeThreshold": {"type": "violationsInSequence", "violationsCount": 2},
    "tagFilterExpression": None,
    "severity": 10,
    "affectedLocationsCount": 2,
    "evaluationType": "PER_LOCATION",
}


def test_documented_payload_is_accepted_by_sdk():
    """Verify that the documented create payload satisfies SyntheticAlertConfig validation."""
    config = SyntheticAlertConfig(**GOOD_PAYLOAD)
    assert config.name == "Login test failing"
    assert config.rule.metric_name == "synthetic.metricsStatus"
    assert config.time_threshold.violations_count == 2
    assert config.tag_filter_expression is None


@pytest.mark.parametrize("missing", ["tagFilterExpression", "rule", "timeThreshold", "syntheticTestIds"])
def test_missing_required_key_rejected(missing):
    """Verify that omitting any required field raises a Pydantic ValidationError."""
    bad = {k: v for k, v in GOOD_PAYLOAD.items() if k != missing}
    with pytest.raises(ValidationError):
        SyntheticAlertConfig(**bad)


def test_missing_rule_metric_name_rejected():
    """Verify that omitting rule.metricName raises ValidationError."""
    bad = {
        **GOOD_PAYLOAD,
        "rule": {"alertType": "failure"},
    }
    with pytest.raises(ValidationError):
        SyntheticAlertConfig(**bad)


def test_find_response_can_be_resubmitted_to_update():
    """Verify that extra server-returned fields (id, created, enabled) are ignored without error."""
    find_response = {**GOOD_PAYLOAD, "id": "alert-123", "created": 1710000000000, "enabled": True}
    config = SyntheticAlertConfig(**find_response)
    assert config.name == "Login test failing"


SERVER_MANAGED_KEYS = {"id", "created", "initialCreated", "readOnly", "enabled", "rbacTags", "displayUrl"}


def _live_tag_filter(name, string_value):
    """A TAG_FILTER as returned by a real tenant: `value` mirrors stringValue, other typed fields are null."""
    return {
        "type": "TAG_FILTER",
        "name": name,
        "stringValue": string_value,
        "numberValue": None,
        "booleanValue": None,
        "floatValue": None,
        "key": None,
        "value": string_value,
        "operator": "EQUALS",
        "entity": "NOT_APPLICABLE",
    }


@pytest.mark.parametrize(
    "tag_filter_expression",
    [
        {"type": "EXPRESSION", "logicalOperator": "AND", "elements": []},
        {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
                _live_tag_filter("synthetic.locationLabel", "Browserscript Playback PoP"),
                _live_tag_filter("synthetic.syntheticType", "API Script"),
            ],
        },
        _live_tag_filter("synthetic.locationLabel", "us"),
    ],
    ids=["empty_expression", "expression_with_filters", "bare_tag_filter"],
)
def test_live_find_response_round_trips_through_build_config(tag_filter_expression):
    """Verify a find response shaped like a real tenant's can be passed to update unchanged.

    Server-managed keys must not reach the request body, and null typed fields on a
    TAG_FILTER must not break the nested conversion.
    """
    find_response = {
        "name": "Login test failing",
        "description": "Fails in 2+ locations",
        "syntheticTestIds": [],
        "severity": 5,
        "tagFilterExpression": tag_filter_expression,
        "rule": {"alertType": "failure", "metricName": "status", "aggregation": "SUM"},
        "alertChannelIds": [],
        "gracePeriod": None,
        "timeThreshold": {"type": "violationsInSequence", "violationsCount": 1},
        "customPayloadFields": [],
        "includeOnDemand": False,
        "affectedLocationsCount": None,
        "evaluationType": "PER_LOCATION",
        "id": "alert-123",
        "created": 1764677880138,
        "initialCreated": 1764677880138,
        "readOnly": False,
        "enabled": True,
        "rbacTags": [],
        "displayUrl": "https://instana.example/#/syntheticSmartAlerts;alertId=alert-123/details",
    }

    config, err = _build_config(find_response)

    assert err is None
    assert config is not None
    body = config.to_dict()
    assert SERVER_MANAGED_KEYS.isdisjoint(body)
    assert body["name"] == "Login test failing"
    assert body["tagFilterExpression"]["type"] == tag_filter_expression["type"]


def test_build_config_helper_success():
    """Verify _build_config returns (config_object, None) for valid payload."""
    config, err = _build_config(GOOD_PAYLOAD)
    assert err is None
    assert config is not None
    assert config.name == "Login test failing"


def test_build_config_helper_returns_structured_errors_on_invalid_payload():
    """Verify _build_config produces structured elicitation error dict on invalid payload."""
    config, err = _build_config({"name": "incomplete payload"})
    assert config is None
    assert err is not None
    assert err["elicitation_needed"] is True
    assert err["reason"] == "invalid_payload"
    assert "api_error" in err
    fields = [e["field"] for e in err["api_error"]]
    assert any("rule" in f for f in fields)
    assert any("timeThreshold" in f or "time_threshold" in f for f in fields)


def test_build_config_helper_handles_non_dict_payload():
    """Verify _build_config rejects non-dict payloads cleanly."""
    config, err = _build_config("[1, 2, 3]")
    assert config is None
    assert err == {"error": "payload must be a JSON object"}


def test_build_config_preserves_tag_filter_fields():
    """Verify a TAG_FILTER tagFilterExpression keeps its nested fields through serialization."""
    tag_filter = {
        "type": "TAG_FILTER",
        "name": "synthetic.locationId",
        "operator": "EQUALS",
        "entity": "NOT_APPLICABLE",
        "stringValue": "loc-1",
    }
    config, err = _build_config({**GOOD_PAYLOAD, "tagFilterExpression": tag_filter})
    assert err is None
    assert config is not None
    assert config.to_dict()["tagFilterExpression"] == tag_filter


def test_build_config_preserves_nested_expression():
    """Verify an EXPRESSION tagFilterExpression keeps its nested elements."""
    element = {
        "type": "TAG_FILTER",
        "name": "synthetic.locationId",
        "operator": "EQUALS",
        "entity": "NOT_APPLICABLE",
        "stringValue": "loc-1",
    }
    expression = {"type": "EXPRESSION", "logicalOperator": "AND", "elements": [element]}
    config, err = _build_config({**GOOD_PAYLOAD, "tagFilterExpression": expression})
    assert err is None
    assert config is not None
    dumped = config.to_dict()["tagFilterExpression"]
    assert dumped["type"] == "EXPRESSION"
    assert dumped["logicalOperator"] == "AND"
    assert dumped["elements"] == [element]


def test_build_config_preserves_custom_payload_fields():
    """Verify customPayloadFields entries are converted and keep their type-specific fields."""
    field = {"type": "staticString", "key": "team", "value": "sre"}
    config, err = _build_config({**GOOD_PAYLOAD, "customPayloadFields": [field]})
    assert err is None
    assert config is not None
    assert config.to_dict()["customPayloadFields"] == [field]



def _issue_fields(err):
    return [e["field"] for e in err["api_error"]]


@pytest.mark.parametrize(
    "tag_filter, expected_field",
    [
        ({"name": "x"}, "tagFilterExpression"),  # missing discriminator
        ({"type": "BOGUS"}, "tagFilterExpression"),  # unknown discriminator
        (
            {"type": "TAG_FILTER", "name": "x", "operator": "NOPE", "entity": "NOT_APPLICABLE"},
            "tagFilterExpression.operator",
        ),
        (
            {"type": "TAG_FILTER", "operator": "EQUALS", "entity": "NOT_APPLICABLE"},
            "tagFilterExpression.name",
        ),
        (
            {"type": "EXPRESSION", "logicalOperator": "AND", "elements": "zzz"},
            "tagFilterExpression",
        ),
    ],
)
def test_build_config_invalid_tag_filter_returns_structured_error(tag_filter, expected_field):
    """Verify a malformed tagFilterExpression yields an elicitation error, not an exception."""
    config, err = _build_config({**GOOD_PAYLOAD, "tagFilterExpression": tag_filter})
    assert config is None
    assert err["elicitation_needed"] is True
    assert err["reason"] == "invalid_payload"
    assert expected_field in _issue_fields(err)


@pytest.mark.parametrize(
    "bad_field",
    [
        {"key": "k"},  # missing discriminator
        {"type": "BOGUS", "key": "k"},  # unknown discriminator
        {"type": "staticString", "value": "v"},  # missing key
    ],
)
def test_build_config_invalid_custom_payload_field_reports_index(bad_field):
    """Verify a malformed customPayloadFields entry is reported with its list index."""
    good = {"type": "staticString", "key": "ok", "value": "v"}
    config, err = _build_config({**GOOD_PAYLOAD, "customPayloadFields": [good, bad_field]})
    assert config is None
    assert err["elicitation_needed"] is True
    assert all(f.startswith("customPayloadFields[1]") for f in _issue_fields(err))


def test_build_config_reports_all_nested_issues_together():
    """Verify issues from tagFilterExpression and customPayloadFields are returned in one response."""
    config, err = _build_config({
        **GOOD_PAYLOAD,
        "tagFilterExpression": {"type": "BOGUS"},
        "customPayloadFields": [{"key": "k"}],
    })
    assert config is None
    fields = _issue_fields(err)
    assert "tagFilterExpression" in fields
    assert "customPayloadFields[0]" in fields
