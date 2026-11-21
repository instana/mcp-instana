"""Mocked e2e tests for SLO prompt branches not covered by test_prompt_modules.py."""

import pytest

from src.prompts.slo.slo_prompts import SLOPrompts


class TestSLOReportAndConfigPromptsE2E:
    """get_slo_report_full / get_slo_configurations_full parameter handling."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_includes_to_and_correction_lists(self):
        text = SLOPrompts.get_slo_report_full(
            slo_id="slo-1", to="11 March 2026, 1:00 PM|UTC",
            exclude_correction_id="c-1", include_correction_id="c-2",
        )
        assert "'to': '11 March 2026, 1:00 PM|UTC'" in text
        assert "'exclude_correction_id': ['c-1']" in text
        assert "'include_correction_id': ['c-2']" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_report_defaults_when_no_optional_filters(self):
        text = SLOPrompts.get_slo_report_full(slo_id="slo-2")
        assert "defaults to SLO window start" in text
        assert "defaults to current time" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configurations_defaults(self):
        text = SLOPrompts.get_slo_configurations_full()
        assert "'page_size': 10" in text
        assert "'page': 1" in text
        assert "'query'" not in text
        assert "(not specified)" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_configurations_all_filters_are_embedded_as_lists(self):
        text = SLOPrompts.get_slo_configurations_full(
            query="checkout", slo_status="breaching", entity_type="application",
            blueprint="latency", tag="prod", kubernetes_cluster_uuid="uuid-1",
            page_size=25, page=3,
        )
        assert "'query': 'checkout'" in text
        assert "'slo_status': 'BREACHING'" in text
        assert "'entity_type': ['application']" in text
        assert "'blueprint': ['latency']" in text
        assert "'tag': ['prod']" in text
        assert "'kubernetes_cluster_uuid': 'uuid-1'" in text
        assert "'page_size': 25" in text
        assert "'page': 3" in text


class TestSLOCorrelationPromptsE2E:
    """Infrastructure and event correlation prompts."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_infrastructure_defaults(self):
        text = SLOPrompts.correlate_slo_breach_with_infrastructure()
        assert '"tag": None' in text
        assert '"infra_entity_types": None' in text
        assert 'operation="get_plugins"' in text
        assert '"type": "host"' in text
        assert '"granularity": 300000' in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_infrastructure_with_tag_type_and_short_window(self):
        text = SLOPrompts.correlate_slo_breach_with_infrastructure(
            tag="prod", infra_type="docker", time_window_hours=2
        )
        assert '"tag": ["prod"]' in text
        assert '"infra_entity_types": ["docker"]' in text
        assert 'Entity plugin type is known as "docker"' in text
        assert '"type": "docker"' in text
        assert "time_window_hours=2 h" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_infrastructure_long_window_uses_hourly_granularity(self):
        text = SLOPrompts.correlate_slo_breach_with_infrastructure(time_window_hours=6)
        assert '"granularity": 3600000' in text
        assert '"granularity": 300000' not in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_events_defaults_and_tag(self):
        default = SLOPrompts.correlate_slo_breach_with_events()
        assert '"tag": None' in default
        assert "last 1 hours" in default

        tagged = SLOPrompts.correlate_slo_breach_with_events(tag="payments", time_window_hours=12)
        assert '"tag": ["payments"]' in tagged
        assert "last 12 hours" in tagged


class TestSLOLookupPromptsE2E:
    """Prompts that resolve an SLO or release by name, id or neither."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_post_release_by_name(self):
        text = SLOPrompts.slo_post_release_impact_analysis(release_name="rel-1")
        assert 'operation="get_all_releases"' in text
        assert '"name_filter": "rel-1"' in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_post_release_id_takes_precedence(self):
        text = SLOPrompts.slo_post_release_impact_analysis(release_name="rel-1", release_id="id-9")
        assert 'operation="get_release"' in text
        assert '"release_id": "id-9"' in text
        assert 'operation="get_all_releases"' not in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_post_release_without_identifier_reports_error(self):
        text = SLOPrompts.slo_post_release_impact_analysis()
        assert "ERROR: Either release_name or release_id must be provided" in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_audit_alert_history_lookup_variants(self):
        by_name = SLOPrompts.audit_slo_alert_configuration_history(slo_name="Checkout SLO")
        assert '"query": "Checkout SLO"' in by_name

        by_id = SLOPrompts.audit_slo_alert_configuration_history(slo_name="x", slo_id="slo-5")
        assert 'SLO ID provided directly: "slo-5"' in by_id
        assert '"query": "x"' not in by_id

        missing = SLOPrompts.audit_slo_alert_configuration_history()
        assert "ERROR: Either slo_name or slo_id must be provided" in missing

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_align_correction_windows_lookup_variants(self):
        by_name = SLOPrompts.align_correction_windows_with_maintenance(slo_name="Checkout SLO")
        assert '"query": "Checkout SLO"' in by_name

        by_id = SLOPrompts.align_correction_windows_with_maintenance(slo_id="slo-6")
        assert 'SLO ID provided directly: "slo-6"' in by_id

        missing = SLOPrompts.align_correction_windows_with_maintenance()
        assert "ERROR: Either slo_name or slo_id must be provided" in missing


class TestSLOHealthPromptsE2E:
    """sre_health_overview and error budget investigation parameters."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_sre_health_overview_defaults_and_overrides(self):
        default = SLOPrompts.sre_health_overview()
        assert "time window: 24 hour(s)" in default
        assert '"tag": None' in default
        assert "not specified" in default

        custom = SLOPrompts.sre_health_overview(tag="prod", time_window_hours=4)
        assert "tag filter: prod" in custom
        assert '"tag": ["prod"]' in custom
        assert "last 4 hours" in custom

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_error_budget_burn_defaults_and_overrides(self):
        default = SLOPrompts.slo_error_budget_burn_investigation()
        assert "last 7 day(s) (604800000 ms)" in default
        assert '"tag": None' in default

        custom = SLOPrompts.slo_error_budget_burn_investigation(tag="gold", days=2)
        assert "last 2 day(s) (172800000 ms)" in custom
        assert '"tag": ["gold"]' in custom


class TestSLOCrossDomainPromptsE2E:
    """Synthetic and RUM correlation prompts."""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_synthetic_correlation_lookup_variants(self):
        by_name = SLOPrompts.correlate_slo_with_synthetic_tests(slo_name="Login SLO")
        assert '"query": "Login SLO"' in by_name
        assert '"slo_id": "<resolved_slo_id>"' in by_name

        by_id = SLOPrompts.correlate_slo_with_synthetic_tests(slo_id="slo-7")
        assert 'operation="get_by_id"' in by_id
        assert '"id": "slo-7"' in by_id

        missing = SLOPrompts.correlate_slo_with_synthetic_tests()
        assert "ERROR: Either slo_name or slo_id must be provided" in missing

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_synthetic_correlation_time_window_params(self):
        text = SLOPrompts.correlate_slo_with_synthetic_tests(
            slo_id="slo-7", var_from="1 March 2026, 1:00 PM|UTC", to="2 March 2026, 1:00 PM|UTC"
        )
        assert '"var_from": "1 March 2026, 1:00 PM|UTC"' in text
        assert '"to": "2 March 2026, 1:00 PM|UTC"' in text

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rum_correlation_lookup_variants(self):
        by_name = SLOPrompts.correlate_slo_with_rum_data(slo_name="Web SLO")
        assert '"query": "Web SLO"' in by_name

        by_id = SLOPrompts.correlate_slo_with_rum_data(slo_id="slo-8")
        assert '"id": "slo-8"' in by_id
        assert "entity.websiteId" in by_id

        missing = SLOPrompts.correlate_slo_with_rum_data()
        assert "ERROR: Either slo_name or slo_id must be provided" in missing

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_rum_correlation_time_window_params(self):
        text = SLOPrompts.correlate_slo_with_rum_data(
            slo_id="slo-8", var_from="1 March 2026, 1:00 PM|UTC", to="2 March 2026, 1:00 PM|UTC"
        )
        assert '"var_from": "1 March 2026, 1:00 PM|UTC"' in text
        assert '"to": "2 March 2026, 1:00 PM|UTC"' in text
