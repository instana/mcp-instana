"""
Instana UI link helpers.

Build deep links into the Instana UI for applications, application services and
synthetic tests, plus ready-to-paste markdown links, so tool results can carry a
clickable ``link`` next to each entity.
"""

import logging
import urllib.parse
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _base(base_url: Optional[str]) -> str:
    return (base_url or "").rstrip("/")


def build_markdown_link(label: Optional[str], url: str) -> str:
    """
    Build a plain markdown link.

    Brackets in the label are escaped so they cannot end the link text, and
    parentheses in the URL are percent-encoded so they cannot end the link early.
    """
    # Collapse all whitespace (incl. newlines) so a label cannot break the link syntax.
    clean_label = " ".join(str(label).split()) if label is not None else ""
    if not clean_label:
        clean_label = url
    md_label = clean_label.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    md_url = url.replace(" ", "%20").replace("(", "%28").replace(")", "%29")
    return f"[{md_label}]({md_url})"


def build_application_url(base_url: Optional[str], app_id: Optional[str]) -> str:
    """URL of an application perspective's summary page in the Instana UI."""
    base = _base(base_url)
    if not app_id:
        return f"{base}/#/applications"
    return f"{base}/#/application;appId={urllib.parse.quote(str(app_id), safe='')}/summary;latencyTab=overTime"


def build_service_url(
    base_url: Optional[str],
    application_id: Optional[str],
    service_id: Optional[str],
    boundary_scope: str = "ALL",
) -> str:
    """URL of a service within an application perspective in the Instana UI."""
    base = _base(base_url)
    if not service_id:
        return f"{base}/#/services"
    app_param = f"appId={urllib.parse.quote(str(application_id), safe='')};" if application_id else ""
    svc_param = urllib.parse.quote(str(service_id), safe="")
    return (
        f"{base}/#/service;{app_param}serviceId={svc_param};"
        f"boundaryScope={urllib.parse.quote(str(boundary_scope), safe='')}/summary;latencyTab=overTime;callsTab=call"
    )


def build_synthetic_test_url(base_url: Optional[str], test: Dict[str, Any]) -> str:
    """URL of a synthetic test's summary page in the Instana UI."""
    base = _base(base_url)
    try:
        test_id = str(test.get("id") or "")
        test_label = str(test.get("label") or "")
        config = test.get("configuration") or {}
        test_type = str(config.get("syntheticType") or "HTTPAction")

        raw_loc_ids = test.get("locations") or []
        raw_loc_labels = test.get("locationDisplayLabels") or []

        location_ids = [str(x) for x in raw_loc_ids if x is not None]
        location_labels = [str(x) for x in raw_loc_labels if x is not None]

        # "/" is deliberately not in the safe set: a label such as "/testpath" would
        # otherwise add a path segment and break the Instana URL parser.
        encoded_label = urllib.parse.quote(test_label, safe="()")
        encoded_location_labels = urllib.parse.quote(",".join(location_labels), safe="()")
        encoded_location_ids = urllib.parse.quote(",".join(location_ids), safe="")

        return (
            f"{base}/#/synthetic;"
            f"testId={test_id};"
            f"testLabel={encoded_label};"
            f"type={test_type};"
            f"locationDisplayLabels={encoded_location_labels};"
            f"locationIds={encoded_location_ids};"
            f"runType=Scheduled;"
            f"executionType=Scheduled/summary"
        )
    except Exception as e:
        logger.warning("Failed to build URL for synthetic test %s: %s", test.get("id", "unknown"), e)
        return f"{base}/#/synthetic"


def add_application_link(base_url: Optional[str], app: Dict[str, Any]) -> None:
    """
    Add a markdown ``link`` to an application config / perspective dict in place.

    Does nothing without a base URL or an ``id``: such a link could not open anything useful.
    """
    if not _base(base_url) or not app.get("id"):
        return
    url = build_application_url(base_url, app["id"])
    app["link"] = build_markdown_link(app.get("label") or app["id"], url)


def add_service_link(
    base_url: Optional[str],
    application_id: Optional[str],
    service: Dict[str, Any],
    boundary_scope: str = "ALL",
) -> None:
    """Add a markdown ``link`` to a service dict in place (skipped without a base URL or ``id``)."""
    if not _base(base_url) or not service.get("id"):
        return
    url = build_service_url(base_url, application_id, service["id"], boundary_scope)
    service["link"] = build_markdown_link(service.get("label") or service["id"], url)


def add_synthetic_test_link(base_url: Optional[str], test: Dict[str, Any]) -> None:
    """Add a markdown ``link`` to a synthetic test dict in place (skipped without a base URL or ``id``)."""
    if not _base(base_url) or not test.get("id"):
        return
    url = build_synthetic_test_url(base_url, test)
    test["link"] = build_markdown_link(test.get("label") or test["id"], url)
