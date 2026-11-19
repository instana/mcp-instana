"""
Timestamp Utility Module

Provides timezone-aware datetime parsing and Unix timestamp conversion.
This standalone utility helps convert human-readable datetime strings into precise
Unix epoch timestamps (milliseconds) for use with Instana APIs.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, available_timezones

logger = logging.getLogger(__name__)

# Default timezone applied when none is given (all timestamps are resolved against UTC)
DEFAULT_TIMEZONE = "UTC"

# Trailing word that looks like a zone: a short abbreviation in any case ("PST", "xyz") or an IANA name
# ("Asia/Kolkata", "America/Argentina/Buenos_Aires", "Etc/GMT+5"). Only a hint: parse_timezone decides.
_INLINE_ZONE_TOKEN = re.compile(r"^[A-Za-z]{2,5}$|^[A-Za-z]+(?:/[A-Za-z0-9_+\-]+)+$")
# Zone keys equivalent to UTC (a trailing 'Z' does not conflict with these)
_UTC_KEYS = {"UTC", "GMT", "Etc/UTC", "Etc/GMT", "Zulu"}

# Timezone abbreviations accepted in addition to IANA names (matched case-insensitively).
#
# The table follows one rule so that a name never silently means two different offsets:
#   * Regional names (no S/D letter: ET, CT, MT, PT, CET, EET, WET, AET, NZT) follow the local
#     DST rules of the region, so "2 PM ET" is UTC-5 in winter and UTC-4 in summer.
#   * Standard/daylight names (EST, EDT, PST, PDT, AEST, AEDT, CEST, ...) pin ONE fixed offset all
#     year, because the S or D in the name says which one it is.
#   * Regions without DST (IST, JST, SGT, ...) map to their IANA zone; the offset never changes.
# Fixed offsets use "Etc/GMT±N" zones, whose sign is inverted (Etc/GMT-10 is UTC+10).
# Deliberately NOT included because the abbreviation is ambiguous: BST (British/Bangladesh), and
# half-hour zones such as ACST/ACDT. Pass an IANA name (e.g. "Europe/London") for those.
# Ambiguity notes: IST means India (not Irish/Israel); CST means US Central (not China).
TIMEZONE_ALIASES = {
    # --- UTC / GMT
    "UTC": "UTC",
    "GMT": "GMT",
    # --- Regions without DST (offset is constant)
    "IST": "Asia/Kolkata",           # UTC+5:30 India
    "JST": "Asia/Tokyo",             # UTC+9
    "KST": "Asia/Seoul",             # UTC+9
    "SGT": "Asia/Singapore",         # UTC+8
    "HKT": "Asia/Hong_Kong",         # UTC+8
    "PKT": "Asia/Karachi",           # UTC+5
    "WIB": "Asia/Jakarta",           # UTC+7
    "MSK": "Europe/Moscow",          # UTC+3
    "SAST": "Africa/Johannesburg",   # UTC+2
    "WAT": "Africa/Lagos",           # UTC+1
    "CAT": "Africa/Maputo",          # UTC+2
    "EAT": "Africa/Nairobi",         # UTC+3
    # --- Regional names (DST-aware)
    "ET": "America/New_York",
    "CT": "America/Chicago",
    "MT": "America/Denver",
    "PT": "America/Los_Angeles",
    "CET": "Europe/Paris",
    "EET": "Europe/Helsinki",
    "WET": "Europe/Lisbon",
    "AET": "Australia/Sydney",       # Australian Eastern (local time, AEST in winter / AEDT in summer)
    "NZT": "Pacific/Auckland",       # New Zealand (local time, NZST / NZDT)
    # --- Standard / daylight names (fixed offset all year)
    "EST": "Etc/GMT+5",              # UTC-5
    "EDT": "Etc/GMT+4",              # UTC-4
    "CST": "Etc/GMT+6",              # UTC-6
    "CDT": "Etc/GMT+5",              # UTC-5
    "MST": "Etc/GMT+7",              # UTC-7
    "MDT": "Etc/GMT+6",              # UTC-6
    "PST": "Etc/GMT+8",              # UTC-8
    "PDT": "Etc/GMT+7",              # UTC-7
    "AKST": "Etc/GMT+9",             # UTC-9
    "AKDT": "Etc/GMT+8",             # UTC-8
    "HST": "Etc/GMT+10",             # UTC-10
    "WEST": "Etc/GMT-1",             # UTC+1
    "CEST": "Etc/GMT-2",             # UTC+2
    "EEST": "Etc/GMT-3",             # UTC+3
    "AWST": "Etc/GMT-8",             # UTC+8
    "AEST": "Etc/GMT-10",            # UTC+10
    "AEDT": "Etc/GMT-11",            # UTC+11
    "NZST": "Etc/GMT-12",            # UTC+12
    "NZDT": "Etc/GMT-13",            # UTC+13
    # Legacy spellings kept for backwards compatibility
    "EST5": "Etc/GMT+5",
    "PST8": "Etc/GMT+8",
}

# Plausible range for a Unix timestamp in milliseconds:
# lower bound ≈ 1973-03-03 (rejects 0, negatives, and second-resolution values)
# upper bound ≈ year 5138 (rejects microsecond-resolution values and bare garbage)
_MIN_EPOCH_MS: int = 10**11
_MAX_EPOCH_MS: int = 10**14
# The same range expressed in seconds (for parameters such as ingestionTime)
_MIN_EPOCH_S: int = _MIN_EPOCH_MS // 1000
_MAX_EPOCH_S: int = _MAX_EPOCH_MS // 1000


def epoch_ms_to_utc(timestamp_ms: int | float) -> datetime:
    """Convert a Unix timestamp in milliseconds to a timezone-aware UTC datetime.

    Raises:
        ValueError: if timestamp_ms is not a plausible 13-digit Unix millisecond value
                    (rejects 0, negatives, second-resolution epochs, and huge values).
    """
    if (
        isinstance(timestamp_ms, bool)
        or not isinstance(timestamp_ms, (int, float))
        or not (_MIN_EPOCH_MS <= timestamp_ms <= _MAX_EPOCH_MS)
    ):
        raise ValueError(
            f"{timestamp_ms!r} is not a plausible Unix timestamp in milliseconds "
            f"(expected a 13-digit integer; 0 and second-resolution values are rejected)."
        )
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_ms() -> int:
    """Return the current Unix timestamp in milliseconds as an integer."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def default_window(
    window_ms: int = 3_600_000,
    to_ms: Optional[int] = None
) -> tuple[int, int]:
    """Return (from_ms, to_ms) for a time window ending at to_ms.

    A missing or non-positive to_ms (None, 0, negative) means "omitted" and resolves to now, the same
    way convert_nested_datetime_param treats an empty ``timeFrame.to``. It never yields a 1970 window.
    """
    to = to_ms if to_ms is not None and to_ms > 0 else utc_now_ms()
    return to - window_ms, to


def utc_now_iso() -> str:
    """Return the current server time as an ISO-8601 UTC string (YYYY-MM-DDTHH:mm:ssZ)."""
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


@lru_cache(maxsize=1)
def _iana_names_by_casefold() -> Dict[str, str]:
    """Map lower-cased IANA names to their canonical spelling (e.g. 'asia/kolkata' -> 'Asia/Kolkata')."""
    return {name.casefold(): name for name in available_timezones()}


def parse_timezone(tz_str: str) -> ZoneInfo:
    """
    Parse timezone string to ZoneInfo object.

    Args:
        tz_str: Alias from TIMEZONE_ALIASES (e.g. "UTC", "IST", "ET", "PST") or an IANA name
            (e.g. "Asia/Kolkata"). Both are matched case-insensitively on every platform; the
            returned zone always carries the canonical IANA key.

    Returns:
        ZoneInfo object for the timezone

    Raises:
        ValueError: If the timezone is neither a supported alias nor an IANA name.
            Unknown timezones are never silently treated as UTC.
    """
    original = tz_str
    # Check if it's an alias
    if tz_str.upper() in TIMEZONE_ALIASES:
        tz_str = TIMEZONE_ALIASES[tz_str.upper()]

    # Zone files are looked up by exact name, which is case-sensitive on Linux but not on macOS or
    # Windows. Resolve to the canonical spelling first so behaviour (and ZoneInfo.key) is identical everywhere.
    tz_str = _iana_names_by_casefold().get(tz_str.casefold(), tz_str)

    try:
        return ZoneInfo(tz_str)
    except Exception as e:
        # If even UTC cannot be loaded, the tz database is missing (e.g. Windows
        # without the 'tzdata' package) - not a problem with the user's input.
        try:
            ZoneInfo("UTC")
        except Exception:
            raise RuntimeError(
                "Timezone database not found. Install it with: pip install tzdata"
            ) from e
        raise ValueError(
            f"Unknown timezone '{original}'. Use an alias such as 'UTC' or 'IST', "
            "or an IANA name such as 'Asia/Kolkata'."
        ) from e


def is_utc_zone(name: str) -> bool:
    """Return True if name is 'Z' or any alias/IANA name equivalent to UTC."""
    name = name.strip()
    if name.upper() == "Z":
        return True
    try:
        return parse_timezone(name).key in _UTC_KEYS
    except ValueError:
        return False


def _split_inline_zone(text: str) -> tuple[str, str | None]:
    """
    Split a trailing zone token off a datetime string (e.g. "10 March 2026, 2:00 PM ET").

    Returns (text_without_zone, zone_token); zone_token is None when the string has no inline zone.
    The last word is a zone token only if parse_timezone resolves it: an alias or an IANA name, in any
    case. Anything else, including month names ("10 March") and unknown words, is left in the text.
    parse_datetime_string reports an unknown zone-like word as "Unknown timezone" if parsing fails.
    """
    tokens = text.split()
    last_token = tokens[-1] if tokens else ""
    if len(tokens) > 1 and last_token.upper() not in ("AM", "PM") and (
        last_token.upper() in TIMEZONE_ALIASES or _INLINE_ZONE_TOKEN.match(last_token)
    ):
        try:
            parse_timezone(last_token)
        except ValueError:
            return text, None
        return text[:-len(last_token)].strip(), last_token
    return text, None


def _inline_zone_or(param_value: str, datetime_str: str, default: str) -> str:
    """Return the zone written at the end of datetime_str, or default when there is none.

    An explicit "|zone" suffix in param_value always wins, so default is returned unchanged then.
    """
    if "|" in param_value:
        return default
    try:
        return _split_inline_zone(datetime_str.strip())[1] or default
    except ValueError:
        return default  # unknown zone: convert_to_timestamp reports it as an error dict


def _localize(naive: datetime, tz: ZoneInfo) -> datetime:
    """
    Attach tz to a naive wall-clock time, refusing times that DST makes nonexistent or ambiguous.

    Raises:
        ValueError: if the time falls in a spring-forward gap (does not exist) or a fall-back
            overlap (occurs twice). Silently picking one would be off by an hour.
    """
    first = naive.replace(tzinfo=tz, fold=0)
    second = naive.replace(tzinfo=tz, fold=1)
    if first.utcoffset() == second.utcoffset():
        return first
    if first.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != naive:
        raise ValueError(
            f"{naive:%Y-%m-%d %H:%M} does not exist in {tz.key} (clocks skip it when DST starts). "
            f"Choose a different time, or use UTC or a fixed-offset zone such as EST/PST."
        )
    raise ValueError(
        f"{naive:%Y-%m-%d %H:%M} is ambiguous in {tz.key} (it occurs twice when DST ends). "
        f"Use UTC or a fixed-offset zone such as EST/PST to say which one is meant."
    )


# ISO-8601 forms that carry their own UTC offset (e.g. "+05:30", "-0800"); strptime's %z reads both spellings
_OFFSET_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M%z",
    "%Y-%m-%d %H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%d %H:%M%z",
)


def parse_datetime_string(datetime_str: str, timezone: str = DEFAULT_TIMEZONE) -> datetime:
    """
    Parse various datetime string formats and return timezone-aware datetime.

    CRITICAL: The input datetime string is interpreted as being IN the specified timezone.
    For example, "YYYY-MM-DD 01:47:00" with timezone="IST" means 01:47 India time on
    that date, which will be correctly converted to the equivalent UTC timestamp.

    Supported formats:
    - "DD Month YYYY, h:mm AM/PM"
    - "DD Month YYYY, 00:00 AM"  (midnight; uses 24-hour hour with AM/PM literal)
    - "YYYY-MM-DD HH:mm:ss"
    - "YYYY-MM-DDTHH:mm:ss"
    - "YYYY-MM-DDTHH:mm:ssZ"  (trailing 'Z' forces UTC regardless of the timezone argument)
    - "YYYY-MM-DDTHH:mm:ss.sssZ"  (fractional seconds, as JavaScript emits)
    - "YYYY-MM-DDTHH:mm:ss+05:30"  (explicit UTC offset; it overrides the timezone argument)
    - "YYYY-MM-DDTHH:mm" and "YYYY-MM-DD"  (the date alone means midnight)
    - "DD/MM/YYYY HH:mm"
    - "Month DD, YYYY h AM/PM"

    Args:
        datetime_str: Human-readable datetime string (interpreted as being in the specified timezone)
        timezone: Timezone string (default: UTC)

    Returns:
        Timezone-aware datetime object
    """
    # Check if datetime string ends with an inline timezone abbreviation (e.g. "... 2:00 PM IST").
    # If so, extract it and use it instead of the provided timezone parameter.
    datetime_str_clean, detected_tz = _split_inline_zone(datetime_str.strip())
    if detected_tz:
        logger.info(f"Detected timezone '{detected_tz}' in datetime string, using it instead of '{timezone}'")

    # Use detected timezone if found, otherwise use provided timezone
    tz_to_use = detected_tz if detected_tz else timezone
    tz = parse_timezone(tz_to_use)

    # Handle format with 'Z' suffix (UTC indicator)
    if datetime_str_clean.endswith('Z'):
        if detected_tz and parse_timezone(detected_tz).key not in _UTC_KEYS:
            raise ValueError(
                f"'{datetime_str.strip()}' ends with 'Z' (UTC) but the zone '{detected_tz}' was also given. "
                f"Use one or the other."
            )
        datetime_str_clean = datetime_str_clean[:-1]  # Remove 'Z'
        tz = ZoneInfo("UTC")  # Force UTC timezone
        logger.info("Detected format with 'Z' suffix, using UTC timezone")

    # List of datetime formats to try (with explicit year).
    # Each %B entry is paired with a %b variant so both "March" and "Mar" are accepted.
    _formats_with_year = [
        "%d %B %Y, %I:%M %p",      # 10 March 2026, 2:00 PM
        "%d %B %Y, %I %p",          # 10 March 2026, 2 PM
        "%d %B %Y, %H:%M %p",       # 10 October 2023, 00:00 AM (handles 00:00)
        "%B %d, %Y %I:%M %p",       # March 10, 2026 2:00 PM
        "%B %d, %Y %I %p",          # March 10, 2026 2 PM
    ]
    formats = []
    for _fmt in _formats_with_year:
        formats.append(_fmt)
        formats.append(_fmt.replace("%B", "%b"))
    formats += [
        "%Y-%m-%d %H:%M:%S.%f",     # 2026-03-10 14:00:00.123
        "%Y-%m-%dT%H:%M:%S.%f",     # 2026-03-10T14:00:00.123 (JavaScript toISOString() style, with 'Z')
        "%Y-%m-%d %H:%M:%S",        # 2026-03-10 14:00:00
        "%Y-%m-%dT%H:%M:%S",        # 2026-03-10T14:00:00
        "%Y-%m-%dT%H:%M",           # 2026-03-10T14:00
        "%Y-%m-%d %H:%M",           # 2026-03-10 14:00
        "%Y-%m-%d",                 # 2026-03-10 (midnight in the given timezone)
        "%d/%m/%Y %H:%M",           # 10/03/2026 14:00 (day first; month-first is not accepted, it is ambiguous)
        "%d-%m-%Y %H:%M",           # 10-03-2026 14:00
        "%Y/%m/%d %H:%M",           # 2026/03/10 14:00
    ]

    # Year-less formats: if matched, the current year (in the target timezone) is substituted automatically.
    # These act as a safety net for cases where the year was omitted by the caller.
    # Each %B entry is paired with a %b variant so both "March" and "Mar" are accepted.
    _yearless_with_full_month = [
        "%d %B, %I:%M %p",          # 10 March, 2:00 PM
        "%d %B, %I %p",             # 10 March, 2 PM
        "%d %B, %H:%M %p",          # 10 March, 00:00 AM
        "%d %B, %H:%M",             # 10 March, 14:00
        "%d %B %H:%M",              # 10 March 14:00
        "%B %d, %I:%M %p",          # March 10, 2:00 PM
        "%B %d, %I %p",             # March 10, 2 PM
        "%B %d, %H:%M",             # March 10, 14:00
        "%B %d %H:%M",              # March 10 14:00
        "%d %B %I:%M %p",           # 10 March 2:00 PM  (no comma)
        "%d %B %I %p",              # 10 March 2 PM     (no comma)
        "%d %B",                    # 10 March (midnight)
        "%B %d",                    # March 10 (midnight)
    ]
    yearless_formats = []
    for _fmt in _yearless_with_full_month:
        yearless_formats.append(_fmt)
        yearless_formats.append(_fmt.replace("%B", "%b"))

    # An explicit UTC offset ("2026-03-10T14:00:00+05:30") fixes the instant, so it wins over the timezone argument
    for fmt in _OFFSET_FORMATS:
        try:
            return datetime.strptime(datetime_str_clean, fmt)
        except ValueError:
            continue

    # Try each format with explicit year first
    for fmt in formats:
        try:
            dt_naive = datetime.strptime(datetime_str_clean, fmt)
        except ValueError:
            continue
        return _localize(dt_naive, tz)

    # Try year-less formats, substituting the current year in the target timezone.
    # Prepend the year so strptime always parses with a real year — this avoids
    # the CPython year-1900 default (not a leap year) which silently rejects "29 February"
    # and emits a DeprecationWarning in Python 3.13+ (behaviour changes in 3.15).
    current_year = datetime.now(tz).year
    for fmt in yearless_formats:
        try:
            dt_naive = datetime.strptime(f"{current_year} {datetime_str_clean}", f"%Y {fmt}")
        except ValueError:
            continue
        logger.info(
            f"Parsed year-less datetime '{datetime_str_clean}' using format '{fmt}'; "
            f"substituting current year {current_year}"
        )
        return _localize(dt_naive, tz)

    # A trailing zone-like word that is not a known zone ("... 2:00 PM XYZ") deserves a clear
    # "Unknown timezone" error, but only if the rest of the string is a valid datetime on its own.
    tokens = datetime_str.split()  # original text: datetime_str_clean has lost a trailing 'Z' (e.g. "XYZ")
    if len(tokens) > 1 and _INLINE_ZONE_TOKEN.match(tokens[-1]) and tokens[-1].upper() not in ("AM", "PM"):
        try:
            parse_datetime_string(" ".join(tokens[:-1]), timezone)
        except ValueError:
            pass
        else:
            parse_timezone(tokens[-1])  # raises "Unknown timezone '<word>'"

    # If no format matched, raise error
    raise ValueError(
        f"Unable to parse datetime string: '{datetime_str}'. "
        f"Supported formats include: '10 March 2026, 2:00 PM', '10 March, 2:00 PM' (current year assumed), "
        f"'2026-03-10 14:00:00', '2026-03-10T14:00:00Z', '2026-03-10T14:00:00.000Z', "
        f"'2026-03-10T14:00:00+05:30' and '2026-03-10', etc."
    )


def convert_to_timestamp(
    datetime_str: str,
    timezone: str = DEFAULT_TIMEZONE,
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
            - "DD Month YYYY, h:mm AM/PM"
            - "YYYY-MM-DD HH:mm:ss"
            - "Month DD, YYYY h AM/PM"
            - "YYYY-MM-DDTHH:mm:ss"

        timezone: Timezone for the datetime (default: "UTC")
            Supports any name in TIMEZONE_ALIASES (e.g. "UTC", "IST", "ET", "PST", "CET", "AEST";
            case-insensitive) or any IANA name (e.g. "Asia/Kolkata", "Europe/London").
            Regional names (ET, CT, MT, PT, CET, ...) follow local DST; names with an S or D
            (EST, PDT, AEST, ...) are a fixed offset all year.

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
        # Convert a UTC datetime to milliseconds
        convert_to_timestamp("DD Month YYYY, h:mm AM/PM", "UTC")

        # Convert UTC datetime to seconds
        convert_to_timestamp("YYYY-MM-DD HH:mm:ss", "UTC", "seconds")
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
    timezone: str = DEFAULT_TIMEZONE,
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

# Relative expressions, all anchored to the server's UTC clock:
#   "yesterday", "<N> <unit> ago" (e.g. "30 minutes ago") and "in <N> <unit>" (e.g. "in 2 hours")
_UNIT_PATTERN = r"seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?"
_RELATIVE_RE = re.compile(
    rf"^\s*(?:(?P<yesterday>yesterday)"
    rf"|(?P<past_amount>\d+)\s*(?P<past_unit>{_UNIT_PATTERN})\s+ago"
    rf"|in\s+(?P<future_amount>\d+)\s*(?P<future_unit>{_UNIT_PATTERN}))\s*$",
    re.IGNORECASE,
)
_RELATIVE_UNIT_TO_MS = {"s": 1_000, "m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000}
# Longest amount accepted; anything bigger cannot be a sensible time offset (and would only overflow)
_MAX_RELATIVE_AMOUNT_DIGITS = 9


def parse_relative_offset_ms(value: str) -> Optional[int]:
    """
    Return the signed offset from now, in milliseconds, for a relative expression.

    "yesterday" and "<N> <unit> ago" give a negative offset; "in <N> <unit>" gives a positive one.
    Units are seconds, minutes, hours, days and weeks. Returns None if value is not a relative expression
    (or its amount is 0), so the caller can try other formats.

    Raises:
        ValueError: if the amount has more than 9 digits.
    """
    match = _RELATIVE_RE.match(value)
    if not match:
        return None
    if match.group("yesterday"):
        return -_RELATIVE_UNIT_TO_MS["d"]
    is_past = match.group("past_amount") is not None
    amount_text = match.group("past_amount" if is_past else "future_amount")
    unit = match.group("past_unit" if is_past else "future_unit")
    if len(amount_text) > _MAX_RELATIVE_AMOUNT_DIGITS:
        raise ValueError(f"'{value.strip()}' is too large to be a sensible time offset.")
    amount = int(amount_text)
    if amount <= 0:
        return None
    offset = amount * _RELATIVE_UNIT_TO_MS[unit.lower()[0]]
    return -offset if is_past else offset


def _epoch_bounds(output_unit: str) -> tuple[int, int]:
    """Return the plausible (min, max) Unix timestamp for output_unit."""
    if output_unit == "seconds":
        return _MIN_EPOCH_S, _MAX_EPOCH_S
    return _MIN_EPOCH_MS, _MAX_EPOCH_MS


def _epoch_problem(value: Any, param_name: str, output_unit: str) -> Optional[str]:
    """
    Return an error message if value is not a plausible Unix timestamp in output_unit, else None.

    A non-finite number, 0, a negative number and anything outside the plausible range (about 1973 to
    year 5138) are rejected. When the value would be valid in the *other* unit, the message says so.
    """
    omit_hint = f"Omit '{param_name}' to use the server default."
    if isinstance(value, float) and not math.isfinite(value):
        return f"'{param_name}' has value {value!r} which is not a valid Unix timestamp. {omit_hint}"

    low, high = _epoch_bounds(output_unit)
    if low <= value <= high:
        return None

    other = "seconds" if output_unit == "milliseconds" else "milliseconds"
    other_low, other_high = _epoch_bounds(other)
    if other_low <= value <= other_high:
        return (
            f"'{param_name}' has value {value!r} which looks like a Unix timestamp in {other}, "
            f"but this parameter expects {output_unit}."
        )
    detail = " (0 is 1970-01-01)" if value == 0 else ""
    return (
        f"'{param_name}' has value {value!r} which is not a valid Unix timestamp in {output_unit}{detail}. "
        f"{omit_hint}"
    )


_DIGITS_RE = re.compile(r"^\s*-?\d+\s*$")


def _offset_conflicts_with_zone(datetime_str: str, zone: str) -> bool:
    """Return True if datetime_str carries a numeric UTC offset that differs from the offset of zone then."""
    for fmt in _OFFSET_FORMATS:
        try:
            dt = datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
        try:
            return parse_timezone(zone).utcoffset(dt.replace(tzinfo=None)) != dt.utcoffset()
        except ValueError:
            return False  # unknown zone: convert_to_timestamp reports it
    return False


def _zone_conflict(datetime_str: str, zone: str) -> Optional[str]:
    """Describe the clash between a 'Z' / numeric offset in datetime_str and an explicit zone, or None."""
    if datetime_str.endswith("Z") and not is_utc_zone(zone):
        return f"'{datetime_str}' ends with 'Z' (UTC) but the zone '{zone}' was also given."
    if _offset_conflicts_with_zone(datetime_str, zone):
        return f"'{datetime_str}' has a UTC offset that differs from the zone '{zone}' that was also given."
    return None


def _convert_relative(datetime_str: str, param_name: str, output_unit: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a relative expression ('2 days ago', 'in 2 hours', 'yesterday') against the UTC clock.

    Returns None if datetime_str is not a relative expression; otherwise the convert_datetime_param result.
    The resolved instant must be a plausible Unix timestamp, so absurd amounts become an error.
    """
    failure = {"value": None, "converted": False}
    try:
        offset_ms = parse_relative_offset_ms(datetime_str)
    except ValueError as e:
        return {"error": f"Failed to convert {param_name} datetime: {e}", **failure}
    if offset_ms is None:
        return None

    current = get_current_timestamp(DEFAULT_TIMEZONE, "milliseconds")
    if "error" in current:
        return {"error": f"Failed to convert {param_name} datetime: {current['error']}", **failure}

    resolved_ms = current["timestamp"] + offset_ms
    if not _MIN_EPOCH_MS <= resolved_ms <= _MAX_EPOCH_MS:
        return {
            "error": (
                f"Failed to convert {param_name} datetime: '{datetime_str.strip()}' resolves to "
                f"{resolved_ms} ms, which is not a plausible Unix timestamp."
            ),
            **failure,
        }
    value = resolved_ms if output_unit == "milliseconds" else resolved_ms // 1000
    return {"value": value, "converted": True, "timezone": DEFAULT_TIMEZONE}


# Query end-of-range parameters. A value for one of these may not lie in the future: there is no data
# yet, so the query would silently return nothing (or an empty window). Matched on the last dotted
# segment, so the nested "timeFrame.to" / "time_frame.to" are covered too. Parameters that are
# legitimately scheduled ahead (maintenance window start_time/end_time, SLO correction startTime,
# release start) deliberately do not match and are not checked.
_END_TIME_PARAM_NAMES = frozenset({"to", "to_time"})

# Tolerated clock difference between the caller and this server for "to" values
_FUTURE_SKEW_MS = 60_000


def _is_end_time_param(param_name: str) -> bool:
    """Return True if param_name is a query end-of-range parameter that must not be in the future."""
    return param_name.rsplit(".", 1)[-1] in _END_TIME_PARAM_NAMES


def _future_problem(value: Any, param_name: str, output_unit: str) -> Optional[str]:
    """Return an error message if the epoch value is later than now (plus skew), else None."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    value_ms = value * 1000 if output_unit == "seconds" else value
    now_ms = utc_now_ms()
    if value_ms <= now_ms + _FUTURE_SKEW_MS:
        return None
    resolved = epoch_ms_to_utc(value_ms).strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"'{param_name}' resolves to {resolved} UTC, which is in the future "
        f"(current UTC time: {utc_now_iso()}). Use a time at or before now, "
        f"or omit '{param_name}' to use the current time."
    )


def check_time_order(
    from_value: Any,
    to_value: Any,
    from_name: str = "from_time",
    to_name: str = "to_time",
) -> Optional[str]:
    """
    Return an error message if the start of a range is not before its end, else None.

    Both values are epoch timestamps in the same unit. A missing end (None) means "now", so a start
    in the future is also rejected. Non-numeric or missing starts are not checked here (the per-value
    conversion has already validated them).
    """
    numeric = (int, float)
    if not isinstance(from_value, numeric) or isinstance(from_value, bool):
        return None
    if to_value is None:
        # Compare in the unit of from_value: a seconds-range value is far below the ms clock
        end = utc_now_ms() if from_value > _MAX_EPOCH_S else utc_now_ms() // 1000
        end_label = "now"
    elif isinstance(to_value, numeric) and not isinstance(to_value, bool):
        end = to_value
        end_label = f"'{to_name}'"
    else:
        return None
    if from_value >= end:
        return (
            f"'{from_name}' ({from_value}) must be earlier than {end_label} ({end}). "
            f"Swap the values or choose an earlier '{from_name}'."
        )
    return None


def _convert_datetime_value(
    param_value: Any,
    param_name: str,
    default_timezone: str = DEFAULT_TIMEZONE,
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
    
    Numeric values (and digit strings such as "1773151200000") must be a plausible Unix timestamp in
    output_unit, roughly 1973 to year 5138. 0, negatives, NaN/inf and a value in the other unit are errors.

    Examples:
        # Numeric value (no conversion)
        result = convert_datetime_param(<unix_timestamp_milliseconds>, "to")
        # Returns: {"value": <unix_timestamp_milliseconds>, "converted": False}
        
        # Datetime string with timezone
        result = convert_datetime_param("YYYY-MM-DD HH:mm:ss|UTC", "to")
        # Returns: {"value": <unix_timestamp_milliseconds>, "converted": True, "timezone": "UTC"}
        
        # Datetime string without timezone (uses the default timezone argument, UTC)
        result = convert_datetime_param("YYYY-MM-DD HH:mm:ss", "to")
        # Returns: {"value": <unix_timestamp_milliseconds>, "converted": True, "timezone": "UTC"}

        # Relative time: "yesterday", "<N> seconds|minutes|hours|days|weeks ago" or "in <N> <unit>"
        result = convert_datetime_param("2 days ago", "from_time")
        # Returns: {"value": <unix_timestamp_milliseconds>, "converted": True, "timezone": "UTC"}
    """
    # If None, return as-is (caller treats absence of a value as "use the server default")
    if param_value is None:
        return {"value": param_value, "converted": False}

    # Numeric values: pass through if a plausible Unix timestamp in output_unit, error otherwise
    # (0, negatives, NaN/inf, and values in the wrong unit such as seconds where milliseconds are expected)
    if isinstance(param_value, (int, float)) and not isinstance(param_value, bool):
        problem = _epoch_problem(param_value, param_name, output_unit)
        if problem:
            return {"error": problem, "value": None, "converted": False}
        return {"value": param_value, "converted": False}

    # bool is a subclass of int; treat it as an invalid type rather than a timestamp
    if isinstance(param_value, bool):
        return {
            "error": f"'{param_name}' must be a Unix timestamp in milliseconds, not a boolean.",
            "value": None,
            "converted": False,
        }
    
    # If not a string, return as-is
    if not isinstance(param_value, str):
        return {"value": param_value, "converted": False}
    
    # A string of digits is an epoch value that arrived as text; treat it exactly like the number
    if _DIGITS_RE.match(param_value):
        number = int(param_value)
        problem = _epoch_problem(number, param_name, output_unit)
        if problem:
            return {"error": problem, "value": None, "converted": False}
        return {"value": number, "converted": True, "timezone": DEFAULT_TIMEZONE}

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

    # "now" resolves to the current epoch time (timezone-independent)
    if datetime_str.strip().lower() == "now":
        current = get_current_timestamp(DEFAULT_TIMEZONE, output_unit)
        if "error" in current:
            return {
                "error": f"Failed to convert {param_name} datetime: {current['error']}",
                "value": None,
                "converted": False
            }
        return {"value": current["timestamp"], "converted": True, "timezone": DEFAULT_TIMEZONE}

    # Relative times ("yesterday", "2 days ago", "in 2 hours") are anchored to the server's UTC clock
    relative_result = _convert_relative(datetime_str, param_name, output_unit)
    if relative_result is not None:
        return relative_result

    # A trailing 'Z' or numeric offset already fixes the zone, so a different explicit "|zone" is contradictory
    if "|" in param_value:
        conflict = _zone_conflict(datetime_str.strip(), timezone)
        if conflict:
            return {
                "error": f"Failed to convert {param_name} datetime: {conflict} Use one or the other.",
                "value": None,
                "converted": False
            }

    # An inline zone ("... 2:00 PM ET") overrides the default, so report that one
    timezone = _inline_zone_or(param_value, datetime_str, timezone)

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


def convert_datetime_param(
    param_value: Any,
    param_name: str,
    default_timezone: str = DEFAULT_TIMEZONE,
    output_unit: str = "milliseconds",
    allow_future: bool = False,
) -> Dict[str, Any]:
    """
    Convert a datetime parameter to a timestamp and validate it (see _convert_datetime_value).

    On top of the conversion and plausible-range checks, a query end-of-range parameter ("to",
    "to_time", including nested names such as "timeFrame.to") must not be in the future. Every router
    funnels its time parameters through this function, so the check fires for all of them. Other
    parameters (maintenance window start/end, SLO correction startTime, release start, from_time...)
    may legitimately be in the future and are not checked here; use check_time_order for from/to pairs.

    Pass allow_future=True when the query domain permits an end time in the future (for example listing
    releases, which can be scheduled slightly ahead); the future check is then skipped.
    """
    result = _convert_datetime_value(param_value, param_name, default_timezone, output_unit)
    if "error" in result or allow_future or not _is_end_time_param(param_name):
        return result
    problem = _future_problem(result["value"], param_name, output_unit)
    if problem:
        return {"error": problem, "value": None, "converted": False}
    return result


def convert_datetime_params(
    params: Dict[str, Any],
    param_names: List[str],
    default_timezone: str = DEFAULT_TIMEZONE,
    output_unit: str = "milliseconds",
    allow_future: bool = False,
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
        allow_future: Skip the "end time must not be in the future" check (default: False)
    
    Returns:
        Dictionary with:
        - "params": Updated params dictionary with converted values
        - "conversions": Dict mapping param names to conversion info
        - "error": Error message if any conversion failed (optional)
    
    Examples:
        # Convert multiple time parameters
        params = {"from_time": "YYYY-MM-DD HH:mm:ss|UTC", "to_time": <unix_timestamp_milliseconds>}
        result = convert_datetime_params(params, ["from_time", "to_time"])
        # Returns: {
        #     "params": {"from_time": <unix_timestamp_milliseconds>, "to_time": <unix_timestamp_milliseconds>},
        #     "conversions": {
        #         "from_time": {"converted": True, "timezone": "UTC"},
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
            output_unit,
            allow_future=allow_future,
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
    default_timezone: str = DEFAULT_TIMEZONE,
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
        params = {"time_frame": {"to": "YYYY-MM-DD HH:mm:ss|UTC", "windowSize": 3600000}}
        result = convert_nested_datetime_param(params, "time_frame", "to")
        # Returns: {
        #     "params": {"time_frame": {"to": <unix_timestamp_milliseconds>, "windowSize": 3600000}},
        #     "converted": True,
        #     "timezone": "UTC"
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

    # Sentinel values (0, None, "", False): the API treats absence of "to" as "now".
    # Drop the key rather than forwarding a value that would mean 1970-01-01.
    # (A flat parameter with value 0 is an error instead, because there it is a deliberate value.)
    if nested_value is None or nested_value is False or (
        isinstance(nested_value, (int, float, str)) and nested_value in (0, "")
    ):
        updated_params = {**params, parent_key: {k: v for k, v in parent_dict.items() if k != nested_key}}
        return {"params": updated_params, "converted": True}

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
        # Copy only the two levels that change; everything else in params is shared, not cloned
        updated_params = {
            **params,
            parent_key: {**parent_dict, nested_key: conversion_result["value"]},
        }

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
            "YYYY-MM-DD HH:mm:ss|UTC",
            "start"
        )
        # Returns: {"value": <unix_timestamp_milliseconds>, "converted": True, "timezone": "UTC"}
        
        # Without timezone (requires elicitation)
        result = convert_datetime_param_with_required_timezone(
            "YYYY-MM-DD HH:mm:ss",
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
            "message": f"I see you want to use '{value}' for {param_name}, but I need to know which timezone.\n\nPlease specify the timezone:\n- UTC (Coordinated Universal Time)\n- IST (India Standard Time)",
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


# ---------------------------------------------------------------------------
# Time-range helpers (lifted from src/event/events_tools.py so that
# change_intelligence and other modules can share them without importing
# the full events module).
# ---------------------------------------------------------------------------

# Time conversion constants (milliseconds)
MS_PER_MINUTE: int = 60 * 1000
MS_PER_HOUR:   int = 60 * MS_PER_MINUTE
MS_PER_DAY:    int = 24 * MS_PER_HOUR
MS_PER_WEEK:   int = 7  * MS_PER_DAY
MS_PER_MONTH:  int = 30 * MS_PER_DAY

_DEFAULT_TIME_WINDOW_MINUTES = 10


def convert_time_range_to_window_size(time_range: str) -> int:
    """Convert a natural-language time range to a window size in milliseconds.

    Supported phrases (case-insensitive):
    - "last N minutes", "last minute", "past minute"
    - "last N hours", "last hour", "past hour"
    - "last N days", "last day", "past day", "yesterday"
    - "last N weeks", "last week", "past week"
    - "last N months", "last month", "past month"

    Falls back to 10 minutes when the string cannot be parsed.

    Args:
        time_range: Natural-language string, e.g. "last 24 hours".

    Returns:
        Window size in milliseconds (always > 0).
    """
    if not time_range:
        return _DEFAULT_TIME_WINDOW_MINUTES * MS_PER_MINUTE

    t = time_range.lower().strip()

    if "minute" in t:
        m = re.search(r'(\d+)\s?minute', t)  # NOSONAR
        if m:
            return int(m.group(1)) * MS_PER_MINUTE
        if "last minute" in t or "past minute" in t:
            return 1 * MS_PER_MINUTE

    elif "hour" in t:
        m = re.search(r'(\d+)\s?hour', t)  # NOSONAR
        if m:
            return int(m.group(1)) * MS_PER_HOUR
        if "last hour" in t or "past hour" in t:
            return 1 * MS_PER_HOUR
        if t in ("last few hours", "last hours", "few hours"):
            return _DEFAULT_TIME_WINDOW_MINUTES * MS_PER_MINUTE

    elif "day" in t:
        m = re.search(r'(\d+)\s?day', t)  # NOSONAR
        if m:
            return int(m.group(1)) * MS_PER_DAY
        if "last day" in t or "past day" in t or "yesterday" in t:
            return 1 * MS_PER_DAY

    elif "week" in t:
        m = re.search(r'(\d+)\s?week', t)  # NOSONAR
        if m:
            return int(m.group(1)) * MS_PER_WEEK
        if "last week" in t or "past week" in t:
            return 1 * MS_PER_WEEK

    elif "month" in t:
        m = re.search(r'(\d+)\s?month', t)  # NOSONAR
        if m:
            return int(m.group(1)) * MS_PER_MONTH
        if "last month" in t or "past month" in t:
            return 1 * MS_PER_MONTH

    return _DEFAULT_TIME_WINDOW_MINUTES * MS_PER_MINUTE


def build_time_params(
    time_range: str | None = None,
    from_time: int | None = None,
    to_time: int | None = None,
    now_ms: int | None = None,
) -> Dict[str, Any]:
    """Build ``api_params`` and display timestamps from flexible time inputs.

    Priority:
    1. Both ``from_time`` and ``to_time`` → used as-is (``time_range`` ignored).
    2. Exactly one of ``from_time`` / ``to_time`` (mixed input):
       the missing bound is derived from the window of ``time_range``
       (default 10 minutes when ``time_range`` is absent). With only
       ``to_time`` the window ends there; with only ``from_time`` the window
       starts there and is capped at ``now_ms`` (and at least ``from_time``).
       Without ``time_range`` and only ``from_time``, the end is ``now_ms``.
    3. ``window_size`` derived from ``time_range``.
    4. Default 10-minute window ending now.

    Args:
        now_ms: Optional "current time" in epoch ms (injectable for tests /
            callers that own their own clock). Defaults to the system clock.

    Returns a dict with keys:
    - ``api_params``: dict ready for the Instana Events API
      (either ``{"window_size": N}`` or ``{"var_from": X, "to": Y}``)
    - ``from_time``: epoch-ms start (for display)
    - ``to_time``:   epoch-ms end   (for display)
    """
    api_params: Dict[str, Any] = {}
    if now_ms is None:
        now_ms = utc_now_ms()
    default_window = _DEFAULT_TIME_WINDOW_MINUTES * MS_PER_MINUTE

    if from_time is not None or to_time is not None:
        window = convert_time_range_to_window_size(time_range) if time_range else default_window
        if to_time is not None:
            resolved_to = to_time
            resolved_from = from_time if from_time is not None else to_time - window
        else:
            resolved_from = from_time
            resolved_to = max(from_time, min(from_time + window, now_ms)) if time_range else now_ms
        api_params["var_from"] = resolved_from
        api_params["to"]       = resolved_to
        return {"api_params": api_params, "from_time": resolved_from, "to_time": resolved_to}

    if time_range:
        window_size = convert_time_range_to_window_size(time_range)
        api_params["window_size"] = window_size
        return {"api_params": api_params, "from_time": now_ms - window_size, "to_time": now_ms}

    # Default: 10-minute window ending now
    default_from = now_ms - default_window
    api_params["var_from"] = default_from
    api_params["to"]       = now_ms
    return {"api_params": api_params, "from_time": default_from, "to_time": now_ms}