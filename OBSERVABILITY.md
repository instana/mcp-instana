# MCP Observability Configuration Guide

This document provides comprehensive instructions for enabling and configuring observability in the MCP Instana Server using Traceloop SDK for distributed tracing.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Client-Specific Configurations](#client-specific-configurations)
    - [GitHub Copilot](#github-copilot)
    - [Claude Desktop](#claude-desktop)
    - [Custom MCP Client](#custom-mcp-client)
- [Starting the Server](#starting-the-server)
- [Viewing Traces in Instana](#viewing-traces-in-instana)
- [Troubleshooting](#troubleshooting)

## Overview

MCP-Instana Observability integrates with the Traceloop SDK to provide distributed tracing for your MCP server and client interactions.

## Prerequisites

Before enabling observability, ensure you have:

- Traceloop SDK installed (see [Installation](#installation))
- Access to an Instana instance for viewing spans

## Installation

### Install Traceloop SDK

If you don't already have it:

```bash
# Using pip
pip install traceloop-sdk==0.47.5

# Using uv
uv add traceloop-sdk==0.47.5
```

Without this, you'll see warnings like:
```
Traceloop requested but not installed. Install with: pip install traceloop-sdk
```

## Configuration

### Environment Variables

Observability in MCP-Instana is feature-flag controlled. It will only be enabled if the environment variable `ENABLE_MCP_OBSERVABILITY` is set.

#### Main Feature Flag

| Variable | Default |
|----------|---------|
| `ENABLE_MCP_OBSERVABILITY` | `false` | 

**Accepted values:**
- `true`, `1`, `yes`, `on` → enables observability
- `false`, `0`, `no`, `off` → disables observability (default)

**Important:** If this flag is not set (or set to false), MCP observability will remain completely disabled, even if Traceloop and Instana configs are present.

#### Traceloop Configuration Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TRACELOOP_BASE_URL` | Your Instana OTLP endpoint URL | `https://otlp-pink-saas.instana.rocks:4317` |
| `TRACELOOP_HEADERS` | Authentication header for Instana | `x-instana-key=your_instana_key` |
| `OTEL_EXPORTER_OTLP_INSECURE` | Whether to use insecure connection | `false` (recommended) |

#### Export Modes

You can export traces to Instana in two different modes:

**Agent Mode :**

Export traces to a local Instana agent running on your machine:

```bash
export TRACELOOP_BASE_URL=<instana-agent-host>:4317
export TRACELOOP_HEADERS="api-key=<api-key>""
export OTEL_EXPORTER_OTLP_INSECURE=true
```

**Agentless Mode (Direct to Backend):**

Export traces directly to the Instana backend:

```bash
export TRACELOOP_BASE_URL=<instana-otlp-endpoint>:4317
export TRACELOOP_HEADERS="x-instana-key=<agent-key>"
export OTEL_EXPORTER_OTLP_INSECURE=false
```

**Note:** Replace the values with your actual Instana configuration:
- For agentless mode, use your Instana backend OTLP endpoint and API key
- For agent mode, ensure your local Instana agent is running and accessible

### Client-Specific Configurations

Depending on your client (GitHub Copilot, Claude Desktop, or a custom MCP client), configuration differs for HTTP mode and STDIO mode. In all cases, ensure the flag `ENABLE_MCP_OBSERVABILITY=true` is set.

#### GitHub Copilot

##### HTTP Mode (mcp.json)

For Streamable HTTP mode, configure `.vscode/mcp.json`:

```json
{
  "servers": {
    "Instana MCP Server": {
      "command": "npx",
      "args": [
        "mcp-remote", "http://0.0.0.0:8080/mcp/",
        "--allow-http",
        "--header", "instana-base-url: <your-instana-url>",
        "--header", "instana-api-token: <your-instana-token>"
      ],
      "env": {
        "ENABLE_MCP_OBSERVABILITY": "true",
        "TRACELOOP_BASE_URL": "<your-instana-otlp-url>",
        "TRACELOOP_HEADERS": "x-instana-key=<your-instana-key>",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
      }
    }
  }
}
```

**Note:** Replace the following values:
- `<your-instana-url>`: Your Instana instance URL (e.g., `https://your-instance.instana.io`)
- `<your-instana-token>`: Your Instana API token
- `<your-instana-otlp-url>`: Your Instana OTLP endpoint (for ex - `https://otlp-pink-saas.instana.rocks:4317`)
- `<your-instana-key>`: Your Instana authentication key

##### STDIO Mode (mcp.json)

For STDIO mode, configure `.vscode/mcp.json`:

```json
{
  "servers": {
    "Instana MCP Server": {
      "command": "uv",
      "args": [
        "run",
        "src/core/server.py",
        "--tools", "infra"
      ],
      "cwd": "<path-to-mcp-instana>",
      "env": {
        "INSTANA_BASE_URL": "<your-instana-url>",
        "INSTANA_API_TOKEN": "<your-instana-token>",
        "ENABLE_MCP_OBSERVABILITY": "true",
        "TRACELOOP_BASE_URL": "<your-instana-otlp-url>",
        "TRACELOOP_HEADERS": "x-instana-key=<your-instana-key>",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
      }
    }
  }
}
```

**Note:** Replace `<path-to-mcp-instana>` with the absolute path to your mcp-instana project directory.

#### Claude Desktop

##### HTTP Mode (claude_desktop_config.json)

For Streamable HTTP mode, configure Claude Desktop:

**File Locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "npx",
      "args": [
        "mcp-remote", "http://0.0.0.0:8080/mcp/",
        "--allow-http",
        "--header", "instana-base-url: <your-instana-url>",
        "--header", "instana-api-token: <your-instana-token>"
      ],
      "env": {
        "ENABLE_MCP_OBSERVABILITY": "true",
        "TRACELOOP_BASE_URL": "<your-instana-otlp-url>",
        "TRACELOOP_HEADERS": "x-instana-key=<your-instana-key>",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
      }
    }
  }
}
```

##### STDIO Mode (claude_desktop_config.json)

For STDIO mode:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "uv",
      "args": [
        "--directory",
        "<path-to-mcp-instana>",
        "run",
        "src/core/server.py"
      ],
      "cwd": "<path-to-mcp-instana>",
      "env": {
        "INSTANA_BASE_URL": "<your-instana-url>",
        "INSTANA_API_TOKEN": "<your-instana-token>",
        "ENABLE_MCP_OBSERVABILITY": "true",
        "TRACELOOP_BASE_URL": "<your-instana-otlp-url>",
        "TRACELOOP_HEADERS": "x-instana-key=<your-instana-key>",
        "OTEL_EXPORTER_OTLP_INSECURE": "false"
      }
    }
  }
}
```

#### Custom MCP Client

For custom MCP clients:

- **HTTP Mode** → Use the same setup as GitHub Copilot HTTP (JSON config with headers + observability env vars)
- **STDIO Mode** → Use the same setup as Claude STDIO (JSON config with server command, env vars, and observability flag)

## Starting the Server

After updating configurations, you'll need to restart components. The steps differ by mode:

### Streamable HTTP Mode

**Step 1: Export Environment Variables (if needed)**

In case the environment variables are not taking effect, export them in the mcp-instana server terminal:

```bash
export ENABLE_MCP_OBSERVABILITY=true
export TRACELOOP_BASE_URL=<your-instana-otlp-url>
export TRACELOOP_HEADERS="x-instana-key=<your-instana-key>"
export OTEL_EXPORTER_OTLP_INSECURE=false
```

**Note:** `TRACELOOP_BASE_URL` should be your Instana OTLP URL (e.g., `https://otlp-pink-saas.instana.rocks:4317`)

**Step 2: Start the Server**

Start the server explicitly with streamable HTTP transport:

```bash
# Using development installation
uv run src/core/server.py --transport streamable-http

# Using PyPI installation
mcp-instana --transport streamable-http
```

**Step 3: Restart the Client**

Restart the client (e.g., GitHub Copilot, Claude Desktop, or custom MCP client) using its configuration file.

### STDIO Mode

In STDIO mode, you don't need to start the MCP server manually. The client (GitHub Copilot, Claude Desktop, or custom MCP client) will directly launch the MCP server process based on its configuration file.

Simply start the client, and it will take care of invoking the server under the hood.

**Important Note:** In some clients, the root span may not appear automatically unless the session is fully closed:

- **Claude Desktop** → Quit the Claude Desktop app after finishing your session
- **GitHub Copilot** → Stop the MCP server process after your workflow

If the session remains open, the root span will be missing from traces.

## Viewing Traces in Instana

Once observability is enabled and the server is running, you can view traces in Instana:

1. **Log in to Instana**
2. **Navigate to Analytics** → Enable "Show internal calls" (bottom left)
3. **Add Filter**: Service Name → `Instana-MCP-Server` (the app name you used with `traceloop.init()`)
4. **Explore traces**:
   - Filter by time range
   - Drill into individual spans
   - Analyze request flows end-to-end

This visualization makes it easy to trace requests and identify performance bottlenecks.

### Key Benefits

Enabling observability brings immediate advantages:

- **End-to-End Visibility** – See client-to-server flows
- **Performance Optimization** – Identify bottlenecks with real data
- **Error Tracking** – Pinpoint failure points quickly
- **System Understanding** – Learn how components interact

## Troubleshooting

### No Spans Visible?

If you don't see any spans in Instana:

1. **Verify the feature flag is set:**
   ```bash
   echo $ENABLE_MCP_OBSERVABILITY
   # Should output: true
   ```

2. **Check Traceloop SDK installation:**
   ```bash
   pip show traceloop-sdk
   ```

3. **Confirm Instana configuration:**
   - Verify `TRACELOOP_BASE_URL` is correct
   - Verify `TRACELOOP_HEADERS` contains valid authentication key
   - Check `OTEL_EXPORTER_OTLP_INSECURE` is set appropriately

4. **Check server logs for errors:**
   - Look for Traceloop initialization messages
   - Check for connection errors to Instana

### Environment Variables Not Taking Effect?

If environment variables don't seem to work:

1. **For HTTP mode:** Export variables in the server terminal before starting
2. **For STDIO mode:** Ensure variables are in the client configuration file
3. **Restart both server and client** after configuration changes
4. **Check for typos** in variable names (they are case-sensitive)