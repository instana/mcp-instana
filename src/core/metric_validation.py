"""
Pre-flight validation for Website / Mobile App analyze queries.

This module validates metric, beacon-type, and aggregation combinations
*before* an API call is made, preventing confusing Instana backend errors
from reaching the LLM. The validation pipeline has two layers:

1. **Local checks (no I/O):**
   - ``validate_beacon_type_known`` — rejects unrecognized or camelCase beacon
     types against the hardcoded beacon-type maps in ``utils.py``.
   - ``validate_metric_compatibility`` — cross-references user-supplied metrics
     against a pre-fetched catalog to verify metric existence, beacon-type
     compatibility, and (best-effort) aggregation support.

2. **Catalog fetch (I/O):**
   - ``fetch_metric_catalog_internal`` — retrieves the metric catalog from the
     Instana API via the SDK's catalog API wrapper. Returns projected metric
     cards on success or a plain ``{"error": ...}`` dict on failure (fail-closed;
     never returns ``elicitation_needed`` on infrastructure errors).

Validation ordering enforced by callers (website_analyze.py, mobile_app_analyze.py):
    beacon-type check  →  catalog fetch  →  metric compatibility check  →  API call

Key design decisions:
- Beacon-type validation rejects camelCase inputs (e.g. "pageLoad") even when
  ``.upper()`` would match a map key, to avoid inconsistent behavior across
  beacon types whose camelCase forms do/don't collapse to valid UPPER_SNAKE keys.
- Aggregation validation is best-effort: skipped when the catalog provides empty
  aggregation lists (indicating unavailable metadata, not "no valid aggregations").
- All validation errors use ``elicitation_needed`` to guide the LLM toward the
  catalog, while infrastructure failures (catalog unreachable, malformed response)
  use plain ``error`` dicts.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from src.core.utils import decode_response, normalize_beacon_type, project_metric_card

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure validation functions (no I/O, fully unit-testable)
# ---------------------------------------------------------------------------

def _build_reverse_beacon_type_map(beacon_type_map: Dict[str, str]) -> Dict[str, str]:
    return {v: k for k, v in beacon_type_map.items()}


def _build_catalog_index(catalog: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {m["metricId"]: m for m in catalog if isinstance(m, dict) and m.get("metricId")}


def _check_single_metric(
    metric_entry: Any,
    beacon_type_camel: str,
    catalog_index: Dict[str, Dict[str, Any]],
    reverse_map: Dict[str, str],
) -> Optional[str]:
    if not isinstance(metric_entry, dict):
        return f"invalid metric entry (expected dict with 'metric' key): {metric_entry!r}"

    metric_name = metric_entry.get("metric")
    if not metric_name or not isinstance(metric_name, str):
        return "metric entry missing required 'metric' field"

    catalog_entry = catalog_index.get(metric_name)
    if catalog_entry is None:
        return f"metric '{metric_name}' not found in catalog"

    beacon_types = catalog_entry.get("beaconTypes", [])
    if beacon_type_camel not in beacon_types:
        display_types = sorted(
            reverse_map.get(bt, bt) for bt in beacon_types
        )
        requested_display = reverse_map.get(beacon_type_camel, beacon_type_camel)
        return (
            f"metric '{metric_name}' is incompatible with beacon_type "
            f"'{requested_display}'; valid beacon types: {display_types}"
        )

    # Validation policy: metric existence and beacon-type compatibility are
    # mandatory checks. Aggregation validation is best-effort — it only runs
    # when the catalog provides non-empty aggregation metadata. Empty aggregation
    # lists (from project_metric_card converting None→[]) indicate unavailable
    # metadata, not "no aggregations are valid." This is a policy choice: we
    # fail-closed on structural issues (non-dict entries, missing metricId) but
    # skip aggregation validation when the catalog simply lacks that metadata.
    aggregation = metric_entry.get("aggregation")
    if aggregation:
        valid_aggs = catalog_entry.get("aggregations", [])
        if valid_aggs and aggregation not in valid_aggs:
            return (
                f"metric '{metric_name}' with beacon_type "
                f"'{reverse_map.get(beacon_type_camel, beacon_type_camel)}' "
                f"does not support aggregation '{aggregation}'; "
                f"valid aggregations: {valid_aggs}"
            )

    return None


def validate_beacon_type_known(
    beacon_type: str,
    beacon_type_map: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    # Accept request-format only (UPPER_SNAKE), case-insensitively.
    # Reject catalog-format camelCase: "pageLoad".upper() == "PAGELOAD" would
    # accidentally match, but "sessionStart".upper() == "SESSIONSTART" would not,
    # creating inconsistent behavior. Requiring uniform case (all-upper or
    # all-lower) prevents camelCase pass-through for any beacon type.
    if beacon_type:
        is_uniform_case = beacon_type == beacon_type.upper() or beacon_type == beacon_type.lower()
        if is_uniform_case and beacon_type.upper() in beacon_type_map:
            return None

    valid_types = sorted(beacon_type_map.keys())
    msg = f"unrecognized beacon_type '{beacon_type}'; valid values: {valid_types}"
    return {
        "elicitation_needed": True,
        "reason": f"Unrecognized beacon_type '{beacon_type}'; valid values: {valid_types}",
        "api_error": [msg],
        "message": "Use a valid beacon_type from the list above.",
    }


def validate_metric_compatibility(
    metrics: List[Dict[str, Any]],
    beacon_type: str,
    catalog: List[Dict[str, Any]],
    beacon_type_map: Dict[str, str],
    catalog_operation: str,
) -> Optional[Dict[str, Any]]:
    if not metrics:
        return None

    # normalize_beacon_type returns the original string if not in the map;
    # validate_beacon_type_known (called before this function) guarantees the
    # beacon_type is in the map, so this always produces the camelCase form.
    beacon_type_camel = normalize_beacon_type(beacon_type, beacon_type_map)

    reverse_map = _build_reverse_beacon_type_map(beacon_type_map)
    catalog_index = _build_catalog_index(catalog)

    errors: List[str] = []
    for entry in metrics:
        error = _check_single_metric(entry, beacon_type_camel, catalog_index, reverse_map)
        if error:
            errors.append(error)

    if not errors:
        return None

    return {
        "elicitation_needed": True,
        "reason": (
            f"Metric compatibility validation failed: "
            f"{len(errors)} invalid metric/aggregation/beacon_type "
            f"combination{'s' if len(errors) != 1 else ''} detected"
        ),
        "api_error": errors,
        "required_action": {
            "resource_type": "catalog",
            "operation": catalog_operation,
            "params": {},
        },
        "message": "Use compatible metric, aggregation, and beacon_type combinations from the metric catalog.",
    }


# ---------------------------------------------------------------------------
# Catalog fetch helper (I/O, requires ApiClient)
# ---------------------------------------------------------------------------

def fetch_metric_catalog_internal(
    api_client: Any,
    catalog_api_class: Any,
    fetch_method_name: str,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    underlying = getattr(api_client, "api_client", None)
    if underlying is None:
        return {"error": "Cannot access underlying ApiClient for catalog fetch"}

    try:
        catalog_instance = catalog_api_class(api_client=underlying)
    except Exception as e:
        return {"error": f"Failed to instantiate catalog API: {e}"}

    fetch_method = getattr(catalog_instance, fetch_method_name, None)
    if fetch_method is None:
        return {"error": f"Catalog API has no method '{fetch_method_name}'"}

    try:
        response = fetch_method()
    except Exception as e:
        return {"error": f"Failed to fetch metric catalog: {e}"}

    if response.status != 200:
        return {"error": f"Failed to fetch metric catalog for pre-flight validation: HTTP {response.status}"}

    try:
        response_text = decode_response(response)
        raw_metrics = json.loads(response_text)
    except Exception as e:
        return {"error": f"Failed to parse metric catalog response: {e}"}

    if not isinstance(raw_metrics, list):
        return {"error": "Metric catalog response is not a list — cannot validate"}

    for m in raw_metrics:
        if not isinstance(m, dict):
            return {"error": "Metric catalog response contains non-dict entries — cannot validate"}

    projected = [project_metric_card(m) for m in raw_metrics]

    for entry in projected:
        metric_id = entry.get("metricId")
        if not metric_id or not isinstance(metric_id, str):
            return {"error": "Metric catalog response contains malformed entries — cannot validate"}
        if not isinstance(entry.get("beaconTypes"), list):
            return {"error": "Metric catalog response contains malformed entries — cannot validate"}
        if not isinstance(entry.get("aggregations"), list):
            return {"error": "Metric catalog response contains malformed entries — cannot validate"}

    return projected
