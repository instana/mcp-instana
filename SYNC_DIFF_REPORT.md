# Sync Diff Report: Internal → Public Repo

**Source (internal):** `/Users/jaysharma/Documents/mcp-refactoring/mcp-instana-ibm`  
**Target (public):** `/Users/jaysharma/Documents/GitHub/mcp-instana-public` (this repo)  
**Generated:** 2025-07-09

---

## Summary

| Category | Count |
|---|---|
| Files only in internal (must be copied to public) | 12+ |
| Files only in public (internal-specific, keep as-is or evaluate) | 8+ |
| Files differing (internal has newer content) | 50+ |
| Internal-only directories | `src/admin/`, `evaluation/`, `dev/`, `ibm-internal-only/` |

---

## 1. New Files in Internal Repo — Need to Copy to Public

These files exist **only in the internal repo** and contain new features/functionality that should be synced to public:

### Source Code

| File | Description |
|---|---|
| `src/core/launcher.py` | New launcher process manager — starts both MCP server + admin HTTP server as separate processes with graceful shutdown, health monitoring, and `LOG_LEVEL` env var support |
| `src/core/metric_validation.py` | New pre-flight validation module for website/mobile app analyze queries — validates beacon types, metric catalog compatibility, and aggregations before API calls |
| `src/mobile_app/mobile_app_session_replay.py` | New session replay tool — `get_session_replay_action_beacons` with cursor-based pagination, `NaN` cleaning, and full parameter validation |
| `src/router/infrastructure_smart_router_tool.py` | New unified smart router for infrastructure — replaces direct `InfrastructureAnalyze` with a single tool covering `analyze`, `catalog`, and `resources` resource types |
| `src/admin/admin_server.py` | New admin HTTP server (FastAPI-based) for health checks and admin operations |
| `src/prompts/application/application_analyze.py` | New prompt file for application analyze workflows |
| `Dockerfile.public` | Public-flavored Dockerfile (simpler, no IBM internal registry) |
| `start.sh` | Container startup script that reads config YAML, parses ports with `yq`, exports `PORT`/`ADMIN_PORT`/`LOG_LEVEL`, then starts the launcher |

### Config / Build Files

| File | Description |
|---|---|
| `requirements.txt` | Explicit requirements file (generated from uv.lock) used in Docker builds |
| `requirements-extras.txt` | Extra requirements for development/testing |
| `sonar-project.properties` | SonarQube configuration |
| `.secrets.baseline` | detect-secrets baseline file |
| `.sonar.setup.bash` | SonarQube setup script |
| `.whitesource` | WhiteSource/Mend security scanning config |
| `release-number` | Release number tracking file |

### Internal-Only Directories (Do NOT copy to public)

| Directory | Reason |
|---|---|
| `ibm-internal-only/` | IBM-internal configs/docs — must not be in public repo |
| `evaluation/` | Evaluation scripts/results — internal use only |
| `dev/` | Developer scripts — internal use only |
| `.sps/` | IBM SPS pipeline config — internal only |
| `tests/admin/` | Admin server tests (depends on `src/admin/admin_server.py`) |

---

## 2. Files Only in Public Repo — Evaluate / Keep

These files exist **only in the public repo** and are not in internal:

| File | Action |
|---|---|
| `CONTRIBUTING.md` | Public-specific contribution guide — keep as-is |
| `.github/dco.yml` | DCO check for public GitHub — keep |
| `.github/workflows/` | Public CI/CD workflows — keep |
| `schema/` | JSON schema directory — may be removed per internal `pyproject.toml` change (no longer in `packages`) |
| `src/infrastructure/elicitation_handler.py` | Old Option 2 elicitation handler — replaced by `infrastructure_smart_router_tool.py` in internal |
| `src/infrastructure/entity_registry.py` | Old Option 2 entity registry — replaced by smart router |
| `src/infrastructure/infrastructure_analyze_old.py` | Archived old analyze tool — can be removed |
| `dist/` | Built distribution artifacts — should be in `.gitignore` |

---

## 3. Modified Files — Detailed Diff Summary

### 3.1 `pyproject.toml` — Version & Dependencies

| Change | Internal Value | Public Value |
|---|---|---|
| **Version** | `0.12.76` | `0.9.9` |
| `requires-python` | `>=3.10,<=3.14.6` | `>=3.10,<3.15` |
| `instana-client` | `==1.0.9` | `==1.0.8` |
| New deps | `fastapi`, `uvicorn` (for admin server) | — |
| New test deps | `httpx` (for TestClient) | — |
| `packages` | `["src"]` | `["src", "schema"]` |
| Removed lint rules | — | `PLC0415`, `B017` removed from ignore list |
| Author list | Removed `Riya Kumari` entry | Includes `Riya Kumari` |

**Action:** Update `pyproject.toml` — bump version, add `fastapi`/`uvicorn`/`httpx`, update `instana-client`, remove `schema` from packages, update `requires-python`.

---

### 3.2 `Dockerfile` — Complete Rewrite (IBM Internal)

The internal `Dockerfile` uses IBM-specific base images (`icr.io/instana-int/...`) and is **not suitable for public**. The internal repo includes a separate `Dockerfile.public` for the public version.

**Action:** Copy `Dockerfile.public` from internal as the public `Dockerfile` (or sync specific improvements like the health check change from `requests` to `urllib.request`).

Key relevant change for public:
```diff
- CMD python -c "import requests; requests.get('http://127.0.0.1:8080/health', timeout=5)" || exit 1
+ CMD python3.11 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5)" || exit 1
```

---

### 3.3 `src/core/server.py` — Server Initialization & Configuration

Key changes in the internal version:

1. **LOG_LEVEL from environment** — reads `LOG_LEVEL` env var before `basicConfig` so container config drives log verbosity:
   ```python
   log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
   logging.basicConfig(level=log_level)
   ```

2. **Infrastructure smart router replaces direct analyze tool** — the `infra_analyze_new_client` field is renamed to `smart_router_infrastructure_client` and the class changes from `InfrastructureAnalyze` → `InfrastructureSmartRouterMCPTool`.

3. **New infrastructure prompts registered** — `InfrastructureAnalyzePrompts` and `InfrastructureCatalogPrompts` are now loaded.

4. **Prompt registration reordering** — infrastructure prompts added to the `"infra"` category alongside analyze/catalog.

5. **`--tools` help text updated** — now includes `releases` and `maintenance` categories.

6. **Default `--log-level` reads env var** — `default=os.getenv("LOG_LEVEL", "INFO")`.

---

### 3.4 `src/core/utils.py` — Shared Utilities & Refactoring

Major additions/changes:

1. **New `parse_payload()` function** — centralized payload parsing (dict/JSON string/Python literal) with graceful error handling. Previously duplicated in multiple tool files.

2. **New beacon type maps added as module-level constants:**
   ```python
   WEBSITE_BEACON_TYPE_MAP = {"PAGELOAD": "pageLoad", "PAGE_CHANGE": "pageChange", ...}
   MOBILE_BEACON_TYPE_MAP = {"SESSION_START": "sessionStart", "VIEW_CHANGE": "viewChange", ...}
   ```

3. **`extract_tag_names_from_tree()` refactored** — extracted into two private helpers (`_extract_tag_name_from_dict`, `_process_dict_children`) and updated to support multiple catalog formats (infrastructure, website, mobile app) including `tagTree` and `tags` array structures.

4. **Import reordering** — `from src.core.api_headers import build_instana_api_headers` moved to top-level imports.

5. **Trailing whitespace normalization** — many blank lines changed from `\n` to `\n    ` (trailing space on empty lines), which is a code style difference.

6. **`__version__`** — internal shows `0.9.6`, public shows `0.9.9` (internal has a different version tracking mechanism).

---

### 3.5 `src/core/api_headers.py` — Minor Style

Only trailing-whitespace differences and one f-string consistency fix:
```diff
- raise ValueError("Cookie name contains invalid characters...")
+ raise ValueError(f"Cookie name contains invalid characters...")
```

---

### 3.6 `src/core/timestamp_utils.py` — Blank Line Only

Only a leading blank line difference (extra blank line in public).

---

### 3.7 `src/core/alert_config_utils.py` — Trailing Whitespace Only

Only trailing-whitespace style differences.

---

### 3.8 `src/infrastructure/infrastructure_analyze.py` — Complete Rewrite

The public repo uses the **old "Option 2 / Two-Pass elicitation architecture"** while the internal repo has completely rewritten this file to use **direct SDK calls**.

**Internal architecture:**
- Class renamed: `InfrastructureAnalyze` → `InfrastructureAnalyzeMCPTools`
- Removed: `ElicitationHandler`, `EntityCapabilityRegistry`, schema directory resolution, `analyze_infrastructure` two-pass tool
- Added 4 new direct SDK methods:
  - `get_available_metrics(payload)` — wraps `GetAvailableMetricsQuery`
  - `get_entities(payload)` — wraps `GetInfrastructureQuery` with auto tagFilterExpression normalization
  - `get_aggregated_entity_groups(payload)` — wraps `GetInfrastructureGroupsQuery`
  - `get_available_plugins(payload)` — wraps `GetAvailablePluginsQuery`
- New `_normalize_tag_filter_expression()` helper — converts `TAG_FILTER` → `EXPRESSION` envelope, normalizes value fields (`value` → `stringValue`/`numberValue`/`booleanValue`)
- All methods accept `payload` as `Dict | str` and use shared `parse_payload()` from `utils.py`

**Action:** Full file replacement. The old elicitation approach (`elicitation_handler.py`, `entity_registry.py`) should be removed and replaced with the new `InfrastructureAnalyzeMCPTools` + `InfrastructureSmartRouterMCPTool` pattern.

---

### 3.9 `src/infrastructure/infrastructure_catalog.py` — Significant Changes

1. **`get_infrastructure_catalog_metrics()`** — switches from `get_infrastructure_catalog_metrics()` to `get_infrastructure_catalog_metrics_without_preload_content()`, reads raw HTTP response, parses JSON manually. Return type changed from `List[str]` → `Dict[str, Any]`. Refactored with helpers: `_extract_metric_name_from_item`, `_process_metrics_list`, `_handle_list_result`, `_handle_dict_result`, `_handle_sdk_object_result`.

2. **`get_infrastructure_catalog_plugins()`** — completely rewritten to return a **hardcoded static list of 422 plugin IDs** instead of making an API call. This avoids API overhead for a mostly-static resource.

3. **`get_infrastructure_catalog_plugins_with_custom_metrics()`** — switches to `_without_preload_content` variant.

4. **NEW `get_plugin_schema(plugin, filter)`** — combines `get_infrastructure_catalog_metrics` + `get_tag_catalog` into one call, returns `{metrics, tags, errors, summary}`. Reduces LLM tool calls.

5. **`get_tag_catalog()`** — switches to `_without_preload_content` variant.

6. **`get_infrastructure_catalog_search_fields()`** — switches to `_without_preload_content` variant, parses raw JSON.

7. **Import cleanup** — removed unused `ApiClient`, `Configuration` imports; added `extract_tag_names_from_tree` import.

---

### 3.10 `src/router/infrastructure_smart_router_tool.py` — New File (Internal Only → Public)

New unified smart router class `InfrastructureSmartRouterMCPTool` that:
- Supports `resource_type`: `analyze`, `catalog`, `resources`
- `analyze`: `get_entities`, `get_entity_groups` with auto-routing based on `groupBy` presence in payload
- `catalog`: `get_plugins`, `get_metrics`, `get_tag_catalog`, `get_plugin_schema`
- `resources`: `get_snapshot`, `get_snapshots`
- Uses `HINT_GET_PLUGINS_FIRST` constant to guide LLMs toward correct workflow
- Detailed docstring with 3-step workflow guide

**Action:** Copy this file to public repo (replacing/removing old `infrastructure_analyze.py` tool registration).

---

### 3.11 `src/router/mobile_app_smart_router.py` — Session Replay Support

1. **New `session_replay` resource type** added — routes to `MobileAppSessionReplayMCPTools`
2. **`MOBILE_BEACON_TYPE_MAP` imported from `utils.py`** instead of inline dict
3. **New constants:** `SESSION_REPLAY_VALID_OPERATIONS`, `PARAM_SESSION_ID`, `PARAM_CURSOR`, `PARAM_PAGE_SIZE`, `PARAM_FILTER_FIELDS`
4. **`_handle_analyze()`** gains `filter_fields` parameter, passes it to `get_all_mobile_app_beacons`
5. **New `_handle_session_replay()` method** — routes `get_session_replay_action_beacons`
6. **Tool description updated** with session replay documentation, `ANALYZE WORKFLOW` vs general workflow decision tree, and detailed pagination rules for session replay

---

### 3.12 `src/mobile_app/mobile_app_analyze.py` — Metric Validation

1. **New metric compatibility validation block** — after other pre-flight checks, validates beacon type + metrics against catalog using `metric_validation.py` functions
2. **`filter_fields` parameter** added to `_validate_and_normalize_params`, with default `True`
3. Import style cleanup (multi-line → single-line imports)

---

### 3.13 `src/mobile_app/mobile_app_session_replay.py` — New File

Full new module. See §1 "New Files" above for description.

---

### 3.14 `src/website/website_analyze.py` — Metric Validation

New metric compatibility validation block added (same pattern as mobile app):
- Tracks `user_provided_metrics` flag
- Validates beacon type using `WEBSITE_BEACON_TYPE_MAP`
- Fetches metric catalog via `fetch_metric_catalog_internal`
- Validates metric compatibility with `validate_metric_compatibility`
- New field keys added: `stackTrace`, `parsedStackTrace`, `errorId`, `stackTraceReadability`, `sessionId`, `backendTraceId`

---

### 3.15 `src/website/website_catalog.py` — Import Style

Single-line vs multi-line imports (functional equivalence only, no logic change).

---

### 3.16 `src/website/website_alert.py` — Import Style + EOF

Import style cleanup (multi-line → single-line) and missing EOF newline added.

---

### 3.17 `src/event/events_tools.py` — Event Filtering Improvements

1. **Removed `has_get_events_id_query` flag** — try/except import block removed
2. **New `entity_label` field** added to event filter structure (alongside `entity_name`)
3. **New `rca` filter field** — `rca` filter field added with `None` check (not truthy check)
4. **Filter matching refactored** — explicit if-chain replaced with `filter_checks` list of `(value, lambda)` tuples; `rca` uses `_matches_rca()` method

---

### 3.18 `src/application/application_resources.py` — New Operations

New `execute_resources_operation()` dispatcher method added supporting:
- `get_applications(name_filter, application_boundary_scope)`
- `get_services(name_filter, include_snapshot_ids)`
- `get_application_services(application_id, service_id, ...)`
- `get_application_endpoints(application_id, service_id, endpoint_id, ...)`

Called by `application_smart_router_tool.py` for the new `resources` resource type.

---

### 3.19 `src/router/application_smart_router_tool.py` — Resources Resource Type

1. **New `resources` resource type** — routes to `execute_resources_operation()` in `application_resources.py`
2. **Operations:** `get_applications`, `get_services`, `get_application_services`, `get_application_endpoints`
3. **Tag filter entity field documentation** — added detailed documentation for `SOURCE`/`DESTINATION`/`NOT_APPLICABLE` entity field values
4. **`settings` resource type scope** — narrowed from `application, endpoint, service, manual_service` to just `application`

---

### 3.20 `src/slo/slo_alert_config.py` — Payload Parsing & Required Fields

1. **`parse_payload()` imported from `utils.py`** — replaces local `_parse_payload()` method
2. **`apdexIds` field added** — `apdexIds=request_body.get("apdexIds", [])` added to create/update calls (required field per API, mutually exclusive with `sloIds`)

---

### 3.21 `src/core/metric_validation.py` — New File

Full new module for pre-flight metric validation. See §1 "New Files" above.

---

### 3.22 `src/prompts/application/application_resources.py` — New Prompt Methods

New prompt methods added:
- `get_applications()` — returns application perspectives prompt
- `get_services()` — returns services prompt
- `get_application_services()` — returns application-scoped services prompt
- `get_application_endpoints()` — returns endpoints prompt

---

### 3.23 `src/prompts/application/application_analyze.py` — New File

New prompts file for application analyze operations (only in internal).

---

### 3.24 `CHANGELOG.md` — Internal vs Public Versioning

The internal changelog starts at `0.12.5` (latest) and goes down, while the public stops at `0.9.8`. The internal history covers versions `0.10.0` through `0.12.5` that are not in the public repo.

**Action:** Merge internal changelog entries (versions `0.10.0`–`0.12.76`) into public `CHANGELOG.md` after filtering out any IBM-internal references.

---

### 3.25 `.gitignore` — Different Patterns

| Internal adds | Public adds |
|---|---|
| `.build/`, `report.xml` (IBM DevSecOps pipeline) | `.ruff_cache/`, `.venv`, `.Bob/`, `.vscode/`, `mcp-instana.mcpb`, UV comment block, `.pypirc` |

**Action:** Merge patterns — add `.ruff_cache/`, `.venv`, `.Bob/`, `.vscode/`, `mcp-instana.mcpb` to public's `.gitignore`.

---

### 3.26 `conftest.py` — Trailing Blank Line Only

One extra leading blank line in public version. No logic change.

---

### 3.27 Other Prompt Files (Minor/Style Changes)

The following prompt files have only minor differences (import style, trailing whitespace):

| File | Change |
|---|---|
| `src/prompts/automation/action_history.py` | Minor style |
| `src/prompts/events/events_tools.py` | Minor style |
| `src/prompts/mobile_app/mobile_app_alert.py` | Minor style |
| `src/prompts/mobile_app/mobile_app_analyze.py` | Minor style |
| `src/prompts/mobile_app/mobile_app_configuration.py` | Minor style |
| `src/prompts/releases/releases_prompts.py` | Minor style |
| `src/prompts/website/website_alert.py` | Minor style |

---

### 3.28 Test Files (Multiple)

Many test files differ due to the new/refactored source code. Key additions:

| Test File (Internal Only) | Covers |
|---|---|
| `tests/admin/` | New admin server tests |
| `tests/core/test_launcher.py` | `launcher.py` tests |
| `tests/core/test_metric_catalog_fetch.py` | Metric catalog fetch tests |
| `tests/core/test_metric_validation.py` | `metric_validation.py` tests |
| `tests/mobile_app/test_mobile_app_session_replay.py` | Session replay tests |
| `tests/prompts/application/test_application_analyze.py` | Application analyze prompt tests |
| `tests/prompts/application/test_application_analyze_prompts.py` | Additional analyze prompt tests |
| `tests/e2e/application/test_application_analyze.py` | E2E application analyze tests |

Existing test files also updated to reflect refactored APIs (e.g., changed imports, updated assertions for new return types like `Dict` vs `List`).

---

## 4. Files to Ignore (Not Sync)

The following files should **not** be synced from internal to public:

| File/Directory | Reason |
|---|---|
| `ibm-internal-only/` | IBM internal documentation |
| `.secrets.baseline` | IBM DevSecOps tooling |
| `.sonar.setup.bash`, `sonar-project.properties` | IBM SonarQube configuration |
| `.sps/` | IBM SPS pipeline |
| `.whitesource` | IBM Mend security scanning |
| `evaluation/` | Internal evaluation scripts |
| `dev/` | Internal developer scripts |
| `release-number` | IBM release tracking |
| `.github/pull_request_template.md` | IBM internal PR template |
| `contributing.md` (internal lowercase) | IBM-specific contribution guide |
| `coverage.xml`, `htmlcov/` | Build artifacts |
| `tests/admin/` | Depends on `src/admin/` (needs admin server in public first) |

---

## 5. Recommended Sync Order

1. **Update `pyproject.toml`** — bump version to `0.12.76`, add deps (`fastapi`, `uvicorn`, `httpx`), update `instana-client` to `1.0.9`, update `requires-python`
2. **Copy new source files:**
   - `src/core/launcher.py`
   - `src/core/metric_validation.py`
   - `src/mobile_app/mobile_app_session_replay.py`
   - `src/router/infrastructure_smart_router_tool.py`
   - `src/admin/__init__.py` + `src/admin/admin_server.py`
   - `src/prompts/application/application_analyze.py`
3. **Update existing source files** (major changes):
   - `src/infrastructure/infrastructure_analyze.py` (full rewrite)
   - `src/infrastructure/infrastructure_catalog.py`
   - `src/core/server.py`
   - `src/core/utils.py`
   - `src/router/mobile_app_smart_router.py`
   - `src/router/application_smart_router_tool.py`
   - `src/application/application_resources.py`
   - `src/slo/slo_alert_config.py`
   - `src/mobile_app/mobile_app_analyze.py`
   - `src/website/website_analyze.py`
   - `src/event/events_tools.py`
4. **Remove obsolete files:**
   - `src/infrastructure/elicitation_handler.py`
   - `src/infrastructure/entity_registry.py`
   - `src/infrastructure/infrastructure_analyze_old.py`
   - `schema/` directory (if removing from `packages`)
5. **Update `CHANGELOG.md`** — add internal versions `0.10.0`–`0.12.76`
6. **Update `.gitignore`** — add missing patterns
7. **Add/update test files** for new functionality
8. **Optionally copy `start.sh`** and `Dockerfile.public` (as new public `Dockerfile`)
