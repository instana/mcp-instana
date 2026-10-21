"""
SLO prompts module.

This module contains a single consolidated class, SLOPrompts, with 11 high-quality
prompt templates for SLO-related workflows. These prompts are designed to guide
the LLM through multi-step, cross-domain tasks that span SLOs, infrastructure metrics,
events, releases, synthetic tests, and Real User Monitoring (RUM).

"""

from typing import Any, Dict, Optional

from src.prompts import auto_register_prompt


class SLOPrompts:
    """Class containing SLO-related prompts for SRE workflows and cross-domain analysis."""

    @auto_register_prompt
    @staticmethod
    def get_slo_report_full(
        slo_id: str,
        var_from: Optional[str] = None,
        to: Optional[str] = None,
        exclude_correction_id: Optional[str] = None,
        include_correction_id: Optional[str] = None,
    ) -> str:
        """Generate a full SLO report with all available filtering options"""
        params_dict: Dict[str, Any] = {
            "slo_id": slo_id,
        }
        if var_from:
            params_dict["var_from"] = var_from
        if to:
            params_dict["to"] = to
        if exclude_correction_id:
            params_dict["exclude_correction_id"] = [exclude_correction_id]
        if include_correction_id:
            params_dict["include_correction_id"] = [include_correction_id]

        return f"""
        Generate a full SLO report with all available filtering options.

        Call:
          manage_slo, resource_type="report", operation="get",
          params={params_dict}
          → slo_id (required): {slo_id}
          → var_from (optional): {var_from or '(not specified — defaults to SLO window start)'}
            Accepts Unix ms timestamp (e.g. 1741604400000) or human datetime with timezone
            (e.g. "10 March 2026, 2:00 PM|IST"). Same format for "to".
          → to (optional): {to or '(not specified — defaults to current time)'}
          → exclude_correction_id / include_correction_id (optional): omit if not specified.

        Interpretation & Presentation Guidelines:
        - Key Metrics Glossary:
          * sli: Actual Service Level Indicator value (0.0 to 1.0 fraction; e.g. 0.999 = 99.9%).
          * slo: Configured target threshold as a fraction (e.g. 0.99 means 99% target).
            State the value as returned; do not interpret whether it is a typical or unusual target.
          * totalErrorBudget & errorBudgetSpent: Count of allowed vs. consumed bad events/time units
            (same unit for both fields).
          * errorBudgetRemaining: Count of remaining allowed bad events/time units
            (same unit as totalErrorBudget).
          * errorBurnRate: Consumption rate of error budget across the window
            (>1.0 means burning faster than sustainable).
        - Chart Summary: Summarize overall trends from scalar fields only. Inspect chart time
          series (errorChart, violationDistribution, etc.) only if non-zero variations occur.
        """

    @auto_register_prompt
    @staticmethod
    def get_slo_configurations_full(
        query: Optional[str] = None,
        slo_status: Optional[str] = None,
        entity_type: Optional[str] = None,
        blueprint: Optional[str] = None,
        tag: Optional[str] = None,
        kubernetes_cluster_uuid: Optional[str] = None,
        page_size: Optional[int] = None,
        page: Optional[int] = None,
    ) -> str:
        """List SLO configurations with full filter options"""
        params_dict: Dict[str, Any] = {
            "page_size": page_size or 10,
            "page": page or 1,
        }
        if query:
            params_dict["query"] = query
        if slo_status:
            params_dict["slo_status"] = slo_status.upper()
        if entity_type:
            params_dict["entity_type"] = [entity_type]
        if blueprint:
            params_dict["blueprint"] = [blueprint]
        if tag:
            params_dict["tag"] = [tag]
        if kubernetes_cluster_uuid:
            params_dict["kubernetes_cluster_uuid"] = kubernetes_cluster_uuid

        return f"""
        List SLO configurations with full filter options.

        Call:
          manage_slo, resource_type="configuration", operation="get_all",
          params={params_dict}
          → query (optional): {query or '(not specified)'}
          → slo_status (optional): {slo_status.upper() if slo_status else '(not specified)'}
            Valid values: "GOOD" (meeting target), "BREACHING" (violating target). Always uppercase.
          → entity_type (optional): {entity_type or '(not specified)'}
            Must be a JSON list (e.g. ["application"], ["service"], ["website"]).
          → blueprint (optional): {blueprint or '(not specified)'}
            Must be a JSON list (e.g. ["latency"], ["availability"], ["traffic"]).
          → tag (optional): {tag or '(not specified)'}
            Must be a JSON list (e.g. ["production"]).
          → kubernetes_cluster_uuid (optional): {kubernetes_cluster_uuid or '(not specified)'}
          → page_size: {page_size or 10}, page: {page or 1}
          → Note: blueprint, entity_type, tag, and infra_entity_types must be JSON lists.
            slo_status is a plain uppercase string, not a list.

        Output Guidelines:
        - If 0 SLOs are returned, report that no matching SLOs were found and stop
          (do not issue unrequested follow-up queries).
        - The result has no per-SLO "status" field; breaching/good status comes from the
          slo_status filter — state "status confirmed by filter" in the output.
        - Display key identification fields: ID, Name, Target %, Blueprint, Entity Type, Tags.
          Omit deep nested config JSON blobs.
        """

    @auto_register_prompt
    @staticmethod
    def correlate_slo_breach_with_infrastructure(
        tag: Optional[str] = None,
        infra_type: Optional[str] = None,
        time_window_hours: Optional[int] = None,
    ) -> str:
        """Correlate BREACHING SLOs with host/container infrastructure metrics to identify whether infrastructure issues are causing SLO violations"""
        effective_window = time_window_hours or 1
        window_ms = effective_window * 3600000
        granularity_ms = min(window_ms, 300000 if effective_window <= 3 else 3600000)

        # Format list parameters properly for manage_slo schema
        tag_filter = f'["{tag}"]' if tag else "None"
        infra_filter = f'["{infra_type}"]' if infra_type else "None"

        step2_instruction = (
            f'2. Entity plugin type is known as "{infra_type}": proceed directly to Step 3.'
            if infra_type else
            '2. Call manage_infrastructure, resource_type="catalog", operation="get_plugins" '
            'only if plugin type is unknown to discover valid entity types (e.g. "host", "docker", "kubernetesPod").'
        )

        return f"""
        Correlate BREACHING SLOs with host/container infrastructure metrics to identify
        whether infrastructure issues are causing SLO violations.

        Steps:

        1. Call manage_slo, resource_type="configuration", operation="get_all",
           params={{
             "slo_status": "BREACHING",
             "tag": {tag_filter},
             "infra_entity_types": {infra_filter},
             "page_size": 10
           }}
           → 'tag' and 'infra_entity_types' must be JSON lists/arrays (or None if not filtering).
           → Collect per SLO: id, name, target, indicator definition (blueprint + threshold + aggregation),
             entity type, entity filter, and evaluation window (fromTimestamp, toTimestamp).
           → Dedup rule: group SLOs that share the exact same entity scope —
             query infrastructure once per group and reuse results for all members.

        {step2_instruction}

        3. For each SLO group (up to 5 groups max):
           a. Call manage_slo, resource_type="report", operation="get",
              params={{"slo_id": "<slo_id>"}}
              → Collect: SLI value, budget spent vs total, burn rate, fromTimestamp, toTimestamp.
              → Use toTimestamp as timeFrame.to; derive windowSize = toTimestamp - fromTimestamp.
           b. Call manage_infrastructure, resource_type="analyze", operation="get_entity_groups",
              params={{
                "payload": {{
                  "type": "{infra_type or 'host'}",
                  "groupBy": ["host.name"],
                  "metrics": [
                    {{"metric": "cpu.used", "granularity": {granularity_ms}, "aggregation": "MEAN"}},
                    {{"metric": "cpu.used", "granularity": {granularity_ms}, "aggregation": "MAX"}},
                    {{"metric": "memory.used", "granularity": {granularity_ms}, "aggregation": "MAX"}}
                  ],
                  "timeFrame": {{
                    "to": "<toTimestamp_from_step3a>",
                    "windowSize": "<toTimestamp - fromTimestamp>"
                  }},
                  "tagFilterExpression": <slo_entity_tagFilterExpression_or_empty_expression>,
                  "pagination": {{"retrievalSize": 10}}
                }}
              }}
              → Window Note: timeFrame.windowSize is the SLO report span (toTimestamp - fromTimestamp),
                NOT time_window_hours. The granularity {granularity_ms} ms (derived from
                time_window_hours={effective_window} h) controls metric resolution only — it does not
                set the query window.
              → Granularity Rule: windowSize / granularity must be <= 1000. If the SLO report span makes
                the ratio exceed 1000, use granularity 3600000 for all metrics instead.
              → Scope Rule: The API returns up to 10 hosts in alphabetical order (metric-based ordering
                requires granularity=1 and is not used here). Rank the returned hosts yourself by
                cpu.used MAX descending and report the top saturated ones. State "first 10 of <total>
                hosts (alphabetical sample)" in the output table so coverage is clear. Do NOT page
                further.

        4. Correlate:
           - Unit Note: Infrastructure API metric values are 0.0-1.0 fractions (multiply by 100 for %).
           - Compare infrastructure peak utilization against thresholds (CPU MAX > 80%, Memory MAX > 85%)
             during the SLO evaluation window (fromTimestamp → toTimestamp).

        5. Present a summary table:
           SLO Name | Entity Scope | Evaluated Hosts | SLI / Burn Rate | CPU % (Mean/Max) | Memory % (Max) | Correlated Root Cause?
        """

    @auto_register_prompt
    @staticmethod
    def correlate_slo_breach_with_events(
        tag: Optional[str] = None,
        time_window_hours: Optional[int] = None,
    ) -> str:
        """Correlate BREACHING SLOs with open Instana incidents and issues to identify probable root cause"""
        effective_window = time_window_hours or 1
        tag_param = f'["{tag}"]' if tag else "None"
        return f"""
        Correlate BREACHING SLOs with open Instana incidents and issues to identify
        probable root cause.

        Steps:

        1. Call manage_slo, resource_type="configuration", operation="get_all",
           params={{"slo_status": "BREACHING", "tag": {tag_param}, "page_size": 10}}
           → Collect: slo name, id, target, entity definition (applicationId, websiteId, or infraType) for each breaching SLO.

        2. Call manage_events, operation="get_events" (single batch query for the time window):
           params={{
             "filters": {{
               "event_type_filters": ["INCIDENT", "ISSUE"],
               "severity": 10,
               "state": "open",
               "time_range": "last {effective_window} hours",
               "max_events": 50
             }}
           }}
           → Collect: event id, problem description, entity.id, entity.label, start time, state, severity.
           → Note: If an HTTP 5xx occurs, retry once.

        3. Correlate:
           - Match events with breaching SLOs by comparing event entity IDs/labels with the SLO's applicationId, websiteId, or service name.
           - Overlap rule: An event overlaps if event.start_time <= window_end AND (event.end_time is null OR event.end_time >= window_start).

        4. Present a table:
           SLO Name | Entity Target | Correlated Event | Severity | Problem Description | Event State
           → Clearly state how many breaching SLOs and events were evaluated (e.g. "Evaluated top 10 breaching SLOs against 50 recent events").
        """

    @auto_register_prompt
    @staticmethod
    def slo_post_release_impact_analysis(
        release_name: Optional[str] = None,
        release_id: Optional[str] = None,
    ) -> str:
        """Analyze SLO health after a release — fetch the release details, retrieve SLO configs for the affected application, generate reports from release time to now, and identify error budget burns triggered by the deployment"""
        if release_name and not release_id:
            release_lookup = (
                f'1. Look up the release by name: call manage_releases, '
                f'operation="get_all_releases", params={{"name_filter": "{release_name}"}}\n'
                f'   → Select the matching release and note its id and start timestamp.'
            )
        elif release_id:
            release_lookup = (
                f'1. Fetch release details directly: call manage_releases, '
                f'operation="get_release", params={{"release_id": "{release_id}"}}\n'
                f'   → Note the release start timestamp and associated applications.'
            )
        else:
            release_lookup = (
                '1. ERROR: Either release_name or release_id must be provided. '
                'Please supply one of these parameters and retry.'
            )

        return f"""
        Analyze SLO health after a release to identify error budget burns triggered by
        the deployment.

        Note: If both release_name and release_id are provided, release_id takes precedence.

        Steps:

        {release_lookup}

        2. Call manage_slo, resource_type="configuration", operation="get_all",
           params={{
             "entity_type": ["application"],
             "query": "<application_name_from_release>",
             "page_size": 10
           }}
           → Match SLOs where entity.applicationId matches the release application ID (or by name).

        3. For each application SLO, generate the Post-Release Report:
           Call manage_slo, resource_type="report", operation="get",
           params={{"slo_id": "<slo_id>", "var_from": "<release_start_timestamp_or_formatted_date>"}}
           → Accepted formats for var_from: Unix ms timestamp (e.g. 1772794460000) or datetime with timezone ("DD Month YYYY, HH:MM AM/PM|UTC").
           → Window Rule: If release is older than 7 days, cap the evaluation window to 7 days post-release.
           → Collect scalar metrics: SLI, totalErrorBudget, errorBudgetSpent, errorBurnRate (ignore raw chart series).

        4. Generate the Pre-Release Baseline Report:
           Call manage_slo, resource_type="report", operation="get" for each SLO
           with to="<release_start_timestamp>" and var_from="<release_start - duration>" for the exact same duration preceding the release.

        5. Compare & Flag:
           - Flag if post-release burn rate exceeds pre-release rate by > 20% or remaining error budget dropped below 20%.
           - Zero Baseline Rule: If pre-release burn rate was 0 and post-release burn rate > 0, report as "New Error Budget Burn" rather than an undefined percentage delta.

        6. Present a table:
           SLO Name | Pre-Release SLI | Post-Release SLI | Error Budget Spent/Total | Burn Rate (Pre vs Post) | Impact Status
        """

    @auto_register_prompt
    @staticmethod
    def audit_slo_alert_configuration_history(
        slo_name: Optional[str] = None,
        slo_id: Optional[str] = None,
    ) -> str:
        """Retrieve all historical versions of alert configurations linked to a specific SLO for compliance auditing — shows what changed, when, and by whom"""
        if slo_name and not slo_id:
            slo_lookup = (
                f'1. Resolve the SLO by name: call manage_slo, resource_type="configuration", '
                f'operation="get_all", params={{"query": "{slo_name}"}}\n'
                f'   → Select the matching SLO and note its id.'
            )
        elif slo_id:
            slo_lookup = (
                f'1. SLO ID provided directly: "{slo_id}" — skip name resolution and proceed '
                f'to Step 2.'
            )
        else:
            slo_lookup = (
                '1. ERROR: Either slo_name or slo_id must be provided. '
                'Please supply one of these parameters and retry.'
            )

        return f"""
        Retrieve all historical versions of alert configurations linked to a specific SLO
        for compliance auditing.

        Note: If both slo_name and slo_id are provided, slo_id takes precedence.

        Steps:

        {slo_lookup}

        2. Call manage_slo, resource_type="alert", operation="find_active",
           params={{"slo_id": "<resolved_slo_id>"}}
           → Collect: alert config id, name, severity, rule type, sloIds for each alert config associated with this SLO.

        3. For each alert config id collected in Step 2, call (in parallel):
           manage_slo, resource_type="alert", operation="find_versions",
           params={{"id": "<alert_config_id>"}}
           → Collect version summary: created (Unix ms), enabled (boolean), changeSummary.changeType (CREATE/UPDATE/ENABLE/DISABLE), and changeSummary.author.
           → Note: Version summaries contain change metadata. Do not fabricate property-level diffs for UPDATE entries; mark diff as "Not in summary" unless specific versions are fetched via alert.find(id, valid_on=...).

        4. Sort all version entries across all alert configs by created timestamp ascending. Convert timestamps to ISO-8601 UTC or "DD Month YYYY, HH:MM UTC".

        5. Present:
           - Section A: Current alert configs — ID, Name, Severity, Rule Type, Currently Enabled (determined by latest version's enabled field). Flag if config is shared across multiple SLOs.
           - Section B: Chronological change log —
             Timestamp (UTC) | Alert Config ID | Config Name | Change Type | Enabled State | Author
        """

    @auto_register_prompt
    @staticmethod
    def align_correction_windows_with_maintenance(
        slo_name: Optional[str] = None,
        slo_id: Optional[str] = None,
    ) -> str:
        """List all SLO correction windows for a given SLO and cross-reference them with Instana maintenance windows in the same period to verify operational alignment"""
        if slo_name and not slo_id:
            slo_lookup = (
                f'1. Resolve the SLO by name: call manage_slo, resource_type="configuration", '
                f'operation="get_all", params={{"query": "{slo_name}"}}\n'
                f'   → Select the matching SLO and note its id.'
            )
        elif slo_id:
            slo_lookup = (
                f'1. SLO ID provided directly: "{slo_id}" — skip name resolution and proceed '
                f'to Step 2.'
            )
        else:
            slo_lookup = (
                '1. ERROR: Either slo_name or slo_id must be provided. '
                'Please supply one of these parameters and retry.'
            )

        return f"""
        List all SLO correction windows for a given SLO and cross-reference them with
        Instana maintenance windows in the same period to verify operational alignment.

        Note: If both slo_name and slo_id are provided, slo_id takes precedence.

        Steps:

        {slo_lookup}

        2. Call manage_slo, resource_type="correction", operation="get_all",
           params={{"slo_id": ["<resolved_slo_id>"], "page_size": 50}}
           → Collect: correction window name, start time, duration, duration unit, scheduling recurrence, tags.

        3. Call manage_maintenance_windows, resource_type="window", operation="list_all"
           → Collect: maintenance window id, name, start time, end time, query/applications, state.
           → Filtering: Focus on active/scheduled maintenance windows within the evaluation period (e.g. past 30 days) and filter by relevant application/scope. Exclude paused or unscheduled windows.

        4. Analyze Overlap:
           - For recurring correction windows, evaluate active occurrences within the evaluation period rather than expanding infinite recurrences.
           - Note: Maintenance windows contain 'name', 'query', and 'state' (they do not have a 'reason' field).

        5. Flag correction windows that have NO matching maintenance window covering the SLO's application/entity.

        6. Present two tables:
           Table A — Aligned Windows:
             Correction Window Name | Occurrence Start (UTC) | Duration | Overlapping MW Name | MW Scope | MW State
           Table B — Unaligned Correction Windows (no maintenance match):
             Correction Window Name | Occurrence Start (UTC) | Duration | Tags | Action Required
        """

    @auto_register_prompt
    @staticmethod
    def sre_health_overview(
        tag: Optional[str] = None,
        time_window_hours: Optional[int] = None,
    ) -> str:
        """Comprehensive SRE health snapshot: lists all BREACHING SLOs, active alert configurations, correction windows active this period, and open critical incidents. Designed for morning standups or incident triage"""
        effective_window = time_window_hours or 24
        tag_param = f'["{tag}"]' if tag else "None"
        return f"""
        Comprehensive SRE health snapshot for incident triage.
        → tag filter: {tag or '(not specified — include all)'}
        → time window: {effective_window} hour(s)

        Steps (execute in parallel where independent):

        1. [Section 1 — Breaching SLOs]
           Call manage_slo, resource_type="configuration", operation="get_all",
           params={{
             "slo_status": "BREACHING",
             "tag": {tag_param},
             "page_size": 10
           }}
           → Collect: slo name, id, entity definition (applicationId, websiteId, etc.), target,
             blueprint, totalHits.
           → Scope Note: Report top 10 breaching SLOs and display the totalHits count.

        2. [Section 2 — Alert configurations for breaching SLOs]
           For each breaching SLO from Step 1, call manage_slo, resource_type="alert",
           operation="find_active", params={{"slo_id": "<slo_id>"}}
           → Collect and de-duplicate alert configs across all per-SLO calls.
           → Do NOT call find_active without a slo_id filter.
           → Note: Alert configs include 'triggering', 'sloIds', 'severity', and 'rule'
             (no 'enabled' field).

        3. [Section 3 — Correction windows for breaching SLOs]
           Call manage_slo, resource_type="correction", operation="get_all",
           params={{"slo_id": ["<top_breaching_slo_ids>"], "page_size": 10}}
           → Collect: correction window name, start time, duration, linked SLO IDs.

        4. [Section 4 — Open critical incidents]
           Call manage_events, operation="get_events",
           params={{
             "filters": {{
               "event_type_filters": ["INCIDENT"],
               "severity": 10,
               "state": "open",
               "time_range": "last {effective_window} hours",
               "max_events": 20
             }}
           }}
           → Collect: event id, problem description, entity.id, entity.label, start time, state.
           → Window Check: Inspect event 'start' timestamps against the {effective_window}-hour window.

        5. [Correlation Summary]
           Match open incidents against breaching SLOs using applicationId, websiteId, or service targets.

        6. Present results in 4 sections with transparent scope counts (e.g. "Showing top 10 of totalHits"):
           Section 1: Breaching SLOs — SLO Name | Entity Target | Target % | Blueprint | ID
           Section 2: Linked Alert Configs — Alert Name | Severity | Rule Type | Linked SLO IDs
           Section 3: Linked Correction Windows — Window Name | Start | Duration | Linked SLO IDs
           Section 4: Open Critical Incidents — Problem | Entity | Start Time | State
           Correlation Summary: Breaching SLO Name | Correlated Incident | Incident Start
        """

    @auto_register_prompt
    @staticmethod
    def correlate_slo_with_synthetic_tests(
        slo_name: Optional[str] = None,
        slo_id: Optional[str] = None,
        var_from: Optional[str] = None,
        to: Optional[str] = None,
    ) -> str:
        """Fetch the SLO report and corresponding synthetic test pass rates for the same time window to determine whether synthetic monitoring aligns with SLO degradations"""
        if slo_name and not slo_id:
            slo_lookup = (
                f'1. Resolve the SLO by name: call manage_slo, resource_type="configuration", '
                f'operation="get_all", params={{"query": "{slo_name}"}}\n'
                f'   → Select the matching SLO, note its id and entity details (applicationId/websiteId/testId).'
            )
        elif slo_id:
            slo_lookup = (
                f'1. Fetch SLO configuration: call manage_slo, resource_type="configuration", '
                f'operation="get_by_id", params={{"id": "{slo_id}"}}\n'
                f'   → Note its entity definition and target.'
            )
        else:
            slo_lookup = (
                '1. ERROR: Either slo_name or slo_id must be provided. '
                'Please supply one of these parameters and retry.'
            )

        report_params = ['"slo_id": "<resolved_slo_id>"']
        if var_from:
            report_params.append(f'"var_from": "{var_from}"')
        if to:
            report_params.append(f'"to": "{to}"')
        report_params_str = ", ".join(report_params)

        return f"""
        Fetch the SLO report and corresponding synthetic test pass rates for the same time
        window to determine whether synthetic monitoring aligns with SLO degradations.

        Note: If both slo_name and slo_id are provided, slo_id takes precedence.

        Steps:

        {slo_lookup}
          → Also collect entity.syntheticTestIds (list of linked test IDs) and entity.type.

        2. Call manage_slo, resource_type="report", operation="get",
           params={{{report_params_str}}}
           → Collect: SLI value, error budget spent vs total, burn rate, violationDistribution,
             fromTimestamp, toTimestamp.
           → Derive: window_size_ms = toTimestamp - fromTimestamp.
           → bucket_width = window_size_ms / count(keys in violationDistribution).
           → If all buckets are 0 (no violations), the SLO is healthy — skip Steps 3a/3b and
             state "SLO is meeting targets; no synthetic correlation needed".

        3a. If entity.syntheticTestIds is non-empty, call manage_synthetics,
            resource_type="test_playback", operation="get_test_summary_list",
            params={{
              "payload": {{
                "metrics": [{{"metric": "success_rate", "aggregation": "MEAN", "granularity": 600}}],
                "timeFrame": {{
                  "to": <toTimestamp_from_step2>,
                  "windowSize": <window_size_ms_from_step2>
                }},
                "TagFilterExpression": {{
                  "type": "TAG_FILTER",
                  "name": "synthetic.testId",
                  "operator": "EQUALS",
                  "entity": "NOT_APPLICABLE",
                  "stringValue": "<first_id_from_entity.syntheticTestIds>"
                }},
                "pagination": {{"page": 1, "pageSize": 20}}
              }}
            }}
            → If syntheticTestIds has multiple IDs, use an EXPRESSION with logicalOperator "OR".
            → If entity.syntheticTestIds is empty or entity.type is not "synthetic", skip Steps
              3a and 3b and state "no synthetic test link available for this SLO".
            → Collect: per-test overall success_rate (0.0-1.0), locationStatusList,
              totalTestRuns, successRuns.
            → Skip location rows where totalTestRuns = 0 — location was inactive in this window.

        3b. Call manage_synthetics, resource_type="test_playback",
            operation="get_synthetic_result_list",
            params={{
              "payload": {{
                "syntheticMetrics": ["synthetic.metricsStatus", "synthetic.metricsResponseTime"],
                "timeFrame": {{
                  "to": <toTimestamp_from_step2>,
                  "windowSize": <window_size_ms_from_step2>
                }},
                "TagFilterExpression": {{
                  "type": "TAG_FILTER",
                  "name": "synthetic.testId",
                  "operator": "EQUALS",
                  "entity": "NOT_APPLICABLE",
                  "stringValue": "<first_id_from_entity.syntheticTestIds>"
                }},
                "order": {{"by": "start_time", "direction": "DESC"}},
                "pagination": {{"page": 1, "pageSize": 50}}
              }}
            }}
            → Returns one row per individual test run with its start_time and pass/fail status
              (synthetic.metricsStatus: 1 = pass, 0 = fail).
            → Collect: start_time (ms), synthetic.metricsStatus, synthetic.metricsResponseTime
              for each run. This enables per-bucket failure matching.
            → Pagination loop: after each page, check the earliest start_time on that page.
              If earliest start_time > earliest dip bucket start (fromTimestamp + dip_i x bucket_width)
              AND totalHits > page x pageSize, fetch the next page (increment page by 1) and repeat.
              Stop when earliest start_time on the page is <= the earliest dip bucket start,
              or when all pages are exhausted (page x pageSize >= totalHits).
              This ensures runs closest in time to each dip bucket are always fetched.

        4. Correlate:
           - Pass Rate Unit: success_rate is 0.0-1.0 (multiply by 100 for %).
           - Map SLI dip buckets: bucket_i covers
             [fromTimestamp + i x bucket_width, fromTimestamp + (i+1) x bucket_width).
           - Per-bucket matching: a test run falls in bucket_i if
             run.start_time >= bucket_i_start AND run.start_time < bucket_i_end.
             Count failed runs (metricsStatus = 0) per bucket.
           - If a bucket has SLI dips AND contains failed test runs, mark as "correlated".
           - If a bucket has SLI dips but no failed runs, mark as "not correlated — SLO dipped
             without a synthetic failure".
           - If the window is still in progress (toTimestamp > now), note that SLI figures
             are provisional.

        5. Present side by side:
           Time Window | SLI Value (%) | Error Budget (Spent/Total) | Synthetic Test Name | Overall Pass Rate % | Failed Runs in Dip Buckets | Location | Correlation Flag
        """

    @auto_register_prompt
    @staticmethod
    def correlate_slo_with_rum_data(
        slo_name: Optional[str] = None,
        slo_id: Optional[str] = None,
        var_from: Optional[str] = None,
        to: Optional[str] = None,
    ) -> str:
        """Correlate backend SLO performance with Real User Monitoring (RUM) data — identifies whether backend SLI degradations translate into degraded frontend user experience"""
        if slo_name and not slo_id:
            slo_lookup = (
                f'1. Resolve the SLO by name: call manage_slo, resource_type="configuration", '
                f'operation="get_all", params={{"query": "{slo_name}"}}\n'
                f'   → Select the matching SLO, note its id, entity.websiteId, and entity.beaconType.'
            )
        elif slo_id:
            slo_lookup = (
                f'1. Fetch SLO configuration: call manage_slo, resource_type="configuration", '
                f'operation="get_by_id", params={{"id": "{slo_id}"}}\n'
                f'   → Note entity.websiteId, entity.beaconType, and target.'
            )
        else:
            slo_lookup = (
                '1. ERROR: Either slo_name or slo_id must be provided. '
                'Please supply one of these parameters and retry.'
            )

        report_params = ['"slo_id": "<resolved_slo_id>"']
        if var_from:
            report_params.append(f'"var_from": "{var_from}"')
        if to:
            report_params.append(f'"to": "{to}"')
        report_params_str = ", ".join(report_params)

        return f"""
        Correlate backend SLO performance with Real User Monitoring (RUM) data to identify
        whether backend SLI degradations translate into degraded frontend user experience.

        Note: If both slo_name and slo_id are provided, slo_id takes precedence.

        Steps:

        {slo_lookup}
          → Note: Collect entity.websiteId AND entity.beaconType — both required for Step 3.

        2. Call manage_slo, resource_type="report", operation="get",
           params={{{report_params_str}}}
           → Collect: SLI value, error budget spent vs total, burn rate, violationDistribution,
             fromTimestamp, toTimestamp.
           → Derive duration: window_size_ms = toTimestamp - fromTimestamp.

        3. Map entity.beaconType to the RUM query:
           - If entity.beaconType == "httpRequest": use beacon_type "HTTPREQUEST",
             metric "responseTime", aggregation "P95".
           - Otherwise (pageLoad or unrecognised): use beacon_type "PAGELOAD",
             metric "onLoadTime", aggregation "P95".

           Call manage_websites, resource_type="analyze", operation="get_beacon_groups",
           params={{
             "metrics": [{{"metric": "<metric_from_mapping_above>", "aggregation": "P95"}}],
             "group": {{"groupByTag": "beacon.page.name", "groupbyTagEntity": "NOT_APPLICABLE"}},
             "tag_filter_expression": {{
               "type": "TAG_FILTER",
               "name": "beacon.website.id",
               "operator": "EQUALS",
               "entity": "NOT_APPLICABLE",
               "value": "<entity.websiteId_from_step1>"
             }},
             "time_frame": {{
               "windowSize": <window_size_ms_from_step2>
             }},
             "beacon_type": "<beacon_type_from_mapping_above>"
           }}
           → Collect: page name, P95 latency (ms) per page.
           → Window Note: The RUM API may adjust timeframe; compare adjustedTimeframe against
             the SLO window and state any gap.

        4. Correlate:
           - Continuous Breach Rule: If violationDistribution shows violations across all buckets,
             report that the SLO is continuously breached and backend latency is sustained.
           - Compare page P95 latencies against relative baselines: flag pages more than 2x the
             median page latency as elevated.
           - Note: Step 3 returns one aggregate per page across the whole window; per-bucket
             correlation is not possible — state this in the output.

        5. Present a table:
           Time Window | SLI Value (%) | Error Budget (Spent/Total) | Page Name | P95 Latency (ms) | Relative Baseline | Correlation Finding
        """

    @auto_register_prompt
    @staticmethod
    def slo_error_budget_burn_investigation(
        tag: Optional[str] = None,
        days: Optional[int] = None,
    ) -> str:
        """For availability SLOs, retrieve reports over the specified period and cross-reference with infrastructure anomaly events to determine whether infrastructure issues are driving error budget consumption"""
        effective_days = days or 7
        window_ms = effective_days * 86400000
        tag_param = f'["{tag}"]' if tag else "None"
        return f"""
        For availability SLOs, retrieve reports over the specified period and
        cross-reference with infrastructure anomaly events to determine whether
        infrastructure issues are driving error budget consumption.
        → tag filter: {tag or '(not specified — query all availability SLOs)'}
        → period: last {effective_days} day(s) ({window_ms} ms)

        Steps:

        1. Call manage_slo, resource_type="configuration", operation="get_all",
           params={{
             "blueprint": ["availability"],
             "tag": {tag_param},
             "page_size": 10
           }}
           → Collect: slo id, name, target, entity definition (entity.type, entity.applicationId,
             entity.websiteId).
           → Keep only SLOs with entity.type in ["application", "website"]; skip "synthetic" and
             "mobile" entities.
           → Report on the top 10 SLOs by target (highest target %) — or those matching tag if
             supplied. Do not fetch reports for more than 10 SLOs in a single run.

        2. For each selected SLO (max 10), call:
           manage_slo, resource_type="report", operation="get",
           params={{
             "slo_id": "<slo_id>",
             "var_from": <current_time_ms - {window_ms}>
           }}
           → var_from is the window start as a Unix ms integer: subtract {window_ms} ms from the
             current Unix time in milliseconds (e.g. if now = 1792030000000, pass 1792030000000 - {window_ms}).
             The tool accepts epoch ms integers directly — do not convert to a string or date.
           → Collect scalar metrics: sli, totalErrorBudget, errorBudgetSpent, errorBurnRate,
             violationDistribution, fromTimestamp, toTimestamp.
           → bucket_width = (toTimestamp - fromTimestamp) / count(keys in violationDistribution).

        3a. For application SLOs with an entity.applicationId, call:
            manage_applications, resource_type="resources",
            operation="get_application_services",
            params={{"application_id": "<entity.applicationId>"}}
            → Collect service names for use as event entity filters in Step 3b.

        3b. Call manage_events, operation="get_events",
            params={{
              "filters": {{
                "event_type_filters": ["ISSUE", "INCIDENT"],
                "entity_type": "INFRASTRUCTURE",
                "from_time": "<fromTimestamp_from_step2_as_ms>",
                "to_time": "<toTimestamp_from_step2_as_ms>",
                "max_events": 50
              }}
            }}
            → Using from_time/to_time instead of state="open" ensures resolved events within
              the analysis period are included.
            → Collect: event id, problem description, entity.label, start time, end time, severity.

        4. Correlate:
           - Error Budget Spent %: (errorBudgetSpent / totalErrorBudget) x 100 when
             totalErrorBudget > 0. If totalErrorBudget is 0, state "budget denominator is zero —
             percentage undefined". Values above 100% are valid and should be reported as-is.
           - Map burn windows: bucket i covers
             [fromTimestamp + i x bucket_width, fromTimestamp + (i+1) x bucket_width).
           - For application SLOs: match event entity.label against service names from Step 3a.
             If no match is possible, state "correlation is time-based only".
           - Overlap rule: an event overlaps bucket i if event.start_time < bucket_i_end AND
             (event.end_time is null OR event.end_time > bucket_i_start).
           - If an SLO has continuous violations across all buckets, state that time-overlap is
             non-discriminative and list candidate events without a confirmed link.

        5. Present a table:
           SLO Name | Target % | SLI % | Error Budget Spent/Total | Burn Rate | Top Burn Period | Correlated Infra Event | Severity | Root Cause Finding
        """

    @classmethod
    def get_prompts(cls):
        """Return all (name, method) tuples for all prompts defined in this class."""
        return [
            ('get_slo_report_full', cls.get_slo_report_full),
            ('get_slo_configurations_full', cls.get_slo_configurations_full),
            ('correlate_slo_breach_with_infrastructure', cls.correlate_slo_breach_with_infrastructure),
            ('correlate_slo_breach_with_events', cls.correlate_slo_breach_with_events),
            ('slo_post_release_impact_analysis', cls.slo_post_release_impact_analysis),
            ('audit_slo_alert_configuration_history', cls.audit_slo_alert_configuration_history),
            ('align_correction_windows_with_maintenance', cls.align_correction_windows_with_maintenance),
            ('sre_health_overview', cls.sre_health_overview),
            ('correlate_slo_with_synthetic_tests', cls.correlate_slo_with_synthetic_tests),
            ('correlate_slo_with_rum_data', cls.correlate_slo_with_rum_data),
            ('slo_error_budget_burn_investigation', cls.slo_error_budget_burn_investigation),
        ]
