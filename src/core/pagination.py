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
* Each page request (e.g. ``"page_2"`` or ``"next"``) fetches fresh data from the
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

# "page_10", "PAGE_3": the destination page is embedded in the operation string.
_PAGE_N_RE = re.compile(r"^page_(\d+)$", re.IGNORECASE)


def operation_for_page(page: int) -> str:
    """Return the operation string that jumps to *page* (e.g. ``"page_3"``)."""
    return f"page_{max(1, int(page))}"


def _first_int(*candidates: Any) -> Optional[int]:
    """Return the first candidate that is a usable (non-empty) value, as an int >= 1."""
    for value in candidates:
        if value is None or str(value).strip() == "":
            continue
        try:
            return max(1, int(value))
        except (ValueError, TypeError):
            return 1
    return None


def resolve_nav_page(
    operation: Optional[str],
    params: Dict[str, Any],
    page_number: Any = None,
    target_page: Any = None,
) -> Optional[int]:
    """
    Return the destination page for a navigation request, or ``None`` when *operation*
    is not a navigation operation.

    * ``page_N``     -> N (the number is inside the operation string)
    * ``go_to_page`` -> target_page, else page_number / page
    * ``next``       -> current page + 1   (current = page_number / page)
    * ``previous``   -> current page - 1   (minimum 1)

    A missing current page is treated as page 1 (and logged), which is exactly why a
    ``next`` call that lacks ``page_number`` keeps returning page 2.
    """
    op = (operation or "").strip()

    match = _PAGE_N_RE.match(op)
    if match:
        return max(1, int(match.group(1)))

    if op == "go_to_page":
        page = _first_int(
            params.get("target_page"), target_page,
            params.get("page_number"), page_number,
            params.get("page"),
        )
        if page is None:
            logger.warning("[pagination] go_to_page without a page number - defaulting to 1")
            return 1
        return page

    if op in ("next", "previous"):
        current = _first_int(params.get("page_number"), page_number, params.get("page"))
        if current is None:
            logger.warning(
                "[pagination] '%s' without page_number - defaulting to page 1. "
                "Use pagination.%s_operation from the last response instead.",
                op, op,
            )
            current = 1
        return current + 1 if op == "next" else max(1, current - 1)

    return None


def add_navigation(pagination: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add ``has_previous`` / ``next_operation`` / ``previous_operation`` to a pagination
    dict (in place).

    The operation values are ``None`` when there is no such page, otherwise the exact
    operation string (``"page_N"``) the agent should call to move there.
    """
    if not isinstance(pagination, dict):
        return pagination
    try:
        page = max(1, int(pagination.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    pagination["has_previous"] = page > 1
    pagination["next_operation"] = operation_for_page(page + 1) if pagination.get("has_more") else None
    pagination["previous_operation"] = operation_for_page(page - 1) if page > 1 else None
    return pagination


def _to_int(value: Any, default: int) -> int:
    """Parse an int from an int/str (LLMs send both); fall back to *default*."""
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


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
    safe_page = max(1, _to_int(page, 1))
    safe_size = max(1, _to_int(page_size, PAGE_SIZE))
    total = max(0, _to_int(total_items, 0))
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
    safe_page = max(1, _to_int(page, 1))
    safe_size = max(1, min(max_page_size, _to_int(page_size, PAGE_SIZE)))
    start = (safe_page - 1) * safe_size
    page_records = list(items[start:start + safe_size]) if start < len(items) else []
    return page_records, build_pagination(safe_page, safe_size, len(items), list_id)
