"""
Tests for Timestamp Utility Module

This module contains comprehensive tests for the timestamp utility functions.
"""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.core.timestamp_utils import (
    TIMEZONE_ALIASES,
    convert_datetime_param,
    convert_datetime_param_with_required_timezone,
    convert_datetime_params,
    convert_nested_datetime_param,
    convert_to_timestamp,
    get_current_timestamp,
    parse_datetime_string,
    parse_timezone,
)


class TestParseTimezone(unittest.TestCase):
    """Test parse_timezone function"""

    def test_parse_timezone_with_alias(self):
        """Test parsing timezone with common alias"""
        tz = parse_timezone("IST")
        self.assertEqual(str(tz), "Asia/Kolkata")

    def test_parse_timezone_with_iana_name(self):
        """Test parsing timezone with IANA name"""
        tz = parse_timezone("America/New_York")
        self.assertEqual(str(tz), "America/New_York")

    def test_parse_timezone_utc(self):
        """Test parsing UTC timezone"""
        tz = parse_timezone("UTC")
        self.assertEqual(str(tz), "UTC")

    def test_parse_timezone_invalid_defaults_to_utc(self):
        """Test that invalid timezone defaults to UTC"""
        tz = parse_timezone("Invalid/Timezone")
        self.assertEqual(str(tz), "UTC")

    def test_parse_timezone_case_insensitive_alias(self):
        """Test that timezone aliases are case-insensitive"""
        tz = parse_timezone("ist")
        self.assertEqual(str(tz), "Asia/Kolkata")


class TestParseDatetimeString(unittest.TestCase):
    """Test parse_datetime_string function"""

    def test_parse_datetime_format_1(self):
        """Test parsing '10 March 2026, 2:00 PM' format"""
        dt = parse_datetime_string("10 March 2026, 2:00 PM", "UTC")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 10)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 0)

    def test_parse_datetime_format_2(self):
        """Test parsing '10 March 2026, 2 PM' format"""
        dt = parse_datetime_string("10 March 2026, 2 PM", "UTC")
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 0)

    def test_parse_datetime_format_3(self):
        """Test parsing 'March 10, 2026 2:00 PM' format"""
        dt = parse_datetime_string("March 10, 2026 2:00 PM", "UTC")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 3)
        self.assertEqual(dt.day, 10)

    def test_parse_datetime_format_4(self):
        """Test parsing '2026-03-10 14:00:00' format"""
        dt = parse_datetime_string("2026-03-10 14:00:00", "UTC")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 14)

    def test_parse_datetime_format_5(self):
        """Test parsing '2026-03-10T14:00:00' format"""
        dt = parse_datetime_string("2026-03-10T14:00:00", "UTC")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 14)

    def test_parse_datetime_with_timezone(self):
        """Test parsing datetime with IST timezone"""
        dt = parse_datetime_string("10 March 2026, 2:00 PM", "IST")
        self.assertEqual(str(dt.tzinfo), "Asia/Kolkata")

    def test_parse_datetime_with_embedded_timezone(self):
        """Test parsing datetime with timezone in the string"""
        dt = parse_datetime_string("10 March 2026, 2:00 PM IST", "UTC")
        # Should use IST from the string, not UTC
        self.assertEqual(str(dt.tzinfo), "Asia/Kolkata")

    def test_parse_datetime_invalid_format_raises_error(self):
        """Test that invalid format raises ValueError"""
        with self.assertRaises(ValueError) as context:
            parse_datetime_string("invalid date format", "UTC")
        self.assertIn("Unable to parse datetime string", str(context.exception))

    def test_parse_datetime_slash_format(self):
        """Test parsing '10/03/2026 14:00' format"""
        dt = parse_datetime_string("10/03/2026 14:00", "UTC")
        self.assertEqual(dt.day, 10)
        self.assertEqual(dt.hour, 14)

    def test_parse_datetime_iso8601_with_z_suffix(self):
        """Test parsing ISO 8601 format with Z suffix (UTC indicator)"""
        dt = parse_datetime_string("2023-10-10T00:00:00Z", "UTC")
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 10)
        self.assertEqual(dt.hour, 0)
        self.assertEqual(dt.minute, 0)
        self.assertEqual(str(dt.tzinfo), "UTC")

    def test_parse_datetime_iso8601_with_z_suffix_ignores_provided_timezone(self):
        """Test that Z suffix forces UTC regardless of provided timezone"""
        dt = parse_datetime_string("2023-10-10T14:30:00Z", "IST")
        # Should use UTC from Z suffix, not IST
        self.assertEqual(str(dt.tzinfo), "UTC")
        self.assertEqual(dt.hour, 14)

    def test_parse_datetime_midnight_am_format(self):
        """Test parsing '10 October 2023, 00:00 AM' format"""
        dt = parse_datetime_string("10 October 2023, 00:00 AM", "UTC")
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 10)
        self.assertEqual(dt.hour, 0)
        self.assertEqual(dt.minute, 0)

    def test_parse_datetime_midnight_am_format_with_timezone(self):
        """Test parsing midnight AM format with IST timezone"""
        dt = parse_datetime_string("10 October 2023, 00:00 AM", "IST")
        self.assertEqual(dt.hour, 0)
        self.assertEqual(str(dt.tzinfo), "Asia/Kolkata")


class TestConvertToTimestamp(unittest.TestCase):
    """Test convert_to_timestamp function"""

    def test_convert_to_timestamp_success_milliseconds(self):
        """Test successful conversion to milliseconds"""
        result = convert_to_timestamp("10 March 2026, 2:00 PM", "UTC", "milliseconds")
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn("timestamp", result)
        self.assertIsInstance(result["timestamp"], int)
        self.assertEqual(result["unit"], "milliseconds")

    def test_convert_to_timestamp_success_seconds(self):
        """Test successful conversion to seconds"""
        result = convert_to_timestamp("10 March 2026, 2:00 PM", "UTC", "seconds")
        self.assertTrue(result["success"])
        self.assertEqual(result["unit"], "seconds")

    def test_convert_to_timestamp_with_ist(self):
        """Test conversion with IST timezone"""
        result = convert_to_timestamp("10 March 2026, 2:00 PM", "IST", "milliseconds")
        self.assertTrue(result["success"])
        self.assertEqual(result["timezone"], "IST")

    def test_convert_to_timestamp_empty_datetime_str(self):
        """Test with empty datetime string"""
        result = convert_to_timestamp("", "UTC")
        self.assertIn("error", result)
        self.assertIn("cannot be empty", result["error"])

    def test_convert_to_timestamp_whitespace_datetime_str(self):
        """Test with whitespace-only datetime string"""
        result = convert_to_timestamp("   ", "UTC")
        self.assertIn("error", result)

    def test_convert_to_timestamp_empty_timezone(self):
        """Test with empty timezone (should default to UTC)"""
        result = convert_to_timestamp("10 March 2026, 2:00 PM", "")
        self.assertTrue(result["success"])
        self.assertEqual(result["timezone"], "UTC")

    def test_convert_to_timestamp_invalid_output_unit(self):
        """Test with invalid output unit"""
        result = convert_to_timestamp("10 March 2026, 2:00 PM", "UTC", "invalid")
        self.assertIn("error", result)
        self.assertIn("Invalid output_unit", result["error"])

    def test_convert_to_timestamp_invalid_datetime_format(self):
        """Test with invalid datetime format"""
        result = convert_to_timestamp("not a valid date", "UTC")
        self.assertIn("error", result)

    def test_convert_to_timestamp_includes_timezone_offset(self):
        """Test that result includes timezone offset"""
        result = convert_to_timestamp("10 March 2026, 2:00 PM", "IST")
        self.assertIn("timezone_offset", result)
        self.assertIn("parsed_datetime", result)


class TestGetCurrentTimestamp(unittest.TestCase):
    """Test get_current_timestamp function"""

    def test_get_current_timestamp_milliseconds(self):
        """Test getting current timestamp in milliseconds"""
        result = get_current_timestamp("UTC", "milliseconds")
        self.assertTrue(result["success"])
        self.assertIn("timestamp", result)
        self.assertIsInstance(result["timestamp"], int)
        self.assertEqual(result["unit"], "milliseconds")

    def test_get_current_timestamp_seconds(self):
        """Test getting current timestamp in seconds"""
        result = get_current_timestamp("UTC", "seconds")
        self.assertTrue(result["success"])
        self.assertEqual(result["unit"], "seconds")

    def test_get_current_timestamp_with_timezone(self):
        """Test getting current timestamp with specific timezone"""
        result = get_current_timestamp("IST", "milliseconds")
        self.assertTrue(result["success"])
        self.assertEqual(result["timezone"], "IST")

    def test_get_current_timestamp_invalid_unit(self):
        """Test with invalid output unit"""
        result = get_current_timestamp("UTC", "invalid")
        self.assertIn("error", result)
        self.assertIn("Invalid output_unit", result["error"])

    def test_get_current_timestamp_includes_datetime(self):
        """Test that result includes current datetime"""
        result = get_current_timestamp("UTC")
        self.assertIn("current_datetime", result)
        self.assertIn("timezone_offset", result)


class TestConvertDatetimeParam(unittest.TestCase):
    """Test convert_datetime_param function"""

    def test_convert_datetime_param_none_value(self):
        """Test with None value"""
        result = convert_datetime_param(None, "to")
        self.assertIsNone(result["value"])
        self.assertFalse(result["converted"])

    def test_convert_datetime_param_numeric_value(self):
        """Test with numeric value (no conversion)"""
        result = convert_datetime_param(1234567890000, "to")
        self.assertEqual(result["value"], 1234567890000)
        self.assertFalse(result["converted"])

    def test_convert_datetime_param_string_with_timezone(self):
        """Test with datetime string including timezone"""
        result = convert_datetime_param("10 March 2026, 2:00 PM|IST", "to")
        self.assertTrue(result["converted"])
        self.assertEqual(result["timezone"], "IST")
        self.assertIsInstance(result["value"], int)

    def test_convert_datetime_param_string_without_timezone(self):
        """Test with datetime string without timezone (uses default)"""
        result = convert_datetime_param("10 March 2026, 2:00 PM", "to", "UTC")
        self.assertTrue(result["converted"])
        self.assertEqual(result["timezone"], "UTC")

    def test_convert_datetime_param_invalid_datetime(self):
        """Test with invalid datetime string"""
        result = convert_datetime_param("invalid date", "to")
        self.assertIn("error", result)
        self.assertFalse(result["converted"])

    def test_convert_datetime_param_non_string_non_numeric(self):
        """Test with non-string, non-numeric value"""
        result = convert_datetime_param(["list"], "to")
        self.assertEqual(result["value"], ["list"])
        self.assertFalse(result["converted"])


class TestConvertDatetimeParams(unittest.TestCase):
    """Test convert_datetime_params function"""

    def test_convert_datetime_params_multiple_params(self):
        """Test converting multiple parameters"""
        params = {
            "from_time": "10 March 2026, 1:00 PM|IST",
            "to_time": "10 March 2026, 2:00 PM|IST"
        }
        result = convert_datetime_params(params, ["from_time", "to_time"])
        self.assertIn("params", result)
        self.assertIn("conversions", result)
        self.assertTrue(result["conversions"]["from_time"]["converted"])
        self.assertTrue(result["conversions"]["to_time"]["converted"])

    def test_convert_datetime_params_mixed_types(self):
        """Test with mix of string and numeric values"""
        params = {
            "from_time": "10 March 2026, 1:00 PM|IST",
            "to_time": 1234567890000
        }
        result = convert_datetime_params(params, ["from_time", "to_time"])
        self.assertTrue(result["conversions"]["from_time"]["converted"])
        self.assertFalse(result["conversions"]["to_time"]["converted"])

    def test_convert_datetime_params_missing_param(self):
        """Test with parameter not in params dict"""
        params = {"from_time": "10 March 2026, 1:00 PM|IST"}
        result = convert_datetime_params(params, ["from_time", "to_time"])
        self.assertIn("params", result)
        self.assertIn("from_time", result["conversions"])
        self.assertNotIn("to_time", result["conversions"])

    def test_convert_datetime_params_conversion_error(self):
        """Test with invalid datetime causing error"""
        params = {"from_time": "invalid date"}
        result = convert_datetime_params(params, ["from_time"])
        self.assertIn("error", result)
        self.assertIn("param_name", result)

    def test_convert_datetime_params_empty_list(self):
        """Test with empty parameter list"""
        params = {"from_time": "10 March 2026, 1:00 PM|IST"}
        result = convert_datetime_params(params, [])
        self.assertEqual(result["params"], params)
        self.assertEqual(result["conversions"], {})


class TestConvertNestedDatetimeParam(unittest.TestCase):
    """Test convert_nested_datetime_param function"""

    def test_convert_nested_datetime_param_success(self):
        """Test successful nested parameter conversion"""
        params = {
            "time_frame": {
                "to": "10 March 2026, 2:00 PM|IST",
                "windowSize": 3600000
            }
        }
        result = convert_nested_datetime_param(params, "time_frame", "to")
        self.assertTrue(result["converted"])
        self.assertEqual(result["timezone"], "IST")
        self.assertIsInstance(result["params"]["time_frame"]["to"], int)

    def test_convert_nested_datetime_param_parent_not_dict(self):
        """Test when parent is not a dictionary"""
        params = {"time_frame": "not a dict"}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        self.assertFalse(result["converted"])

    def test_convert_nested_datetime_param_parent_missing(self):
        """Test when parent key doesn't exist"""
        params = {"other_key": {}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        self.assertFalse(result["converted"])

    def test_convert_nested_datetime_param_nested_key_missing(self):
        """Test when nested key doesn't exist"""
        params = {"time_frame": {"windowSize": 3600000}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        self.assertFalse(result["converted"])

    def test_convert_nested_datetime_param_numeric_value(self):
        """Test when nested value is already numeric"""
        params = {"time_frame": {"to": 1234567890000}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        self.assertFalse(result["converted"])

    def test_convert_nested_datetime_param_conversion_error(self):
        """Test when conversion fails"""
        params = {"time_frame": {"to": "invalid date"}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        self.assertIn("error", result)
        self.assertFalse(result["converted"])


class TestConvertDatetimeParamWithRequiredTimezone(unittest.TestCase):
    """Test convert_datetime_param_with_required_timezone function"""

    def test_convert_with_required_timezone_success(self):
        """Test successful conversion with timezone"""
        result = convert_datetime_param_with_required_timezone(
            "10 March 2026, 2:00 PM|IST",
            "start"
        )
        self.assertTrue(result["converted"])
        self.assertEqual(result["timezone"], "IST")
        self.assertIsInstance(result["value"], int)

    def test_convert_with_required_timezone_missing(self):
        """Test when timezone is missing (requires elicitation)"""
        result = convert_datetime_param_with_required_timezone(
            "10 March 2026, 2:00 PM",
            "start"
        )
        self.assertTrue(result["elicitation_needed"])
        self.assertIn("message", result)
        self.assertIn("missing_parameters", result)
        self.assertIn("timezone", result["missing_parameters"])

    def test_convert_with_required_timezone_none_value(self):
        """Test with None value"""
        result = convert_datetime_param_with_required_timezone(None, "start")
        self.assertIsNone(result["value"])
        self.assertFalse(result["converted"])

    def test_convert_with_required_timezone_numeric_value(self):
        """Test with numeric value"""
        result = convert_datetime_param_with_required_timezone(1234567890000, "start")
        self.assertEqual(result["value"], 1234567890000)
        self.assertFalse(result["converted"])

    def test_convert_with_required_timezone_non_string(self):
        """Test with non-string value"""
        result = convert_datetime_param_with_required_timezone(["list"], "start")
        self.assertEqual(result["value"], ["list"])
        self.assertFalse(result["converted"])

    def test_convert_with_required_timezone_conversion_error(self):
        """Test when conversion fails"""
        result = convert_datetime_param_with_required_timezone(
            "invalid date|IST",
            "start"
        )
        self.assertIn("error", result)
        self.assertFalse(result["converted"])


class TestTimezoneAliases(unittest.TestCase):
    """Test TIMEZONE_ALIASES constant"""

    def test_timezone_aliases_contains_common_timezones(self):
        """Test that common timezone aliases are defined"""
        self.assertIn("IST", TIMEZONE_ALIASES)
        self.assertIn("UTC", TIMEZONE_ALIASES)
        self.assertIn("ET", TIMEZONE_ALIASES)
        self.assertIn("PT", TIMEZONE_ALIASES)

    def test_timezone_aliases_values_are_valid(self):
        """Test that alias values are valid IANA names"""
        for alias, iana_name in TIMEZONE_ALIASES.items():
            try:
                ZoneInfo(iana_name)
            except Exception:
                self.fail(f"Invalid IANA timezone name for alias {alias}: {iana_name}")


if __name__ == '__main__':
    unittest.main()
