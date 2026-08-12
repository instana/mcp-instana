# API Token Permissions

This document outlines the required permissions for each Instana MCP tool. Permissions are categorized by operation type to help you configure API tokens with appropriate access levels.

## Prerequisites

- Valid Instana API Token
- Access to Instana permission management interface
- Understanding of your intended use cases (read-only monitoring vs. configuration changes)

### What Happens Without Required Permissions?

If your API token lacks required permissions:
- Read operations will return `403 Forbidden` errors
- Write operations (Create/Update/Delete) will fail with permission denied errors
- The MCP tool will return an error message indicating missing permissions

### How to Configure API Token Permissions

1. Navigate to **Settings → Team Settings → API Tokens** in your Instana dashboard
2. Create a new token or edit an existing one
3. Under **Permissions**, enable the required permissions based on your use case:
   - **For monitoring only:** Default Read permissions are sufficient
   - **For configuration management:** Enable specific permissions marked as `Required: Yes`
4. Save the token and use it in your MCP configuration

## Permission Categories

### Read-Only Tools

These tools only fetch data and require **no additional permissions** beyond the default Read access. They perform no Create, Update, or Delete (CUD) operations.

#### analyze_infrastructure

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Infrastructure** | Configuration of global Smart Alerts for infrastructure | `No` |
| **Infrastructure** | Create, edit and delete Custom Entities | `No` |

#### manage_events

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Events and alerts** | Configuration of alert channels | `No` |
| **Events and alerts** | Configuration of events and alerts | `No` |
| **Events and alerts** | Configuration of maintenance windows | `No` |
| **Events and alerts** | Configuration of global custom payload for alerts | `No` |
| **Events and alerts** | Invoking an alert channel | `No` |
| **Events and alerts** | Manual closure of events | `No` |

#### manage_automation

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Automation** | Configuration of automation actions | `No` |
| **Automation** | Execution of automation actions | `No` |
| **Automation** | Configuration of automation policies | `No` |

#### manage_websites

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Websites** | Website monitoring configuration | `No` |
| **Websites** | Create, edit, and delete website conversion goals for business impact | `No` |
| **Websites** | Configuration of Smart Alerts for websites | `No` |

#### manage_logs

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Logs** | Read access to logs | `Yes` |


### Configuration Tools 

These tools can modify Instana configuration and require **explicit permissions** for write operations, as detailed in each tool's permission table.

#### manage_applications 

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Applications** | Configuration of applications | `Yes` |
| **Applications** | Customize service rules and endpoint mapping | `No` |
| **Applications** | Configuration of subtraces | `No` |
| **Applications** | Configuration of PII | `No` |
| **Applications** | Configuration of Smart Alerts for application | `Yes` |
| **Applications** | Configuration of global Smart Alerts for application | `Yes` |

#### manage_custom_dashboards

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Custom dashboards** | Management of all public custom dashboards | `Yes` |

#### manage_releases

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Global functions** | Configuration of releases | `Yes` |
| **Global functions** | Configuration of database analysis tool integrations | `No` |
| **Global functions** | Access to account and billing information | `No` |

#### manage_slo

| Category | Permission | Required |
| :--- | :--- | :---: |
| **Service levels** | Configuration of service level objectives | `Yes` |
| **Service levels** | Configuration of SLO correction windows | `Yes` |
| **Service levels** | Configuration of SLO smart alerts | `Yes` |
| **Service levels** | Configuration of Apdex | `No` |


## Troubleshooting Permission Issues

### Common Error Messages

**"403 Forbidden" or "Insufficient permissions"**
- **Cause:** API token lacks required permissions
- **Solution:** Review the permission table for your tool and enable required permissions

**"401 Unauthorized"**
- **Cause:** Invalid or expired API token
- **Solution:** Verify token is valid and not expired

### Verifying Your Token Permissions

Use the Instana API to check your token's current permissions:

```bash
curl -X GET "https://your-instana-instance.com/api/settings/users/api-tokens" \
  -H "Authorization: apiToken YOUR_TOKEN"
