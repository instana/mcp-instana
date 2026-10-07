<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [For First-Time Users](#for-first-time-users)
  - [Recommended Learning Path](#recommended-learning-path)
  - [Common Use Cases](#common-use-cases)
- [Tool Categories and Configuration Identifiers](#tool-categories-and-configuration-identifiers)
- [1. Application Resources](#1-application-resources)
  - [Capabilities](#capabilities)
    - [Resource Types:](#resource-types)
  - [Example Prompts](#example-prompts)
    - [Metrics Queries](#metrics-queries)
    - [Alert Configuration](#alert-configuration)
    - [Application Settings](#application-settings)
    - [Catalog Operations](#catalog-operations)
    - [Application Resources and Topology](#application-resources-and-topology)
    - [Trace Analysis](#trace-analysis)
- [2. Infrastructure Analysis](#2-infrastructure-analysis)
  - [Capabilities](#capabilities-1)
    - [Resource Types:](#resource-types-1)
  - [Example Prompts](#example-prompts-1)
    - [Pass 1 - Intent-Based Queries](#pass-1---intent-based-queries)
    - [Pass 2 - Specific Selections](#pass-2---specific-selections)
    - [Smart Alert Configuration](#smart-alert-configuration)
- [3. Events Monitoring](#3-events-monitoring)
  - [Capabilities](#capabilities-2)
    - [Resource Types:](#resource-types-2)
  - [Example Prompts](#example-prompts-2)
    - [General Event Queries](#general-event-queries)
    - [Kubernetes Events](#kubernetes-events)
    - [Agent Monitoring Events](#agent-monitoring-events)
    - [Advanced Filtering](#advanced-filtering)
- [4. Website Monitoring](#4-website-monitoring)
  - [Capabilities](#capabilities-3)
    - [Resource Types:](#resource-types-3)
  - [Example Prompts](#example-prompts-3)
    - [Beacon Analysis](#beacon-analysis)
    - [Geographic Analysis](#geographic-analysis)
    - [Browser and Device Analysis](#browser-and-device-analysis)
    - [Configuration and Advanced Settings](#configuration-and-advanced-settings)
    - [Website Alert Configuration](#website-alert-configuration)
- [5. Automation Actions](#5-automation-actions)
  - [Capabilities](#capabilities-4)
    - [Resource Types:](#resource-types-4)
  - [Example Prompts](#example-prompts-4)
    - [Action Catalog](#action-catalog)
    - [Action Matching](#action-matching)
    - [Execution History](#execution-history)
- [6. Custom Dashboards](#6-custom-dashboards)
  - [Capabilities](#capabilities-5)
    - [Resource Types:](#resource-types-5)
  - [Example Prompts](#example-prompts-5)
    - [Dashboard Management](#dashboard-management)
    - [Dashboard Creation](#dashboard-creation)
    - [Dashboard Updates](#dashboard-updates)
    - [Sharing](#sharing)
- [7. SLO Management](#7-slo-management)
  - [Capabilities](#capabilities-6)
    - [Resource Types:](#resource-types-6)
  - [Example Prompts](#example-prompts-6)
    - [SLO Configuration](#slo-configuration)
    - [SLO Reporting](#slo-reporting)
    - [SLO Alerts](#slo-alerts)
    - [Error Budget Corrections](#error-budget-corrections)
- [8. Release Tracking](#8-release-tracking)
  - [Capabilities](#capabilities-7)
    - [Resource Types:](#resource-types-7)
  - [Example Prompts](#example-prompts-7)
    - [Release Management](#release-management)
    - [Release Impact Analysis](#release-impact-analysis)
- [9. Mobile App Monitoring](#9-mobile-app-monitoring)
  - [Capabilities](#capabilities-8)
    - [Resource Types:](#resource-types-8)
  - [Example Prompts](#example-prompts-8)
    - [Beacon Analysis](#beacon-analysis-1)
    - [Geographic Analysis](#geographic-analysis-1)
    - [View and Device Analysis](#view-and-device-analysis)
    - [Configuration and Alerts](#configuration-and-alerts)
    - [Session Replay](#session-replay)
- [10. Synthetic Monitoring](#10-synthetic-monitoring)
  - [Capabilities](#capabilities-9)
    - [Resource Types:](#resource-types-9)
  - [Example Prompts](#example-prompts-9)
    - [Test Configuration](#test-configuration)
    - [Test Results and Health](#test-results-and-health)
    - [Datacenter and Location Health](#datacenter-and-location-health)
- [11. Maintenance Windows](#11-maintenance-windows)
  - [Capabilities](#capabilities-10)
    - [Resource Types:](#resource-types-10)
  - [Example Prompts](#example-prompts-10)
    - [Listing Maintenance Windows](#listing-maintenance-windows)
    - [Creating and Managing Windows](#creating-and-managing-windows)
    - [Bulk Operations and Templates](#bulk-operations-and-templates)
- [Advanced Usage Tips](#advanced-usage-tips)
  - [Time Range Specifications](#time-range-specifications)
  - [Error Handling and Troubleshooting](#error-handling-and-troubleshooting)
  - [Filtering and Grouping](#filtering-and-grouping)
    - [Simple Tag Filter](#simple-tag-filter)
    - [Complex Filters with OR Logic](#complex-filters-with-or-logic)
    - [Complex Filters with AND Logic](#complex-filters-with-and-logic)
    - [Nested Expressions](#nested-expressions)
  - [Combining Tools](#combining-tools)
    - [Scenario 1: Release Impact Analysis](#scenario-1-release-impact-analysis)
    - [Scenario 2: Infrastructure to Application Correlation](#scenario-2-infrastructure-to-application-correlation)
    - [Scenario 3: SLO Breach Investigation](#scenario-3-slo-breach-investigation)
    - [Scenario 4: Multi-Environment Monitoring](#scenario-4-multi-environment-monitoring)
    - [Scenario 5: Website Performance Analysis](#scenario-5-website-performance-analysis)
  - [Best Practices](#best-practices)
- [Getting Help](#getting-help)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Instana MCP Server - Tools and Example Prompts

## Overview

The Instana MCP (Model Context Protocol) Server enables AI assistants and automation tools to interact with your Instana observability platform through natural language. Instead of manually navigating the Instana UI or writing API calls, you can ask questions and perform operations using conversational prompts.

**What you can do:**
- Query application and infrastructure metrics
- Analyze events and incidents
- Monitor website performance
- Manage SLOs and releases
- Create and configure dashboards
- Browse automation actions
- Monitor Mobile app performance

## Prerequisites

Before using these tools, ensure you have:

1. **Instana MCP Server Running**
   - Server must be started in either `streamable-http` or `stdio` mode
   - See [README.md](../README.md) for installation and setup instructions

2. **Valid Instana Credentials**
   - **API Token Authentication**: Instana API token with appropriate permissions
     - Use for: Programmatic access, automation, CI/CD pipelines
     - Configuration: Set via environment variables or HTTP headers
   - **Session Authentication**: For UI-initiated calls (auth token + CSRF token)
      - Credentials can be provided via environment variables or HTTP headers
      - Use for: Browser-based interactions, UI extensions
      - Configuration: Automatically handled by browser session

3. **Instana Environment Details**
   - Base URL of your Instana instance (e.g., `https://your-tenant.instana.io`)
   - Knowledge of your tenant structure (units, zones, etc.)
   - Understanding of monitored applications and infrastructure

4. **Appropriate Permissions**
   - Read access for query operations
   - Write access for configuration changes (alerts, SLOs, dashboards)
   - Admin access for certain management operations

5. **MCP Client**
   - Claude Desktop, GitHub Copilot, or any MCP-compatible client
   - Client must be configured to connect to the Instana MCP Server
   - See [README.md](../README.md) for client configuration examples

## Quick Start

### For First-Time Users

Start with these simple operations to familiarize yourself with the tools:

1. **List Operations** - Get an overview of available resources
   ```
   List all applications in Instana
   Show me all configured websites
   Get all SLO configurations
   ```

2. **Simple Queries** - Fetch recent data with default time ranges
   ```
   Show me application metrics for the Payment Service in the last hour
   Get recent events from the production namespace
   What are the current SLO statuses?
   ```

3. **Explore Catalogs** - Understand available metrics and tags
   ```
   What metrics are available for application monitoring?
   Show me the tag catalog for website beacons
   List available automation actions
   ```

### Recommended Learning Path

1. **Start with Read-Only Operations**
   - Query metrics, events, and configurations
   - Build confidence with the tool responses
   - Understand the data structure

2. **Experiment with Filters**
   - Add time ranges to your queries
   - Filter by specific services or namespaces
   - Group results by different dimensions

3. **Try Multi-Step Workflows**
   - Combine multiple queries for deeper analysis
   - Follow the workflow examples in this document
   - Correlate data across different tools

4. **Perform Configuration Changes**
   - Create dashboards to visualize your data
   - Set up alerts for critical conditions
   - Configure SLOs for your services

### Common Use Cases

- **Troubleshooting**: Investigate incidents by correlating events, metrics, and logs
- **Performance Analysis**: Analyze application and infrastructure performance trends
- **Release Validation**: Verify deployment success and monitor post-release metrics
- **SLO Monitoring**: Track service level objectives and error budgets
- **Capacity Planning**: Analyze resource utilization and growth patterns

This document provides comprehensive examples of how to interact with the Instana MCP Server tools. Each tool is designed to handle specific monitoring and observability tasks with natural language queries.

## Tool Categories and Configuration Identifiers

When starting the MCP server with the `--categories` option (e.g. `python -m src.core.server --categories app,infra`), use the corresponding category identifier:

| Section | Category Name | Category Identifier (`--categories`) | Unified Tool Name |
|---|---|---|---|
| 1 | Application Resources | `app` | `manage_applications` |
| 2 | Infrastructure Analysis | `infra` | `manage_infrastructure` |
| 3 | Events Monitoring | `events` | `manage_events` |
| 4 | Website Monitoring | `website` | `manage_websites` |
| 5 | Automation Actions | `automation` | `manage_automation` |
| 6 | Custom Dashboards | `settings` | `manage_custom_dashboards` |
| 7 | SLO Management | `slo` | `manage_slo` |
| 8 | Release Tracking | `releases` | `manage_releases` |
| 9 | Mobile App Monitoring | `mobile_app` | `manage_mobile_apps` |
| 10 | Synthetic Monitoring | `synthetic` | `manage_synthetics` |
| 11 | Maintenance Windows | `maintenance` | `manage_maintenance_windows` |

---

## 1. Application Resources

**Tool Name:** `manage_applications`

### Capabilities

This unified tool manages all application-related operations including metrics, alerts, configurations, and catalog information.

#### Resource Types:

**metrics**: Query application call metrics grouped by service, endpoint, or other dimensions

| Operation | Description |
|---|---|
| `get_grouped_calls_metrics` | Query application metrics with flexible filtering, grouping by tags, and aggregating metrics |

**alert_config**: Manage application-specific Smart Alert configurations (full CRUD + enable/disable/restore/update_baseline)

| Operation | Description |
|---|---|
| `find_active` | Find active alert configurations for an application |
| `find` | Get alert configuration by ID and optional valid_on timestamp |
| `find_versions` | Get alert configuration versions |
| `create` | Create application alert configuration |
| `update` | Update existing application alert configuration |
| `delete` | Delete application alert configuration |
| `enable` | Enable application alert configuration |
| `disable` | Disable application alert configuration |
| `restore` | Restore application alert configuration to a historical version |
| `update_baseline` | Update historic baselines for application alert configuration |

**global_alert_config**: Manage global application alert configurations (full CRUD + enable/disable/restore)

| Operation | Description |
|---|---|
| `find_active` | Find active global alert configurations |
| `find` | Get global alert configuration by ID and optional valid_on timestamp |
| `find_versions` | Get global alert configuration versions (version control for global alerts) |
| `create` | Create global alert configuration |
| `update` | Update global alert configuration |
| `delete` | Delete global alert configuration |
| `enable` | Enable global alert configuration |
| `disable` | Disable global alert configuration |
| `restore` | Restore global alert configuration to a historical version |

**settings**: Manage application perspectives, endpoint configs, service configs, and manual service configs

| Operation | Description |
|---|---|
| `get_all` | List all configurations for the given resource subtype (`application`, `endpoint`, `service`, `manual_service`) |
| `get` | Get specific configuration by ID or name (supported for `application`, `endpoint`, `service`) |
| `create` | Create new configuration for application perspectives, endpoints, services, or manual services |
| `update` | Update existing configuration for application perspectives, endpoints, services, or manual services |
| `delete` | Delete configuration for application perspectives, endpoints, services, or manual services |

*Note: `manual_service` does not support the `get` operation (only `get_all`, `create`, `update`, `delete`).*

**catalog**: Access application tag and metric catalogs for constructing valid queries

| Operation | Description |
|---|---|
| `get_tag_catalog` | Get valid tag names for filtering and grouping by use case and data source |
| `get_metric_catalog` | Get application metrics catalog with metadata (metricId, label, aggregations, beaconTypes) |

**resources**: Retrieve application perspectives, services, and service endpoints

| Operation | Description |
|---|---|
| `get_applications` | Get application perspectives with configurations and metadata |
| `get_services` | Get all services across all applications with optional snapshot IDs |
| `get_application_services` | Get services for a specific application perspective |
| `get_application_endpoints` | Get endpoints for an application service with type and technology metadata |

**analyze**: Analyze application traces — list all traces, fetch trace details, and group traces

| Operation | Description |
|---|---|
| `get_all_traces` | List all traces with filtering, pagination, and time range |
| `get_trace_details` | Get detailed information for a specific trace by ID |
| `get_trace_groups` | Group traces by tag with aggregated metrics |

### Example Prompts

#### Metrics Queries

```
Show me the latency and error rates for the "Payment Service" application over the last hour
```

```
List all services in the "E-commerce Platform" application grouped by service name
```

```
Get endpoint metrics for the checkout service, showing the top 10 slowest endpoints by p95 latency
```

```
What are the call counts and error rates for all endpoints in the API Gateway application from March 19, 2026 at 2:00 PM IST to 5:00 PM IST?
```

#### Alert Configuration

```
Show me all active alert configurations for the "Production Frontend" application
```

```
Create a new alert for the Payment Service that triggers when error rate exceeds 5% for 5 minutes
```

```
Disable the "High Latency" alert for the User Service application
```

```
Get the version history of alert configurations for application "Checkout Service"
```

#### Application Settings

```
Create a new application perspective called "Mobile Backend" that includes all services with tag "platform:mobile"
```

```
List all application perspectives in the system
```

```
Update the "API Gateway" application to include downstream services
```

```
Show me the endpoint configuration for the "User Authentication" service
```

#### Catalog Operations

```
Get the tag catalog for application calls to understand available grouping options
```

```
What metrics are available for application monitoring?
```

#### Application Resources and Topology

```
List all monitored services matching "payment" and include their snapshot IDs
```

```
Get all HTTP endpoints configured for the checkout service in application app-123
```

#### Trace Analysis

```
Retrieve the latest 50 traces with window size 1 hour including internal and synthetic calls
```

```
Get detailed call flow and span data for trace ID 8a2b3c4d5e6f
```

```
Group application traces by service name and aggregate total trace counts over the last hour
```

---

## 2. Infrastructure Analysis

**Tool Name:** `manage_infrastructure`

### Capabilities

This unified tool manages all infrastructure-related operations including entity analysis, catalog metadata, snapshot resources, and Smart Alert configurations.

**Key Features:**
- **Auto-Routing**: Automatically routes to `get_entity_groups` when `groupBy` is present in the payload, and to `get_entities` when absent.
- **Dynamic Catalog**: Automatically synchronized with your Instana installation's available plugins and entity types (hosts, JVM, Kubernetes, Docker, databases, message queues, and more).
- **Flexible Metric Aggregation**: Supports MAX, MEAN, MIN, and SUM aggregations over custom time frames.
- **Advanced Filtering**: Rich filtering by tags and properties for precise infrastructure querying.

#### Resource Types:

**analyze**: Query individual infrastructure entities or grouped entity metrics with custom time frames, filters, and aggregations

| Operation | Description |
|---|---|
| `get_entities` | Get individual infrastructure entities with metrics (auto-routed when groupBy is absent) |
| `get_entity_groups` | Get grouped infrastructure entities with aggregated metrics (auto-routed when groupBy is present) |

**catalog**: Discover entity types (plugins), metrics, tag catalog, or full plugin schema in one call

| Operation | Description |
|---|---|
| `get_plugins` | Get all available entity types/plugins in your Instana installation |
| `get_plugin_schema` | Get combined metrics and tags schema for a plugin in one call |
| `get_metrics` | Get infrastructure metrics catalog for a specific plugin |
| `get_tag_catalog` | Get valid tag names for filtering and grouping |

**resources**: Retrieve or search infrastructure snapshots by ID or query criteria

| Operation | Description |
|---|---|
| `get_snapshot` | Get detailed information for a specific snapshot by ID |
| `get_snapshots` | Search and discover multiple snapshots matching criteria |

**alert_config**: Full CRUD management for Instana Infrastructure Smart Alert configurations (create, read, update, delete, enable, disable, restore)

| Operation | Description |
|---|---|
| `find_active` | List all active alert configurations |
| `find` | Get alert configuration by ID |
| `find_versions` | Get all historical versions of an alert configuration |
| `create` | Create a new alert configuration with schema validation |
| `update` | Update an existing alert configuration |
| `delete` | Delete an alert configuration |
| `enable` | Enable an alert configuration |
| `disable` | Disable an alert configuration |
| `restore` | Restore an alert configuration to a historical version |

### Example Prompts

#### Pass 1 - Intent-Based Queries

```
Show me the maximum heap size of JVM instances running on host galactica1
```

```
I want to analyze CPU usage for Kubernetes pods in the production namespace
```

```
Get memory metrics for Docker containers running the payment service
```

```
Show me database connection pool metrics for DB2 instances
```

```
Analyze IBM MQ queue depth and message rates for the order-processing queue
```

#### Pass 2 - Specific Selections

After receiving the schema from Pass 1, you can make specific selections:

```
Get the following JVM metrics: jvm.heap.maxSize, jvm.heap.used, jvm.gc.collectionTime
Filter by: host.name = "galactica1"
Aggregation: max
Time range: last 1 hour
```

```
Query Kubernetes pod metrics: kubernetes.pod.cpu.usage, kubernetes.pod.memory.usage
Group by: kubernetes.namespace.name
Filter by: kubernetes.cluster.name = "prod-cluster"
Order by: cpu usage descending
```

#### Smart Alert Configuration

> **Note:** For a plain listing, omit `alert_ids` and pagination parameters — client-side pagination
> (default 50 per page) is applied automatically to avoid LLM context overflow. Use `alert_ids` to
> filter by known IDs, or `page`/`page_size` only when you need to page through a large result set.

```
List all active Infrastructure Smart Alert configurations
```

```
Show only the Infrastructure Smart Alert configurations with IDs "H5PW_lINTV6yGN8ad5jG49" and "pkPW_lINTV6yGN8ad8jG49"
```

```
List active Infrastructure Smart Alert configurations, page 2 with 25 results per page
```

```
Get details for Infrastructure Smart Alert configuration with ID "H5PW_lINTV6yGN8ad5jG49"
```

```
Show all historical versions of Infrastructure Smart Alert "K8-cpu-alert-high"
```

```
Create a new Infrastructure Smart Alert for high CPU usage on hosts triggering when cpu.used exceeds 90%
```

```
Disable the Infrastructure Smart Alert "K8-cpu-alert-high"
```

```
Restore Infrastructure Smart Alert "K8-cpu-alert-high" to the version created at 1710658800000
```

---

## 3. Events Monitoring

**Tool Name:** `manage_events`

### Capabilities

Monitor and analyze events including incidents, issues, changes, and Kubernetes events with advanced filtering and analysis.

**Key Features:**
- **Smart Routing**: Seamlessly routes requests to specialized event retrieval and analysis tools.
- **Unified Parameter Validation**: Robust client-side validation of time frames, pagination limits, and `max_events`.
- **Natural Language Time Frames**: First-class support for conversational time ranges like "last 24 hours", "last 2 days", or custom datetime ranges with timezone support.
- **Event Filtering & Optimization**: Intelligent filtering options by severity, state, affected entity types, problem description, and availability of Root Cause Analysis (RCA).

#### Resource Types:

**events**: Query and filter events across all types and entities

| Operation | Description |
|---|---|
| `get_events` | Get all events with flexible filters (event types, entity type/name/label, state, problem, severity, RCA, time ranges) |
| `get_event` | Get Event by ID |
| `get_events_by_ids` | Get Events by IDs |
| `get_kubernetes_info_events` | Get Kubernetes Info Events with detailed analysis |
| `get_agent_monitoring_events` | Get Agent Monitoring Events with detailed analysis |

### Example Prompts

#### General Event Queries

```
Show me all critical incidents from the last 24 hours
```

```
Get details for event ID 1a2b3c4d5e6f
```

```
List all open incidents affecting the payment-service with high error rate problems
```

```
Show me all closed issues with severity higher than 5 from April 22, 2025 between 10 AM and 11 AM
```

#### Kubernetes Events

```
Analyze Kubernetes info events from the last 24 hours and identify any pod restart patterns
```

```
Show me all Kubernetes events related to CRI-O Container issues in the last 45 minutes
```

#### Agent Monitoring Events

```
Get agent monitoring events for the production cluster from March 19, 2026 at 2:47 PM IST
```

```
Show me all agent offline events in the last 2 hours
```

#### Advanced Filtering

```
Find all incidents for application services that are currently open with critical severity
```

```
Show me change events (severity -1) from the last week for infrastructure hosts
```

```
Get all warning events (severity 5) affecting Kubernetes pods in the staging namespace
```

---

## 4. Website Monitoring

**Tool Name:** `manage_websites`

### Capabilities

Monitor real user monitoring (RUM) data including page loads, resource loads, errors, and custom beacons with advanced filtering and grouping.

**Key Features:**
- **Flexible Beacon Support**: Built-in support for multiple web beacon types, including PAGELOAD, PAGE_CHANGE, RESOURCELOAD, CUSTOM, HTTPREQUEST, and ERROR.
- **Tag Validation & Elicitation**: Automatic tag validation against the live catalog and catalog-based elicitation workflow when user-supplied filters or group tags are missing or invalid.
- **Response Summarization**: Intelligent payload reduction of 70-80% to deliver fast, LLM-friendly summarized answers.
- **Advanced Beacon Analysis**: Analyze beacons either in aggregated form (beacon groups) or as detailed individual records with pagination support.

#### Resource Types:

**analyze**: Query website beacon metrics — grouped/aggregated or individual beacon data

| Operation | Description |
|---|---|
| `get_beacon_groups` | Get Website Beacon Groups - grouped/aggregated beacon data |
| `get_beacons` | Get Website Beacons - individual beacon data with pagination |

**catalog**: Access website metric and tag catalogs for constructing valid queries

| Operation | Description |
|---|---|
| `get_metrics` | Get Website Metrics Catalog |
| `get_tag_catalog` | Get Website Tag Catalog by beacon type and use case |

**configuration**: List and get website configurations (read-only; use Instana UI for modifications)

| Operation | Description |
|---|---|
| `get_all` | Get All Websites |
| `get` | Get Website by ID or name with automatic name resolution |

**advanced_config**: Retrieve advanced website settings — geo-location, IP masking, and geo-mapping rules (read-only)

| Operation | Description |
|---|---|
| `get_geo_config` | Get Geo-Location Configuration |
| `get_ip_masking` | Get IP Masking Configuration |
| `get_geo_rules` | Get Geo Mapping Rules |

**alert**: Query active and version-specific website alert configurations (read-only)

| Operation | Description |
|---|---|
| `find_active_website_alert_configs` | Get all active alert configurations for a website |
| `find_website_alert_config` | Get smart alert configuration by ID |

### Example Prompts

#### Beacon Analysis

```
Show me page load beacon counts grouped by page name for the Robot Shop website in the last hour
```

```
Get average page load time by browser type for the E-commerce site
```

```
List all error beacons from the last 24 hours grouped by error message
```

```
Show me resource load times for JavaScript files on the home page
```

#### Geographic Analysis

```
Analyze page load performance by geographic location for users in Asia
```

```
Show me beacon counts grouped by country for the last week
```

#### Browser and Device Analysis

```
Compare page load times across Chrome, Firefox, and Safari browsers
```

```
Show me mobile vs desktop performance metrics for the checkout page
```

#### Configuration and Advanced Settings

```
List all configured websites in Instana
```

```
Get the configuration details for the "Production Website" including geo-location settings
```

```
Show me IP masking configuration for the customer portal website
```

```
Get geo-mapping rules configured for the E-commerce website
```

#### Website Alert Configuration

```
Show me all active alert configurations for website ID "website-abc123"
```

```
Get alert configuration details for alert ID "alert-123" valid on timestamp 1742349976000
```

---

## 5. Automation Actions

**Tool Name:** `manage_automation`

### Capabilities

Browse automation action catalog and view execution history for automated remediation and response actions.

#### Resource Types:

**catalog**: Browse and search the automation action catalog

| Operation | Description |
|---|---|
| `get_actions` | List all available automation actions |
| `get_action_details` | Get detailed information about a specific action |
| `get_action_matches` | Search for matching actions by name/description |
| `get_action_matches_by_id_and_time_window` | Get action matches by application or snapshot ID and time window |
| `get_action_types` | Get available action types |
| `get_action_tags` | Get available action tags |

**history**: View action execution history and retrieve instance details

| Operation | Description |
|---|---|
| `list` | List action execution instances with filtering |
| `get_details` | Get details of a specific action execution |

### Example Prompts

#### Action Catalog

```
List all available automation actions in the catalog
```

```
Find actions related to CPU performance issues
```

```
Get details for the "Restart Service" automation action
```

```
Show me all actions tagged with "kubernetes" and "scaling"
```

```
What action types are available in the system?
```

#### Action Matching

```
Find automation actions that match "CPU spends significant time waiting for input/output"
```

```
Get recommended actions for application snapshot ID snap-12345 based on current issues
```

#### Execution History

```
Show me the execution history of automation actions from the last 7 days
```

```
Get details for action instance execution ID abc-123-def
```

```
List all failed automation action executions from yesterday
```

```
Show me automation actions triggered by event ID evt-789
```

---

## 6. Custom Dashboards

**Tool Name:** `manage_custom_dashboards`

### Capabilities

Create, read, update, and delete custom dashboards with widgets for visualizing metrics and monitoring data.

#### Resource Types:

**custom_dashboard**: CRUD operations for custom dashboards plus sharing metadata

| Operation | Description |
|---|---|
| `get_all` | Get all custom dashboards |
| `get` | Get specific dashboard by ID |
| `create` | Create new custom dashboard |
| `update` | Update existing custom dashboard |
| `delete` | Delete custom dashboard |
| `get_shareable_users` | Get shareable users for dashboard |
| `get_shareable_api_tokens` | Get shareable API tokens for dashboard |

### Example Prompts

#### Dashboard Management

```
List all custom dashboards in the system
```

```
Show me dashboards with "production" in the title
```

```
Get the configuration for dashboard ID abc123
```

```
Delete the dashboard named "Test Dashboard"
```

#### Dashboard Creation

```
Create a new dashboard called "Production Monitoring" with global read-write access
```

```
Create a dashboard titled "API Performance" with a latency chart widget showing the last hour of data
```

```
Build a comprehensive dashboard for the Payment Service with widgets for latency, error rate, and throughput
```

#### Dashboard Updates

```
Update the "Infrastructure Overview" dashboard to add a new CPU usage widget
```

```
Modify the access rules for the "Team Dashboard" to restrict access to the DevOps team
```

#### Sharing

```
Show me all users who can access custom dashboards
```

```
List all API tokens that have dashboard access
```

---

## 7. SLO Management

**Tool Name:** `manage_slo`

### Capabilities

Manage Service Level Objectives including configuration, reporting, alerts, and error budget corrections.

**Key Features:**
- **Intelligent Datetime & Timezone Parsing**: Effortless datetime parsing for SLO report queries, with timezone elicitation to ensure accurate query context.
- **Error Budget Corrections**: Rich support for scheduling correction windows (maintenance, exclusions) with recurring rules (RFC 5545 RRULE expressions).
- **SLO Alert Lifecycle & Version Control**: Full control over alert configs, including CRUD operations, enable, disable, and restoring to historical versions.
- **Dual Indicator Types**: Configure and monitor both time-based (latency/availability) and event-based service level objectives.

#### Resource Types:

**configuration**: Full CRUD management for SLO configurations plus tag listing

| Operation | Description |
|---|---|
| `get_all` | List and filter SLO configurations with pagination |
| `get_by_id` | Get SLO configuration by ID |
| `create` | Create SLO configuration with time-based and event-based indicators |
| `update` | Update SLO configuration |
| `delete` | Delete SLO configuration |
| `get_tags` | List SLO tags |

**report**: Generate SLO performance reports with error budget and burn rate data

| Operation | Description |
|---|---|
| `get` | Generate SLO report with SLI value, error budget, burn rates, and time-series charts (supports intelligent datetime parsing with timezone elicitation) |

**alert**: Full lifecycle management for SLO alert configurations

| Operation | Description |
|---|---|
| `find_active` | Find active alert configurations |
| `find` | Get alert configuration by ID |
| `find_versions` | Get alert configuration versions |
| `create` | Create alert configurations |
| `update` | Update alert configurations |
| `delete` | Delete alert configurations |
| `enable` | Enable alert configurations |
| `disable` | Disable alert configurations |
| `restore` | Restore alert configuration to a version |

**correction**: Manage error budget correction windows (planned downtime exclusions)

| Operation | Description |
|---|---|
| `get_all` | List correction windows with filtering |
| `get_by_id` | Get correction window by ID |
| `create` | Create correction windows (with support for recurring correction windows with recurrence rules) |
| `update` | Update correction windows |
| `delete` | Delete correction windows |

### Example Prompts

#### SLO Configuration

```
List all SLO configurations in the system
```

```
Show me SLOs for the Payment Service with status "warning"
```

```
Get the configuration for SLO ID slo-12345
```

```
Create a new SLO for the API Gateway with 99.9% availability target over a 30-day rolling window
```

```
Update the latency SLO for the Checkout Service to have a 95% target
```

```
Delete the SLO configuration for the deprecated User Service
```

#### SLO Reporting

```
Get the SLO report for the Payment Service showing error budget consumption
```

```
Show me SLO compliance for all services in the production environment from the last 7 days
```

```
What's the current error budget status for the API Gateway SLO?
```

#### SLO Alerts

```
Show me all active SLO alert configurations
```

```
Create an alert that triggers when the Payment Service SLO drops below 99.5%
```

```
Disable SLO alerts for the staging environment
```

#### Error Budget Corrections

```
List all error budget corrections for the last month
```

```
Create a correction for the planned maintenance window on March 20th from 2 AM to 4 AM
```

```
Get correction details for correction ID corr-456
```

---

## 8. Release Tracking

**Tool Name:** `manage_releases`

### Capabilities

Track software releases and analyze their impact on application performance and stability.

**Key Features:**
- **Case-Insensitive Substring Filtering**: Easily search for releases using the `name_filter` parameter.
- **Intelligent Timezone Handling**: Robust, automatic conversion of human-entered start times (e.g., with "IST", "UTC") into valid timestamps.
- **Scope Definition**: Define scopes to link releases to specific applications and services.
- **Impact Analysis**: Correlate deployment events with metrics, traces, and incidents.

#### Resource Types:
**releases**: CRUD operations for release tracking and deployment records

| Operation | Description |
|---|---|
| `get_all_releases` | List all releases with pagination and optional time range filtering (operation="get_all_releases") |
| `get_release` | Get release details by ID including applications, services, and scopes (operation="get_release") |
| `create_release` | Create new release with associated applications and services (operation="create_release") |
| `update_release` | Update existing release (operation="update_release") |
| `delete_release` | Delete release (operation="delete_release") |

### Example Prompts

#### Release Management

```
List all releases from the last 30 days
```

```
Show me releases for the "frontend" application
```

```
Get details for release ID l1wgr3DsQkGLf8u18JiGsg
```

```
Create a new release called "frontend/release-2000" deployed on March 19, 2026 at 2:47 PM IST for the Mobile App
```

```
Update release "backend/v2.5.0" to include the Payment Service
```

```
Delete the test release "staging/test-release-001"
```

#### Release Impact Analysis

```
Analyze application performance after the "frontend/release-2000" deployment
```

```
Check for new incidents after the Payment Service release from yesterday
```

```
Compare KPIs (latency, error rate, throughput) before and after the API Gateway release
```

```
Show me how error rates changed after the release deployed at 2:47 PM IST on March 19th
```

```
Get statistics on latency evolution after the Checkout Service release compared to the previous week
```

---

## 9. Mobile App Monitoring

**Tool Name:** `manage_mobile_apps`

### Capabilities

Monitor mobile app monitoring data including session starts, HTTP requests, errors, custom beacons, and user sessions with advanced filtering and grouping.

**Key Features:**
- **Flexible Beacon Support**: Complete coverage of mobile beacon types, including SESSION_START, VIEW_CHANGE, HTTP_REQUEST, CUSTOM, PERF, and DROP_BEACON.
- **Tag Validation & Elicitation**: Catalog-backed validation of filter/group tags, guiding the LLM/user via elicitation if invalid tags are used.
- **Response Summarization**: Summarizes payloads by 70-80% for high-speed, LLM-friendly interactions.
- **Session Replay & Action Beacons**: Retrieve session-specific beacons or step-by-step action beacons for session replay debugging.

#### Resource Types:

**analyze**: Query mobile app beacon metrics — grouped/aggregated or individual beacon data

| Operation | Description |
|---|---|
| `get_mobile_app_beacon_groups` | Get Mobile App Beacon Groups - grouped/aggregated beacon data |
| `get_all_mobile_app_beacons` | Get Mobile App Beacons - individual beacon data with pagination |

**catalog**: Access mobile app metric and tag catalogs for constructing valid queries

| Operation | Description |
|---|---|
| `get_mobile_app_metric_catalog` | Get Mobile App Metrics Catalog |
| `get_mobile_app_tag_catalog` | Get Mobile App Tag Catalog by beacon type and use case |

**configuration**: List and get mobile app configurations (read-only; use Instana UI for modifications)

| Operation | Description |
|---|---|
| `get_all` | Get all mobile apps |
| `get` | Get mobile app by ID or name with automatic name resolution |

**advanced_config**: Retrieve advanced mobile app settings — geo-location, IP masking, geo-mapping rules, and source map upload configs (read-only)

| Operation | Description |
|---|---|
| `get_geo_config` | Get Geo-Location Configuration |
| `get_ip_masking` | Get IP Masking Configuration |
| `get_geo_rules` | Get Geo Mapping Rules |
| `get_source_map_upload_config` | Get Source Map Upload Configuration |
| `get_mobile_app_source_map_upload_config_by_id` | Get Source Map Upload Configuration by ID |

**alert**: Query active and version-specific mobile app alert configurations (read-only)

| Operation | Description |
|---|---|
| `find_active_mobile_app_alert_configs` | Get all active alert configurations for a mobile app |
| `find_mobile_app_alert_config` | Get smart alert configuration by ID |

**session**: Retrieve session beacons and paginated session replay action beacons

| Operation | Description |
|---|---|
| `get_session_beacons` | Get all beacons for a session by session ID and timestamp |
| `get_session_replay_action_beacons` | Get paginated session replay action beacons by mobile app ID and session ID |

### Example Prompts

#### Beacon Analysis

```
Show me session start beacon counts grouped by view name for the Robot Shop mobile app in the last hour
```

```
Get average view change time by user model type for the Products view
```

```
List all crash beacons from the last 24 hours grouped by crash group label
```

```
Get performance beacons for Android mobile app sessions where the platform is Android, grouped by performance subtypes
```

#### Geographic Analysis

```
Show me session start beacon counts grouped by country for the last week
```

#### View and Device Analysis

```
Compare session start times across Google Pixel 4XL, iPhone 7, and iPhone 13
```

```
Show me android vs ios performance metrics for the products view
```

#### Configuration and Alerts

```
List all monitored mobile apps in Instana
```

```
Show me all active alert configurations for mobile app ID "mobile-app-123"
```

```
Get source map upload configuration details for mobile app "Robot Shop Mobile"
```

#### Session Replay

```
Get session replay action beacons for mobile app ID "i1IsNS7FQAegEljBTkNBMQ" and session ID "1d616527-2635-407f-89fc-de7136b66fb4"
```

---

## 10. Synthetic Monitoring

**Tool Name:** `manage_synthetics`

### Capabilities

Monitor synthetic tests and locations including test configuration, playback results, metrics, and location health with advanced filtering and grouping.

#### Resource Types:

**catalog**: Access metric and tag catalogs for constructing valid synthetic queries

| Operation | Description |
|---|---|
| `get_synthetic_catalog_metrics` | Get available metrics with supported aggregations for query planning |
| `get_synthetic_tag_catalog` | Get valid tag names for filtering, grouping, and smart alerts |

**metrics**: Retrieve one or more aggregated metrics for synthetic monitoring beacons with optional grouping and filtering

| Operation | Description |
|---|---|
| `get_metrics_result` | Retrieve aggregated synthetic metrics grouped by location or test name |

**settings**: Look up synthetic test configuration, location metadata, and datacenter fleet information

| Operation | Description |
|---|---|
| `get_synthetic_test` | Get a synthetic test's full configuration by ID or name |
| `get_synthetic_tests` | List synthetic tests with optional filtering by application, location, or credential |
| `get_locations` | List all monitoring locations with type, geo, and capability metadata |
| `get_location_by_id` | Get a single location by ID or name with automatic name resolution |
| `get_all_datacenters` | Get all datacenter (Managed) locations with online count |

**test_playback**: Retrieve per-run results, analytic summaries, location summaries, test health summaries, and detailed result files

| Operation | Description |
|---|---|
| `get_synthetic_result` | Get aggregated playback metrics per test |
| `get_synthetic_result_analytic` | Get the most recent result per test using LAST_VALUE analytic |
| `get_synthetic_result_list` | Get individual test run results with raw status, errors, and timestamps |
| `get_location_summary_list` | Get location-level summary metadata including last run time and PoP version |
| `get_test_summary_list` | Get per-test success rates with per-location breakdown |
| `get_synthetic_result_metadata` | Get available detail data types for a specific test result |
| `get_synthetic_result_detail_data` | Get detail data file contents such as logs, HAR, or screenshots |

### Example Prompts

#### Test Configuration

```
List all synthetic tests configured in Instana
```

```
Get the full configuration details of synthetic test named e2e-api-ScriptTest-automation
```

```
Show me all synthetic tests for application id 6peoVq6pTcGGEvZY4fjkAg
```

```
Get the full details of location named E2ETest PoP
```

#### Test Results and Health

```
Get the most recent status for every synthetic test and highlight any that are failing
```

```
Give me the success rate summary for all the synthetic tests over the last 30 minutes
```

```
Give me the sum of response times for synthetic tests grouped by location over the last 12 hours
```

```
Show me the last 20 individual runs of test Test_SimplePing with timestamps, response times, and errors
```

#### Datacenter and Location Health

```
Show me all datacenter locations — how many are there and how many are currently Online?
```

```
List all datacenters and for each one show the datacenterFlag from custom properties and how many tests are linked to it.
```

```
Are any datacenters currently showing failures across all synthetic test types simultaneously — indicating a full location outage?
```

---

## 11. Maintenance Windows

**Tool Name:** `manage_maintenance_windows`

### Capabilities

Create, modify, close, and list maintenance windows to suppress alerts during planned downtime.

**Key Features:**
- **Predefined Templates**: Fast creation using standardized templates, including `deployment`, `database_migration`, `infrastructure_upgrade`, `emergency`, and `routine`.
- **ServiceNow Integration**: Optional integration to link maintenance windows with ServiceNow change request IDs (e.g. `CHG0012345`).
- **Recurring Windows**: Full support for recurring windows via RFC 5545 RRULE expressions (e.g. daily, weekly recurrence).
- **Bulk Creation**: Create maintenance windows for multiple applications or IMAP codes simultaneously.

#### Resource Types:

**window** Full lifecycle management of maintenance windows

| Operation | Description |
|---|---|
| `create` | Create maintenance windows with template support |
| `modify` | Modify existing maintenance windows |
| `close` | Close and document completed maintenance windows |
| `bulk_create` | Bulk create maintenance windows for multiple IMAP codes |
| `list_active` | List active maintenance windows |
| `list_scheduled` | List scheduled maintenance windows |
| `list_expired` | List expired maintenance windows |
| `list_all` | List all maintenance windows |
| `validate` | Validate maintenance window parameters without creating |

**templates**: Retrieve pre-defined maintenance window templates

| Operation | Description |
|---|---|
| `get` | Retrieve all available maintenance window templates |

### Example Prompts

#### Listing Maintenance Windows

```
Show me all currently active maintenance windows
```

```
List all scheduled maintenance windows for application EAL-012471
```

```
Show me all expired maintenance windows from the last week
```

#### Creating and Managing Windows

```
Create a 2-hour maintenance window for EAL-012471 starting at 2026-06-01 10:00 AM UTC with reason "Scheduled deployment"
```

```
Create a recurring daily maintenance window for ORZ-000012 starting at midnight for 30 minutes
```

```
Modify maintenance window mw-789 to extend it by 60 minutes
```

```
Close maintenance window mw-789 with the note "Completed successfully, no issues found"
```

#### Bulk Operations and Templates

```
Create maintenance windows for EAL-012471 and ORZ-000012 simultaneously for the upcoming infrastructure upgrade
```

```
What maintenance window templates are available?
```

```
Create a deployment maintenance window for EAL-012471 with change request ID CHG0012345
```

---


## Advanced Usage Tips

### Time Range Specifications

The MCP server supports flexible time range formats:

1. **Unix timestamps** (milliseconds): `1742369820000`
2. **Natural language**: `"last 24 hours"`, `"last 2 days"`, `"last 1 hour"`
3. **Datetime with timezone**: `"19 March 2026, 2:47 PM|IST"`, `"20 March 2026, 10:00 AM|UTC"`
4. **Datetime without timezone** (defaults to UTC): `"19 March 2026, 2:47 PM"`

### Error Handling and Troubleshooting
- **Authentication Errors**: Verify API token permissions and expiration
- **Empty Results**: Check time ranges and filter criteria
- **Timeout Errors**: Reduce time range or add more specific filters
- **Permission Denied**: Ensure user has appropriate access levels

### Filtering and Grouping

Most tools support advanced filtering using tag filter expressions. You can use simple filters or combine them with logical operators.

#### Simple Tag Filter

```json
{
  "type": "TAG_FILTER",
  "name": "service.name",
  "operator": "EQUALS",
  "entity": "DESTINATION",
  "value": "payment-service"
}
```

**Supported Operators:** `EQUALS`, `NOT_EQUAL`, `CONTAINS`, `NOT_CONTAIN`, `STARTS_WITH`, `ENDS_WITH`, `GREATER_THAN`, `LESS_THAN`

#### Complex Filters with OR Logic

Filter for multiple namespaces (production OR staging):

```json
{
  "type": "EXPRESSION",
  "logicalOperator": "OR",
  "elements": [
    {
      "type": "TAG_FILTER",
      "name": "kubernetes.namespace.name",
      "operator": "EQUALS",
      "entity": "DESTINATION",
      "value": "production"
    },
    {
      "type": "TAG_FILTER",
      "name": "kubernetes.namespace.name",
      "operator": "EQUALS",
      "entity": "DESTINATION",
      "value": "staging"
    }
  ]
}
```

**Example Prompt:**
```
Show me application metrics for services in either production or staging namespace
```

#### Complex Filters with AND Logic

Filter for payment service with HTTP errors (status > 400):

```json
{
  "type": "EXPRESSION",
  "logicalOperator": "AND",
  "elements": [
    {
      "type": "TAG_FILTER",
      "name": "service.name",
      "operator": "EQUALS",
      "entity": "DESTINATION",
      "value": "payment-service"
    },
    {
      "type": "TAG_FILTER",
      "name": "call.http.status",
      "operator": "GREATER_THAN",
      "entity": "DESTINATION",
      "value": "400"
    }
  ]
}
```

**Example Prompt:**
```
Show me all calls to payment-service that returned HTTP status codes greater than 400
```

#### Nested Expressions

Combine AND/OR logic for complex scenarios:

```json
{
  "type": "EXPRESSION",
  "logicalOperator": "AND",
  "elements": [
    {
      "type": "EXPRESSION",
      "logicalOperator": "OR",
      "elements": [
        {
          "type": "TAG_FILTER",
          "name": "kubernetes.namespace.name",
          "operator": "EQUALS",
          "entity": "DESTINATION",
          "value": "production"
        },
        {
          "type": "TAG_FILTER",
          "name": "kubernetes.namespace.name",
          "operator": "EQUALS",
          "entity": "DESTINATION",
          "value": "staging"
        }
      ]
    },
    {
      "type": "TAG_FILTER",
      "name": "service.name",
      "operator": "CONTAINS",
      "entity": "DESTINATION",
      "value": "payment"
    }
  ]
}
```

**Example Prompt:**
```
Show me metrics for payment-related services in production or staging environments
```

### Combining Tools

For comprehensive analysis, combine multiple tools in workflows. Here are real-world scenarios:

#### Scenario 1: Release Impact Analysis

**Workflow:** Track a release → Check for incidents → Analyze performance changes

```
Step 1: Get release details
"Get details for release frontend/v2.5.0"

Step 2: Check for incidents after release
"Show me all critical incidents that occurred after March 19, 2026 at 2:47 PM IST"

Step 3: Analyze application metrics
"Compare latency and error rates for the Frontend application before and after March 19, 2026 at 2:47 PM IST"

Step 4: Check automation actions
"Show me automation actions triggered for the Frontend application since March 19, 2026"
```

#### Scenario 2: Infrastructure to Application Correlation

**Workflow:** Identify infrastructure issues → Correlate with application performance

```
Step 1: Analyze infrastructure metrics
"Show me CPU and memory usage for Kubernetes pods in the production namespace with high resource consumption"

Step 2: Get affected applications
"List all services running on pods with CPU usage above 80%"

Step 3: Check application performance
"Show me latency and error rates for the affected services in the last hour"

Step 4: Review events
"Get all Kubernetes events related to pod restarts or OOMKilled in the last hour"
```

#### Scenario 3: SLO Breach Investigation

**Workflow:** Detect SLO breach → Investigate root cause → Check remediation

```
Step 1: Check SLO status
"Show me all SLOs that are currently in breach or warning state"

Step 2: Get SLO report
"Get the detailed SLO report for the Payment Service including error budget consumption"

Step 3: Analyze related events
"Show me all incidents affecting the Payment Service in the last 24 hours"

Step 4: Review metrics
"Get latency, error rate, and throughput metrics for Payment Service endpoints"

Step 5: Check automation
"Show me automation actions executed for the Payment Service in the last 24 hours"
```

#### Scenario 4: Multi-Environment Monitoring

**Workflow:** Compare performance across environments

```
Step 1: Get production metrics
"Show me application metrics for services in the production namespace"

Step 2: Get staging metrics
"Show me application metrics for services in the staging namespace"

Step 3: Compare error rates
"Compare error rates between production and staging for the API Gateway service"

Step 4: Check configuration differences
"Show me application perspective configurations for production and staging"
```

#### Scenario 5: Website Performance Analysis

**Workflow:** Analyze user experience → Identify bottlenecks → Correlate with backend

```
Step 1: Get website beacon data
"Show me page load times grouped by page name for the E-commerce website in the last hour"

Step 2: Analyze by geography
"Show me page load performance by country for users experiencing slow load times"

Step 3: Check browser impact
"Compare page load times across Chrome, Firefox, and Safari"

Step 4: Correlate with backend services
"Show me latency metrics for the API services called by the slow-loading pages"

Step 5: Check for errors
"Get all error beacons from the website in the last hour"
```

### Best Practices

1. **Start broad, then narrow**: Begin with list operations, then drill down to specific resources
2. **Use catalog operations**: Check available metrics and tags before querying
3. **Leverage time ranges**: Use appropriate time windows for your analysis
4. **Group and aggregate**: Use grouping to identify patterns across multiple entities
5. **Combine filters**: Use multiple filter criteria to precisely target your analysis

---

## Getting Help

For more information:
- Check the main [README.md](../README.md) for setup and configuration
- Review [OBSERVABILITY.md](../OBSERVABILITY.md) for monitoring the MCP server itself
- See [DOCKER.md](../DOCKER.md) for containerized deployment options
