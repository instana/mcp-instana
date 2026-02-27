"""
Validation utilities for MCP tools.

This module provides reusable validation functions to ensure parameters
are valid before making API calls, reducing API failures and improving performance.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class ValidationError:
    """Represents a single validation error."""

    def __init__(
        self,
        field: str,
        message: str,
        provided_value: Any = None,
        valid_values: Optional[List[str]] = None,
        valid_range: Optional[str] = None,
        example: Optional[str] = None
    ):
        self.field = field
        self.message = message
        self.provided_value = provided_value
        self.valid_values = valid_values
        self.valid_range = valid_range
        self.example = example

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation error to dictionary format."""
        error_dict: Dict[str, Any] = {
            "field": self.field,
            "message": self.message,
        }

        if self.provided_value is not None:
            error_dict["provided_value"] = self.provided_value

        if self.valid_values:
            error_dict["valid_values"] = self.valid_values

        if self.valid_range:
            error_dict["valid_range"] = self.valid_range

        if self.example:
            error_dict["example"] = self.example

        return error_dict


class ValidationResult:
    """Result of parameter validation."""

    def __init__(self):
        self.errors: List[ValidationError] = []

    def add_error(self, error: ValidationError):
        """Add a validation error."""
        self.errors.append(error)

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary format."""
        if self.is_valid():
            return {"valid": True}

        return {
            "valid": False,
            "error_count": len(self.errors),
            "errors": [error.to_dict() for error in self.errors],
            "message": "Parameter validation failed. Please correct the following fields and try again."
        }


class TimeValidator:
    """Validator for time-related parameters."""

    # Maximum time range: 90 days in milliseconds
    MAX_TIME_RANGE_MS = 90 * 24 * 60 * 60 * 1000

    # Minimum valid timestamp (Jan 1, 2020)
    MIN_TIMESTAMP_MS = 1577836800000

    @staticmethod
    def validate_timestamp(
        value: Optional[int],
        field_name: str,
        required: bool = False
    ) -> Optional[ValidationError]:
        """
        Validate a timestamp parameter.

        Args:
            value: Timestamp in milliseconds
            field_name: Name of the field being validated
            required: Whether the field is required

        Returns:
            ValidationError if invalid, None if valid
        """
        # Check if required
        if required and value is None:
            return ValidationError(
                field=field_name,
                message=f"{field_name} is required",
                example="1770429420000"
            )

        # If not required and not provided, it's valid
        if value is None:
            return None

        # Check type
        if not isinstance(value, int):
            return ValidationError(
                field=field_name,
                message=f"{field_name} must be an integer (milliseconds since epoch)",
                provided_value=value,
                example="1770429420000"
            )

        # Check if timestamp is reasonable (not too old)
        current_time_ms = int(datetime.now().timestamp() * 1000)

        if value < TimeValidator.MIN_TIMESTAMP_MS:
            return ValidationError(
                field=field_name,
                message=f"{field_name} is too far in the past (before Jan 1, 2020)",
                provided_value=value,
                valid_range=f"Must be >= {TimeValidator.MIN_TIMESTAMP_MS} (Jan 1, 2020)",
                example=str(current_time_ms - 86400000)  # Yesterday
            )

        # Check if timestamp is in the future
        if value > current_time_ms + 60000:  # Allow 1 minute clock skew
            return ValidationError(
                field=field_name,
                message=f"{field_name} cannot be in the future",
                provided_value=value,
                valid_range=f"Must be <= {current_time_ms} (current time)",
                example=str(current_time_ms)
            )

        return None

    @staticmethod
    def validate_time_range(
        value: Optional[str],
        field_name: str = "time_range"
    ) -> Optional[ValidationError]:
        """
        Validate a natural language time range parameter.

        Args:
            value: Time range string like "last 24 hours"
            field_name: Name of the field being validated

        Returns:
            ValidationError if invalid, None if valid
        """
        if value is None:
            return None

        if not isinstance(value, str):
            return ValidationError(
                field=field_name,
                message=f"{field_name} must be a string",
                provided_value=value,
                example="last 24 hours"
            )

        # Valid patterns
        valid_patterns = [
            r"last\s+\d+\s+minute(s)?",
            r"last\s+\d+\s+hour(s)?",
            r"last\s+\d+\s+day(s)?",
            r"last\s+\d+\s+week(s)?",
            r"last\s+\d+\s+month(s)?",
            r"last\s+few\s+hours",
            r"last\s+hours",
            r"few\s+hours"
        ]

        value_lower = value.lower().strip()

        # Check if matches any valid pattern
        is_valid = any(re.match(pattern, value_lower) for pattern in valid_patterns)

        if not is_valid:
            return ValidationError(
                field=field_name,
                message=f"{field_name} format is not recognized",
                provided_value=value,
                valid_values=[
                    "last X minutes",
                    "last X hours",
                    "last X days",
                    "last X weeks",
                    "last X months",
                    "last few hours"
                ],
                example="last 24 hours"
            )

        # Extract number and validate range
        number_match = re.search(r'(\d+)', value_lower)
        if number_match:
            number = int(number_match.group(1))

            # Check reasonable limits for minutes
            if "minute" in value_lower and number > 1440:  # 24 hours
                return ValidationError(
                    field=field_name,
                    message=f"{field_name} specifies too many minutes (max 1440 minutes / 24 hours)",
                    provided_value=value,
                    valid_range="1-1440 minutes",
                    example="last 60 minutes"
                )

            if "hour" in value_lower and number > 720:  # 30 days
                return ValidationError(
                    field=field_name,
                    message=f"{field_name} specifies too many hours (max 720 hours / 30 days)",
                    provided_value=value,
                    valid_range="1-720 hours",
                    example="last 24 hours"
                )

            if "day" in value_lower and number > 90:
                return ValidationError(
                    field=field_name,
                    message=f"{field_name} specifies too many days (max 90 days)",
                    provided_value=value,
                    valid_range="1-90 days",
                    example="last 7 days"
                )

            if "week" in value_lower and number > 12:
                return ValidationError(
                    field=field_name,
                    message=f"{field_name} specifies too many weeks (max 12 weeks)",
                    provided_value=value,
                    valid_range="1-12 weeks",
                    example="last 2 weeks"
                )

            if "month" in value_lower and number > 3:
                return ValidationError(
                    field=field_name,
                    message=f"{field_name} specifies too many months (max 3 months)",
                    provided_value=value,
                    valid_range="1-3 months",
                    example="last 1 month"
                )

        return None

    @staticmethod
    def validate_time_parameters(
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        time_range: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate time-related parameters together.

        At least one time specification is REQUIRED:
        - Either time_range (e.g., "last 24 hours", "last 7 days")
        - Or from_time (with optional to_time, which defaults to now)

        Args:
            from_time: Start timestamp in milliseconds
            to_time: End timestamp in milliseconds
            time_range: Natural language time range

        Returns:
            ValidationResult with any errors found
        """
        result = ValidationResult()

        # CRITICAL: At least one time parameter must be provided
        if from_time is None and time_range is None:
            result.add_error(ValidationError(
                field="time_range or from_time",
                message="MISSING REQUIRED PARAMETER: Time specification is required but was not provided by the user. DO NOT create a default value or assume a time range. You MUST ask the user to specify the time range using the ask_followup_question tool.",
                valid_values=[
                    "Ask user: 'What time range would you like to query?' with suggestions like:",
                    "- 'last 5 minutes'",
                    "- 'last 1 hour'",
                    "- 'last 24 hours'",
                    "- 'last 7 days'",
                    "- 'last 30 days'",
                    "Or ask for specific timestamps (from_time in milliseconds)"
                ],
                example='Use ask_followup_question to get time_range from user before retrying the operation'
            ))
            return result  # Return early - no point validating individual params

        # Validate individual timestamps if provided
        from_error = TimeValidator.validate_timestamp(from_time, "from_time", required=False)
        if from_error:
            result.add_error(from_error)

        to_error = TimeValidator.validate_timestamp(to_time, "to_time", required=False)
        if to_error:
            result.add_error(to_error)

        # Validate time_range if provided
        time_range_error = TimeValidator.validate_time_range(time_range, "time_range")
        if time_range_error:
            result.add_error(time_range_error)

        # If both timestamps are valid, check their relationship
        if from_time is not None and to_time is not None and not from_error and not to_error:
            # Check if from_time is before to_time
            if from_time >= to_time:
                result.add_error(ValidationError(
                    field="from_time",
                    message="from_time must be before to_time",
                    provided_value=from_time,
                    example=f"Use from_time < {to_time}"
                ))

            # Check if time range is reasonable
            time_diff = to_time - from_time
            if time_diff > TimeValidator.MAX_TIME_RANGE_MS:
                days = time_diff / (24 * 60 * 60 * 1000)
                result.add_error(ValidationError(
                    field="time_range",
                    message=f"Time range is too large ({days:.1f} days). Maximum allowed is 90 days.",
                    valid_range="Maximum 90 days between from_time and to_time",
                    example="Reduce the time range or use filters to narrow results"
                ))

        return result


class EventsValidator:
    """Validator for events-specific parameters."""

    VALID_EVENT_TYPES = ["incident", "issue", "change"]

    @staticmethod
    def validate_event_type_filters(
        value: Optional[List[str]],
        field_name: str = "event_type_filters"
    ) -> Optional[ValidationError]:
        """
        Validate event type filters parameter.

        Args:
            value: List of event types
            field_name: Name of the field being validated

        Returns:
            ValidationError if invalid, None if valid
        """
        if value is None:
            return None

        if not isinstance(value, list):
            return ValidationError(
                field=field_name,
                message=f"{field_name} must be a list",
                provided_value=value,
                valid_values=EventsValidator.VALID_EVENT_TYPES,
                example='["incident", "issue"]'
            )

        # Check each value
        invalid_types = []
        for event_type in value:
            if event_type not in EventsValidator.VALID_EVENT_TYPES:
                invalid_types.append(event_type)

        if invalid_types:
            return ValidationError(
                field=field_name,
                message=f"Invalid event types: {', '.join(invalid_types)}",
                provided_value=value,
                valid_values=EventsValidator.VALID_EVENT_TYPES,
                example='["incident", "issue"]'
            )

        return None

    @staticmethod
    def validate_max_events(
        value: Optional[int],
        field_name: str = "max_events"
    ) -> Optional[ValidationError]:
        """
        Validate max_events parameter.

        Args:
            value: Maximum number of events
            field_name: Name of the field being validated

        Returns:
            ValidationError if invalid, None if valid
        """
        if value is None:
            return None

        if not isinstance(value, int):
            return ValidationError(
                field=field_name,
                message=f"{field_name} must be an integer",
                provided_value=value,
                example="50"
            )

        if value < 1:
            return ValidationError(
                field=field_name,
                message=f"{field_name} must be at least 1",
                provided_value=value,
                valid_range="1-1000",
                example="50"
            )

        if value > 1000:
            return ValidationError(
                field=field_name,
                message=f"{field_name} is too large (max 1000 to prevent performance issues)",
                provided_value=value,
                valid_range="1-1000",
                example="100"
            )

        return None
