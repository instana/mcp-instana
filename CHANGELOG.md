# Changelog
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
