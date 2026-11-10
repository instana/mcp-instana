# Changelog
### Unreleased
- **New Feature:** Shared, stateless pagination for list operations (releases, synthetic tests, synthetic alert configs, application alert configs, global application alert configs, application settings, custom dashboards). Paged responses carry a `pagination` envelope (`page`, `page_size`, `total_items`, `total_pages`, `has_more`, `has_previous`, `next_operation`, `previous_operation`). Copy `next_operation` / `previous_operation` (`page_N`) into the next call with the same params; `next` / `previous` / `go_to_page` remain as aliases but need the current page / `target_page` and return an error instead of guessing.
- **Behaviour:** Paging stays opt-in where it was before: `get_all_releases`, synthetic `get_synthetic_tests`, application settings `get_all` and custom dashboard `get_all` return the same data as before unless `page` / `page_size` (`page_number` for releases) is given. Application and global application alert config `find_active` (first 10) and synthetic alert `find_active` (page size 50) keep their existing default paging.
- **Behaviour:** Out-of-range pages return an empty list with `has_more=false` everywhere (synthetic alert `find_active` no longer clamps to the last page). Its legacy `total_pages` now reports 1 (not 0) for an empty result, matching the envelope.
- **Fix:** `get_all_releases` accepts `page_number` / `page_size` sent as strings. Synthetic `get_synthetic_tests` rejects `page` / `page_size` combined with `offset` / `limit`.

### 1.0.4
- **IMPORTANT:** Upgraded the FastMCP dependency to 4.1.0.
- **Enhancement:** Tool selection is now configurable via `mcp.json`, allowing specific tools to be enabled or omitted.
- **Enhancement:** Improved performance of the `get_events` operation and the `find_active` operation for infrastructure and global application Smart Alerts.
- **Enhancement:** Enhanced the SLO prompts.
- **New**: Introducing smart alerts for synthetics.

### 1.0.3
- **IMPORTANT**: SSL certificate verification is **enabled by default** and configurable
- **New Feature:** Added support for Infrastructure Smart Alert configurations via `manage_infrastructure`.
- **Enhancement:** Introduced catalog response caching for all catalog operations to reduce redundant API calls and improve response times.
- **Enhancement:** Improved MCP call tracking with better analytics segmentation
- **Enhancement:** Extended mobile app session support with unified session and session-replay beacon handling.
- **Chore:** Added IBM Bob CLI and Kiro CLI setup guides; updated Docker and README documentation.

### 1.0.2
- **Enhancement:** Introduced Async functionality to all the tool calls across all MCP tools.
- **Enhancement:** Added domain-aware `groupbyTagEntity` validation for application queries.
- **Enhancement:** Hardened graceful shutdown for stdio transport.
- **Fix:** Fixed business criticality field handling in application settings.
- **Fix:** Fixed oTelLLM infrastructure analyze issue by adding a static metric list.
- **Chore:** Updated tools and examples documentation.

### 1.0.1
- **New Feature:** Introduced `manage_synthetics` as a unified smart router for managing synthetic monitoring operations.
- **Enhancement:** Added multi-arch docker support for windows.
- **Enhancement:** Added pre-flight validation checks across all MCP tools.

### 1.0.0
- **New Feature:** Introduced `manage_infrastructure` as a unified smart router for infrastructure operations, replacing `analyze_infrastructure`. Consolidates analyze, catalog, and snapshot resource operations into a single tool.
- **New Feature:** Added Session Replay support in mobile-apps tool.
- **Enhancement:** Refactored maintenance window tool with improved parameter handling, duration calculation, and recurring window support.
- **Enhancement:** Added new application prompts for traces and resource operations.
- **Maintenance:** Removed static schema JSON files — infrastructure schema is now fetched live from the Instana API.

### 0.9.9
-  **New Feature:** Introduced maintenance window management functionality with unified smart router for creating, updating, and managing maintenance windows.

### 0.9.8
-  **New Feature:** JWT authentication is now enforced for all routes to enhance security.
-  **New Feature:** Introduced separate unified smart router to handle all mobile app operations, improving routing consistency and maintainability.
-  **Enhancement:** Introduced alert configurations support for websites tool.
-  **Enhancement:** Introduced better workflow for application analyze queries to reduce tool calls and improve response accuracy.
-  **Maintenance:** CSRF Token authentication is now enforced for all routes to enhance security.

### 0.9.6
-  **New Feature:** Introduced a unified smart router to handle all releases-related operations.

### 0.9.0
-  **New Feature:**  Introduced a unified smart router to handle all SLO-related operations.

### 0.8.1
-  **Fix:** Add `--env` flag for setting environment variables via CLI

### 0.8.0

-   **Enhancement:** Introduced separate unified smart router to handle all automation and event related operations, improving routing consistency and maintainability.

### 0.7.5

-   **Enhancement:** Introduced a unified smart router to handle all website-related operations, improving routing consistency and maintainability.
-    **Fix:** Corrected payload mapping logic for Application Analyze queries to ensure accurate request handling and response generation.

### 0.7.1

-   **Fix:** Fixed schema directory not being included in PyPI package distribution.
-   **Enhancement:** Added OTelLLM schema support for infrastructure analyze.

### 0.7.0

-   **Dependency Update:** Refactored Applications and Infrastructure tools for optimized performance.

### 0.6.2

-   **New Feature:** Added header for the User-agent for version tracking of mcp instana.

### 0.6.1

-   **Chore:** Updated README with Website Tools documentation.
-   **Chore:** Added KIRO setup instructions to README.

### 0.6.1

-   **Chore:** Updated README with Website Tools documentation.
-   **Chore:** Added KIRO setup instructions to README.

### 0.6.0

-   **Fix:** Improved accuracy across Application, Infrastructure, and
    Event tools by fixing broken functionality.
-   **Enhancement:** Added multi-architecture Docker image support.

### 0.5.0

-   **New Feature:** Added support for using MCP Instana as an extension
    within AI MCP clients.

### 0.4.0

-   **New Feature:** Added Website Monitoring tools.
-   **Enhancement:** Enhanced Event capabilities with new issue,
    incident, and change retrieval tools.

### 0.3.1

-   **Enhancement:** Optimized Docker image to reduce storage footprint.

### 0.3.0

-   **Enhancement:** Added prompt enable/disable functionality.
-   **New Feature:** Introduced Application Alert Global tools.
-   **New Feature:** Added automation tools.
-   **Fix:** Resolved application analyze tools for better handling of
    payloads.
-   **Enhancement:** Added Docker support.

### 0.2.0

-   **New Feature:** Added comprehensive Application Settings tools.
-   **New Feature:** Introduced the MCP Instana CLI.

### 0.1.0

-   Initial public release of the MCP Server for IBM
    Instana.
-   **New Feature:** Introduced core Monitoring Capabilities
    (Application, Infrastructure, and Event Monitoring).
