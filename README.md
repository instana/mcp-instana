<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**

- [MCP Server for IBM Instana](#mcp-server-for-ibm-instana)
  - [Architecture Overview](#architecture-overview)
  - [Workflow](#workflow)
  - [Prerequisites](#prerequisites)
    - [Option 1: Install from PyPI (Recommended)](#option-1-install-from-pypi-recommended)
    - [Option 2: Development Installation](#option-2-development-installation)
      - [Installing uv](#installing-uv)
      - [Setting Up the Environment](#setting-up-the-environment)
    - [Header-Based Authentication for Streamable HTTP Mode](#header-based-authentication-for-streamable-http-mode)
  - [Starting the Local MCP Server](#starting-the-local-mcp-server)
    - [Server Command Options](#server-command-options)
      - [Using the CLI (PyPI Installation)](#using-the-cli-pypi-installation)
      - [Using Development Installation](#using-development-installation)
    - [Starting in Streamable HTTP Mode](#starting-in-streamable-http-mode)
      - [Using CLI (PyPI Installation)](#using-cli-pypi-installation)
      - [Using Development Installation](#using-development-installation-1)
    - [Starting in Stdio Mode](#starting-in-stdio-mode)
      - [Using CLI (PyPI Installation)](#using-cli-pypi-installation-1)
      - [Using Development Installation](#using-development-installation-2)
    - [Tool Categories](#tool-categories)
      - [Using CLI (PyPI Installation)](#using-cli-pypi-installation-2)
      - [Using Development Installation](#using-development-installation-3)
    - [Verifying Server Status](#verifying-server-status)
    - [Common Startup Issues](#common-startup-issues)
  - [Setup and Usage](#setup-and-usage)
    - [Claude Desktop](#claude-desktop)
      - [Streamable HTTP Mode](#streamable-http-mode)
      - [Stdio Mode](#stdio-mode)
    - [GitHub Copilot](#github-copilot)
      - [Streamable HTTP Mode](#streamable-http-mode-1)
      - [Stdio Mode](#stdio-mode-1)
  - [Supported Features](#supported-features)
  - [Available Tools](#available-tools)
  - [Tool Filtering](#tool-filtering)
    - [Available Tool Categories](#available-tool-categories)
    - [Usage Examples](#usage-examples)
      - [Using CLI (PyPI Installation)](#using-cli-pypi-installation-3)
      - [Using Development Installation](#using-development-installation-4)
    - [Benefits of Tool Filtering](#benefits-of-tool-filtering)
  - [Example Prompts](#example-prompts)
  - [Docker Deployment](#docker-deployment)
    - [Docker Architecture](#docker-architecture)
      - [**pyproject.toml** (Development)](#pyprojecttoml-development)
      - [**pyproject-runtime.toml** (Production)](#pyproject-runtimetoml-production)
    - [Building the Docker Image](#building-the-docker-image)
      - [**Prerequisites**](#prerequisites-1)
      - [**Build Command**](#build-command)
      - [**What the Build Does**](#what-the-build-does)
    - [Running the Docker Container](#running-the-docker-container)
      - [**Basic Usage**](#basic-usage)
      - [**Environment Variables**](#environment-variables)
      - [**Docker Compose Example**](#docker-compose-example)
    - [Docker Security Features](#docker-security-features)
      - [**Security Best Practices Implemented**](#security-best-practices-implemented)
      - [**Image Size Optimization**](#image-size-optimization)
    - [Testing the Docker Container](#testing-the-docker-container)
      - [**Health Check**](#health-check)
      - [**MCP Inspector Testing**](#mcp-inspector-testing)
      - [**Logs and Debugging**](#logs-and-debugging)
    - [Production Deployment](#production-deployment)
      - [**Recommended Production Setup**](#recommended-production-setup)
      - [**Kubernetes Example**](#kubernetes-example)
  - [Troubleshooting](#troubleshooting)
    - [**Docker Issues**](#docker-issues)
      - [**Container Won't Start**](#container-wont-start)
      - [**Connection Issues**](#connection-issues)
      - [**Performance Issues**](#performance-issues)
    - [**General Issues**](#general-issues)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# MCP Server for IBM Instana

The Instana MCP server enables seamless interaction with the Instana observability platform, allowing you to access real-time observability data directly within your development workflow.

It serves as a bridge between clients (such as AI agents or custom tools) and the Instana REST APIs, converting user queries into Instana API requests and formatting the responses into structured, easily consumable formats.

The server supports both **Streamable HTTP** and **Stdio** transport modes for maximum compatibility with different MCP clients. For more details, refer to the [MCP Transport Modes specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).

## Architecture Overview

```mermaid
graph LR
    subgraph "Application Host Process"
        MH[MCP Host]
        MSI[Instana MCP Server]
        MST[ProductA MCP Server]
        MSC[ProductB MCP Server]

        MH <--> MSI
        MH <--> MSC
        MH <--> MST
    end

    subgraph "Remote Service"
        II[Instana Instance]
        TI[ProductA Instance]
        CI[ProductB Instance]

        MSI <--> II
        MST <--> TI
        MSC <--> CI
    end

    subgraph "LLM"
        L[LLM]
        MH <--> L
    end
```

## Workflow

Consider a simple example: You're using an MCP Host (such as Claude Desktop, VS Code, or another client) connected to the Instana MCP Server. When you request information about Instana alerts, the following process occurs:

1. The MCP client retrieves the list of available tools from the Instana MCP server
2. Your query is sent to the LLM along with tool descriptions
3. The LLM analyzes the available tools and selects the appropriate one(s) for retrieving Instana alerts
4. The client executes the chosen tool(s) through the Instana MCP server
5. Results (latest alerts) are returned to the LLM
6. The LLM formulates a natural language response
7. The response is displayed to you

```mermaid
sequenceDiagram
    participant User
    participant ChatBot as MCP Host
    participant MCPClient as MCP Client
    participant MCPServer as Instana MCP Server
    participant LLM
    participant Instana as Instana Instance

    ChatBot->>MCPClient: Load available tools from MCP Server
    MCPClient->>MCPServer: Request available tool list
    MCPServer->>MCPClient: Return list of available tools
    User->>ChatBot: Ask "Show me the latest alerts from Instana for application robot-shop"
    ChatBot->>MCPClient: Forward query
    MCPClient->>LLM: Send query and tool description
    LLM->>MCPClient: Select appropriate tool(s) for Instana alert query
    MCPClient->>MCPServer: Execute selected tool(s)
    MCPServer->>Instana: Retrieve alerts for application robot-shop
    MCPServer->>MCPClient: Send alerts of Instana result
    MCPClient->>LLM: Forward alerts of Instana
    LLM->>ChatBot: Generate natural language response for Instana alerts
    ChatBot->>User: Show Instana alert response
```

## Prerequisites

### Option 1: Install from PyPI (Recommended)

The easiest way to use mcp-instana is to install it directly from PyPI:

```shell
pip install mcp-instana
```

After installation, you can run the server using the `mcp-instana` command directly.

### Option 2: Development Installation

For development or local customization, you can clone and set up the project locally.

#### Installing uv

This project uses `uv`, a fast Python package installer and resolver. To install `uv`, you have several options:

**Using pip:**
```shell
pip install uv
```

**Using Homebrew (macOS):**
```shell
brew install uv
```

For more installation options and detailed instructions, visit the [uv documentation](https://github.com/astral-sh/uv).

#### Setting Up the Environment

After installing `uv`, set up the project environment by running:

```shell
uv sync
```

### Header-Based Authentication for Streamable HTTP Mode

When using **Streamable HTTP mode**, you must pass Instana credentials via HTTP headers. This approach enhances security and flexibility by:

- Avoiding credential storage in environment variables
- Enabling the use of different credentials for different requests
- Supporting shared environments where environment variable modification is restricted

**Required Headers:**
- `instana-base-url`: Your Instana instance URL
- `instana-api-token`: Your Instana API token

**Authentication Flow:**
1. HTTP headers (`instana-base-url`, `instana-api-token`) must be present in each request
2. Requests without these headers will fail

This design ensures secure credential transmission where credentials are only sent via headers for each request, making it suitable for scenarios requiring different credentials or avoiding credential storage in environment variables.

## Starting the Local MCP Server

Before configuring any MCP client (Claude Desktop, GitHub Copilot, or custom MCP clients), you need to start the local MCP server. The server supports two transport modes: **Streamable HTTP** and **Stdio**.

### Server Command Options

#### Using the CLI (PyPI Installation)

If you installed mcp-instana from PyPI, use the `mcp-instana` command:

```bash
mcp-instana [OPTIONS]
```

#### Using Development Installation

For local development, use the `uv run` command:

```bash
uv run src/core/server.py [OPTIONS]
```

**Available Options:**
- `--transport <mode>`: Transport mode (choices: `streamable-http`, `stdio`)
- `--debug`: Enable debug mode with additional logging
- `--log-level <level>`: Set the logging level (choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `--tools <categories>`: Comma-separated list of tool categories to enable (e.g., infra,app,events,automation,website). Enabling a category will also enable its related prompts. For example: `--tools infra` enables the infra tools and all infra-related prompts.
- `--list-tools`: List all available tool categories and exit
- `--port <port>`: Port to listen on (default: 8080)
- `--help`: Show help message and exit

### Starting in Streamable HTTP Mode

**Streamable HTTP mode** provides a REST API interface and is recommended for most use cases.

#### Using CLI (PyPI Installation)

```bash
# Start with all tools enabled (default)
mcp-instana --transport streamable-http

# Start with debug logging
mcp-instana --transport streamable-http --debug

# Start with a specific log level
mcp-instana --transport streamable-http --log-level WARNING

# Start with specific tool categories only
mcp-instana --transport streamable-http --tools infra,events

# Combine options (specific log level, custom tools)
mcp-instana --transport streamable-http --log-level DEBUG --tools app,events
```

#### Using Development Installation

```bash
# Start with all tools enabled (default)
uv run src/core/server.py --transport streamable-http

# Start with debug logging
uv run src/core/server.py --transport streamable-http --debug

# Start with a specific log level
uv run src/core/server.py --transport streamable-http --log-level WARNING

# Start with specific tool and prompts categories only
uv run src/core/server.py --transport streamable-http --tools infra,events

# Combine options (specific log level, custom tools and prompts)
uv run src/core/server.py --transport streamable-http --log-level DEBUG --tools app,events
```

**Key Features of Streamable HTTP Mode:**
- Uses HTTP headers for authentication (no environment variables needed)
- Supports different credentials per request
- Better suited for shared environments
- Default port: 8080
- Endpoint: `http://0.0.0.0:8080/mcp/`

### Starting in Stdio Mode

**Stdio mode** uses standard input/output for communication and requires environment variables for authentication.

#### Using CLI (PyPI Installation)

```bash
# Set environment variables first
export INSTANA_BASE_URL="https://your-instana-instance.instana.io"
export INSTANA_API_TOKEN="your_instana_api_token"

# Start the server (stdio is the default if no transport specified)
mcp-instana

# Or explicitly specify stdio mode
mcp-instana --transport stdio
```

#### Using Development Installation

```bash
# Set environment variables first
export INSTANA_BASE_URL="https://your-instana-instance.instana.io"
export INSTANA_API_TOKEN="your_instana_api_token"

# Start the server (stdio is the default if no transport specified)
uv run src/core/server.py

# Or explicitly specify stdio mode
uv run src/core/server.py --transport stdio
```

**Key Features of Stdio Mode:**
- Uses environment variables for authentication
- Direct communication via stdin/stdout
- Required for certain MCP client configurations

### Tool Categories

You can optimize server performance by enabling only the tools and prompts categories you need:

#### Using CLI (PyPI Installation)

```bash
# List all available categories
mcp-instana --list-tools

# Enable specific categories
mcp-instana --transport streamable-http --tools infra,app
mcp-instana --transport streamable-http --tools events
```

#### Using Development Installation

```bash
# List all available categories
uv run src/core/server.py --list-tools

# Enable specific categories
uv run src/core/server.py --transport streamable-http --tools infra,app
uv run src/core/server.py --transport streamable-http --tools events
```

**Available Categories:**
- **`infra`**: Infrastructure monitoring tools and prompts (resources, catalog, topology, analyze, metrics)
- **`app`**: Application performance tools and prompts (resources, metrics, alerts, catalog, topology, analyze, settings, global alerts)
- **`events`**: Event monitoring tools and prompts (Kubernetes events, agent monitoring)
- **`automation`**: Automation-related tools and prompts (action catalog, action history)
- **`website`**: Website monitoring tools and prompts (metrics, catalog, analyze, configuration)

### Verifying Server Status

Once started, you can verify the server is running:

**For Streamable HTTP mode:**
```bash
# Check server health
curl http://0.0.0.0:8080/mcp/

# Or with custom port
curl http://0.0.0.0:9000/mcp/
```

**For Stdio mode:**
The server will start and wait for stdin input from MCP clients.

### Common Startup Issues

**Certificate Issues:**
If you encounter SSL certificate errors, ensure your Python environment has access to system certificates:
```bash
# macOS - Install certificates for Python
/Applications/Python\ 3.13/Install\ Certificates.command
```

**Port Already in Use:**
If port 8080 is already in use, specify a different port:
```bash
uv run src/core/server.py --transport streamable-http --port 9000
```

**Missing Dependencies:**
Ensure all dependencies are installed:
```bash
uv sync
```

## Setup and Usage

### Claude Desktop

Claude Desktop supports both Streamable HTTP and Stdio modes for MCP integration.

Configure Claude Desktop by editing the configuration file:

**File Locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### Streamable HTTP Mode

The Streamable HTTP mode provides a REST API interface for MCP communication using JSON-RPC over HTTP.

**Step 1: Start the MCP Server in Streamable HTTP Mode**

Before configuring Claude Desktop, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](#starting-the-local-mcp-server) section for detailed instructions.

**Step 2: Configure Claude Desktop**

Configure Claude Desktop to pass Instana credentials via headers:

```json:claude_desktop_config.json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "npx",
      "args": [
        "mcp-remote", "http://0.0.0.0:8080/mcp/",
        "--allow-http",
        "--header", "instana-base-url: https://your-instana-instance.instana.io",
        "--header", "instana-api-token: your_instana_api_token"
      ]
    }
  }
}
```

**Note:** To use npx, we recommend first installing NVM (Node Version Manager), then using it to install Node.js.
Installation instructions are available at: https://nodejs.org/en/download

**Step 3: Test the Connection**

Restart Claude Desktop. You should now see Instana MCP Server in the Claude Desktop interface as shown below:

![](./images/claudeTools.png)

You can now run queries in Claude Desktop:

```
get me all endpoints from Instana
```
![](./images/claudeResponse.png)

#### Stdio Mode

**Configuration using CLI (PyPI Installation - Recommended):**

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": ["--transport", "stdio"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

**Note:** If you encounter "command not found" errors, use the full path to mcp-instana. Find it with `which mcp-instana` and use that path instead.

**Configuration using Development Installation:**

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "uv",
      "args": [
        "--directory",
        "<path-to-mcp-instana-folder>",
        "run",
        "src/core/server.py"
      ],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

### GitHub Copilot

GitHub Copilot supports MCP integration through VS Code configuration.
For GitHub Copilot integration with VS Code, refer to this [setup guide](https://code.visualstudio.com/docs/copilot/setup).

#### Streamable HTTP Mode

**Step 1: Start the MCP Server in Streamable HTTP Mode**

Before configuring VS Code, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](#starting-the-local-mcp-server) section for detailed instructions.

**Step 2: Configure VS Code**

Refer to [Use MCP servers in VS Code](https://code.visualstudio.com/docs/copilot/chat/mcp-servers) for detailed configuration.

You can directly create or update `.vscode/mcp.json` with the following configuration:

```json:.vscode/mcp.json
{
  "servers": {
    "Instana MCP Server": {
      "command": "npx",
      "args": [
        "mcp-remote", "http://0.0.0.0:8080/mcp/",
        "--allow-http",
        "--header", "instana-base-url: https://your-instana-instance.instana.io",
        "--header", "instana-api-token: your_instana_api_token"
      ],
      "env": {
        "PATH": "/usr/local/bin:/bin:/usr/bin",
        "SHELL": "/bin/sh"
      }
    }
  }
}
```

**Note:** Replace the following values with your actual configuration:
- `instana-base-url`: Your Instana instance URL
- `instana-api-token`: Your Instana API token
- `command`: Update the npx path to match your system's Node.js installation (e.g., `/path/to/your/node/bin/npx`)
- Environment variables: Adjust PATH and other environment variables as needed for your system


#### Stdio Mode

**Step 1: Create VS Code MCP Configuration**

**Using CLI (PyPI Installation - Recommended):**

Create `.vscode/mcp.json` in your project root:

```json:.vscode/mcp.json
{
  "servers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": ["--transport", "stdio"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

**Using Development Installation:**

Create `.vscode/mcp.json` in your project root:

```json:.vscode/mcp.json
{
  "servers": {
    "Instana MCP Server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/your/project/mcp-instana",
        "run",
        "src/core/server.py"
      ],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

**Note:** Replace the following values with your actual configuration:
- For CLI installation: Ensure `mcp-instana` is in your PATH
- For development installation: 
  - `command`: Update the uv path to match your system's uv installation (e.g., `/path/to/your/uv/bin/uv` or `/usr/local/bin/uv`)
  - `--directory`: Update with the absolute path to your mcp-instana project directory
- `INSTANA_BASE_URL`: Your Instana instance URL
- `INSTANA_API_TOKEN`: Your Instana API token

**Step 2: Manage Server in VS Code**

1. **Open `.vscode/mcp.json`** - you'll see server management controls at the top
2. **Click `Start`** next to `Instana MCP Server` to start the server
3. Running status along with the number of tools indicates the server is running

**Step 3: Test Integration**

Switch to Agent Mode in GitHub Copilot and reload tools.
Here is an example of a GitHub Copilot response:

![GitHub Copilot Response](./images/copilotResponse.png)

## Supported Features

- [ ] Application
  - [ ] Application Metrics
    - [ ] Application Metrics
    - [ ] Endpoint Metrics
    - [ ] Service Metrics
    - [ ] Data Metrics
  - [x] Application Resources
    - [x] Get Applications Endpoints
    - [x] Get Applications
    - [x] Get Services
    - [x] Get Application Services
  - [x] Application Alert Configuration
    - [x] Get All Smart Alert Configurations
    - [x] Get Smart Alert Configuration
    - [x] Get Smart Alert Config Versions
    - [ ] Create Smart Alert Configuration
    - [ ] Update Smart Alert Configuration
    - [x] Delete Smart Alert Configuration
    - [ ] Recalculate Smart Alert Config Baseline
    - [x] Enable Application Alert Config
    - [x] Disable Smart Alert Config
    - [x] Restore Smart Alert Config
- [ ] Infrastructure
  - [ ] Infrastructure Analyze
    - [x] Get Available Metrics
    - [ ] Get infrastructure entities
    - [ ] Get grouped entities with aggregated metrics
    - [x] Get available plugins/entity types
  - [x] Infrastructure Catalog
    - [x] Get Payload Keys By plugin ID
    - [x] Get Infrastructure Catalog Metrics
    - [x] Get Infrastructure Catalog Plugins
    - [x] Get Infrastructure Catalog Plugins with Custom Metrics
    - [x] Get Infrastructure Catalog Search Fields
    - [x] Get Infrastructure Catalog Search Fields with Custom Metrics
    - [x] Get Tag Catalog
    - [x] Get Tag Catalog ALL
  - [ ] Infrastructure Resources
    - [x] Get Monitoring State
    - [ ] Get plugin Payload
    - [x] Search Snapshots
    - [x] Get Snapshot Details for single Snapshot ID
    - [x] Get Details for Multiple Snapshot IDs
    - [x] Software Versions
  - [x] Infrastructure Topology
    - [x] Get Hosts for Snapshot
    - [x] Get Topology
  - [x] Events
    - [x] Events
      - [x] Get Event
      - [x] Get Events by IDs
      - [x] Get Agent Monitoring Events
      - [x] Get Kubernetes Info Events
      - [x] Get Issues
      - [x] Get Incidents
      - [x] Get Changes

## Available Tools

| Tool                                                          | Category                       | Description                                            |
|---------------------------------------------------------------|--------------------------------|------------------------------------------------------- |
| `get_application_metrics`                                     | Application Metrics            | Get ApplicationMetrics                                 |
| `get_endpoints_metrics`                                       | Application Metrics            | Get Endpoint metrics                                   |
| `get_services_metrics`                                        | Application Metrics            | Get Service metrics                                    |
| `get_application_data_metrics_v2`                             | Application Metrics            | Get Application Data Metrics                           |
| `get_applications`                                            | Application Resources          | Get applications                                       |
| `get_application_services`                                    | Application Resources          | Get applications/services                              |
| `get_application_endpoints`                                   | Application Resources          | Get endpoints                                          |
| `get_services`                                                | Application Resources          | Get services                                           |
| `get_monitoring_state`                                        | Infrastructure Resources       | Monitored host count                                   |
| `get_plugin_payload`                                          | Infrastructure Resources       | Get a payload for a snapshot                           |
| `get_snapshots`                                               | Infrastructure Resources       | Search snapshots                                       |
| `post_snapshots`                                              | Infrastructure Resources       | Get snapshot details for multiple snapshots            |
| `get_snapshot`                                                | Infrastructure Resources       | Get snapshot details                                   |
| `software_versions`                                           | Infrastructure Resources       | Get installed software                                 |
| `get_available_payload_keys_by_plugin_id`                     | Infrastructure Catalog         | Get Payload Keys By plugin ID                          |
| `get_infrastructure_catalog_metrics`                          | Infrastructure Catalog         | Get Infrastructure Catalog Metrics                     |
| `get_infrastructure_catalog_plugins`                          | Infrastructure Catalog         | Get Infrastructure Catalog Plugins                     |
| `get_infrastructure_catalog_plugins_with_custom_metrics`      | Infrastructure Catalog         | Get Infrastructure Catalog Plugins with Custom Metrics |
| `get_infrastructure_catalog_search_fields`                    | Infrastructure Catalog         | Get Infrastructure Catalog Search Fields               |
| `get_tag_catalog`                                             | Infrastructure Catalog         | Get Tag Catalog                                        |
| `get_tag_catalog_all`                                         | Infrastructure Catalog         | Get Tag Catalog ALL                                    |
| `get_related_hosts`                                           | Infrastructure Topology        | Get Related Hosts                                      |
| `get_topology`                                                | Infrastructure Topology        | Get Topology                                           |
| `get_available_metrics`                                       | Infrastructure Analyze         | Get Available Metrics                                  |
| `get_entities`                                                | Infrastructure Analyze         | Get infrastructure entities                            |
| `get_aggregated_entity_groups`                                | Infrastructure Analyze         | Get grouped entities with aggregated metrics           |
| `get_available_plugins`                                       | Infrastructure Analyze         | Get available entity types                             |
| `get_application_alert_configs`                               | Application Alert Configuration| Get All Smart Alert Configurations                     |
| `find_application_alert_config`                               | Application Alert Configuration| Get Smart Alert Configuration                          |
| `find_application_alert_config_versions`                      | Application Alert Configuration| Get Smart Alert Config Versions                        |
| `create_application_alert_config`                             | Application Alert Configuration| Create Smart Alert Configuration                       |
| `update_application_alert_config`                             | Application Alert Configuration| Update Smart Alert Configuration                       |
| `delete_application_alert_config`                             | Application Alert Configuration| Delete Smart Alert Configuration                       |
| `update_application_historic_baseline`                        | Application Alert Configuration| Recalculate Smart Alert Config Baseline                |
| `enable_application_alert_config`                             | Application Alert Configuration| Enable Application Alert Config                        |
| `disable_application_alert_config`                            | Application Alert Configuration| Disable Smart Alert Config                             |
| `restore_application_alert_config`                            | Application Alert Configuration| Restore Smart Alert Config                             |
| `get_event`                                                   | Events                         | Get Specific Event by ID                               |
| `get_kubernetes_info_events`                                  | Events                         | Get Kubernetes Info Events                             |
| `get_agent_monitoring_events`                                 | Events                         | Get Agent Monitoring Events                            |
| `get_issues`                                                  | Events                         | Get Issues                                             |
| `get_incidents`                                               | Events                         | Get Incidents                                          |
| `get_changes`                                                 | Events                         | Get Changes                                            |
| `get_events_by_ids`                                           | Events                         | Get Events by IDs                                      |


## Tool Filtering

The MCP server supports selective tool loading to optimize performance and reduce resource usage. You can enable only the tool categories you need for your specific use case.

### Available Tool Categories

- **`infra`**: Infrastructure monitoring tools
  - Infrastructure Resources: Host monitoring, snapshot management, software inventory
  - Infrastructure Catalog: Plugin metadata, metrics definitions, tag management
  - Infrastructure Topology: Host relationships and system topology visualization
  - Infrastructure Analyze: Entity metrics, aggregation, and plugin discovery
  - Infrastructure Metrics: Performance data collection

- **`app`**: Application performance tools
  - Application Resources: Service and endpoint discovery
  - Application Metrics: Performance measurement across application components
  - Application Alert Configuration: Smart alert management
  - Application Catalog: Metadata and definitions
  - Application Topology: Service dependency mapping
  - Application Analyze: Application performance analysis
  - Application Settings: Configuration management
  - Application Global Alert: Global alert management

- **`events`**: Event monitoring tools
  - Events: Kubernetes events, agent monitoring, incidents, issues, changes and system event tracking

- **`automation`**: Automation-related tools
  - Action Catalog: Automation action discovery and management
  - Action History: Tracking and managing automation action history

- **`website`**: Website monitoring tools
  - Website Metrics: Performance measurement for websites
  - Website Catalog: Website metadata and definitions
  - Website Analyze: Website performance analysis
  - Website Configuration: Website configuration management

### Usage Examples

#### Using CLI (PyPI Installation)

```bash
# Enable only infrastructure and events tools
mcp-instana --tools infra,events --transport streamable-http

# Enable only application tools
mcp-instana --tools app --transport streamable-http

# Enable automation and website tools
mcp-instana --tools automation,website --transport streamable-http

# Enable all tools (default behavior)
mcp-instana --transport streamable-http

# List all available tool categories and their tools
mcp-instana --list-tools
```

#### Using Development Installation

```bash
# Enable only infrastructure and events tools
uv run src/core/server.py --tools infra,events --transport streamable-http

# Enable only application tools
uv run src/core/server.py --tools app --transport streamable-http

# Enable automation and website tools
uv run src/core/server.py --tools automation,website --transport streamable-http

# Enable all tools (default behavior)
uv run src/core/server.py --transport streamable-http

# List all available tool categories and their tools
uv run src/core/server.py --list-tools
```

### Benefits of Tool Filtering

- **Performance**: Reduced startup time and memory usage
- **Security**: Limit exposure to only necessary APIs
- **Clarity**: Focus on specific use cases (e.g., only infrastructure monitoring)
- **Resource Efficiency**: Lower CPU and network usage

## Example Prompts

Here are some example prompts (with their corresponding results) that you can use to get started with the Instana Observability Platform API:

- **Query 1**
```
We want to understand what search criteria are available in Instana so that 
we can find the correct search tags for specific entities and 
build complex queries to filter entities in Instana. Can you help with this?
```

- **Result 1**
```
Here is the list of search criteria available in Instana:

entity.jvm.dropwizard.timer
entity.otel
host.name
entity.dropwizard.meter
entity.springboot.name
entity.kubernetes.node.name
entity.tuxedoapp.tuxedoService.name
entity.ace.integrationServer.name
entity.containerd.containerIdentity.tuxedo.domain.tuxconfig
entity.host.mac
```

- **Query 2**
```
Our application deployments seem to be failing intermittently.
Can you fetch recent Kubernetes info events from Instana for the last 1 day
to help identify what might be causing these deployment issues?
```

- **Result 2**
![Kubernetes Events](./images/kubernetesEvents.png)

- **Query 3**
```
We are seeing errors in agent logs and experiencing issues with agent behavior. 
Can you fetch recent agent monitoring events from Instana 
to help figure out what might be causing these issues?
```

- **Result 3**
```
The recent agent monitoring events from Instana indicate that there are several issues with the agent behavior, including:

JVM attach generic issues: There are 36 events related to JVM attach generic issues, affecting multiple entities such as Process (/etc/java-8-64bit-jdk/jdk8u402-b06/bin/java), Process (/etc/java-16-64bit-jdk/jdk-16.0.2+7/bin/java), and others.
Python sensor not installed: There are 7 events related to Python sensor not installed issues, affecting entities such as Process (/usr/bin/python3), Process (/usr/libexec/platform-python), and others.
PostgreSQL authentication failed: There are 2 events related to PostgreSQL authentication failed issues, affecting entities such as PostgreSQL DB (PostgreSQL) and PostgreSQL DB (PostgreSQL @5432).
PostgreSQL connection failed: There is 1 event related to PostgreSQL connection failed issues, affecting the entity PostgreSQL DB (PostgreSQL @5432).
Spring Boot actuator not configured: There is 1 event related to Spring Boot actuator not configured issues, affecting the entity Spring Boot App (sqs-demo-application 0.0.1).
These issues may be causing the errors in the agent logs and affecting the agent behavior. It is recommended to investigate and resolve these issues to ensure proper agent functionality.
```

- **Query 4**
```
We're setting up comprehensive application performance monitoring across our entire infrastructure. 
Can you retrieve all the applications that Instana has discovered? I need to see which applications are available 
so I can configure monitoring dashboards, set up alerts, and establish performance baselines for each service in our environment.
```

- **Result 4**
```
The discovered applications are:

Ovcharov
AWS Resources
Cedric OTel
Cedric Sein Otel
Col
Damian - Sample Go App
Fofo
INSTANA-ECOSYSTEM-SAP-CF
Kate
```

- **Query 5**
```
We're investigating an issue for the snapshot id "qjNuS6pmtYkxCBKwqsfxvHylisU" and 
want to see which hosts might be affected. Can you get the hosts for this snapshot id?
```

- **Result 5**
```
The hosts related to the snapshot with ID "qjNuS6pmtYkxCBKwqsfxvHylisU" are:

XDrSHZ5iq0BV_bPxQ6FFGsbxqv4
There is 1 host related to this snapshot.
```

- **Query 6**
```
We want to get specific metrics for Amazon MQ in Instana. Can you show all possible tags
I can use for the plugin awsMq?
```

- **Result 6**
```
The following tags are available for the plugin "awsMq":

aws.accountId
aws.arn
aws.mq.brokerName
aws.mq.deploymentMode
aws.mq.engineVersion
aws.mq.instanceType
dfq.selftype
dfq.type
label
metricId
type
zone
These tags can be used to filter and group metrics for Amazon MQ in Instana.
```

- **Query 7**
```
We want to troubleshoot issues with custom metric collection, hence need details of the
plugins which are configured with custom metrics in Instana. Can you help us get the details?
```

- **Result 7**
```
JVM and OpenTelemetry SDK. The JVM plugin is identified by the label "JVM" and the plugin ID "jvmRuntimePlatform". 
The OpenTelemetry SDK plugin is identified by the label "OpenTelemetry SDK" and the plugin ID "openTelemetry".
```

- **Query 8**
```
We want to see what kind of systems Instana is tracking. We want to explore the monitoring 
capabilities of our Instana installation. Please give me the list of monitored entity types.
```

- **Result 8**
```
The list includes various plugins such as businessActivity, azureManagedHSM, kafkaConnectWorker, and many more.
The total number of available plugins is 395, but only the first 50 are shown in the output.
```

- **Query 9**
```
We're having performance issues with our db2Database. What payload keys are available for the
db2Database plugin so I can access detailed monitoring data?
```

- **Result 9**
```
The available payload keys for the db2Database plugin are:

tableSpaceNamesSense
topqueries
diaglogentries
dbConfig
dbmConfig
lockWaits
runstats
dbutilities
toptotalstmts
idlogdiskwait
idhadrstats
reorgtablesize
```

- **Query 10**
```
We have SLAs for our cryptographic services. What Azure Managed HSM metrics can help 
monitor service levels using the azureManagedHSM plugin?
```

- **Result 10**
```
The azureManagedHSM plugin provides three metrics that can help monitor service levels for cryptographic services:
1. Total Service Api Hits: This metric measures the total number of API hits for the service.
2. Overall Service Api Latency: This metric measures the overall latency of service API requests.
3. Overall Service Availability: This metric measures the availability of the service.
```

## Docker Deployment

The MCP Instana server can be deployed using Docker for production environments. The Docker setup is optimized for security, performance, and minimal resource usage.

### Docker Architecture

The project uses a **two-file dependency management strategy**:

#### **pyproject.toml** (Development)
- **Purpose**: Full development environment with all tools
- **Dependencies**: 20 essential + 8 development dependencies (pytest, ruff, coverage, etc.)
- **Usage**: Local development, testing, and CI/CD
- **Size**: Larger but includes all development tools

#### **pyproject-runtime.toml** (Production)
- **Purpose**: Minimal production runtime dependencies only
- **Dependencies**: 20 essential dependencies only
- **Usage**: Docker production builds
- **Size**: Optimized for minimal image size and security

### Building the Docker Image

#### **Prerequisites**
- Docker installed and running
- Access to the project source code

#### **Build Command**
```bash
# Build the optimized production image
docker build -t mcp-instana .

# Build with a specific tag
docker build -t mcp-instana:v1.0.0 .
```

#### **What the Build Does**
1. **Multi-stage build** for optimal size and security
2. **Builder stage**: Installs only runtime dependencies from `pyproject-runtime.toml`
3. **Runtime stage**: Creates minimal production image with non-root user
4. **Security**: No hardcoded secrets, proper user permissions
5. **Optimization**: Only essential dependencies (20 vs 95+ in development)

### Running the Docker Container

#### **Basic Usage**
```bash
# Run with environment variables (recommended)
docker run -p 8080:8080 \
  -e INSTANA_API_TOKEN=your_instana_token \
  -e INSTANA_BASE_URL=https://your-instana-instance.instana.io \
  mcp-instana

# Run with custom port
docker run -p 8081:8080 \
  -e INSTANA_API_TOKEN=your_instana_token \
  -e INSTANA_BASE_URL=https://your-instana-instance.instana.io \
  mcp-instana
```

#### **Environment Variables**
The container requires the following environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `INSTANA_API_TOKEN` | Your Instana API token | `your_instana_token` |
| `INSTANA_BASE_URL` | Your Instana instance URL | `https://your-instana-instance.instana.io` |
| `PORT` | Server port (optional, defaults to 8080) | `8080` |

#### **Docker Compose Example**
```yaml
version: '3.8'
services:
  mcp-instana:
    build: .
    ports:
      - "8080:8080"
    environment:
      - INSTANA_API_TOKEN=${INSTANA_API_TOKEN}
      - INSTANA_BASE_URL=${INSTANA_BASE_URL}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://127.0.0.1:8080/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Docker Security Features

#### **Security Best Practices Implemented**
- ✅ **Non-root user**: Container runs as `mcpuser` (not root)
- ✅ **No hardcoded secrets**: All credentials passed via environment variables
- ✅ **Minimal dependencies**: Only 20 essential runtime dependencies
- ✅ **Multi-stage build**: Build tools don't make it to final image
- ✅ **Health checks**: Built-in container health monitoring
- ✅ **Optimized base image**: Uses `python:3.11-slim`

#### **Image Size Optimization**
- **Original approach**: 95+ dependencies → ~1-2GB+ image
- **Optimized approach**: 20 dependencies → ~266MB image
- **Size reduction**: ~70-80% smaller images
- **Benefits**: Faster deployments, lower storage costs, reduced attack surface

### Testing the Docker Container

#### **Health Check**
```bash
# Check if container is healthy
docker ps

# Test the MCP endpoint
curl http://localhost:8080/mcp/
```

#### **MCP Inspector Testing**
```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8080/mcp/
```

#### **Logs and Debugging**
```bash
# View container logs
docker logs <container_id>

# Follow logs in real-time
docker logs -f <container_id>

# Execute commands in running container
docker exec -it <container_id> /bin/bash
```

### Production Deployment

#### **Recommended Production Setup**
1. **Use environment variables** for all secrets
2. **Set up proper logging** and monitoring
3. **Configure health checks** for container orchestration
4. **Use container orchestration** (Kubernetes, Docker Swarm, etc.)
5. **Implement proper backup** and disaster recovery

#### **Kubernetes Example**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-instana
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-instana
  template:
    metadata:
      labels:
        app: mcp-instana
    spec:
      containers:
      - name: mcp-instana
        image: mcp-instana:latest
        ports:
        - containerPort: 8080
        env:
        - name: INSTANA_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: instana-secrets
              key: api-token
        - name: INSTANA_BASE_URL
          value: "https://your-instana-instance.instana.io"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Troubleshooting

### **Docker Issues**

#### **Container Won't Start**
```bash
# Check container logs
docker logs <container_id>

# Common issues:
# 1. Missing environment variables
# 2. Port already in use
# 3. Invalid Instana credentials
```

#### **Connection Issues**
```bash
# Test container connectivity
docker exec -it <container_id> curl http://127.0.0.1:8080/health

# Check port mapping
docker port <container_id>
```

#### **Performance Issues**
```bash
# Check container resource usage
docker stats <container_id>

# Monitor container health
docker inspect <container_id> | grep -A 10 Health
```

### **General Issues**

- **GitHub Copilot**
  - If you encounter issues with GitHub Copilot, try starting/stopping/restarting the server in the `mcp.json` file and keep only one server running at a time.

- **Certificate Issues** 
  - If you encounter certificate issues, such as `[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate`: 
    - Check that you can reach the Instana API endpoint using `curl` or `wget` with SSL verification. 
      - If that works, your Python environment may not be able to verify the certificate and might not have access to the same certificates as your shell or system. Ensure your Python environment uses system certificates (macOS). You can do this by installing certificates to Python:
      `//Applications/Python\ 3.13/Install\ Certificates.command`
    - If you cannot reach the endpoint with SSL verification, try without it. If that works, check your system's CA certificates and ensure they are up-to-date.
