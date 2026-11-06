"""Unit tests for the change-timeline normalize_changes.py helper script."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent.parent / "src" / "skills" / "change-timeline"
SCRIPT = SKILL_DIR / "scripts" / "normalize_changes.py"
SKILL_MD = SKILL_DIR / "SKILL.md"

_spec = importlib.util.spec_from_file_location("normalize_changes", SCRIPT)
nc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nc)

ENVELOPE_KEYS = {
    "scope", "window", "changes", "counts_by_type", "sources_queried", "truncated", "dropped", "notes",
}
RECORD_KEYS = {
    "id", "ts", "type", "title", "detail", "entity", "service_id", "severity", "source_layer", "match_confidence",
}


def _input(**overrides):
    data = {
        "scope": {
            "scope_type": "service",
            "service_id": "svc-1",
            "application_id": None,
            "label": "frontend",
            "kubernetes_cluster_name": "cluster-a",
            "kubernetes_namespace_name": "shop",
        },
        "window": {"from": 1_700_000_000_000, "to": 1_700_086_400_000},
        "sources": {
            "releases": {"releases": []},
            "events": {"events": [], "events_returned": 0},
            "kubernetes_events": {"events": [], "events_count": 0, "events_analyzed": 0, "events_filtered_out": 0},
        },
    }
    data.update(overrides)
    return data


def _event(event_id, ts, service_id="svc-1", label="frontend", type_="change", **extra):
    ev = {
        "eventId": event_id,
        "type": type_,
        "problem": "Deployment changed",
        "detail": "detail text",
        "entity": {"type": "service", "label": label, "serviceId": service_id},
    }
    ev["timestamp" if type_ == "change" else "start"] = ts
    ev.update(extra)
    return ev


class TestScriptExists(unittest.TestCase):
    def test_script_exists_and_is_referenced_by_skill(self):
        self.assertTrue(SCRIPT.exists())
        self.assertIn("scripts/normalize_changes.py", SKILL_MD.read_text(encoding="utf-8"))


class TestEnvelope(unittest.TestCase):
    def test_empty_sources_envelope(self):
        result = nc.normalize(_input())
        self.assertEqual(set(result), ENVELOPE_KEYS)
        self.assertEqual(result["changes"], [])
        self.assertEqual(result["counts_by_type"], {"release": 0, "change_event": 0, "kubernetes_info_event": 0})
        self.assertEqual(result["sources_queried"], ["releases", "events", "kubernetes_events"])
        self.assertFalse(result["truncated"])
        self.assertEqual(result["dropped"], 0)
        self.assertEqual(result["window"]["from_iso"], "2023-11-14T22:13:20Z")

    def test_record_fields_present(self):
        data = _input()
        data["sources"]["events"] = {"events": [_event("e1", 100)]}
        record = nc.normalize(data)["changes"][0]
        self.assertEqual(set(record), RECORD_KEYS)
        self.assertEqual(record["type"], "change_event")
        self.assertEqual(record["source_layer"], "entity")
        self.assertEqual(record["match_confidence"], "exact")


class TestSortingAndDedup(unittest.TestCase):
    def test_sorted_by_ts_then_id(self):
        data = _input()
        data["sources"]["events"] = {"events": [_event("b", 200), _event("c", 100), _event("a", 200)]}
        ids = [r["id"] for r in nc.normalize(data)["changes"]]
        self.assertEqual(ids, ["c", "a", "b"])

    def test_deduplicates_by_type_and_id(self):
        data = _input()
        data["sources"]["events"] = {"events": [_event("a", 100), _event("a", 100)]}
        self.assertEqual(len(nc.normalize(data)["changes"]), 1)

    def test_detail_truncated_to_140(self):
        data = _input()
        data["sources"]["events"] = {"events": [_event("a", 100, detail="x" * 500)]}
        detail = nc.normalize(data)["changes"][0]["detail"]
        self.assertLessEqual(len(detail), 140)
        self.assertTrue(detail.endswith("..."))

    def test_incident_uses_start_and_severity(self):
        data = _input()
        data["sources"]["events"] = {"events": [_event("i1", 500, type_="incident", severity=10)]}
        record = nc.normalize(data)["changes"][0]
        self.assertEqual(record["ts"], 500)
        self.assertEqual(record["severity"], "critical")


class TestReleases(unittest.TestCase):
    def test_exact_case_insensitive_match_only(self):
        data = _input()
        data["sources"]["releases"] = {"releases": [
            {"id": "r1", "name": "rel-1", "start": 10, "scopes": [{"name": "Frontend"}]},
            {"id": "r2", "name": "rel-2", "start": 20, "scopes": [{"name": "k8s-demo-frontend"}]},
        ]}
        result = nc.normalize(data)
        self.assertEqual([r["id"] for r in result["changes"]], ["r1"])
        self.assertEqual(result["counts_by_type"]["release"], 1)
        self.assertTrue(any("rel-2" in n and "out of scope" in n for n in result["notes"]))


class TestEntityFiltering(unittest.TestCase):
    def test_service_id_filter(self):
        data = _input()
        data["sources"]["events"] = {"events": [_event("a", 1), _event("b", 2, service_id="svc-other")]}
        result = nc.normalize(data)
        self.assertEqual([r["id"] for r in result["changes"]], ["a"])
        self.assertTrue(any("dropped as out of scope" in n for n in result["notes"]))

    def test_application_scope_uses_application_id(self):
        data = _input()
        data["scope"].update(scope_type="application", application_id="app-1", service_id=None, label="shop")
        keep = {"eventId": "a", "type": "change", "timestamp": 1, "entity": {"label": "shop", "applicationId": "app-1"}}
        drop = {"eventId": "b", "type": "change", "timestamp": 2, "entity": {"label": "shop", "applicationId": "app-2"}}
        data["sources"]["events"] = {"events": [keep, drop]}
        self.assertEqual([r["id"] for r in nc.normalize(data)["changes"]], ["a"])

    def test_label_fallback_is_exact_and_heuristic(self):
        data = _input()
        no_id = {"eventId": "a", "type": "change", "timestamp": 1, "entity": {"label": "Frontend"}}
        substr = {"eventId": "b", "type": "change", "timestamp": 2, "entity": {"label": "frontend-db"}}
        data["sources"]["events"] = {"events": [no_id, substr]}
        changes = nc.normalize(data)["changes"]
        self.assertEqual([r["id"] for r in changes], ["a"])
        self.assertEqual(changes[0]["match_confidence"], "heuristic")

    def test_non_dict_entity_does_not_crash(self):
        data = _input()
        str_entity = {"eventId": "a", "type": "change", "timestamp": 1, "entity": "frontend"}
        none_entity = {"eventId": "b", "type": "change", "timestamp": 2, "entity": None}
        num_entity = {"eventId": "c", "type": "change", "timestamp": 3, "entity": 12345}
        data["sources"]["events"] = {"events": [str_entity, none_entity, num_entity]}
        changes = nc.normalize(data)["changes"]
        # str_entity matches scope label "frontend" heuristically
        self.assertEqual([r["id"] for r in changes], ["a"])
        self.assertEqual(changes[0]["match_confidence"], "heuristic")

    def test_entity_event_truncation_note(self):
        data = _input()
        data["sources"]["events"] = {"events": [], "events_returned": 50}
        self.assertTrue(any("truncated" in n for n in nc.normalize(data)["notes"]))


class TestKubernetesEvents(unittest.TestCase):
    def _k8s(self, **kw):
        payload = {
            "events": [{"eventId": "k1", "start": 50, "problem": "Pod restarted", "entityLabel": "shop/pod-1"}],
            "events_count": 1, "events_analyzed": 1, "events_filtered_out": 0,
        }
        payload.update(kw)
        return payload

    def test_k8s_records_are_infrastructure_heuristic(self):
        data = _input()
        data["sources"]["kubernetes_events"] = self._k8s()
        result = nc.normalize(data)
        record = result["changes"][0]
        self.assertEqual(record["type"], "k8s_event")
        self.assertEqual(record["source_layer"], "infrastructure")
        self.assertEqual(record["match_confidence"], "heuristic")
        self.assertIsNone(record["service_id"])
        self.assertEqual(result["counts_by_type"]["kubernetes_info_event"], 1)

    def test_unknown_topology_excludes_k8s_from_timeline(self):
        data = _input()
        data["scope"]["kubernetes_cluster_name"] = None
        data["scope"]["kubernetes_namespace_name"] = None
        data["sources"]["kubernetes_events"] = self._k8s()
        result = nc.normalize(data)
        self.assertEqual(result["changes"], [])
        self.assertTrue(any("not verified" in n for n in result["notes"]))

    def test_exact_namespace_matching_drops_adjacent_siblings(self):
        data = _input()
        data["sources"]["kubernetes_events"] = {
            "events": [
                {"eventId": "k1", "start": 50, "problem": "Pod restarted", "entityLabel": "shop/pod-1"},
                {"eventId": "k2", "start": 60, "problem": "Sandbox recreated", "entityLabel": "shop-dev/pod-2"},
                {"eventId": "k3", "start": 70, "problem": "Probe failed", "entityLabel": "shop-dev/pod-3"},
            ],
            "events_count": 3,
            "events_analyzed": 3,
            "events_filtered_out": 0,
        }
        result = nc.normalize(data)
        self.assertEqual([r["id"] for r in result["changes"]], ["k1"])
        self.assertEqual(result["counts_by_type"]["kubernetes_info_event"], 1)
        self.assertTrue(any("Adjacent-namespace events excluded" in n and "shop-dev: 2" in n for n in result["notes"]))

    def test_k8s_tool_cap_truncation_note(self):
        data = _input()
        data["sources"]["kubernetes_events"] = self._k8s(events_count=250, events_analyzed=200)
        notes = nc.normalize(data)["notes"]
        self.assertTrue(any("tool cap" in n and "50 not analyzed" in n for n in notes))

    def test_k8s_api_cap_truncation_note(self):
        data = _input()
        data["sources"]["kubernetes_events"] = self._k8s(events_count=10000, events_analyzed=50)
        notes = nc.normalize(data)["notes"]
        self.assertTrue(any("API cap" in n and "10000" in n for n in notes))
        self.assertFalse(any("tool cap" in n for n in notes))

    def test_filtered_out_note(self):
        data = _input()
        data["sources"]["kubernetes_events"] = self._k8s(events_filtered_out=7)
        notes = nc.normalize(data)["notes"]
        self.assertTrue(any("filter: 7" in n for n in notes))

    def test_literal_unknown_topology_excludes_k8s_from_timeline(self):
        """SKILL.md records the literal string 'unknown'; it must behave like a missing value."""
        data = _input()
        data["scope"]["kubernetes_cluster_name"] = "unknown"
        data["scope"]["kubernetes_namespace_name"] = "unknown"
        data["sources"]["kubernetes_events"] = self._k8s(
            events=[{"eventId": "k9", "start": 50, "problem": "Pod restarted", "entityLabel": "other-ns/pod-9"}],
        )
        result = nc.normalize(data)
        self.assertEqual(result["scope"]["k8s_scope_mode"], "unscoped")
        self.assertEqual(result["changes"], [])
        self.assertEqual(result["counts_by_type"]["kubernetes_info_event"], 0)
        self.assertTrue(any("not verified" in n for n in result["notes"]))
        self.assertFalse(any("cluster-level only" in n for n in result["notes"]))

    def test_literal_unknown_topology_is_null_in_scope(self):
        data = _input()
        data["scope"]["kubernetes_cluster_name"] = "unknown"
        data["scope"]["kubernetes_namespace_name"] = "unknown"
        scope = nc.normalize(data)["scope"]
        self.assertIsNone(scope["kubernetes_cluster_name"])
        self.assertIsNone(scope["kubernetes_namespace_name"])

    def test_unknown_namespace_with_real_cluster_is_cluster_scoped(self):
        data = _input()
        data["scope"]["kubernetes_cluster_name"] = "cluster-a"
        data["scope"]["kubernetes_namespace_name"] = "unknown"
        data["sources"]["kubernetes_events"] = self._k8s()
        result = nc.normalize(data)
        self.assertEqual(result["scope"]["k8s_scope_mode"], "cluster-scoped")
        self.assertEqual([r["id"] for r in result["changes"]], ["k1"])
        self.assertTrue(any("cluster-level only (cluster-a)" in n for n in result["notes"]))

    def test_not_queried_cluster_with_namespace_is_namespace_scoped(self):
        data = _input()
        data["scope"]["kubernetes_cluster_name"] = "not queried (namespace resolved)"
        data["scope"]["kubernetes_namespace_name"] = "shop"
        data["sources"]["kubernetes_events"] = self._k8s()
        result = nc.normalize(data)
        self.assertEqual(result["scope"]["k8s_scope_mode"], "namespace-scoped")
        self.assertEqual(result["scope"]["kubernetes_cluster_name"], "not queried (namespace resolved)")
        self.assertEqual([r["id"] for r in result["changes"]], ["k1"])
        self.assertFalse(any("cluster-level only" in n for n in result["notes"]))

    def test_non_kubernetes_mode_skips_k8s(self):
        data = _input()
        data["scope"]["k8s_scope_mode"] = "non-kubernetes"
        data["scope"]["kubernetes_cluster_name"] = None
        data["scope"]["kubernetes_namespace_name"] = None
        data["sources"]["kubernetes_events"] = self._k8s()
        result = nc.normalize(data)
        self.assertEqual(result["changes"], [])
        self.assertTrue(any("not Kubernetes-backed" in n for n in result["notes"]))
        self.assertFalse(any("unknown" in n for n in result["notes"]))

    def test_cluster_not_queried_when_namespace_resolved(self):
        data = _input()
        data["scope"]["kubernetes_cluster_name"] = "not queried (namespace resolved)"
        data["scope"]["kubernetes_namespace_name"] = "shop"
        result = nc.normalize(data)
        self.assertFalse(any("kubernetes_cluster_name is unknown" in n for n in result["notes"]))


class TestFailuresAndTruncation(unittest.TestCase):
    def test_failed_and_missing_sources_reported(self):
        data = _input()
        data["sources"] = {"releases": {"error": "boom"}, "events": None}
        result = nc.normalize(data)
        self.assertEqual(result["sources_queried"], [])
        self.assertTrue(any("'releases' failed: boom" in n for n in result["notes"]))
        self.assertTrue(any("'events' failed" in n for n in result["notes"]))
        self.assertTrue(any("'kubernetes_events' failed" in n for n in result["notes"]))

    def test_max_changes_truncation_keeps_most_recent(self):
        data = _input(max_changes=2)
        data["sources"]["events"] = {"events": [_event(f"e{i}", i) for i in range(1, 5)]}
        result = nc.normalize(data)
        self.assertEqual([r["id"] for r in result["changes"]], ["e3", "e4"])
        self.assertTrue(result["truncated"])
        self.assertEqual(result["dropped"], 2)


class TestTimestampRobustness(unittest.TestCase):
    def test_safe_int_ts_accepts_numeric_forms(self):
        self.assertEqual(nc._safe_int_ts(1742369820000), 1742369820000)
        self.assertEqual(nc._safe_int_ts(1742369820000.0), 1742369820000)
        self.assertEqual(nc._safe_int_ts("1742369820000"), 1742369820000)
        self.assertEqual(nc._safe_int_ts(" 1742369820.5 "), 1742369820)

    def test_safe_int_ts_returns_zero_for_unusable_values(self):
        for bad in (None, "", "abc", True, [], {}, float("inf"), float("nan")):
            self.assertEqual(nc._safe_int_ts(bad), 0, f"value {bad!r}")

    def test_float_string_and_garbage_timestamps_do_not_crash(self):
        data = _input()
        data["sources"]["events"] = {"events": [
            _event("e1", "1742369820.5"),
            _event("e2", "not-a-number"),
            _event("e3", None),
            _event("e4", 5000),
        ]}
        result = nc.normalize(data)
        by_id = {r["id"]: r["ts"] for r in result["changes"]}
        self.assertEqual(by_id, {"e1": 1742369820, "e2": 0, "e3": 0, "e4": 5000})
        self.assertTrue(any("2 record(s) had a missing or unparseable timestamp" in n for n in result["notes"]))

    def test_release_and_k8s_string_start_do_not_crash(self):
        data = _input()
        data["sources"]["releases"] = {"releases": [
            {"id": "r1", "name": "v1", "start": "1742369820.5", "scopes": [{"name": "frontend"}]},
        ]}
        data["sources"]["kubernetes_events"] = {
            "events": [{"eventId": "k1", "problem": "Pod Crash", "entityLabel": "shop/pod-1", "start": "oops"}],
            "events_count": 1, "events_analyzed": 1, "events_filtered_out": 0,
        }
        result = nc.normalize(data)
        by_id = {r["id"]: r["ts"] for r in result["changes"]}
        self.assertEqual(by_id, {"r1": 1742369820, "k1": 0})

    def test_events_without_id_get_distinct_synthetic_ids(self):
        data = _input()
        e1 = _event(None, 1000)
        e2 = _event(None, 1000, problem="Config changed")
        e3 = _event("", 2000)
        data["sources"]["events"] = {"events": [e1, e2, e3]}
        result = nc.normalize(data)
        self.assertEqual(len(result["changes"]), 3)
        self.assertEqual(len({r["id"] for r in result["changes"]}), 3)
        self.assertNotIn("None", [r["id"] for r in result["changes"]])


class TestCli(unittest.TestCase):
    def test_cli_reads_file_and_prints_envelope(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "in.json"
            path.write_text(json.dumps(_input()), encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = nc.main([str(path)])
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(buf.getvalue())), ENVELOPE_KEYS)

    def test_cli_invalid_input_returns_error(self):
        self.assertEqual(nc.main(["/nonexistent/path.json"]), 1)


if __name__ == "__main__":
    unittest.main()
