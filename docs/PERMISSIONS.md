# API Token Permissions

This document outlines the permissions an Instana API token needs for each Instana MCP tool. Tools are grouped by whether they can modify Instana configuration. Within each tool, permissions are listed together with the operations that need them.

## Prerequisites

- Valid Instana API Token
- Access to Instana permission management interface
- Understanding of your intended use cases (read-only monitoring vs. configuration changes)

### What Happens Without Required Permissions?

If your API token lacks required permissions:
- The Instana backend rejects the request with `403 Forbidden` (or `401 Unauthorized` for an invalid token)
- This applies to **some read operations too**: certain `get`/`list`/`find` operations require a configuration or view permission (see the per-tool tables below)
- The MCP tool returns an error message to the caller instead of data

### How to Configure API Token Permissions

1. Navigate to **Settings → Security & Access → Access Control → API Tokens** in your Instana UI
2. Create a new token or edit an existing one
3. Under **Permissions**, enable the permissions needed for the tools and operations you plan to use (see the tables below)
4. Save the token and use it in your MCP configuration

> **Note:** Only tools and operations that appear in a table below need a permission. Everything else (for example application metrics, infrastructure analyze/catalog, event queries) works with the default permissions every token has.

## Permission Categories

Each table lists only the permissions that an operation actually needs. `Yes` in the **Required** column means the permission must be enabled on the token to run the listed operations; `(write operations only)` means the read operations of that resource work without it.

### Read-Only Tools

These tools expose only read operations. They never create, update, or delete Instana configuration.

#### manage_events

Operations: `get_events`, `get_event`, `get_events_by_ids`, `get_kubernetes_info_events`, `get_agent_monitoring_events`. No additional permissions beyond the default are required.

#### manage_automation

Resource types `catalog` (`get_actions`, `get_action_details`, `get_action_matches`, `get_action_matches_by_id_and_time_window`, `get_action_types`, `get_action_tags`) and `history` (`list`, `get_details`). All operations are read-only and need no additional permissions. The tool cannot configure policies, run actions, or delete action history, so the related Automation permissions are not required.

#### manage_websites

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Websites** | Website monitoring configuration | `Yes` | `advanced_config`: `get_geo_config`, `get_ip_masking`, `get_geo_rules` |
| **Websites** | Configuration of Smart Alerts for websites | `Yes` | `alert`: `find_active_website_alert_configs`, `find_website_alert_config` |

`analyze`, `catalog`, and `configuration` (`get_all`, `get`) operations need no additional permissions.

#### manage_mobile_apps

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Mobile app monitoring** | Mobile app monitoring configuration | `Yes` | `advanced_config`: `get_geo_config`, `get_ip_masking`, `get_geo_rules` |
| **Mobile app monitoring** | Configuration of Smart Alerts for mobile apps | `Yes` | `alert`: `find_active_mobile_app_alert_configs`, `find_mobile_app_alert_config` |

`analyze`, `catalog`, `configuration` (`get_all`, `get`), and `session` need no additional permissions.

> **Note:** The `advanced_config` source-map operations (`get_source_map_upload_config`, `get_mobile_app_source_map_upload_config_by_id`) are currently unavailable due to an authentication limitation in the tool itself. They will return an error regardless of token permissions.

#### manage_alert_channels

This tool is read-only (`get_overview`, `get`) and masks all secrets in its responses.

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Alert Channels** | Configuration of alert channels | `Yes` |

> **Note:** To fetch Instana's alert channel details the `Configuration of alert channels` (`canConfigureIntegrations`) permission is required for read access.

### Tools With Write Operations

These tools can create, update, or delete Instana configuration. The tables show which permissions the operations need.

#### manage_infrastructure

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Infrastructure** | Configuration of global Smart Alerts for infrastructure | `Yes` (write operations only) | `alert_config`: `create`, `update`, `delete`, `enable`, `disable`, `restore` |

`analyze`, `catalog`, `resources`, and the read operations of `alert_config` (`find_active`, `find`, `find_versions`) need no additional permissions. Custom entity management is not exposed by this tool.

#### manage_applications

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Applications** | Configuration of applications | `Yes` | `settings` with `resource_subtype="application"`: all operations (including `get_all`, `get`) |
| **Applications** | Customize service rules and endpoint mapping | `Yes` | `settings` with `resource_subtype` `endpoint`, `service`, or `manual_service`: all operations (including `get_all`, `get`) |
| **Applications** | Configuration of Smart Alerts for application | `Yes` (write operations only) | `alert_config`: `create`, `update`, `delete`, `enable`, `disable`, `restore`, `update_baseline` |
| **Applications** | Configuration of global Smart Alerts for application | `Yes` (write operations only) | `global_alert_config`: `create`, `update`, `delete`, `enable`, `disable`, `restore` |

`metrics`, `analyze`, `catalog`, `resources`, and the read operations of `alert_config` / `global_alert_config` (`find_active`, `find`, `find_versions`) need no additional permissions. Subtrace and PII configuration are not exposed by this tool.

#### manage_custom_dashboards

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Custom dashboards** | Creation of public custom dashboards (`canCreatePublicCustomDashboards`) | `Yes` (only when sharing) | `create`, `update` with `accessRules` that share the dashboard with other users, roles, teams, or globally |

> **Note:** `get_all`, `get`, `get_shareable_users`, `get_shareable_api_tokens`, and `create` / `update` / `delete` of dashboards that are not shared need no additional permissions. The backend returns `403` only when a request tries to share a dashboard without `canCreatePublicCustomDashboards`.

#### manage_releases

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Global functions** | Configuration of releases | `Yes` | **All** operations: `get_all_releases`, `get_release`, `create_release`, `update_release`, `delete_release` |

> **Note:** Unlike most tools, read operations of `manage_releases` also require this permission.

#### manage_slo

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Service levels** | Configuration of service level objectives | `Yes` (write operations only) | `configuration`: `create`, `update`, `delete` |
| **Service levels** | Configuration of SLO correction windows | `Yes` (write operations only) | `correction`: `create`, `update`, `delete` |
| **Service levels** | Configuration of SLO smart alerts | `Yes` (write operations only) | `alert`: `create`, `update`, `delete`, `enable`, `disable`, `restore` |

`configuration` reads (`get_all`, `get_by_id`, `get_tags`), `correction` reads (`get_all`, `get_by_id`), `report` (`get`), and `alert` reads (`find_active`, `find`, `find_versions`) need no additional permissions. Apdex configuration is not exposed by this tool.

#### manage_synthetics

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Synthetic monitoring** | View synthetic tests | `Yes` | `settings`: `get_synthetic_test`, `get_synthetic_tests` |
| **Synthetic monitoring** | View synthetic locations | `Yes` | `settings`: `get_locations`, `get_location_by_id` |
| **Synthetic monitoring** | Configuration of synthetic locations | `Yes` | `settings`: `get_all_datacenters` |
| **Synthetic monitoring** | Configuration of global Smart Alerts for synthetics | `Yes` (write operations only) | `alert`: `create`, `update`, `delete`, `enable`, `disable`, `restore` |

`catalog`, `metrics`, `test_playback` (results, summaries, and detail data), and the read operations of `alert` (`find_active`, `find`, `find_versions`) need no additional permissions. The tool does not create or modify synthetic tests or locations.

#### manage_maintenance_windows

| Category | Permission | Required | Operations |
| :--- | :--- | :---: | :--- |
| **Events and alerts** | Configuration of maintenance windows | `Yes` | **All** `window` operations: `create`, `modify`, `close`, `list_active`, `list_scheduled`, `list_all`, `list_expired`, `bulk_create`, `validate` |

> **Note:** Listing and validating maintenance windows also requires this permission. The `templates` resource type (`get`) returns built-in templates and needs no additional permission.

## Troubleshooting Permission Issues

### Common Error Messages

**"403 Forbidden" or "Insufficient permissions"**
- **Cause:** API token lacks a permission required by the operation (this can happen for reads, e.g. `manage_releases`, `manage_maintenance_windows`, website/mobile alert configs)
- **Solution:** Find the operation in the tool's table above and enable the listed permission on the token

**"401 Unauthorized" or "Authentication failed. Please check your API token and permissions."**
- **Cause:** Invalid or expired API token
- **Solution:** Verify the token is valid and not expired

### Verifying Your Token Permissions

Use the Instana API to inspect API tokens and their permissions. This call itself requires a token with the **Configuration of API tokens** permission (`CanConfigureApiTokens`):

```bash
curl -X GET "https://your-instana-instance.com/api/settings/api-tokens" \
  -H "Authorization: apiToken YOUR_TOKEN"
```

