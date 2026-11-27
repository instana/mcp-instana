"""Shared builders for structured elicitation responses."""

from typing import Any, Dict


def missing_param(field: str, issue: str, hint: str, reason: str = "missing_required_params") -> Dict[str, Any]:
    """Build the structured elicitation response for a missing or invalid required parameter."""
    return {
        "elicitation_needed": True,
        "reason": reason,
        "api_error": [{"field": field, "issue": issue, "hint": hint}],
        "message": f"Missing required parameter '{field}'. {hint}" if reason == "missing_required_params"
        else f"Invalid parameter '{field}': {issue}. {hint}",
    }
