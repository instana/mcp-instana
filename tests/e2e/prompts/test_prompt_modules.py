"""Mocked e2e tests for prompt modules that have no e2e coverage."""

import pytest

from src.prompts.application.application_analyze import ApplicationAnalyzePrompts
from src.prompts.application.application_catalog import ApplicationCatalogPrompts
from src.prompts.automation.action_catalog import ActionCatalogPrompts
from src.prompts.automation.action_history import ActionHistoryPrompts
from src.prompts.releases.releases_prompts import ReleasesPrompts
from src.prompts.slo.slo_prompts import SLOPrompts


def _names(prompts):
    return [name for name, _ in prompts]


class TestApplicationAnalyzePromptsE2E:
    """Trace analysis prompt templates."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_registered_prompt_names(self):
        assert _names(ApplicationAnalyzePrompts.get_prompts()) == [
            "get_all_traces",
            "get_trace_details",
            "get_trace_groups",
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_trace_details_includes_trace_id_and_options(self):
        text = ApplicationAnalyzePrompts.get_trace_details(
            "trace-1", retrieval_size=50, offset=10, ingestion_time=1742369820
        )
        assert "trace-1" in text
        assert "50" in text
        assert "10" in text
        assert "1742369820" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_traces_and_groups_return_text(self):
        assert isinstance(ApplicationAnalyzePrompts.get_all_traces(), str)
        assert isinstance(ApplicationAnalyzePrompts.get_trace_groups({"group": "x"}), str)


class TestApplicationCatalogPromptsE2E:
    """Application catalog prompt template."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_registered_prompt_names(self):
        assert _names(ApplicationCatalogPrompts.get_prompts()) == ["app_catalog_yesterday"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_app_catalog_yesterday_embeds_limit_and_filters(self):
        text = ApplicationCatalogPrompts.app_catalog_yesterday(
            limit=5, use_case="GROUPING", data_source="CALLS", var_from=1710658800000
        )
        assert "5" in text
        assert "GROUPING" in text
        assert "CALLS" in text
        assert "1710658800000" in text


class TestActionCatalogPromptsE2E:
    """Automation action catalog prompt templates."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_registered_prompt_names(self):
        assert _names(ActionCatalogPrompts.get_prompts()) == [
            "get_action_matches",
            "get_actions",
            "get_action_details",
            "get_action_types",
            "get_action_tags",
            "get_action_matches_by_id_and_time_window",
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_details_embeds_action_id(self):
        assert "action-42" in ActionCatalogPrompts.get_action_details("action-42")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_simple_catalog_prompts_return_text(self):
        assert isinstance(ActionCatalogPrompts.get_actions(), str)
        assert isinstance(ActionCatalogPrompts.get_action_types(), str)
        assert isinstance(ActionCatalogPrompts.get_action_tags(), str)


class TestActionHistoryPromptsE2E:
    """Automation action history prompt templates."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_registered_prompt_names(self):
        assert _names(ActionHistoryPrompts.get_prompts()) == [
            "submit_automation_action",
            "get_action_instance_details",
            "list_action_instances",
            "delete_action_instance",
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_instance_details_embeds_instance_id(self):
        assert "inst-9" in ActionHistoryPrompts.get_action_instance_details("inst-9")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_embeds_payload(self):
        text = ActionHistoryPrompts.submit_automation_action({"name": "restart"})
        assert "restart" in text


class TestReleasesPromptsE2E:
    """Release management and post-release analysis prompt templates."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_registered_prompt_names(self):
        assert _names(ReleasesPrompts.get_prompts()) == [
            "get_all_releases",
            "get_release",
            "create_release",
            "update_release",
            "delete_release",
            "analyze_application_performance_after_release",
            "check_incidents_after_release",
            "analyze_kpi_evolution_after_release",
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_all_releases_shows_filters(self):
        text = ReleasesPrompts.get_all_releases(name_filter="frontend", page_number=2)
        assert "frontend" in text
        assert "Page number: 2" in text
        assert "(not specified)" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_performance_by_release_name_looks_up_by_name(self):
        text = ReleasesPrompts.analyze_application_performance_after_release(
            release_name="release-2000", application_name="checkout"
        )
        assert "release-2000" in text
        assert "checkout" in text
        assert "name_filter='release-2000'" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_performance_by_release_id_looks_up_by_id(self):
        text = ReleasesPrompts.analyze_application_performance_after_release(
            release_id="rel-1"
        )
        assert "release ID 'rel-1'" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_analyze_performance_without_release_uses_fallback(self):
        text = ReleasesPrompts.analyze_application_performance_after_release()
        assert isinstance(text, str) and text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_release_incident_and_kpi_prompts_return_text(self):
        assert "rel-7" in ReleasesPrompts.check_incidents_after_release(release_id="rel-7")
        assert isinstance(ReleasesPrompts.analyze_kpi_evolution_after_release(), str)


class TestSLOPromptsE2E:
    """SLO report, configuration and correlation prompt templates."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_registered_prompt_names(self):
        assert _names(SLOPrompts.get_prompts()) == [
            "get_slo_report_full",
            "get_slo_configurations_full",
            "correlate_slo_breach_with_infrastructure",
            "correlate_slo_breach_with_events",
            "slo_post_release_impact_analysis",
            "audit_slo_alert_configuration_history",
            "align_correction_windows_with_maintenance",
            "sre_health_overview",
            "correlate_slo_with_synthetic_tests",
            "correlate_slo_with_rum_data",
            "slo_error_budget_burn_investigation",
        ]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_full_includes_only_provided_filters(self):
        text = SLOPrompts.get_slo_report_full(
            slo_id="slo-123", var_from="10 March 2026, 2:00 PM|IST"
        )
        assert "slo-123" in text
        assert "10 March 2026, 2:00 PM|IST" in text
        assert "'exclude_correction_id'" not in text
        assert "'var_from': '10 March 2026, 2:00 PM|IST'" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_slo_report_full_includes_correction_filters(self):
        text = SLOPrompts.get_slo_report_full(
            slo_id="slo-9", exclude_correction_id="c-1", include_correction_id="c-2"
        )
        assert "c-1" in text
        assert "c-2" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_correlation_prompts_return_text(self):
        assert isinstance(SLOPrompts.sre_health_overview(), str)
        assert isinstance(SLOPrompts.slo_error_budget_burn_investigation(), str)
        assert isinstance(SLOPrompts.correlate_slo_with_rum_data(), str)
