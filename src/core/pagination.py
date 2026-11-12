"""
Shared, stateless pagination helpers for Instana list tools.

Every paginated tool (applications, synthetic monitors, maintenance windows, ...) uses the
same building blocks so they all behave and look the same:

* :func:`paginate` slices a full in-memory list into one page and returns it together with
  the standard ``pagination`` envelope (see :func:`build_pagination`).
* :func:`build_pagination` builds that envelope for tools whose data source already
  returned just one page.
* :func:`resolve_nav_page` turns a navigation request (``next`` / ``previous`` /
  ``go_to_page`` / ``page_N``) into the destination page number.
* :func:`apply_navigation` is what the smart routers call: it rewrites a navigation
  operation into the tool's list operation (or returns an elicitation error).
* :func:`normalize_page_args` / :func:`page_kwargs` / :func:`coerce_int` are the shared
  argument helpers, so no tool hand-rolls clamping or string coercion.
* :func:`add_navigation` stamps ``next_operation`` / ``previous_operation`` onto a
  ``pagination`` object so the agent can simply copy the operation string from the last
  response instead of tracking and re-sending a page number.

The standard envelope::

    {page, page_size, total_items, total_pages, has_more, has_previous,
     next_operation, previous_operation, list_id?}

``list_id`` names the list the envelope belongs to (e.g. ``"alert_channels"``) so the
agent can tell which list "next" continues.

Stateless Pagination & Ordering Notes:
-------------------------------------
* The server maintains no in-memory session or cache across requests, ensuring high
  availability across multiple server replicas and restarts.
* Each page request (e.g. ``"page_2"``) fetches fresh data from the
  upstream Instana API and slices the requested page offset.
* For APIs where the upstream service returns unsorted or non-deterministic ordering,
  pass a ``sort_key`` (or use :func:`stable_sort_key`) to :func:`paginate` to guarantee
  stable, consistent page slices between consecutive page calls.
* Note that concurrent upstream additions or deletions between page requests may shift
  item offsets; when strict consistency is required, filter by specific identifiers,
  tags, or fixed time windows.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

PAGE_SIZE = 10

# Upper bound for a requested page number (guards against absurd "page_9999999999999").
MAX_PAGE_NUMBER = 1_000_000

# "page_10", "PAGE_3": the destination page is embedded in the operation string.
_PAGE_N_RE = re.compile(r"^page_(\d+)$", re.IGNORECASE)


class NavigationError(ValueError):
    """A navigation request that cannot be resolved to a destination page."""


def operation_for_page(page: int) -> str:
    """Return the operation string that jumps to *page* (e.g. ``"page_3"``)."""
    return f"page_{max(1, int(page))}"


def coerce_int(value: Any, default: int) -> int:
    """Parse an int from an int/str (LLMs send both); fall back to *default*."""
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    try:
        # "2.0" / 2.0 (LLMs and JSON round-trips) are whole numbers too
        as_float = float(value)
        return int(as_float) if as_float.is_integer() else default
    except (ValueError, TypeError, OverflowError):
        return default


def normalize_page_args(
    page: Any,
    page_size: Any,
    default_size: int = PAGE_SIZE,
    max_size: int = 100,
) -> Tuple[int, int]:
    """
    Return a safe ``(page, page_size)`` pair: ints, ``page >= 1`` and
    ``1 <= page_size <= max_size``. Missing or unparsable values use ``1`` /
    *default_size*.
    """
    return (
        max(1, coerce_int(page, 1)),
        max(1, min(max_size, coerce_int(page_size, default_size))),
    )


def page_kwargs(params: Dict[str, Any]) -> Dict[str, Any]:
    """``page`` / ``page_size`` entries of *params* that were actually supplied."""
    return {k: params[k] for k in ("page", "page_size") if params.get(k) is not None}


def _current_page(params: Dict[str, Any], page_number: Any = None) -> Optional[int]:
    """The caller-supplied current page (``page_number`` / ``page``), or ``None``."""
    for value in (params.get("page_number"), page_number, params.get("page")):
        if value is None or str(value).strip() == "":
            continue
        try:
            return int(value)
        except (ValueError, TypeError):
            raise NavigationError(f"page must be a whole number, got {value!r}") from None
    return None


def resolve_nav_page(
    operation: Optional[str],
    params: Dict[str, Any],
    page_number: Any = None,
    target_page: Any = None,
) -> Optional[int]:
    """
    Return the destination page for a navigation request, or ``None`` when *operation*
    is not a navigation operation. Raises :class:`NavigationError` for a navigation
    request that cannot be resolved.

    * ``page_N``     -> N (self-contained; this is the form ``next_operation`` emits)
    * ``go_to_page`` -> target_page (required)
    * ``next``       -> current page + 1   (alias; current = page_number / page, required)
    * ``previous``   -> current page - 1   (alias; current page must be > 1)

    Operations are matched case-insensitively. Nothing is guessed: a missing or invalid
    page number is an error, never a silent default to page 1.
    """
    op = (operation or "").strip().lower()

    match = _PAGE_N_RE.match(op)
    if match:
        destination = int(match.group(1))
    elif op == "go_to_page":
        raw = params.get("target_page") if params.get("target_page") is not None else target_page
        if raw is None or str(raw).strip() == "":
            raise NavigationError("go_to_page requires target_page (a whole number >= 1)")
        try:
            destination = int(raw)
        except (ValueError, TypeError):
            raise NavigationError(f"target_page must be a whole number, got {raw!r}") from None
    elif op in ("next", "previous"):
        current = _current_page(params, page_number)
        if current is None:
            raise NavigationError(
                f"'{op}' needs the current page (page / page_number). "
                f"Use pagination.{op}_operation (e.g. 'page_N') from the last response instead."
            )
        if current < 1:
            raise NavigationError(f"current page must be >= 1, got {current}")
        if op == "previous" and current == 1:
            raise NavigationError("already on the first page; there is no previous page")
        destination = current + 1 if op == "next" else current - 1
    else:
        return None

    if destination < 1:
        raise NavigationError(f"page must be >= 1, got {destination}")
    if destination > MAX_PAGE_NUMBER:
        raise NavigationError(f"page must be <= {MAX_PAGE_NUMBER}, got {destination}")
    return destination


def navigation_error(operation: Optional[str], issue: str) -> Dict[str, Any]:
    """Elicitation-style error returned by routers when navigation cannot be resolved."""
    return {
        "elicitation_needed": True,
        "reason": "invalid_pagination",
        "api_error": [
            {
                "field": "operation",
                "issue": issue,
                "expected": "pagination.next_operation / previous_operation from the last response (e.g. 'page_2')",
            }
        ],
        "message": f"Cannot navigate with operation '{operation}': {issue}",
    }


def apply_navigation(
    operation: Optional[str],
    params: Dict[str, Any],
    target_operation: str,
    page_key: str = "page",
) -> Tuple[Optional[str], Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Router helper. Returns ``(operation, params, error)``.

    For a navigation operation the result is ``(target_operation, params + {page_key: N},
    None)``; for any other operation the inputs are returned unchanged; when navigation
    cannot be resolved, *error* is a ready-to-return elicitation response.
    """
    try:
        destination = resolve_nav_page(operation, params)
    except NavigationError as exc:
        return operation, params, navigation_error(operation, str(exc))
    if destination is None:
        return operation, params, None
    return target_operation, {**params, page_key: destination}, None


def add_navigation(pagination: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add ``has_previous`` / ``next_operation`` / ``previous_operation`` to a pagination
    dict (in place).

    The operation values are ``None`` when there is no such page, otherwise the exact
    operation string (``"page_N"``) the agent should call to move there. When the
    requested page lies beyond ``total_pages`` (if known), ``previous_operation`` points
    at the last real page.
    """
    if not isinstance(pagination, dict):
        return pagination
    try:
        page = max(1, int(pagination.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    pagination["has_previous"] = page > 1
    pagination["next_operation"] = operation_for_page(page + 1) if pagination.get("has_more") else None
    previous_page = page - 1
    total_pages = coerce_int(pagination.get("total_pages"), 0)
    if total_pages >= 1:
        # Past the end: step back to the last real page, not to another empty one.
        previous_page = min(previous_page, total_pages)
    pagination["previous_operation"] = operation_for_page(previous_page) if page > 1 else None
    return pagination


def build_pagination(
    page: Any,
    page_size: Any,
    total_items: Any,
    list_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build the standard pagination envelope.

    Use directly when the data source already returned just one page and only the
    totals are known; use :func:`paginate` when you hold the full list.
    """
    safe_page = max(1, coerce_int(page, 1))
    safe_size = max(1, coerce_int(page_size, PAGE_SIZE))
    total = max(0, coerce_int(total_items, 0))
    envelope: Dict[str, Any] = {
        "page": safe_page,
        "page_size": safe_size,
        "total_items": total,
        "total_pages": max(1, -(-total // safe_size)),  # ceiling division
        "has_more": safe_page * safe_size < total,
    }
    if list_id:
        envelope["list_id"] = list_id
    return add_navigation(envelope)


def stable_sort_key(item: Any) -> Any:
    """
    Extract a stable sort key from an item (dict or object) so that repeated fetches
    produce consistent, deterministic page slices without skipping or repeating items.
    """
    if isinstance(item, dict):
        for key in ("id", "name", "label", "key", "title"):
            val = item.get(key)
            if val is not None:
                return str(val)
        return str(item)
    for attr in ("id", "name", "label", "key", "title"):
        if hasattr(item, attr):
            val = getattr(item, attr)
            if val is not None:
                return str(val)
    return str(item)


def paginate(
    records: List[Any],
    page: Union[int, str, None] = 1,
    page_size: Union[int, str, None] = PAGE_SIZE,
    *,
    max_page_size: int = 100,
    sort_key: Optional[Any] = None,
    list_id: Optional[str] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Slice the full *records* list down to one page and return ``(page_records, envelope)``.

    * ``page`` / ``page_size`` may be int or str; invalid values fall back to 1 / 10.
      ``page_size`` is clamped to ``1..max_page_size``.
    * ``sort_key`` (optional callable) sorts *before* slicing. Pass one (or :func:`stable_sort_key`)
      when the data source does not guarantee a stable order, because the server re-fetches the whole
      list on every page and an unstable order can skip or repeat items between pages.
    * Note on stateless pagination: The server re-fetches the list on each page request
      without keeping server-side session state. Sorting ensures stable ordering, though
      concurrent upstream creations or deletions between page requests may shift items.
    * A page beyond the last one returns an empty list (the envelope still reports the
      requested page) rather than silently showing a different page.
    * ``list_id`` names the list so the agent knows which list "next" continues.
    """
    items = sorted(records, key=sort_key) if sort_key is not None else records
    safe_page, safe_size = normalize_page_args(page, page_size, PAGE_SIZE, max_page_size)
    start = (safe_page - 1) * safe_size
    page_records = list(items[start:start + safe_size]) if start < len(items) else []
    return page_records, build_pagination(safe_page, safe_size, len(items), list_id)
