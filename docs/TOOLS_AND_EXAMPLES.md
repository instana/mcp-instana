<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
## Table of Contents

- [Instana MCP Server - Tools and Example Prompts](#instana-mcp-server---tools-and-example-prompts)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
    - [For First-Time Users](#for-first-time-users)
    - [Recommended Learning Path](#recommended-learning-path)
    - [Common Use Cases](#common-use-cases)
  - [Table of Contents](#table-of-contents)
  - [1. Application Resources](#1-application-resources)
    - [Capabilities](#capabilities)
      - [Resource Types:](#resource-types)
    - [Example Prompts](#example-prompts)
      - [Metrics Queries](#metrics-queries)
      - [Alert Configuration](#alert-configuration)
      - [Application Settings](#application-settings)
      - [Catalog Operations](#catalog-operations)
  - [2. Infrastructure Analysis](#2-infrastructure-analysis)
    - [Capabilities](#capabilities-1)
    - [Example Prompts](#example-prompts-1)
      - [Pass 1 - Intent-Based Queries](#pass-1---intent-based-queries)
      - [Pass 2 - Specific Selections](#pass-2---specific-selections)
  - [3. Events Monitoring](#3-events-monitoring)
    - [Capabilities](#capabilities-2)
    - [Example Prompts](#example-prompts-2)
      - [General Event Queries](#general-event-queries)
      - [Kubernetes Events](#kubernetes-events)
      - [Agent Monitoring Events](#agent-monitoring-events)
      - [Advanced Filtering](#advanced-filtering)
  - [4. Website Monitoring](#4-website-monitoring)
    - [Capabilities](#capabilities-3)
    - [Example Prompts](#example-prompts-3)
      - [Beacon Analysis](#beacon-analysis)
      - [Geographic Analysis](#geographic-analysis)
      - [Browser and Device Analysis](#browser-and-device-analysis)
      - [Configuration](#configuration)
  - [5. Automation Actions](#5-automation-actions)
    - [Capabilities](#capabilities-4)
    - [Example Prompts](#example-prompts-4)
      - [Action Catalog](#action-catalog)
      - [Action Matching](#action-matching)
      - [Execution History](#execution-history)
  - [6. Custom Dashboards](#6-custom-dashboards)
    - [Capabilities](#capabilities-5)
    - [Example Prompts](#example-prompts-5)
      - [Dashboard Management](#dashboard-management)
      - [Dashboard Creation](#dashboard-creation)
      - [Dashboard Updates](#dashboard-updates)
      - [Sharing](#sharing)
  - [7. SLO Management](#7-slo-management)
    - [Capabilities](#capabilities-6)
    - [Example Prompts](#example-prompts-6)
      - [SLO Configuration](#slo-configuration)
      - [SLO Reporting](#slo-reporting)
      - [SLO Alerts](#slo-alerts)
      - [Error Budget Corrections](#error-budget-corrections)
  - [8. Release Tracking](#8-release-tracking)
    - [Capabilities](#capabilities-7)
    - [Example Prompts](#example-prompts-7)
      - [Release Management](#release-management)
      - [Release Impact Analysis](#release-impact-analysis)
  - [9. Mobile App Monitoring](#9-mobile-app-monitoring)
    - [Capabilities](#capabilities-8)
    - [Example Prompts](#example-prompts-8)
      - [Beacon Analysis](#beacon-analysis-1)
      - [Performance Metrics](#performance-metrics)
      - [Geographic Analysis](#geographic-analysis-1)
      - [Device and Platform Analysis](#device-and-platform-analysis)
      - [Configuration](#configuration-1)
      - [Alert Management](#alert-management)
  - [Advanced Usage Tips](#advanced-usage-tips)
    - [Time Range Specifications](#time-range-specifications)
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
- Monitor website and mobile app performance
- Manage SLOs and releases
- Create and configure dashboards
- Browse automation actions

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

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)

**Tools:**
1. [Application Resources](#1-application-resources)
2. [Infrastructure Analysis](#2-infrastructure-analysis)
3. [Events Monitoring](#3-events-monitoring)
4. [Website Monitoring](#4-website-monitoring)
5. [Automation Actions](#5-automation-actions)
6. [Custom Dashboards](#6-custom-dashboards)
7. [SLO Management](#7-slo-management)
8. [Release Tracking](#8-release-tracking)

**Advanced:**
- [Advanced Usage Tips](#advanced-usage-tips)
- [Getting Help](#getting-help)

---

## 1. Application Resources

**Tool Name:** `manage_applications`

### Capabilities

This unified tool manages all application-related operations including metrics, alerts, configurations, and catalog information.

#### Resource Types:
- **metrics**: Query application performance metrics, services, and endpoints
- **alert_config**: Manage application-specific alert configurations
- **global_alert_config**: Manage global application alert configurations
- **settings**: Manage application perspectives, endpoints, services, manual services
- **catalog**: Access application tag and metric catalog information

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

---

## 2. Infrastructure Analysis

**Tool Name:** `analyze_infrastructure`

### Capabilities

This tool uses a two-pass approach for infrastructure analysis:
- **Pass 1**: Provide natural language intent and entity type → Server returns available metrics and filters
- **Pass 2**: Select specific metrics and filters → Server executes query and returns results

The system automatically discovers all entity types from your Instana installation, supporting Kubernetes, JVM, databases, message queues, containers, hosts, and any custom plugins.

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

---

## 3. Events Monitoring

**Tool Name:** `manage_events`

### Capabilities

Monitor and analyze events including incidents, issues, changes, and Kubernetes events with advanced filtering and analysis.

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

#### Configuration

```
List all configured websites in Instana
```

```
Get the configuration details for the "Production Website" including geo-location settings
```

```
Show me IP masking configuration for the customer portal website
```

---

## 5. Automation Actions

**Tool Name:** `manage_automation`

### Capabilities

Browse automation action catalog and view execution history for automated remediation and response actions.

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

## 9. Mobile App Monitoring

**Tool Name:** `manage_mobile_apps`

### Capabilities

Monitor mobile application performance, analyze user sessions, track crashes, and configure mobile app settings.

**Resource Types:**
- **analyze**: Query mobile app beacon data with grouping or filtering
- **catalog**: Get available metrics and tags for mobile app monitoring
- **configuration**: Get mobile app configurations
- **advanced_config**: Retrieve advanced configurations (geo-location, IP masking, geo rules)
- **alert**: Get mobile app alert configurations

### Example Prompts

#### Beacon Analysis

```
Show me all session start beacons for the "Robot Shop" mobile app in the last hour
```

```
Get beacon count per mobile app grouped by view name for the last 24 hours
```

```
Analyze crash beacons for iOS devices in the last 7 days
```

```
Show me HTTP request beacons with response time greater than 2 seconds
```

#### Performance Metrics

```
What are the available metrics for mobile app monitoring?
```

```
Get P95 latency for all views in the "Shopping App" mobile app
```

```
Show me beacon count and average session duration grouped by device model
```

```
Analyze performance metrics for the "Checkout" view across different mobile OS versions
```

#### Geographic Analysis

```
Show me session distribution by country for the last 30 days
```

```
Get beacon count grouped by city for the "Delivery App"
```

```
Analyze crash rates by geographic region
```

#### Device and Platform Analysis

```
Show me beacon distribution across iOS and Android platforms
```

```
Get session count grouped by device manufacturer
```

```
Analyze app version adoption rates across different devices
```

#### Configuration

```
List all mobile apps configured in Instana
```

```
Get configuration details for the "Robot Shop" mobile app
```

```
Show me geo-location configuration for the mobile app
```

```
Get IP masking settings for the "Shopping App"
```

#### Alert Management

```
Show me all active alert configurations for the "Robot Shop" mobile app
```

```
Get details for mobile app alert configuration with ID "alert-123"
```

```
List all alert configurations for mobile app ID "app-abc123"
```

**Important Notes:**
- Always call `get_mobile_app_metric_catalog` first to get valid metrics
- Then call `get_mobile_app_tag_catalog` to get valid tag names
- Tag names MUST start with "mobileBeacon." (e.g., "mobileBeacon.mobileApp.name")
- ALWAYS include `"entity": "NOT_APPLICABLE"` in every tag filter
- Default beacon type is "SESSION_START"

---

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
