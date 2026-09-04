"""
Tests for Validation Module

This module contains comprehensive tests for the validation utility functions.
"""

import unittest
from datetime import datetime
from unittest.mock import patch

from src.core.validation import (
    RETRIEVAL_SIZE_MAX,
    RETRIEVAL_SIZE_MIN,
    VALID_AGGREGATIONS,
    VALID_ENTITY_VALUES,
    VALID_ORDER_DIRECTIONS,
    VALID_TAG_FILTER_OPERATORS,
    WINDOW_SIZE_MAX_MS,
    BooleanCoercer,
    EventsValidator,
    StructureValidator,
    TimeValidator,
    ValidationError,
    ValidationResult,
)


class TestValidationError(unittest.TestCase):
    """Test ValidationError class"""

    def test_validation_error_basic(self):
        """Test basic ValidationError creation"""
        error = ValidationError(
            field="test_field",
            message="Test error message"
        )
        self.assertEqual(error.field, "test_field")
        self.assertEqual(error.message, "Test error message")
        self.assertIsNone(error.provided_value)
        self.assertIsNone(error.valid_values)
        self.assertIsNone(error.valid_range)
        self.assertIsNone(error.example)

    def test_validation_error_with_all_fields(self):
        """Test ValidationError with all optional fields"""
        error = ValidationError(
            field="test_field",
            message="Test error",
            provided_value="invalid",
            valid_values=["valid1", "valid2"],
            valid_range="1-100",
            example="valid1"
        )
        self.assertEqual(error.provided_value, "invalid")
        self.assertEqual(error.valid_values, ["valid1", "valid2"])
        self.assertEqual(error.valid_range, "1-100")
        self.assertEqual(error.example, "valid1")

    def test_validation_error_to_dict_basic(self):
        """Test to_dict with basic fields only"""
        error = ValidationError(
            field="test_field",
            message="Test error"
        )
        result = error.to_dict()
        self.assertEqual(result["field"], "test_field")
        self.assertEqual(result["message"], "Test error")
        self.assertNotIn("provided_value", result)
        self.assertNotIn("valid_values", result)
        self.assertNotIn("valid_range", result)
        self.assertNotIn("example", result)

    def test_validation_error_to_dict_with_all_fields(self):
        """Test to_dict with all fields"""
        error = ValidationError(
            field="test_field",
            message="Test error",
            provided_value="invalid",
            valid_values=["valid1", "valid2"],
            valid_range="1-100",
            example="valid1"
        )
        result = error.to_dict()
        self.assertEqual(result["field"], "test_field")
        self.assertEqual(result["message"], "Test error")
        self.assertEqual(result["provided_value"], "invalid")
        self.assertEqual(result["valid_values"], ["valid1", "valid2"])
        self.assertEqual(result["valid_range"], "1-100")
        self.assertEqual(result["example"], "valid1")

    def test_validation_error_to_dict_with_zero_value(self):
        """Test to_dict with provided_value of 0 (falsy but not None)"""
        error = ValidationError(
            field="test_field",
            message="Test error",
            provided_value=0
        )
        result = error.to_dict()
        self.assertIn("provided_value", result)
        self.assertEqual(result["provided_value"], 0)


class TestValidationResult(unittest.TestCase):
    """Test ValidationResult class"""

    def test_validation_result_init(self):
        """Test ValidationResult initialization"""
        result = ValidationResult()
        self.assertEqual(len(result.errors), 0)
        self.assertTrue(result.is_valid())

    def test_validation_result_add_error(self):
        """Test adding errors to ValidationResult"""
        result = ValidationResult()
        error = ValidationError(field="test", message="error")
        result.add_error(error)
        self.assertEqual(len(result.errors), 1)
        self.assertFalse(result.is_valid())

    def test_validation_result_multiple_errors(self):
        """Test adding multiple errors"""
        result = ValidationResult()
        result.add_error(ValidationError(field="field1", message="error1"))
        result.add_error(ValidationError(field="field2", message="error2"))
        self.assertEqual(len(result.errors), 2)
        self.assertFalse(result.is_valid())

    def test_validation_result_to_dict_valid(self):
        """Test to_dict when validation is valid"""
        result = ValidationResult()
        result_dict = result.to_dict()
        self.assertEqual(result_dict, {"valid": True})

    def test_validation_result_to_dict_invalid(self):
        """Test to_dict when validation has errors"""
        result = ValidationResult()
        result.add_error(ValidationError(field="test", message="error"))
        result_dict = result.to_dict()
        self.assertFalse(result_dict["valid"])
        self.assertEqual(result_dict["error_count"], 1)
        self.assertIn("errors", result_dict)
        self.assertIn("message", result_dict)
        self.assertEqual(len(result_dict["errors"]), 1)


class TestTimeValidator(unittest.TestCase):
    """Test TimeValidator class"""

    def test_validate_timestamp_none_not_required(self):
        """Test timestamp validation with None when not required"""
        error = TimeValidator.validate_timestamp(None, "test_field", required=False)
        self.assertIsNone(error)

    def test_validate_timestamp_none_required(self):
        """Test timestamp validation with None when required"""
        error = TimeValidator.validate_timestamp(None, "test_field", required=True)
        self.assertIsNotNone(error)
        self.assertEqual(error.field, "test_field")
        self.assertIn("required", error.message)

    def test_validate_timestamp_invalid_type(self):
        """Test timestamp validation with invalid type"""
        error = TimeValidator.validate_timestamp("not_an_int", "test_field")
        self.assertIsNotNone(error)
        self.assertIn("must be an integer", error.message)

    def test_validate_timestamp_too_old(self):
        """Test timestamp validation with timestamp before Jan 1, 2020"""
        old_timestamp = 1000000000000  # Year 2001
        error = TimeValidator.validate_timestamp(old_timestamp, "test_field")
        self.assertIsNotNone(error)
        self.assertIn("too far in the past", error.message)

    @patch('src.core.validation.datetime')
    def test_validate_timestamp_in_future(self, mock_datetime):
        """Test timestamp validation with future timestamp"""
        # Mock current time
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        future_timestamp = current_time_ms + 120000  # 2 minutes in future

        error = TimeValidator.validate_timestamp(future_timestamp, "test_field")
        self.assertIsNotNone(error)
        self.assertIn("cannot be in the future", error.message)

    @patch('src.core.validation.datetime')
    def test_validate_timestamp_valid(self, mock_datetime):
        """Test timestamp validation with valid timestamp"""
        # Mock current time
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        valid_timestamp = current_time_ms - 86400000  # Yesterday

        error = TimeValidator.validate_timestamp(valid_timestamp, "test_field")
        self.assertIsNone(error)

    @patch('src.core.validation.datetime')
    def test_validate_timestamp_with_clock_skew(self, mock_datetime):
        """Test timestamp validation allows 1 minute clock skew"""
        # Mock current time
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        # 30 seconds in future (within 1 minute skew allowance)
        timestamp_with_skew = current_time_ms + 30000

        error = TimeValidator.validate_timestamp(timestamp_with_skew, "test_field")
        self.assertIsNone(error)

    def test_validate_time_range_none(self):
        """Test time range validation with None"""
        error = TimeValidator.validate_time_range(None)
        self.assertIsNone(error)

    def test_validate_time_range_invalid_type(self):
        """Test time range validation with invalid type"""
        error = TimeValidator.validate_time_range(123)
        self.assertIsNotNone(error)
        self.assertIn("must be a string", error.message)

    def test_validate_time_range_valid_minutes(self):
        """Test time range validation with valid minutes"""
        error = TimeValidator.validate_time_range("last 30 minutes")
        self.assertIsNone(error)

    def test_validate_time_range_valid_hours(self):
        """Test time range validation with valid hours"""
        error = TimeValidator.validate_time_range("last 24 hours")
        self.assertIsNone(error)

    def test_validate_time_range_valid_days(self):
        """Test time range validation with valid days"""
        error = TimeValidator.validate_time_range("last 7 days")
        self.assertIsNone(error)

    def test_validate_time_range_valid_weeks(self):
        """Test time range validation with valid weeks"""
        error = TimeValidator.validate_time_range("last 2 weeks")
        self.assertIsNone(error)

    def test_validate_time_range_valid_months(self):
        """Test time range validation with valid months"""
        error = TimeValidator.validate_time_range("last 1 month")
        self.assertIsNone(error)

    def test_validate_time_range_valid_few_hours(self):
        """Test time range validation with 'last few hours'"""
        error = TimeValidator.validate_time_range("last few hours")
        self.assertIsNone(error)

    def test_validate_time_range_case_insensitive(self):
        """Test time range validation is case insensitive"""
        error = TimeValidator.validate_time_range("LAST 24 HOURS")
        self.assertIsNone(error)

    def test_validate_time_range_invalid_format(self):
        """Test time range validation with invalid format"""
        error = TimeValidator.validate_time_range("invalid format")
        self.assertIsNotNone(error)
        self.assertIn("not recognized", error.message)

    def test_validate_time_range_too_many_minutes(self):
        """Test time range validation with too many minutes"""
        error = TimeValidator.validate_time_range("last 2000 minutes")
        self.assertIsNotNone(error)
        self.assertIn("too many minutes", error.message)

    def test_validate_time_range_too_many_hours(self):
        """Test time range validation with too many hours"""
        error = TimeValidator.validate_time_range("last 1000 hours")
        self.assertIsNotNone(error)
        self.assertIn("too many hours", error.message)

    def test_validate_time_range_too_many_days(self):
        """Test time range validation with too many days"""
        error = TimeValidator.validate_time_range("last 100 days")
        self.assertIsNotNone(error)
        self.assertIn("too many days", error.message)

    def test_validate_time_range_too_many_weeks(self):
        """Test time range validation with too many weeks"""
        error = TimeValidator.validate_time_range("last 15 weeks")
        self.assertIsNotNone(error)
        self.assertIn("too many weeks", error.message)

    def test_validate_time_range_too_many_months(self):
        """Test time range validation with too many months"""
        error = TimeValidator.validate_time_range("last 5 months")
        self.assertIsNotNone(error)
        self.assertIn("too many months", error.message)

    def test_validate_time_range_singular_forms(self):
        """Test time range validation with singular forms"""
        self.assertIsNone(TimeValidator.validate_time_range("last 1 minute"))
        self.assertIsNone(TimeValidator.validate_time_range("last 1 hour"))
        self.assertIsNone(TimeValidator.validate_time_range("last 1 day"))
        self.assertIsNone(TimeValidator.validate_time_range("last 1 week"))
        self.assertIsNone(TimeValidator.validate_time_range("last 1 month"))

    def test_validate_time_parameters_no_params(self):
        """Test time parameters validation with no parameters"""
        result = TimeValidator.validate_time_parameters()
        self.assertFalse(result.is_valid())
        self.assertEqual(len(result.errors), 1)
        self.assertIn("MISSING REQUIRED PARAMETER", result.errors[0].message)

    def test_validate_time_parameters_with_time_range(self):
        """Test time parameters validation with time_range"""
        result = TimeValidator.validate_time_parameters(time_range="last 24 hours")
        self.assertTrue(result.is_valid())

    @patch('src.core.validation.datetime')
    def test_validate_time_parameters_with_from_time(self, mock_datetime):
        """Test time parameters validation with from_time"""
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        from_time = current_time_ms - 86400000  # Yesterday

        result = TimeValidator.validate_time_parameters(from_time=from_time)
        self.assertTrue(result.is_valid())

    @patch('src.core.validation.datetime')
    def test_validate_time_parameters_with_both_timestamps(self, mock_datetime):
        """Test time parameters validation with both timestamps"""
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        from_time = current_time_ms - 86400000  # Yesterday
        to_time = current_time_ms

        result = TimeValidator.validate_time_parameters(from_time=from_time, to_time=to_time)
        self.assertTrue(result.is_valid())

    @patch('src.core.validation.datetime')
    def test_validate_time_parameters_from_after_to(self, mock_datetime):
        """Test time parameters validation when from_time is after to_time"""
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        from_time = current_time_ms
        to_time = current_time_ms - 86400000  # Yesterday

        result = TimeValidator.validate_time_parameters(from_time=from_time, to_time=to_time)
        self.assertFalse(result.is_valid())
        self.assertTrue(any("must be before" in error.message for error in result.errors))

    @patch('src.core.validation.datetime')
    def test_validate_time_parameters_range_too_large(self, mock_datetime):
        """Test time parameters validation with range exceeding 90 days"""
        mock_now = datetime(2026, 4, 8, 5, 0, 0)
        mock_datetime.now.return_value = mock_now

        current_time_ms = int(mock_now.timestamp() * 1000)
        from_time = current_time_ms - (100 * 24 * 60 * 60 * 1000)  # 100 days ago
        to_time = current_time_ms

        result = TimeValidator.validate_time_parameters(from_time=from_time, to_time=to_time)
        self.assertFalse(result.is_valid())
        self.assertTrue(any("too large" in error.message for error in result.errors))

    def test_validate_time_parameters_invalid_time_range(self):
        """Test time parameters validation with invalid time_range"""
        result = TimeValidator.validate_time_parameters(time_range="invalid")
        self.assertFalse(result.is_valid())

    def test_validate_time_parameters_invalid_from_time(self):
        """Test time parameters validation with invalid from_time"""
        result = TimeValidator.validate_time_parameters(from_time="not_an_int")
        self.assertFalse(result.is_valid())


class TestEventsValidator(unittest.TestCase):
    """Test EventsValidator class"""

    def test_validate_event_type_filters_none(self):
        """Test event type filters validation with None"""
        error = EventsValidator.validate_event_type_filters(None)
        self.assertIsNone(error)

    def test_validate_event_type_filters_invalid_type(self):
        """Test event type filters validation with invalid type"""
        error = EventsValidator.validate_event_type_filters("not_a_list")
        self.assertIsNotNone(error)
        self.assertIn("must be a list", error.message)

    def test_validate_event_type_filters_valid_single(self):
        """Test event type filters validation with single valid type"""
        error = EventsValidator.validate_event_type_filters(["incident"])
        self.assertIsNone(error)

    def test_validate_event_type_filters_valid_multiple(self):
        """Test event type filters validation with multiple valid types"""
        error = EventsValidator.validate_event_type_filters(["incident", "issue", "change"])
        self.assertIsNone(error)

    def test_validate_event_type_filters_invalid_type_in_list(self):
        """Test event type filters validation with invalid type in list"""
        error = EventsValidator.validate_event_type_filters(["incident", "invalid_type"])
        self.assertIsNotNone(error)
        self.assertIn("Invalid event types", error.message)
        self.assertIn("invalid_type", error.message)

    def test_validate_event_type_filters_all_invalid(self):
        """Test event type filters validation with all invalid types"""
        error = EventsValidator.validate_event_type_filters(["invalid1", "invalid2"])
        self.assertIsNotNone(error)
        self.assertIn("invalid1", error.message)
        self.assertIn("invalid2", error.message)

    def test_validate_event_type_filters_empty_list(self):
        """Test event type filters validation with empty list"""
        error = EventsValidator.validate_event_type_filters([])
        self.assertIsNone(error)

    def test_validate_max_events_none(self):
        """Test max_events validation with None"""
        error = EventsValidator.validate_max_events(None)
        self.assertIsNone(error)

    def test_validate_max_events_invalid_type(self):
        """Test max_events validation with invalid type"""
        error = EventsValidator.validate_max_events("not_an_int")
        self.assertIsNotNone(error)
        self.assertIn("must be an integer", error.message)

    def test_validate_max_events_too_small(self):
        """Test max_events validation with value less than 1"""
        error = EventsValidator.validate_max_events(0)
        self.assertIsNotNone(error)
        self.assertIn("must be at least 1", error.message)

    def test_validate_max_events_negative(self):
        """Test max_events validation with negative value"""
        error = EventsValidator.validate_max_events(-5)
        self.assertIsNotNone(error)
        self.assertIn("must be at least 1", error.message)

    def test_validate_max_events_too_large(self):
        """Test max_events validation with value greater than 1000"""
        error = EventsValidator.validate_max_events(1500)
        self.assertIsNotNone(error)
        self.assertIn("too large", error.message)

    def test_validate_max_events_valid_min(self):
        """Test max_events validation with minimum valid value"""
        error = EventsValidator.validate_max_events(1)
        self.assertIsNone(error)

    def test_validate_max_events_valid_max(self):
        """Test max_events validation with maximum valid value"""
        error = EventsValidator.validate_max_events(1000)
        self.assertIsNone(error)

    def test_validate_max_events_valid_middle(self):
        """Test max_events validation with middle range value"""
        error = EventsValidator.validate_max_events(50)
        self.assertIsNone(error)


class TestValidatorConstants(unittest.TestCase):
    """Test validator constants"""

    def test_time_validator_max_time_range(self):
        """Test TimeValidator MAX_TIME_RANGE_MS constant"""
        expected = 90 * 24 * 60 * 60 * 1000  # 90 days in milliseconds
        self.assertEqual(TimeValidator.MAX_TIME_RANGE_MS, expected)

    def test_time_validator_min_timestamp(self):
        """Test TimeValidator MIN_TIMESTAMP_MS constant"""
        expected = 1577836800000  # Jan 1, 2020
        self.assertEqual(TimeValidator.MIN_TIMESTAMP_MS, expected)

    def test_events_validator_valid_event_types(self):
        """Test EventsValidator VALID_EVENT_TYPES constant"""
        expected = ["incident", "issue", "change"]
        self.assertEqual(EventsValidator.VALID_EVENT_TYPES, expected)


# ---------------------------------------------------------------------------
# StructureValidator tests
# ---------------------------------------------------------------------------

class TestStructureValidatorTagFilter(unittest.TestCase):
    """Tests for StructureValidator.validate_tag_filter_expression"""

    def _valid_tag_filter(self):
        return {
            "type": "TAG_FILTER",
            "name": "service.name",
            "operator": "EQUALS",
            "entity": "DESTINATION",
            "value": "my-service",
        }

    def test_none_returns_none(self):
        """Optional field: None → None (no error)"""
        self.assertIsNone(StructureValidator.validate_tag_filter_expression(None))

    def test_valid_tag_filter_returns_none(self):
        self.assertIsNone(
            StructureValidator.validate_tag_filter_expression(self._valid_tag_filter())
        )

    def test_valid_expression_returns_none(self):
        expr = {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [self._valid_tag_filter()],
        }
        self.assertIsNone(StructureValidator.validate_tag_filter_expression(expr))

    def test_missing_entity_flagged(self):
        tf = self._valid_tag_filter()
        del tf["entity"]
        result = StructureValidator.validate_tag_filter_expression(tf)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])
        self.assertTrue(any("entity" in e and "MISSING" in e for e in result["api_error"]))

    def test_invalid_entity_flagged(self):
        tf = self._valid_tag_filter()
        tf["entity"] = "WRONG"
        result = StructureValidator.validate_tag_filter_expression(tf)
        self.assertIsNotNone(result)
        self.assertTrue(any("entity" in e for e in result["api_error"]))

    def test_invalid_operator_flagged(self):
        tf = self._valid_tag_filter()
        tf["operator"] = "LIKE"
        result = StructureValidator.validate_tag_filter_expression(tf)
        self.assertIsNotNone(result)
        self.assertTrue(any("operator" in e for e in result["api_error"]))

    def test_missing_name_flagged(self):
        tf = self._valid_tag_filter()
        tf["name"] = ""
        result = StructureValidator.validate_tag_filter_expression(tf)
        self.assertIsNotNone(result)
        self.assertTrue(any("name" in e for e in result["api_error"]))

    def test_invalid_type_flagged(self):
        result = StructureValidator.validate_tag_filter_expression(
            {"type": "UNKNOWN", "name": "x", "operator": "EQUALS", "entity": "DESTINATION"}
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("type" in e for e in result["api_error"]))

    def test_non_dict_flagged(self):
        result = StructureValidator.validate_tag_filter_expression("not-a-dict")
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_multiple_errors_collected_in_one_pass(self):
        """Missing entity AND invalid operator must both appear in one response."""
        tf = {"type": "TAG_FILTER", "name": "service.name", "operator": "LIKE"}
        # entity missing, operator bad → 2 errors
        result = StructureValidator.validate_tag_filter_expression(tf)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["api_error"]), 2)

    def test_expression_invalid_logical_operator(self):
        expr = {
            "type": "EXPRESSION",
            "logicalOperator": "XOR",
            "elements": [self._valid_tag_filter()],
        }
        result = StructureValidator.validate_tag_filter_expression(expr)
        self.assertIsNotNone(result)
        self.assertTrue(any("logicalOperator" in e for e in result["api_error"]))

    def test_expression_missing_elements(self):
        expr = {"type": "EXPRESSION", "logicalOperator": "AND"}
        result = StructureValidator.validate_tag_filter_expression(expr)
        self.assertIsNotNone(result)
        self.assertTrue(any("elements" in e for e in result["api_error"]))

    def test_nested_expression_error_reported(self):
        """Errors in nested elements must bubble up."""
        bad_child = {"type": "TAG_FILTER", "name": "x", "operator": "BAD_OP", "entity": "DESTINATION"}
        expr = {"type": "EXPRESSION", "logicalOperator": "AND", "elements": [bad_child]}
        result = StructureValidator.validate_tag_filter_expression(expr)
        self.assertIsNotNone(result)
        self.assertTrue(any("operator" in e for e in result["api_error"]))

    def test_custom_field_name_in_error(self):
        result = StructureValidator.validate_tag_filter_expression(
            {"type": "TAG_FILTER", "name": "x", "operator": "EQUALS"},
            field_name="myFilter",
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("myFilter" in e for e in result["api_error"]))


class TestStructureValidatorMetrics(unittest.TestCase):
    """Tests for StructureValidator.validate_metrics_array"""

    def _valid_metrics(self):
        return [{"metric": "calls", "aggregation": "SUM"}]

    def test_none_optional_returns_none(self):
        self.assertIsNone(StructureValidator.validate_metrics_array(None))

    def test_none_required_returns_elicitation(self):
        result = StructureValidator.validate_metrics_array(None, required=True)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_valid_metrics_returns_none(self):
        self.assertIsNone(StructureValidator.validate_metrics_array(self._valid_metrics()))

    def test_not_a_list(self):
        result = StructureValidator.validate_metrics_array({"metric": "calls"})
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_empty_list_required(self):
        result = StructureValidator.validate_metrics_array([], required=True)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_empty_list_optional_returns_none(self):
        self.assertIsNone(StructureValidator.validate_metrics_array([]))

    def test_exceeds_max_items(self):
        metrics = [{"metric": f"m{i}", "aggregation": "SUM"} for i in range(6)]
        result = StructureValidator.validate_metrics_array(metrics, max_items=5)
        self.assertIsNotNone(result)
        self.assertTrue(any("maximum" in e for e in result["api_error"]))

    def test_invalid_aggregation(self):
        result = StructureValidator.validate_metrics_array(
            [{"metric": "calls", "aggregation": "AVERAGE"}]
        )
        self.assertIsNotNone(result)
        self.assertTrue(any("aggregation" in e for e in result["api_error"]))

    def test_missing_metric_name(self):
        result = StructureValidator.validate_metrics_array([{"aggregation": "SUM"}])
        self.assertIsNotNone(result)
        self.assertTrue(any("metric" in e for e in result["api_error"]))

    def test_multiple_errors_in_one_pass(self):
        """Two bad entries → all errors in one dict."""
        metrics = [
            {"metric": "", "aggregation": "BAD"},
            {"metric": "latency", "aggregation": "NOPE"},
        ]
        result = StructureValidator.validate_metrics_array(metrics)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["api_error"]), 2)

    def test_all_valid_aggregations_accepted(self):
        for agg in VALID_AGGREGATIONS:
            result = StructureValidator.validate_metrics_array(
                [{"metric": "calls", "aggregation": agg}]
            )
            self.assertIsNone(result, f"Expected None for aggregation={agg}")


class TestStructureValidatorOrder(unittest.TestCase):
    """Tests for StructureValidator.validate_order"""

    def test_none_returns_none(self):
        self.assertIsNone(StructureValidator.validate_order(None))

    def test_valid_asc(self):
        self.assertIsNone(StructureValidator.validate_order({"by": "calls", "direction": "ASC"}))

    def test_valid_desc(self):
        self.assertIsNone(StructureValidator.validate_order({"by": "latency", "direction": "DESC"}))

    def test_lowercase_direction_flagged(self):
        result = StructureValidator.validate_order({"by": "calls", "direction": "desc"})
        self.assertIsNotNone(result)
        self.assertTrue(any("direction" in e for e in result["api_error"]))

    def test_missing_by(self):
        result = StructureValidator.validate_order({"direction": "ASC"})
        self.assertIsNotNone(result)
        self.assertTrue(any("by" in e for e in result["api_error"]))

    def test_missing_direction(self):
        result = StructureValidator.validate_order({"by": "calls"})
        self.assertIsNotNone(result)
        self.assertTrue(any("direction" in e for e in result["api_error"]))

    def test_not_a_dict(self):
        result = StructureValidator.validate_order("ASC")
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_multiple_errors_collected(self):
        result = StructureValidator.validate_order({"by": "", "direction": "asc"})
        self.assertIsNotNone(result)
        self.assertGreaterEqual(len(result["api_error"]), 2)


class TestStructureValidatorTimeFrame(unittest.TestCase):
    """Tests for StructureValidator.validate_time_frame"""

    def test_none_returns_none(self):
        self.assertIsNone(StructureValidator.validate_time_frame(None))

    def test_valid_window_only(self):
        self.assertIsNone(StructureValidator.validate_time_frame({"windowSize": 3_600_000}))

    def test_valid_with_to(self):
        self.assertIsNone(
            StructureValidator.validate_time_frame({"to": 1_710_658_800_000, "windowSize": 3_600_000})
        )

    def test_window_size_zero_is_valid(self):
        self.assertIsNone(StructureValidator.validate_time_frame({"windowSize": 0}))

    def test_window_size_at_max_is_valid(self):
        self.assertIsNone(StructureValidator.validate_time_frame({"windowSize": WINDOW_SIZE_MAX_MS}))

    def test_window_size_exceeds_max(self):
        result = StructureValidator.validate_time_frame({"windowSize": WINDOW_SIZE_MAX_MS + 1})
        self.assertIsNotNone(result)
        self.assertTrue(any("windowSize" in e for e in result["api_error"]))

    def test_negative_window_size(self):
        result = StructureValidator.validate_time_frame({"windowSize": -1})
        self.assertIsNotNone(result)
        self.assertTrue(any("windowSize" in e for e in result["api_error"]))

    def test_non_int_window_size(self):
        result = StructureValidator.validate_time_frame({"windowSize": "3600000"})
        self.assertIsNotNone(result)
        self.assertTrue(any("windowSize" in e for e in result["api_error"]))

    def test_not_a_dict(self):
        result = StructureValidator.validate_time_frame(3_600_000)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_missing_window_size_is_ok(self):
        """windowSize is optional — dict without it should pass."""
        self.assertIsNone(StructureValidator.validate_time_frame({"to": 1_710_658_800_000}))


class TestStructureValidatorPagination(unittest.TestCase):
    """Tests for StructureValidator.validate_pagination"""

    def test_none_returns_none(self):
        self.assertIsNone(StructureValidator.validate_pagination(None))

    def test_valid_retrieval_size(self):
        self.assertIsNone(StructureValidator.validate_pagination({"retrievalSize": 50}))

    def test_min_boundary(self):
        self.assertIsNone(StructureValidator.validate_pagination({"retrievalSize": RETRIEVAL_SIZE_MIN}))

    def test_max_boundary(self):
        self.assertIsNone(StructureValidator.validate_pagination({"retrievalSize": RETRIEVAL_SIZE_MAX}))

    def test_below_min(self):
        result = StructureValidator.validate_pagination({"retrievalSize": 0})
        self.assertIsNotNone(result)
        self.assertTrue(any("retrievalSize" in e for e in result["api_error"]))

    def test_above_max(self):
        result = StructureValidator.validate_pagination({"retrievalSize": RETRIEVAL_SIZE_MAX + 1})
        self.assertIsNotNone(result)
        self.assertTrue(any("retrievalSize" in e for e in result["api_error"]))

    def test_non_int_retrieval_size(self):
        result = StructureValidator.validate_pagination({"retrievalSize": "50"})
        self.assertIsNotNone(result)
        self.assertTrue(any("retrievalSize" in e for e in result["api_error"]))

    def test_not_a_dict(self):
        result = StructureValidator.validate_pagination(50)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_custom_max_retrieval_size(self):
        """Custom max (e.g. trace details allows up to 10 000)."""
        result = StructureValidator.validate_pagination(
            {"retrievalSize": 500},
            max_retrieval_size=10_000,
        )
        self.assertIsNone(result)


class TestStructureValidatorGroup(unittest.TestCase):
    """Tests for StructureValidator.validate_group"""

    def test_none_optional_returns_none(self):
        self.assertIsNone(StructureValidator.validate_group(None))

    def test_none_required_returns_elicitation(self):
        result = StructureValidator.validate_group(None, required=True)
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_valid_group(self):
        group = {"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}
        self.assertIsNone(StructureValidator.validate_group(group))

    def test_camel_case_variant_accepted(self):
        """groupByTag (capital B) should also be accepted."""
        group = {"groupByTag": "service.name", "groupByTagEntity": "SOURCE"}
        self.assertIsNone(StructureValidator.validate_group(group))

    def test_missing_groupby_tag(self):
        result = StructureValidator.validate_group({"groupbyTagEntity": "DESTINATION"})
        self.assertIsNotNone(result)
        self.assertTrue(any("groupbyTag" in e for e in result["api_error"]))

    def test_missing_groupby_tag_entity(self):
        result = StructureValidator.validate_group({"groupbyTag": "service.name"})
        self.assertIsNotNone(result)
        self.assertTrue(any("groupbyTagEntity" in e for e in result["api_error"]))

    def test_default_guidance_is_unchanged(self):
        """No entity_guidance must reproduce the pre-parameter message exactly,
        so any call site that does not opt in is unaffected."""
        expected = (
            "group.groupbyTagEntity: required. "
            "Valid values: ['DESTINATION', 'NOT_APPLICABLE', 'SOURCE']. "
            'Example: "groupbyTagEntity": "DESTINATION"'
        )
        result = StructureValidator.validate_group({"groupbyTag": "service.name"})
        self.assertEqual(result["api_error"][0], expected)

    def test_invalid_groupby_tag_entity(self):
        group = {"groupbyTag": "service.name", "groupbyTagEntity": "ALL"}
        result = StructureValidator.validate_group(group)
        self.assertIsNotNone(result)
        self.assertTrue(any("groupbyTagEntity" in e for e in result["api_error"]))

    def test_not_a_dict(self):
        result = StructureValidator.validate_group("service.name")
        self.assertIsNotNone(result)
        self.assertTrue(result["elicitation_needed"])

    def test_all_valid_entity_values_accepted(self):
        for entity in VALID_ENTITY_VALUES:
            group = {"groupbyTag": "service.name", "groupbyTagEntity": entity}
            self.assertIsNone(StructureValidator.validate_group(group), f"Failed for entity={entity}")

    def test_multiple_errors_collected(self):
        result = StructureValidator.validate_group({})
        self.assertIsNotNone(result)
        # Both groupbyTag and groupbyTagEntity missing
        self.assertGreaterEqual(len(result["api_error"]), 2)


# ---------------------------------------------------------------------------
# BooleanCoercer tests
# ---------------------------------------------------------------------------

class TestBooleanCoercer(unittest.TestCase):
    """Tests for BooleanCoercer.coerce"""

    def test_true_bool_passthrough(self):
        self.assertIs(BooleanCoercer.coerce(True), True)

    def test_false_bool_passthrough(self):
        self.assertIs(BooleanCoercer.coerce(False), False)

    def test_none_returns_none(self):
        self.assertIsNone(BooleanCoercer.coerce(None))

    def test_int_one_returns_true(self):
        self.assertIs(BooleanCoercer.coerce(1), True)

    def test_int_zero_returns_false(self):
        self.assertIs(BooleanCoercer.coerce(0), False)

    def test_other_int_returns_none(self):
        self.assertIsNone(BooleanCoercer.coerce(2))
        self.assertIsNone(BooleanCoercer.coerce(-1))

    def test_string_true_variants(self):
        for val in ("true", "True", "TRUE", "yes", "YES", "on", "ON", "1"):
            self.assertIs(BooleanCoercer.coerce(val), True, f"Failed for {val!r}")

    def test_string_false_variants(self):
        for val in ("false", "False", "FALSE", "no", "NO", "off", "OFF", "0"):
            self.assertIs(BooleanCoercer.coerce(val), False, f"Failed for {val!r}")

    def test_unrecognised_string_returns_none(self):
        self.assertIsNone(BooleanCoercer.coerce("maybe"))
        self.assertIsNone(BooleanCoercer.coerce("enabled"))
        self.assertIsNone(BooleanCoercer.coerce(""))

    def test_whitespace_stripped(self):
        self.assertIs(BooleanCoercer.coerce("  true  "), True)
        self.assertIs(BooleanCoercer.coerce("  false  "), False)

    def test_non_scalar_returns_none(self):
        self.assertIsNone(BooleanCoercer.coerce([]))
        self.assertIsNone(BooleanCoercer.coerce({}))


if __name__ == '__main__':
    unittest.main()

