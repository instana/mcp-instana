"""
Validation utilities for MCP tools.

This module provides reusable validation functions to ensure parameters
are valid before making API calls, reducing API failures and improving performance.

Classes
-------
ValidationError
    Holds a single field-level validation failure with context (provided value,
    valid values, valid range, example).

ValidationResult
    Accumulates zero or more ValidationErrors from a single validation pass.
    Callers check ``result.is_valid()`` and call ``result.to_dict()`` to produce
    the elicitation payload returned to the LLM.

TimeValidator
    Validates timestamp and natural-language time-range parameters.
    Used by: Events router.

EventsValidator
    Validates Events-domain-specific parameters (event_type_filters, max_events).
    Used by: Events router / service layer.

StructureValidator
    Validates the shared structural fields that appear across Application, Website,
    Mobile App, and Infrastructure analyze queries:

    * ``validate_tag_filter_expression`` — TAG_FILTER/EXPRESSION discriminator,
      required ``entity`` field and its enum, ``operator`` enum, non-empty ``name``.
    * ``validate_metrics_array`` — non-empty list, each entry has non-empty
      ``metric`` string and valid ``aggregation`` enum, list length ≤ max_items.
    * ``validate_order`` — ``by`` non-empty, ``direction`` in {ASC, DESC}.
    * ``validate_time_frame`` - ``windowSize`` within SDK bounds (0-2678400000 ms).
    * ``validate_granularity_ratio`` — cross-field check that ``windowSize /
      granularity_ms`` does not exceed ``MAX_GRANULARITY_DATA_POINTS`` (1 000) and
      that the granularity value itself does not overflow a 32-bit integer when the
      backend converts it to milliseconds.  Must be called after both
      ``validate_metrics_array`` and ``validate_time_frame`` pass.
      ``granularity_in_ms=True`` for infrastructure (granularity already in ms);
      ``granularity_in_ms=False`` (default) for all other domains (granularity in
      seconds).
    * ``validate_pagination`` - cursor-based ``retrievalSize`` within 1-200;
      or page-based ``page`` / ``pageSize`` when ``page_based=True``
      (synthetic playback endpoints use ``Pagination`` SDK model).
    * ``validate_synthetic_playback_structure`` — combined preflight for all
      six synthetic endpoints that share the same optional fields
      (``timeFrame``, ``order``, ``pagination``, ``tagFilterExpression``).
      Accepts flags for required-field checks and granularity ratio.
    * ``validate_group`` — ``groupbyTag`` non-empty, ``groupbyTagEntity`` enum.

    All methods collect *every* failing field before returning so the LLM receives
    the full error list in one shot (Vipin's requirement).

BooleanCoercer
    Silently normalises LLM-generated boolean-like values (string ``"true"``/
    ``"false"``, integers 0/1) to Python ``bool`` without triggering elicitation.
    Used anywhere a ``StrictBool`` SDK field would otherwise reject the input.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union


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


# ---------------------------------------------------------------------------
# Constants shared by StructureValidator
# ---------------------------------------------------------------------------

# aggregation enum — identical across MetricConfig, WebsiteMonitoringMetricsConfiguration,
# MobileAppMonitoringMetricsConfiguration, and SimpleMetricConfiguration (infra).
VALID_AGGREGATIONS = frozenset({
    "SUM", "MEAN", "MAX", "MIN",
    "P25", "P50", "P75", "P90", "P95", "P98", "P99", "P99_9", "P99_99",
    "DISTINCT_COUNT", "SUM_POSITIVE", "PER_SECOND", "INCREASE",
})

# beacon_type enum for website endpoints (GetWebsiteBeaconGroups, GetWebsiteBeacons)
VALID_WEBSITE_BEACON_TYPES = frozenset({
    "PAGELOAD", "RESOURCELOAD", "HTTPREQUEST", "ERROR", "CUSTOM", "PAGE_CHANGE",
})

# beacon_type enum for mobile app endpoints (GetMobileAppBeaconGroups, GetMobileAppBeacons)
VALID_MOBILE_BEACON_TYPES = frozenset({
    "SESSION_START", "HTTP_REQUEST", "CRASH", "CUSTOM", "VIEW_CHANGE", "DROP_BEACON", "PERF",
})

# operator enum from TagFilter.field_validator('operator')
VALID_TAG_FILTER_OPERATORS = frozenset({
    "EQUALS", "NOT_EQUAL", "CONTAINS", "NOT_CONTAIN",
    "STARTS_WITH", "ENDS_WITH", "NOT_STARTS_WITH", "NOT_ENDS_WITH",
    "GREATER_THAN", "GREATER_OR_EQUAL_THAN", "LESS_THAN", "LESS_OR_EQUAL_THAN",
    "NOT_EMPTY", "IS_EMPTY", "NOT_BLANK", "IS_BLANK", "REGEX_MATCH",
})

# entity enum — identical across TagFilter, Group, WebsiteBeaconTagGroup,
# MobileAppBeaconTagGroup (all use the same SDK field_validator).
VALID_ENTITY_VALUES = frozenset({"NOT_APPLICABLE", "DESTINATION", "SOURCE"})

# order.direction enum from Order.field_validator('direction')
VALID_ORDER_DIRECTIONS = frozenset({"ASC", "DESC"})

# TimeFrame.window_size SDK bounds (ge=0, le=2678400000  ~31 days)
WINDOW_SIZE_MAX_MS = 2_678_400_000

# CursorPagination.retrieval_size SDK bounds (ge=1, le=200)
RETRIEVAL_SIZE_MIN = 1
RETRIEVAL_SIZE_MAX = 200

# Maximum data points the backend will materialize for time-series endpoints
# (e.g. get_test_summary_list).  Exceeding this produces HTTP 400
# "too many values".  The same cap likely applies to any endpoint whose
# response size scales linearly with windowSize / granularity.
MAX_GRANULARITY_DATA_POINTS = 1_000

# Java Integer.MAX_VALUE in ms — granularity values above this cause the backend
# to overflow when converting seconds → milliseconds internally (HTTP 400
# "integer overflow").  Applies only when granularity_in_ms=False (seconds).
_JAVA_INT_MAX_MS = 2_147_483_647


# ---------------------------------------------------------------------------
# StructureValidator
# ---------------------------------------------------------------------------

class StructureValidator:
    """
    Pre-flight structural validation for the shared fields that appear across
    Application, Website, Mobile App, and Infrastructure analyze queries.

    Every method returns either:
    - ``None``  — the field is absent (optional) or structurally valid.
    - ``Dict``  — an elicitation dict with ``elicitation_needed: True``,
                  a human-readable ``message``, a short ``reason``, and
                  ``api_error`` (list of strings, one per problem found).

    All errors are **collected in a single pass** before returning so the LLM
    receives the complete list in one response (Vipin's requirement: no round-trip
    retries per field).

    The dict format mirrors the pattern established in PR #129
    (metric_validation.py / website_analyze.py / application_call_group.py).
    """

    # ------------------------------------------------------------------
    # tag_filter_expression
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_tag_filter_node(expr: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate the fields of a TAG_FILTER node."""
        name = expr.get("name")
        if not name or not isinstance(name, str):
            errors.append(
                f"{path}.name: required, must be a non-empty string "
                f"(e.g. 'service.name'). Got: {name!r}"
            )

        entity = expr.get("entity")
        if entity is None:
            errors.append(
                f"{path}.entity: MISSING — every TAG_FILTER must include "
                f"'entity'. Valid values: {sorted(VALID_ENTITY_VALUES)}. "
                f"Example: \"entity\": \"DESTINATION\""
            )
        elif entity not in VALID_ENTITY_VALUES:
            errors.append(
                f"{path}.entity: '{entity}' is not valid. "
                f"Valid values: {sorted(VALID_ENTITY_VALUES)}"
            )

        operator = expr.get("operator")
        if not operator or not isinstance(operator, str):
            errors.append(
                f"{path}.operator: required, must be a non-empty string. "
                f"Valid values: {sorted(VALID_TAG_FILTER_OPERATORS)}"
            )
        elif operator not in VALID_TAG_FILTER_OPERATORS:
            errors.append(
                f"{path}.operator: '{operator}' is not valid. "
                f"Valid values: {sorted(VALID_TAG_FILTER_OPERATORS)}"
            )

    @staticmethod
    def _validate_expression_node(expr: Dict[str, Any], path: str, errors: List[str]) -> None:
        """Validate the fields of an EXPRESSION node and recurse into its elements."""
        logical_op = expr.get("logicalOperator")
        if logical_op not in ("AND", "OR"):
            errors.append(
                f"{path}.logicalOperator: must be 'AND' or 'OR', got {logical_op!r}"
            )

        elements = expr.get("elements")
        if elements is None or not isinstance(elements, list):
            errors.append(
                f"{path}.elements: must be a list (can be empty), got {type(elements).__name__!r}"
            )
        else:
            for i, elem in enumerate(elements):
                StructureValidator._collect_tag_filter_errors(
                    elem, f"{path}.elements[{i}]", errors
                )

    @staticmethod
    def _collect_tag_filter_errors(
        expr: Any,
        path: str,
        errors: List[str],
    ) -> None:
        """
        Recursively walk a tagFilterExpression dict and collect every
        structural problem into *errors* as human-readable strings.
        """
        if not isinstance(expr, dict):
            errors.append(
                f"{path}: must be a dict with a 'type' key ('TAG_FILTER' or 'EXPRESSION'), "
                f"got {type(expr).__name__!r}"
            )
            return

        expr_type = expr.get("type")

        if expr_type == "TAG_FILTER":
            StructureValidator._validate_tag_filter_node(expr, path, errors)
        elif expr_type == "EXPRESSION":
            StructureValidator._validate_expression_node(expr, path, errors)
        else:
            errors.append(
                f"{path}.type: '{expr_type}' is not valid. "
                f"Must be 'TAG_FILTER' or 'EXPRESSION'"
            )

    @staticmethod
    def validate_tag_filter_expression(
        expr: Optional[Any],
        field_name: str = "tagFilterExpression",
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a tagFilterExpression dict.

        Returns ``None`` when *expr* is ``None`` (field is optional) or valid.
        Returns an elicitation dict listing **all** problems when invalid.

        Parameters
        ----------
        expr:
            Raw tagFilterExpression value from the LLM payload.
        field_name:
            Label used in error messages. Default: ``"tagFilterExpression"``.
        """
        if expr is None:
            return None

        errors: List[str] = []
        StructureValidator._collect_tag_filter_errors(expr, field_name, errors)

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"{field_name} validation failed: "
                f"{len(errors)} structural problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"The {field_name} has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    # ------------------------------------------------------------------
    # metrics array
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_metric_entry_errors(entry: Any, prefix: str, errors: List[str]) -> None:
        """Validate a single metric entry dict and append any problems to *errors*."""
        if not isinstance(entry, dict):
            errors.append(
                f"{prefix}: must be a dict with 'metric' and 'aggregation' keys, "
                f"got {type(entry).__name__!r}"
            )
            return

        metric_name = entry.get("metric")
        if not metric_name or not isinstance(metric_name, str):
            errors.append(
                f"{prefix}.metric: required, must be a non-empty string "
                f"(e.g. 'latency'). Got: {metric_name!r}"
            )

        aggregation = entry.get("aggregation")
        if not aggregation or not isinstance(aggregation, str):
            errors.append(
                f"{prefix}.aggregation: required, must be a non-empty string. "
                f"Valid values: {sorted(VALID_AGGREGATIONS)}"
            )
        elif aggregation not in VALID_AGGREGATIONS:
            errors.append(
                f"{prefix}.aggregation: '{aggregation}' is not valid. "
                f"Valid values: {sorted(VALID_AGGREGATIONS)}"
            )

    @staticmethod
    def validate_metrics_array(
        metrics: Optional[Any],
        field_name: str = "metrics",
        required: bool = False,
        max_items: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a metrics list.

        Returns ``None`` when valid or absent (and not required).
        Returns an elicitation dict listing all problems otherwise.

        Parameters
        ----------
        metrics:
            Raw metrics field value.
        field_name:
            Label for error messages.
        required:
            When ``True``, absent or empty list is an error.
        max_items:
            Maximum list length (5 for beacon/call/trace groups, 10 for infra).
        """
        if metrics is None:
            if required:
                return {
                    "elicitation_needed": True,
                    "reason": f"{field_name} is required but was not provided",
                    "api_error": [f"{field_name}: required field missing"],
                    "message": (
                        f"{field_name} is required. Provide a list of metric objects, e.g.:\n"
                        f'  [{{"metric": "calls", "aggregation": "SUM"}}, '
                        f'{{"metric": "latency", "aggregation": "MEAN"}}]'
                    ),
                }
            return None

        if not isinstance(metrics, list):
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} must be a list, got {type(metrics).__name__!r}",
                "api_error": [f"{field_name}: must be a list of metric objects"],
                "message": (
                    f"{field_name} must be a list of metric objects, e.g.:\n"
                    f'  [{{"metric": "calls", "aggregation": "SUM"}}]'
                ),
            }

        if required and len(metrics) == 0:
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} is empty — at least one metric is required",
                "api_error": [f"{field_name}: must contain at least one metric"],
                "message": (
                    f"{field_name} must contain at least one metric object, e.g.:\n"
                    f'  [{{"metric": "calls", "aggregation": "SUM"}}]'
                ),
            }

        errors: List[str] = []

        if len(metrics) > max_items:
            errors.append(
                f"{field_name}: contains {len(metrics)} items but maximum allowed is {max_items}"
            )

        for idx, entry in enumerate(metrics):
            StructureValidator._collect_metric_entry_errors(entry, f"{field_name}[{idx}]", errors)

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"{field_name} validation failed: "
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"{field_name} has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    # ------------------------------------------------------------------
    # order
    # ------------------------------------------------------------------

    @staticmethod
    def validate_order(
        order: Optional[Any],
        field_name: str = "order",
    ) -> Optional[Dict[str, Any]]:
        """
        Validate an order object ``{"by": "...", "direction": "ASC"|"DESC"}``.

        Returns ``None`` when *order* is ``None`` (optional) or valid.
        Note: ``direction`` is case-sensitive — 'asc' and 'ASCENDING' are both invalid.
        """
        if order is None:
            return None

        errors: List[str] = []

        if not isinstance(order, dict):
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} must be a dict, got {type(order).__name__!r}",
                "api_error": [f"{field_name}: must be a dict with 'by' and 'direction' keys"],
                "message": (
                    f"{field_name} must be a dict, e.g.:\n"
                    f'  {{"by": "calls", "direction": "DESC"}}'
                ),
            }

        by_val = order.get("by")
        if not by_val or not isinstance(by_val, str):
            errors.append(
                f"{field_name}.by: required, must be a non-empty string "
                f"(e.g. 'calls', 'latency'). Got: {by_val!r}"
            )

        direction = order.get("direction")
        if not direction or not isinstance(direction, str):
            errors.append(
                f"{field_name}.direction: required. "
                f"Valid values: {sorted(VALID_ORDER_DIRECTIONS)} (case-sensitive)"
            )
        elif direction not in VALID_ORDER_DIRECTIONS:
            errors.append(
                f"{field_name}.direction: '{direction}' is not valid. "
                f"Valid values: {sorted(VALID_ORDER_DIRECTIONS)} — note: case-sensitive, "
                f"use 'ASC' or 'DESC' not 'asc'/'desc'/'ASCENDING'/'DESCENDING'"
            )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"{field_name} validation failed: "
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"{field_name} has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    # ------------------------------------------------------------------
    # time_frame
    # ------------------------------------------------------------------

    @staticmethod
    def validate_time_frame(
        time_frame: Optional[Any],
        field_name: str = "timeFrame",
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a timeFrame object ``{"to": <int|None>, "windowSize": <int>}``.

        Checks ``windowSize`` against the SDK ``TimeFrame`` model bounds
        (``ge=0, le=2_678_400_000`` ms  ≈ 31 days).

        The ``to`` field is **not** checked here — datetime string conversion
        is handled separately by ``convert_nested_datetime_param`` in the router.

        Returns ``None`` when *time_frame* is ``None`` (optional) or valid.
        """
        if time_frame is None:
            return None

        if not isinstance(time_frame, dict):
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} must be a dict, got {type(time_frame).__name__!r}",
                "api_error": [f"{field_name}: must be a dict with 'windowSize' and optional 'to' keys"],
                "message": (
                    f"{field_name} must be a dict, e.g.:\n"
                    f'  {{"windowSize": 3600000}}\n'
                    f'  {{"to": 1710658800000, "windowSize": 3600000}}'
                ),
            }

        errors: List[str] = []
        window_size = time_frame.get("windowSize")

        if window_size is not None:
            if not isinstance(window_size, int):
                errors.append(
                    f"{field_name}.windowSize: must be an integer (milliseconds), "
                    f"got {type(window_size).__name__!r}"
                )
            elif window_size < 0 or window_size > WINDOW_SIZE_MAX_MS:
                errors.append(
                    f"{field_name}.windowSize: {window_size} is out of range. "
                    f"Must be 0-{WINDOW_SIZE_MAX_MS} ms (~31 days maximum). "
                    f"Example: 3600000 (1 hour)"
                )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"{field_name} validation failed: "
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"{field_name} has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    # ------------------------------------------------------------------
    # granularity / windowSize ratio  (cross-field)
    # ------------------------------------------------------------------

    @staticmethod
    def validate_granularity_ratio(
        metrics: Optional[Any],
        time_frame: Optional[Any],
        granularity_in_ms: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Cross-field check: ``windowSize / granularity_ms <= MAX_GRANULARITY_DATA_POINTS``.

        Also catches the backend integer-overflow bug where granularity (in seconds)
        exceeds Java's Integer.MAX_VALUE when the backend converts it to milliseconds.

        This is a *cross-field* validator — it requires both ``metrics`` (for
        granularity values) and ``timeFrame`` (for windowSize) to be present.
        Call it **after** ``validate_metrics_array`` and ``validate_time_frame``
        have already passed so that both fields are structurally sound.

        Parameters
        ----------
        metrics:
            The metrics list from the request payload.  Each entry may contain
            an optional ``granularity`` key.  Entries without ``granularity``
            are silently skipped.
        time_frame:
            The ``timeFrame`` dict from the request payload.  If ``None`` or
            ``windowSize`` is absent the check is skipped (nothing to validate).
        granularity_in_ms:
            ``True``  → granularity values are already in **milliseconds**
                        (infrastructure endpoints: ``get_entities``,
                        ``get_aggregated_entity_groups``).
            ``False`` → granularity values are in **seconds** (default; all
                        other domains: application, website, mobile, synthetic).

        Returns
        -------
        ``None`` when valid or when there is insufficient data to check.
        An elicitation dict listing every offending metric entry otherwise.

        Examples
        --------
        Safe — 1 hr window, 600 s granularity (ratio = 6):
            validate_granularity_ratio(
                [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}],
                {"windowSize": 3_600_000},
            )  # → None

        Unsafe — 30-day window, 600 s granularity (ratio = 4 320):
            validate_granularity_ratio(
                [{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}],
                {"windowSize": 2_592_000_000},
            )
            # → elicitation dict with safe minimum granularity suggestion
        """
        # Nothing to validate if either side is missing
        if not metrics or not isinstance(metrics, list):
            return None
        if not time_frame or not isinstance(time_frame, dict):
            return None

        window_size_ms = time_frame.get("windowSize")
        if not isinstance(window_size_ms, int) or window_size_ms <= 0:
            return None

        errors: List[str] = []

        for idx, entry in enumerate(metrics):
            if not isinstance(entry, dict):
                continue
            granularity = entry.get("granularity")
            if granularity is None:
                continue
            if not isinstance(granularity, int) or granularity <= 0:
                # Type/value errors are already caught by validate_metrics_array;
                # skip here to avoid duplicate messages.
                continue

            granularity_ms = granularity if granularity_in_ms else granularity * 1_000

            # Check 1: integer overflow (seconds-only domains)
            if not granularity_in_ms and granularity_ms > _JAVA_INT_MAX_MS:
                max_safe_s = _JAVA_INT_MAX_MS // 1_000  # 2 147 483 s ≈ 35 min
                errors.append(
                    f"metrics[{idx}].granularity {granularity}s overflows when the backend "
                    f"converts it to milliseconds (Java Integer.MAX_VALUE = {_JAVA_INT_MAX_MS} ms). "
                    f"Use granularity <= {max_safe_s}s (~35 minutes)."
                )
                continue  # ratio check is moot if overflow would occur

            # Check 2: too many data points
            ratio = window_size_ms / granularity_ms
            if ratio > MAX_GRANULARITY_DATA_POINTS:
                unit = "ms" if granularity_in_ms else "s"
                # Minimum safe granularity to stay within the cap
                min_safe = (
                    -(-window_size_ms // MAX_GRANULARITY_DATA_POINTS)  # ceiling division
                    if granularity_in_ms
                    else -(-window_size_ms // (MAX_GRANULARITY_DATA_POINTS * 1_000))
                )
                errors.append(
                    f"metrics[{idx}].granularity {granularity}{unit} produces "
                    f"{int(ratio)} data points for windowSize {window_size_ms} ms "
                    f"(max {MAX_GRANULARITY_DATA_POINTS}). "
                    f"Use granularity >= {min_safe}{unit}."
                )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"granularity/windowSize ratio validation failed: "
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"granularity/windowSize ratio has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    # ------------------------------------------------------------------
    # pagination
    # ------------------------------------------------------------------

    @staticmethod
    def validate_pagination(
        pagination: Optional[Any],
        field_name: str = "pagination",
        min_retrieval_size: int = RETRIEVAL_SIZE_MIN,
        max_retrieval_size: int = RETRIEVAL_SIZE_MAX,
        page_based: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a pagination object.

        Two modes controlled by ``page_based``:

        ``page_based=False`` (default) — cursor-based pagination used by
        Application, Website, Mobile App, and Infrastructure endpoints:
            ``{"retrievalSize": <int>}``
            ``retrievalSize``: optional, ``ge=1, le=200``

        ``page_based=True`` — offset-based pagination used by all synthetic
        playback endpoints (``Pagination`` SDK model):
            ``{"page": <int>, "pageSize": <int>}``
            ``page``:     optional, ``ge=1``
            ``pageSize``: optional, ``ge=1, le=200``

        Returns ``None`` when *pagination* is ``None`` (optional) or valid.
        """
        if pagination is None:
            return None

        example = '{"page": 1, "pageSize": 50}' if page_based else '{"retrievalSize": 50}'
        if not isinstance(pagination, dict):
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} must be a dict, got {type(pagination).__name__!r}",
                "api_error": [f"{field_name}: must be a dict, e.g. {example}"],
                "message": f"{field_name} must be a dict, e.g.:\n  {example}",
            }

        errors: List[str] = []

        if page_based:
            page = pagination.get("page")
            if page is not None:
                if not isinstance(page, int):
                    errors.append(
                        f"{field_name}.page: must be an integer, "
                        f"got {type(page).__name__!r}"
                    )
                elif page < 1:
                    errors.append(
                        f"{field_name}.page: {page} is out of range. Must be >= 1"
                    )

            page_size = pagination.get("pageSize")
            if page_size is not None:
                if not isinstance(page_size, int):
                    errors.append(
                        f"{field_name}.pageSize: must be an integer, "
                        f"got {type(page_size).__name__!r}"
                    )
                elif page_size < 1 or page_size > 200:
                    errors.append(
                        f"{field_name}.pageSize: {page_size} is out of range. "
                        f"Must be 1-200"
                    )
        else:
            retrieval_size = pagination.get("retrievalSize")
            if retrieval_size is not None:
                if not isinstance(retrieval_size, int):
                    errors.append(
                        f"{field_name}.retrievalSize: must be an integer, "
                        f"got {type(retrieval_size).__name__!r}"
                    )
                elif retrieval_size < min_retrieval_size or retrieval_size > max_retrieval_size:
                    errors.append(
                        f"{field_name}.retrievalSize: {retrieval_size} is out of range. "
                        f"Must be {min_retrieval_size}-{max_retrieval_size}"
                    )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"{field_name} validation failed: "
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"{field_name} has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    # ------------------------------------------------------------------
    # group  (Application call/trace groups, Website, Mobile App)
    # ------------------------------------------------------------------

    @staticmethod
    def validate_group(
        group: Optional[Any],
        field_name: str = "group",
        required: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a group object ``{"groupbyTag": "...", "groupbyTagEntity": "..."}``.

        Accepts both ``groupbyTag`` and ``groupByTag`` — the service layer
        normalises to the canonical alias afterwards.

        The *value* of ``groupbyTag`` is **not** checked here because allowed
        tag names differ per domain (e.g. only ``trace.endpoint.name`` /
        ``trace.service.name`` for trace groups vs. any catalog tag for call
        groups).  Domain-specific tag name checks belong in the service file.

        Returns ``None`` when *group* is ``None`` (and not required) or valid.
        """
        if group is None:
            if required:
                return {
                    "elicitation_needed": True,
                    "reason": f"{field_name} is required but was not provided",
                    "api_error": [f"{field_name}: required field missing"],
                    "message": (
                        f"{field_name} is required. Provide a grouping object, e.g.:\n"
                        f'  {{"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}}'
                    ),
                }
            return None

        if not isinstance(group, dict):
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} must be a dict, got {type(group).__name__!r}",
                "api_error": [f"{field_name}: must be a dict"],
                "message": (
                    f"{field_name} must be a dict, e.g.:\n"
                    f'  {{"groupbyTag": "service.name", "groupbyTagEntity": "DESTINATION"}}'
                ),
            }

        errors: List[str] = []

        # Accept both camelCase variants the LLM commonly produces
        groupby_tag = group.get("groupbyTag") or group.get("groupByTag")
        if not groupby_tag or not isinstance(groupby_tag, str):
            errors.append(
                f"{field_name}.groupbyTag: required, must be a non-empty string. "
                f"Use 'groupbyTag' (lowercase 'b') as the key. Got: {groupby_tag!r}"
            )

        groupby_tag_entity = (
            group.get("groupbyTagEntity") or group.get("groupByTagEntity")
        )
        if not groupby_tag_entity or not isinstance(groupby_tag_entity, str):
            errors.append(
                f"{field_name}.groupbyTagEntity: required. "
                f"Valid values: {sorted(VALID_ENTITY_VALUES)}. "
                f"Example: \"groupbyTagEntity\": \"DESTINATION\""
            )
        elif groupby_tag_entity not in VALID_ENTITY_VALUES:
            errors.append(
                f"{field_name}.groupbyTagEntity: '{groupby_tag_entity}' is not valid. "
                f"Valid values: {sorted(VALID_ENTITY_VALUES)}"
            )

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": (
                f"{field_name} validation failed: "
                f"{len(errors)} problem{'s' if len(errors) != 1 else ''} found"
            ),
            "api_error": errors,
            "message": (
                f"{field_name} has {len(errors)} problem(s). "
                f"Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }


    # ------------------------------------------------------------------
    # beacon_type
    # ------------------------------------------------------------------

    @staticmethod
    def validate_beacon_type(
        beacon_type: Optional[Any],
        valid_types: frozenset,
        field_name: str = "beacon_type",
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a beacon_type string against a set of allowed values.

        Returns ``None`` when *beacon_type* is ``None`` (optional at router level)
        or valid.  Returns an elicitation dict when the value is present but
        not a recognised enum member.

        Parameters
        ----------
        beacon_type:
            Raw beacon_type value from the LLM payload.
        valid_types:
            frozenset of accepted values (use ``VALID_WEBSITE_BEACON_TYPES``
            or ``VALID_MOBILE_BEACON_TYPES`` from this module).
        field_name:
            Label used in error messages. Default: ``"beacon_type"``.
        """
        if beacon_type is None:
            return None

        if not isinstance(beacon_type, str) or not beacon_type.strip():
            return {
                "elicitation_needed": True,
                "reason": f"{field_name} must be a non-empty string",
                "api_error": [
                    f"{field_name}: must be a non-empty string. "
                    f"Valid values: {sorted(valid_types)}"
                ],
                "message": (
                    f"{field_name} must be a non-empty string. "
                    f"Valid values: {sorted(valid_types)}"
                ),
            }

        if beacon_type not in valid_types:
            return {
                "elicitation_needed": True,
                "reason": (
                    f"{field_name} validation failed: '{beacon_type}' is not a valid beacon type"
                ),
                "api_error": [
                    f"{field_name}: '{beacon_type}' is not valid. "
                    f"Valid values: {sorted(valid_types)}"
                ],
                "message": (
                    f"{field_name} '{beacon_type}' is not valid. "
                    f"Valid values: {sorted(valid_types)}"
                ),
            }

        return None


    # ------------------------------------------------------------------
    # synthetic playback  (cross-method shared preflight)
    # ------------------------------------------------------------------

    @staticmethod
    def validate_synthetic_playback_structure(
        operation: str,
        request_body: Dict[str, Any],
        *,
        requires_metrics: bool = False,
        requires_synthetic_metrics: bool = False,
        check_granularity_ratio: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Run all structural pre-flight validators for a synthetic playback payload.

        Covers the five playback endpoints (``GetTestResult``,
        ``GetTestResultAnalytic``, ``GetTestResultList``,
        ``GetTestResultBase``, ``GetTestSummaryResult``) and the metrics
        endpoint (``GetMetricsResult``).  All share the same optional
        structural fields; only the required-field and granularity flags differ.

        Parameters
        ----------
        operation:
            Human-readable operation name used in error messages.
        request_body:
            Parsed payload dict.
        requires_metrics:
            Validate that ``metrics`` is a non-empty list with valid
            ``metric`` / ``aggregation`` entries.
            (``GetTestResult``, ``GetTestSummaryResult``, ``GetMetricsResult``)
        requires_synthetic_metrics:
            Validate that ``syntheticMetrics`` is a non-empty list of strings.
            (``GetTestResultAnalytic``, ``GetTestResultList``)
        check_granularity_ratio:
            Run the cross-field ``windowSize / granularity`` ratio check.
            Only meaningful when ``requires_metrics=True``.
            Granularity is in **seconds** for all synthetic endpoints.
        """
        errors: List[str] = []

        # --- required fields ---
        if requires_metrics:
            res = StructureValidator.validate_metrics_array(
                request_body.get("metrics"), required=True
            )
            if res:
                errors.extend(res["api_error"])

        if requires_synthetic_metrics:
            sm = request_body.get("syntheticMetrics")
            if not sm:
                errors.append(
                    "syntheticMetrics: required, must be a non-empty list of metric name strings"
                )
            elif not isinstance(sm, list):
                errors.append(
                    f"syntheticMetrics: must be a list of strings, got {type(sm).__name__!r}"
                )
            else:
                for i, item in enumerate(sm):
                    if not isinstance(item, str) or not item.strip():
                        errors.append(f"syntheticMetrics[{i}]: must be a non-empty string")

        # --- optional structural fields ---
        for validator_fn, field_val, kwargs in [
            (StructureValidator.validate_time_frame,            request_body.get("timeFrame"),             {}),
            (StructureValidator.validate_order,                 request_body.get("order"),                 {}),
            (StructureValidator.validate_pagination,            request_body.get("pagination"),            {"page_based": True}),
            (StructureValidator.validate_tag_filter_expression, request_body.get("tagFilterExpression"),   {}),
        ]:
            res = validator_fn(field_val, **kwargs)
            if res:
                errors.extend(res["api_error"])

        # --- cross-field: granularity / windowSize ratio ---
        if check_granularity_ratio:
            res = StructureValidator.validate_granularity_ratio(
                request_body.get("metrics"),
                request_body.get("timeFrame"),
                granularity_in_ms=False,  # synthetic granularity is always in seconds
            )
            if res:
                errors.extend(res["api_error"])

        if not errors:
            return None

        return {
            "elicitation_needed": True,
            "reason": f"{operation} payload has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The {operation} payload has {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }


# ---------------------------------------------------------------------------
# BooleanCoercer
# ---------------------------------------------------------------------------

class BooleanCoercer:
    """
    Silently coerces LLM-generated boolean-like values to Python ``bool``.

    The Instana SDK uses ``StrictBool`` for flags like ``includeInternal``,
    ``includeSynthetic``, and ``fillTimeSeries``.  LLMs frequently produce
    these as strings (``"true"``/``"false"``) or integers (``1``/``0``),
    which Pydantic strict mode rejects with an opaque ``ValidationError``.

    ``coerce`` normalises all common representations to ``True``, ``False``,
    or ``None`` (when the input is ``None`` or unrecognisable).  It never
    raises — callers decide what to do with ``None``.
    """

    _TRUE_VALUES: frozenset = frozenset({"true", "1", "yes", "on"})
    _FALSE_VALUES: frozenset = frozenset({"false", "0", "no", "off"})

    @staticmethod
    def coerce(value: Any) -> Optional[bool]:
        """
        Coerce *value* to ``bool`` or return ``None`` if unrecognisable.

        Parameters
        ----------
        value:
            The raw value from the LLM payload.

        Returns
        -------
        bool or None
            ``True``/``False`` when *value* is a recognised truthy/falsy input.
            ``None`` when *value* is ``None`` or not recognisable as boolean.

        Examples
        --------
        >>> BooleanCoercer.coerce(True)    # bool passthrough
        True
        >>> BooleanCoercer.coerce("true")  # LLM string
        True
        >>> BooleanCoercer.coerce(1)       # int truthy
        True
        >>> BooleanCoercer.coerce(None)
        None
        >>> BooleanCoercer.coerce("maybe")
        None
        """
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value == 1:
                return True
            if value == 0:
                return False
            return None
        if isinstance(value, str):
            lower = value.strip().lower()
            if lower in BooleanCoercer._TRUE_VALUES:
                return True
            if lower in BooleanCoercer._FALSE_VALUES:
                return False
        return None
