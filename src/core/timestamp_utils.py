"""
Timestamp Utility Module

Provides timezone-aware datetime parsing and Unix timestamp conversion.
This standalone utility helps convert human-readable datetime strings into precise
Unix epoch timestamps (milliseconds) for use with Instana APIs.
"""

import logging
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Common timezone mappings
TIMEZONE_ALIASES = {
    "IST": "Asia/Kolkata",
    "ET": "America/New_York",      # Eastern Time (DST-aware)
    "PT": "America/Los_Angeles",   # Pacific Time (DST-aware)
    "CT": "America/Chicago",       # Central Time (DST-aware)
    "MT": "America/Denver",        # Mountain Time (DST-aware)
    "GMT": "GMT",
    "UTC": "UTC",
    "CET": "Europe/Paris",
    "JST": "Asia/Tokyo",
    "AEST": "Australia/Sydney",
    # Add fixed offset support if needed
    "EST5": "Etc/GMT+5",          # Fixed EST (no DST)
    "PST8": "Etc/GMT+8",          # Fixed PST (no DST)
}


def parse_timezone(tz_str: str) -> ZoneInfo:
    """
    Parse timezone string to ZoneInfo object.

    Args:
        tz_str: Timezone string (e.g., "IST", "UTC", "America/New_York")

    Returns:
        ZoneInfo object for the timezone
    """
    # Check if it's an alias
    if tz_str.upper() in TIMEZONE_ALIASES:
        tz_str = TIMEZONE_ALIASES[tz_str.upper()]

    try:
        return ZoneInfo(tz_str)
    except Exception as e:
        logger.warning(f"Failed to parse timezone '{tz_str}': {e}. Defaulting to UTC.")
        return ZoneInfo("UTC")


def parse_datetime_string(datetime_str: str, timezone: str = "UTC") -> datetime:
    """
    Parse various datetime string formats and return timezone-aware datetime.

    CRITICAL: The input datetime string is interpreted as being IN the specified timezone.
    For example, "12 March 2026, 1:47 AM" with timezone="IST" means 1:47 AM India time,
    which will be correctly converted to the equivalent UTC timestamp.

    Supported formats:
    - "10 March 2026, 2:00 PM"
    - "10 October 2023, 00:00 AM"  (midnight; uses 24-hour hour with AM/PM literal)
    - "2026-03-10 14:00:00"
    - "2026-03-10T14:00:00"
    - "2026-03-10T14:00:00Z"  (trailing 'Z' forces UTC regardless of the timezone argument)
    - "10/03/2026 14:00"
    - "March 10, 2026 2 PM"

    Args:
        datetime_str: Human-readable datetime string (interpreted as being in the specified timezone)
        timezone: Timezone string (default: UTC)

    Returns:
        Timezone-aware datetime object
    """
    # Check if datetime string contains a timezone abbreviation at the end
    # If so, extract it and use it instead of the provided timezone parameter
    datetime_str_clean = datetime_str.strip()
    detected_tz = None

    # Check for timezone abbreviations at the end of the string
    for tz_abbr in TIMEZONE_ALIASES:
        if datetime_str_clean.upper().endswith(f" {tz_abbr.upper()}"):
            detected_tz = tz_abbr
            # Remove the timezone from the string (case-insensitive removal)
            datetime_str_clean = datetime_str_clean[:-len(tz_abbr)-1].strip()
            logger.info(f"Detected timezone '{detected_tz}' in datetime string, using it instead of '{timezone}'")
            break

    # Use detected timezone if found, otherwise use provided timezone
    tz_to_use = detected_tz if detected_tz else timezone
    tz = parse_timezone(tz_to_use)

    # Handle format with 'Z' suffix (UTC indicator)
    if datetime_str_clean.endswith('Z'):
        datetime_str_clean = datetime_str_clean[:-1]  # Remove 'Z'
        tz = ZoneInfo("UTC")  # Force UTC timezone
        logger.info("Detected format with 'Z' suffix, using UTC timezone")

    # List of datetime formats to try
    formats = [
        "%d %B %Y, %I:%M %p",      # 10 March 2026, 2:00 PM
        "%d %B %Y, %I %p",          # 10 March 2026, 2 PM
        "%d %B %Y, %H:%M %p",       # 10 October 2023, 00:00 AM (handles 00:00)
        "%B %d, %Y %I:%M %p",       # March 10, 2026 2:00 PM
        "%B %d, %Y %I %p",          # March 10, 2026 2 PM
        "%Y-%m-%d %H:%M:%S",        # 2026-03-10 14:00:00
        "%Y-%m-%dT%H:%M:%S",        # 2026-03-10T14:00:00
        "%Y-%m-%d %H:%M",           # 2026-03-10 14:00
        "%d/%m/%Y %H:%M",           # 10/03/2026 14:00
        "%m/%d/%Y %H:%M",           # 03/10/2026 14:00
        "%d-%m-%Y %H:%M",           # 10-03-2026 14:00
        "%Y/%m/%d %H:%M",           # 2026/03/10 14:00
    ]

    # Try each format
    for fmt in formats:
        try:
            # Parse as naive datetime first
            dt_naive = datetime.strptime(datetime_str_clean, fmt)

            # Create timezone-aware datetime using constructor to handle DST correctly
            dt_aware = datetime(
                dt_naive.year, dt_naive.month, dt_naive.day,
                dt_naive.hour, dt_naive.minute, dt_naive.second,
                tzinfo=tz
            )

            return dt_aware
        except ValueError:
            continue

    # If no format matched, raise error
    raise ValueError(
        f"Unable to parse datetime string: '{datetime_str}'. "
        f"Supported formats include: '10 March 2026, 2:00 PM', '2026-03-10 14:00:00', etc."
    )


def convert_to_timestamp(
    datetime_str: str,
    timezone: str = "UTC",
    output_unit: str = "milliseconds"
) -> Dict[str, Any]:
    """
    Convert human-readable datetime string to Unix timestamp.

    This function provides accurate, timezone-aware timestamp conversion for use with
    Instana APIs. It eliminates the ambiguity of LLM-generated timestamps by
    performing deterministic local conversion.

    Args:
        datetime_str: Human-readable datetime string
            Examples:
            - "10 March 2026, 2:00 PM"
            - "2026-03-10 14:00:00"
            - "March 10, 2026 2 PM"
            - "2026-03-10T14:00:00"

        timezone: Timezone for the datetime (default: "UTC")
            Supports:
            - IANA timezone names: "Asia/Kolkata", "America/New_York", "Europe/London"
            - Common aliases: "IST", "ET", "PT", "CT", "UTC", "GMT"

        output_unit: Output unit for timestamp (default: "milliseconds")
            Options: "milliseconds", "seconds"

    Returns:
        Dictionary containing:
        - timestamp: Unix timestamp in specified unit
        - datetime_str: Original input string
        - parsed_datetime: ISO format of parsed datetime
        - timezone: Timezone used
        - unit: Output unit used

    Examples:
        # Convert IST datetime to milliseconds
        convert_to_timestamp("10 March 2026, 2:00 PM", "IST")

        # Convert UTC datetime to seconds
        convert_to_timestamp("2026-03-10 14:00:00", "UTC", "seconds")
    """
    # Validate inputs
    if not datetime_str or not datetime_str.strip():
        return {
            "error": "datetime_str cannot be empty or whitespace-only",
            "datetime_str": datetime_str,
            "timezone": timezone
        }

    if not timezone or not timezone.strip():
        logger.warning("Empty timezone provided, defaulting to UTC")
        timezone = "UTC"

    # Validate output_unit early
    if output_unit not in ("milliseconds", "seconds"):
        return {
            "error": f"Invalid output_unit: '{output_unit}'. Must be 'milliseconds' or 'seconds'."
        }

    try:
        logger.debug(f"Converting datetime: '{datetime_str}' in timezone: '{timezone}'")

        # Parse the datetime string
        dt = parse_datetime_string(datetime_str, timezone)

        # Convert to Unix timestamp
        timestamp_seconds = dt.timestamp()

        # Convert to requested unit
        if output_unit == "milliseconds":
            timestamp = int(timestamp_seconds * 1000)
        else:  # output_unit == "seconds" (already validated)
            timestamp = int(timestamp_seconds)

        result = {
            "success": True,
            "timestamp": timestamp,
            "datetime_str": datetime_str,
            "parsed_datetime": dt.isoformat(),
            "timezone": timezone,
            "timezone_offset": dt.strftime("%z"),
            "unit": output_unit
        }

        logger.info(f"Successfully converted '{datetime_str}' to timestamp: {timestamp}")
        return result

    except ValueError as e:
        logger.error(f"Failed to parse datetime: {e}")
        return {
            "error": str(e),
            "datetime_str": datetime_str,
            "timezone": timezone
        }
    except Exception as e:
        logger.error(f"Unexpected error in timestamp conversion: {e}", exc_info=True)
        return {
            "error": f"Unexpected error: {e!s}",
            "datetime_str": datetime_str,
            "timezone": timezone
        }


def get_current_timestamp(
    timezone: str = "UTC",
    output_unit: str = "milliseconds"
) -> Dict[str, Any]:
    """
    Get current timestamp in specified timezone and unit.

    Args:
        timezone: Timezone for current time (default: "UTC")
        output_unit: Output unit for timestamp (default: "milliseconds")
            Options: "milliseconds", "seconds"

    Returns:
        Dictionary containing current timestamp and datetime information
    """
    try:
        tz = parse_timezone(timezone)
        now = datetime.now(tz)

        timestamp_seconds = now.timestamp()

        if output_unit == "milliseconds":
            timestamp = int(timestamp_seconds * 1000)
        elif output_unit == "seconds":
            timestamp = int(timestamp_seconds)
        else:
            return {
                "error": f"Invalid output_unit: '{output_unit}'. Must be 'milliseconds' or 'seconds'."
            }

        return {
            "success": True,
            "timestamp": timestamp,
            "current_datetime": now.isoformat(),
            "timezone": timezone,
            "timezone_offset": now.strftime("%z"),
            "unit": output_unit
        }

    except Exception as e:
        logger.error(f"Error getting current timestamp: {e}", exc_info=True)
        return {"error": str(e)}


def convert_datetime_param(
    param_value: Any,
    param_name: str,
    default_timezone: str = "UTC",
    output_unit: str = "milliseconds"
) -> Dict[str, Any]:
    """
    Convert a datetime parameter value to timestamp if it's a string.

    This utility function handles the common pattern of converting datetime strings
    to timestamps while preserving numeric values unchanged.

    Args:
        param_value: The parameter value (can be int, str, or None)
        param_name: Name of the parameter (for error messages)
        default_timezone: Default timezone if not specified in string (default: "UTC")
        output_unit: Output unit for timestamp (default: "milliseconds")

    Returns:
        Dictionary with:
        - "value": Converted timestamp (int) or original value
        - "converted": Boolean indicating if conversion occurred
        - "error": Error message if conversion failed (optional)
        - "timezone": Timezone used for conversion (if converted)

    Examples:
        # Numeric value (no conversion)
        result = convert_datetime_param(1234567890000, "to")
        # Returns: {"value": 1234567890000, "converted": False}

        # Datetime string with timezone
        result = convert_datetime_param("19 March 2026, 2:47 PM|IST", "to")
        # Returns: {"value": 1742369820000, "converted": True, "timezone": "IST"}

        # Datetime string without timezone (uses default)
        result = convert_datetime_param("19 March 2026, 2:47 PM", "to")
        # Returns: {"value": 1742351220000, "converted": True, "timezone": "UTC"}
    """
    # If None or already numeric, return as-is
    if param_value is None or isinstance(param_value, (int, float)):
        return {"value": param_value, "converted": False}

    # If not a string, return as-is
    if not isinstance(param_value, str):
        return {"value": param_value, "converted": False}

    # It's a string - attempt datetime conversion
    logger.debug(f"Converting {param_name} datetime string: {param_value}")

    # Extract timezone if provided, otherwise use default
    if "|" in param_value:
        datetime_str, timezone = param_value.split("|", 1)
        timezone = timezone.strip()
    else:
        datetime_str = param_value
        timezone = default_timezone
        logger.info(f"No timezone provided for {param_name} '{param_value}', using {default_timezone}")

    # Convert to timestamp
    conversion_result = convert_to_timestamp(datetime_str.strip(), timezone, output_unit)

    if "error" in conversion_result:
        return {
            "error": f"Failed to convert {param_name} datetime: {conversion_result['error']}",
            "value": None,
            "converted": False
        }

    logger.info(f"Converted {param_name} to timestamp: {conversion_result['timestamp']} (timezone: {timezone})")
    return {
        "value": conversion_result["timestamp"],
        "converted": True,
        "timezone": timezone
    }


def convert_datetime_params(
    params: Dict[str, Any],
    param_names: List[str],
    default_timezone: str = "UTC",
    output_unit: str = "milliseconds"
) -> Dict[str, Any]:
    """
    Convert multiple datetime parameters in a dictionary.

    This utility function processes multiple parameters at once, converting
    datetime strings to timestamps while preserving numeric values.

    Args:
        params: Dictionary containing parameters
        param_names: List of parameter names to convert
        default_timezone: Default timezone if not specified (default: "UTC")
        output_unit: Output unit for timestamps (default: "milliseconds")

    Returns:
        Dictionary with:
        - "params": Updated params dictionary with converted values
        - "conversions": Dict mapping param names to conversion info
        - "error": Error message if any conversion failed (optional)

    Examples:
        # Convert multiple time parameters
        params = {"from_time": "19 March 2026, 2:47 PM|IST", "to_time": 1234567890000}
        result = convert_datetime_params(params, ["from_time", "to_time"])
        # Returns: {
        #     "params": {"from_time": 1742369820000, "to_time": 1234567890000},
        #     "conversions": {
        #         "from_time": {"converted": True, "timezone": "IST"},
        #         "to_time": {"converted": False}
        #     }
        # }
    """
    updated_params = params.copy()
    conversions = {}

    for param_name in param_names:
        if param_name not in params:
            continue

        param_value = params[param_name]
        conversion_result = convert_datetime_param(
            param_value,
            param_name,
            default_timezone,
            output_unit
        )

        # Check for conversion error
        if "error" in conversion_result:
            return {
                "error": conversion_result["error"],
                "param_name": param_name,
                "params": params
            }

        # Update the parameter value
        updated_params[param_name] = conversion_result["value"]

        # Store conversion info
        conversions[param_name] = {
            "converted": conversion_result["converted"],
            "timezone": conversion_result.get("timezone")
        }

    return {
        "params": updated_params,
        "conversions": conversions
    }


def convert_nested_datetime_param(
    params: Dict[str, Any],
    parent_key: str,
    nested_key: str,
    default_timezone: str = "UTC",
    output_unit: str = "milliseconds"
) -> Dict[str, Any]:
    """
    Convert a datetime parameter nested within a dictionary.

    This utility handles the common pattern of time_frame.to or similar nested structures.

    Args:
        params: Dictionary containing parameters
        parent_key: Key of the parent dictionary (e.g., "time_frame")
        nested_key: Key within the parent dictionary (e.g., "to")
        default_timezone: Default timezone if not specified (default: "UTC")
        output_unit: Output unit for timestamp (default: "milliseconds")

    Returns:
        Dictionary with:
        - "params": Updated params dictionary with converted value
        - "converted": Boolean indicating if conversion occurred
        - "error": Error message if conversion failed (optional)
        - "timezone": Timezone used for conversion (if converted)

    Examples:
        # Convert time_frame.to
        params = {"time_frame": {"to": "19 March 2026, 2:47 PM|IST", "windowSize": 3600000}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        # Returns: {
        #     "params": {"time_frame": {"to": 1742369820000, "windowSize": 3600000}},
        #     "converted": True,
        #     "timezone": "IST"
        # }
    """
    # Check if parent key exists and is a dict
    if parent_key not in params or not isinstance(params[parent_key], dict):
        return {"params": params, "converted": False}

    parent_dict = params[parent_key]

    # Check if nested key exists
    if nested_key not in parent_dict:
        return {"params": params, "converted": False}

    nested_value = parent_dict[nested_key]

    # Convert the nested value
    conversion_result = convert_datetime_param(
        nested_value,
        f"{parent_key}.{nested_key}",
        default_timezone,
        output_unit
    )

    # Check for conversion error
    if "error" in conversion_result:
        return {
            "error": conversion_result["error"],
            "params": params,
            "converted": False
        }

    # Update the nested value if conversion occurred
    if conversion_result["converted"]:
        # Use deepcopy to avoid issues with nested structures
        updated_params = deepcopy(params)
        updated_params[parent_key][nested_key] = conversion_result["value"]

        return {
            "params": updated_params,
            "converted": True,
            "timezone": conversion_result.get("timezone")
        }

    return {"params": params, "converted": False}


def convert_datetime_param_with_required_timezone(
    value: Any,
    param_name: str,
    output_unit: str = "milliseconds"
) -> Dict[str, Any]:
    """
    Convert a datetime parameter that REQUIRES an explicit timezone.

    This utility is used by routers (like releases and SLO) that require users
    to explicitly specify timezone rather than defaulting to UTC. If timezone
    is missing, returns an elicitation response.

    Args:
        value: The parameter value (can be string, int, or None)
        param_name: Name of the parameter for error messages
        output_unit: Output unit for timestamp (default: "milliseconds")

    Returns:
        Dictionary with:
        - "value": Converted timestamp value (or original if not string)
        - "converted": Boolean indicating if conversion occurred
        - "timezone": Timezone used for conversion (if converted)
        - "elicitation_needed": Boolean indicating if timezone is required
        - "message": User-friendly elicitation message (if timezone missing)
        - "error": Error message if conversion failed (optional)

    Examples:
        # With timezone provided
        result = convert_datetime_param_with_required_timezone(
            "19 March 2026, 2:47 PM|IST",
            "start"
        )
        # Returns: {"value": 1742369820000, "converted": True, "timezone": "IST"}

        # Without timezone (requires elicitation)
        result = convert_datetime_param_with_required_timezone(
            "19 March 2026, 2:47 PM",
            "start"
        )
        # Returns: {"elicitation_needed": True, "message": "...", ...}
    """
    # If value is None or already a number, return as-is
    if value is None or isinstance(value, (int, float)):
        return {"value": value, "converted": False}

    # If not a string, return as-is
    if not isinstance(value, str):
        return {"value": value, "converted": False}

    logger.debug(f"Converting {param_name} datetime string: {value}")

    # Check if timezone is provided in format "datetime|timezone"
    if "|" not in value:
        # Return elicitation response
        return {
            "elicitation_needed": True,
            "message": f"I see you want to use '{value}' for {param_name}, but I need to know which timezone.\n\nPlease specify the timezone:\n- IST (India Standard Time)\n- America/New_York (Eastern Time)\n- UTC (Coordinated Universal Time)\n- Europe/London (GMT/BST)\n- Asia/Tokyo (Japan Standard Time)\n\nOr any other IANA timezone name.",
            "missing_parameters": ["timezone"],
            "user_prompt": f"What timezone should be used for {param_name} '{value}'?"
        }

    # Extract timezone
    datetime_str, timezone = value.split("|", 1)

    # Convert to timestamp
    conversion_result = convert_to_timestamp(datetime_str.strip(), timezone.strip(), output_unit)

    if "error" in conversion_result:
        return {
            "error": f"Failed to convert {param_name} datetime: {conversion_result['error']}",
            "value": None,
            "converted": False
        }

    logger.info(f"Converted {param_name} to timestamp: {conversion_result['timestamp']} (timezone: {timezone.strip()})")
    return {
        "value": conversion_result["timestamp"],
        "converted": True,
        "timezone": timezone.strip()
    }
