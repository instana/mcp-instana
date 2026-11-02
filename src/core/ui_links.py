"""
Instana UI link helpers.

Build deep links into the Instana UI for applications, application services and
synthetic tests, plus ready-to-paste markdown links, so tool results can carry a
clickable ``url`` / ``link`` next to each entity.
"""

import logging
import urllib.parse
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _base(base_url: Optional[str]) -> str:
    return (base_url or "").rstrip("/")


def build_markdown_link(label: str, url: str) -> str:
    """
    Build a plain markdown link.

    Brackets in the label are escaped so they cannot end the link text, and
    parentheses in the URL are percent-encoded so they cannot end the link early.
    """
    md_label = str(label).replace("[", "\\[").replace("]", "\\]")
    md_url = url.replace("(", "%28").replace(")", "%29")
    return f"[{md_label}]({md_url})"


def build_application_url(base_url: Optional[str], app_id: Optional[str]) -> str:
    """URL of an application perspective's summary page in the Instana UI."""
    base = _base(base_url)
    if not app_id:
        return f"{base}/#/applications"
    return f"{base}/#/application;appId={app_id}/summary;latencyTab=overTime"


def build_service_url(
    base_url: Optional[str], application_id: Optional[str], service_id: Optional[str]
) -> str:
    """URL of a service within an application perspective in the Instana UI."""
    base = _base(base_url)
    if not service_id:
        return f"{base}/#/services"
    return (
        f"{base}/#/service;appId={application_id};serviceId={service_id};"
        f"boundaryScope=ALL/summary;latencyTab=overTime;callsTab=call"
    )


def build_synthetic_test_url(base_url: Optional[str], test: Dict[str, Any]) -> str:
    """URL of a synthetic test's summary page in the Instana UI."""
    base = _base(base_url)
    try:
        test_id = test.get("id", "")
        test_label = test.get("label", "")
        test_type = (test.get("configuration") or {}).get("syntheticType", "HTTPAction")

        location_ids = test.get("locations") or []
        location_labels = test.get("locationDisplayLabels") or []

        # "/" is deliberately not in the safe set: a label such as "/testpath" would
        # otherwise add a path segment and break the Instana URL parser.
        encoded_label = urllib.parse.quote(test_label, safe="()")
        encoded_location_labels = urllib.parse.quote(",".join(location_labels), safe="()")
        encoded_location_ids = urllib.parse.quote(",".join(location_ids))

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
    """Add ``url`` and ``link`` to an application config / perspective dict in place."""
    url = build_application_url(base_url, app.get("id"))
    app["url"] = url
    app["link"] = build_markdown_link(app.get("label") or app.get("id") or "", url)


def add_service_link(base_url: Optional[str], application_id: Optional[str], service: Dict[str, Any]) -> None:
    """Add ``url`` and ``link`` to a service dict in place."""
    service_id = service.get("id")
    url = build_service_url(base_url, application_id, service_id)
    service["url"] = url
    service["link"] = build_markdown_link(service.get("label") or service_id or "", url)


def add_synthetic_test_link(base_url: Optional[str], test: Dict[str, Any]) -> None:
    """Add ``url`` and ``link`` to a synthetic test dict in place."""
    url = build_synthetic_test_url(base_url, test)
    test["url"] = url
    test["link"] = build_markdown_link(test.get("label") or test.get("id") or "", url)
