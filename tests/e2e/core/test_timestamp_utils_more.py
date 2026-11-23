"""Mocked e2e tests for remaining branches in src/core/timestamp_utils.py."""

import pytest

from src.core.timestamp_utils import (
    convert_datetime_param,
    convert_datetime_param_with_required_timezone,
    convert_datetime_params,
    convert_nested_datetime_param,
    convert_to_timestamp,
    get_current_timestamp,
    parse_datetime_string,
    parse_timezone,
)

# 2026-03-19 14:47:00 UTC
_MARCH_19_UTC_MS = 1773931620000


class TestParseHelpersE2E:
    """parse_timezone and parse_datetime_string."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_parse_timezone_alias_and_invalid(self):
        assert str(parse_timezone("ist")) == "Asia/Kolkata"
        assert str(parse_timezone("Not/AZone")) == "UTC"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_parse_datetime_string_trailing_alias_overrides_timezone(self):
        dt = parse_datetime_string("2026-03-19 14:47:00 IST", timezone="UTC")
        assert str(dt.tzinfo) == "Asia/Kolkata"
        assert dt.hour == 14

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_parse_datetime_string_z_suffix_forces_utc(self):
        dt = parse_datetime_string("2026-03-19T14:47:00Z", timezone="IST")
        assert str(dt.tzinfo) == "UTC"
        assert int(dt.timestamp() * 1000) == _MARCH_19_UTC_MS

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_parse_datetime_string_unparseable_raises(self):
        with pytest.raises(ValueError, match="Unable to parse datetime string"):
            parse_datetime_string("nonsense", "UTC")


class TestConvertToTimestampE2E:
    """Validation and error branches of convert_to_timestamp."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_empty_datetime_string_is_error(self):
        result = convert_to_timestamp("   ")
        assert "cannot be empty" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_blank_timezone_defaults_to_utc(self):
        result = convert_to_timestamp("2026-03-19 14:47:00", timezone="  ")
        assert result["success"] is True
        assert result["timestamp"] == _MARCH_19_UTC_MS

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_output_unit_is_error(self):
        result = convert_to_timestamp("2026-03-19 14:47:00", output_unit="days")
        assert "Invalid output_unit" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_seconds_unit_and_unparseable_input(self):
        ok = convert_to_timestamp("2026-03-19 14:47:00", "UTC", "seconds")
        assert ok["timestamp"] == _MARCH_19_UTC_MS // 1000
        assert ok["unit"] == "seconds"

        bad = convert_to_timestamp("garbage", "UTC")
        assert "Unable to parse" in bad["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unexpected_exception_is_reported(self, monkeypatch):
        def _boom(*_args, **_kwargs):
            raise RuntimeError("kaput")

        monkeypatch.setattr("src.core.timestamp_utils.parse_datetime_string", _boom)
        result = convert_to_timestamp("2026-03-19 14:47:00")
        assert result["error"] == "Unexpected error: kaput"


class TestConvertDatetimeParamE2E:
    """convert_datetime_param pass-through and default timezone branches."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_none_numeric_and_non_string_values_pass_through(self):
        assert convert_datetime_param(None, "to") == {"value": None, "converted": False}
        assert convert_datetime_param(1234, "to") == {"value": 1234, "converted": False}
        assert convert_datetime_param(1.5, "to")["converted"] is False
        assert convert_datetime_param(["x"], "to") == {"value": ["x"], "converted": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_string_without_timezone_uses_default(self):
        result = convert_datetime_param("2026-03-19 14:47:00", "to", default_timezone="UTC")
        assert result == {"value": _MARCH_19_UTC_MS, "converted": True, "timezone": "UTC"}


class TestConvertDatetimeParamsE2E:
    """convert_datetime_params over several keys."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_converts_strings_and_keeps_numbers(self):
        params = {"from_time": "2026-03-19 14:47:00|UTC", "to_time": 99, "other": "x"}
        result = convert_datetime_params(params, ["from_time", "to_time", "missing"])
        assert result["params"]["from_time"] == _MARCH_19_UTC_MS
        assert result["params"]["to_time"] == 99
        assert result["params"]["other"] == "x"
        assert result["conversions"]["from_time"] == {"converted": True, "timezone": "UTC"}
        assert result["conversions"]["to_time"] == {"converted": False, "timezone": None}
        assert "missing" not in result["conversions"]
        # input is not mutated
        assert params["from_time"] == "2026-03-19 14:47:00|UTC"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_returns_error_for_invalid_value(self):
        params = {"from_time": "nonsense|UTC"}
        result = convert_datetime_params(params, ["from_time"])
        assert result["param_name"] == "from_time"
        assert "Failed to convert from_time datetime" in result["error"]
        assert result["params"] is params


class TestConvertNestedDatetimeParamE2E:
    """convert_nested_datetime_param branches."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_missing_parent_or_nested_key_is_noop(self):
        assert convert_nested_datetime_param({}, "time_frame", "to") == {"params": {}, "converted": False}
        not_dict = {"time_frame": 5}
        assert convert_nested_datetime_param(not_dict, "time_frame", "to")["converted"] is False
        no_key = {"time_frame": {"windowSize": 1}}
        assert convert_nested_datetime_param(no_key, "time_frame", "to")["converted"] is False

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_numeric_value_is_not_converted(self):
        params = {"time_frame": {"to": 1000, "windowSize": 5}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        assert result == {"params": params, "converted": False}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_string_value_is_converted_on_a_copy(self):
        params = {"time_frame": {"to": "2026-03-19 14:47:00|UTC", "windowSize": 5}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        assert result["converted"] is True
        assert result["timezone"] == "UTC"
        assert result["params"]["time_frame"] == {"to": _MARCH_19_UTC_MS, "windowSize": 5}
        assert params["time_frame"]["to"] == "2026-03-19 14:47:00|UTC"

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_invalid_value_returns_error(self):
        params = {"time_frame": {"to": "nonsense|UTC"}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        assert result["converted"] is False
        assert "Failed to convert time_frame.to datetime" in result["error"]
        assert result["params"] is params


class TestRequiredTimezoneConversionE2E:
    """convert_datetime_param_with_required_timezone."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_non_strings_pass_through(self):
        assert convert_datetime_param_with_required_timezone(None, "start") == {"value": None, "converted": False}
        assert convert_datetime_param_with_required_timezone(7, "start") == {"value": 7, "converted": False}
        assert convert_datetime_param_with_required_timezone({"a": 1}, "start")["converted"] is False

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_missing_timezone_triggers_elicitation(self):
        result = convert_datetime_param_with_required_timezone("19 March 2026, 2:47 PM", "start")
        assert result["elicitation_needed"] is True
        assert result["missing_parameters"] == ["timezone"]
        assert "start" in result["user_prompt"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_valid_timezone_converts(self):
        result = convert_datetime_param_with_required_timezone("19 March 2026, 2:47 PM|IST", "start")
        assert result["converted"] is True
        assert result["timezone"] == "IST"
        assert result["value"] == _MARCH_19_UTC_MS - (5 * 3600 + 30 * 60) * 1000

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_seconds_output_and_invalid_value(self):
        seconds = convert_datetime_param_with_required_timezone(
            "2026-03-19 14:47:00|UTC", "start", output_unit="seconds"
        )
        assert seconds["value"] == _MARCH_19_UTC_MS // 1000

        bad = convert_datetime_param_with_required_timezone("nonsense|UTC", "start")
        assert bad["converted"] is False
        assert "Failed to convert start datetime" in bad["error"]


class TestCurrentTimestampErrorE2E:
    """Unexpected failures in get_current_timestamp."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_unexpected_exception_returns_error(self, monkeypatch):
        def _boom(*_args, **_kwargs):
            raise RuntimeError("tz failure")

        monkeypatch.setattr("src.core.timestamp_utils.parse_timezone", _boom)
        assert get_current_timestamp() == {"error": "tz failure"}
