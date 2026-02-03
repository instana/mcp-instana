<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
<!-- mcp-name: io.github.instana/mcp-instana -->

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
    - [Kiro Setup](#kiro-setup)
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
      - [**Prerequisites**](#prerequisites)
      - [**Build Command**](#build-command)
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
- `--tools <categories>`: Comma-separated list of tool categories to enable (e.g., infra,app,events,website). Enabling a category will also enable its related prompts. For example: `--tools infra` enables the infra tools and all infra-related prompts.
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
### Kiro Setup

Kiro is an agentic IDE, not an extension that can be downloaded into VS Code or some other IDE.

**Step 1: Download and install Kiro for your operating system from https://kiro.dev/.**

**Step 2: After installation, launch Kiro and open any project in the IDE.**
![alt text](./images/open-kiro.png)

**Step 3: Click the Kiro (Ghost) icon on the left sidebar to access Kiro's features.**
![alt text](./images/kiro-features.png)

**Step 4: Select the Edit Config icon in the top right corner of the MCP Servers section.**
![alt text](./images/edir-kiro-config.png)

**Step 5: Open the MCP server configuration file (mcp.json), similar to how it works in Claude, and update it with your server's name, commands, and headers as shown in the image below.**

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "npx",
      "args": [
        "mcp-remote", "<YOUR_MCP_PORT>/mcp",
        "--allow-http",
        "--header", "instana-base-url: <INSTANA_BASE_URL>",
        "--header", "instana-api-token: <INSTANA_API_TOKEN>"
      ]
    }
  }
}
```

**Step 6: After saving the file, Click the Enable MCP button and you'll see your MCP server and its available tools appear in the bottom-left section of Kiro.**
![alt text](./images/enable-kiro-mcp.png)

**Step 7: Go to the AI Chat panel, enter a prompt related to your MCP server, and view the response directly within Kiro.**
![alt text](./images/kiro-prompt.png)

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

- [x] **Unified Application & Infrastructure Management** (`manage_instana_resources`)
  - [x] Application Metrics
    - [x] Query application metrics with flexible filtering
    - [x] List services and endpoints
    - [x] Group by tags and aggregate metrics
  - [x] Application Alert Configuration
    - [x] Find active alert configurations
    - [x] Get alert configuration versions
    - [x] Create, update, and delete alert configurations
    - [x] Enable, disable, and restore alert configurations
    - [x] Update historic baselines
  - [x] Global Application Alert Configuration
    - [x] Manage global alert configurations
    - [x] Version control for global alerts
  - [x] Application Settings
    - [x] Manage application perspectives
    - [x] Configure endpoints and services
    - [x] Manage manual services
  - [x] Application Catalog
    - [x] Get application tag catalog
    - [x] Get application metric catalog
- [x] **Infrastructure Analysis** (`analyze_infrastructure_elicitation`)
  - [x] Two-pass elicitation for entity/metric queries
  - [x] Support for multiple entity types (JVM, Kubernetes, Docker, etc.)
  - [x] Flexible metric aggregation (max, mean, sum, etc.)
  - [x] Advanced filtering by tags and properties
  - [x] Grouping and ordering capabilities
  - [x] Time range queries
- [x] **Events**
    - [x] Events
      - [x] Get Event
      - [x] Get Events by IDs
      - [x] Get Agent Monitoring Events
      - [x] Get Kubernetes Info Events
      - [x] Get Issues
      - [x] Get Incidents
      - [x] Get Changes
- [x] Website
  - [x] Website Metrics
    - [ ] Get Website Page Load
    - [x] Get Website Beacon Metrics V2
  - [x] Website Catalog
    - [x] Get Website Catalog Metrics
    - [x] Get Website Catalog Tags
    - [ ] Get Website Tag Catalog
  - [x] Website Analyze
    - [x] Get Website Beacon Groups
    - [x] Get Website Beacons
  - [x] Website Configuration
    - [x] Get Websites
    - [x] Get Website
    - [x] Create Website
    - [x] Delete Website
    - [x] Rename Website
    - [x] Get Website Geo Location 
    - [x] Update Website Geo Location 
    - [x] Get Website IP Masking 
    - [x] Update Website IP Masking 
    - [x] Get Website Geo Mapping Rules
    - [ ] Set Website Geo Mapping Rules
    - [ ] Upload Source Map File
    - [ ] Clear Source Map Upload
- [x] **Custom Dashboards** (`manage_custom_dashboards`)
  - [x] Get all custom dashboards
  - [x] Get specific dashboard by ID
  - [x] Create new custom dashboard
  - [x] Update existing custom dashboard
  - [x] Delete custom dashboard
  - [x] Get shareable users for dashboard
  - [x] Get shareable API tokens for dashboard

## Available Tools

| Tool                                                          | Category                       | Description                                            |
|---------------------------------------------------------------|--------------------------------|------------------------------------------------------- |
| `manage_instana_resources`                                    | Application & Infrastructure   | Unified tool for managing application metrics, alert configs, settings, and catalog |
| `manage_custom_dashboards`                                    | Custom Dashboards              | Unified tool for managing custom dashboard CRUD operations |
| `analyze_infrastructure_elicitation`                          | Infrastructure Analyze         | Two-pass infrastructure analysis with entity/metric elicitation |
| `get_actions`                                                 | Automation                     | Get available automation actions from action catalog   |
| `get_action_details`                                          | Automation                     | Get detailed information about a specific action       |
| `get_action_types`                                            | Automation                     | Get available action types                             |
| `get_action_tags`                                             | Automation                     | Get available action tags                              |
| `get_action_matches`                                          | Automation                     | Get action matches for a given search space            |
| `submit_automation_action`                                    | Automation                     | Submit an automation action for execution              |
| `get_action_instance_details`                                 | Automation                     | Get details of an automation action run result         |
| `list_action_instances`                                       | Automation                     | List automation action run results                     |
| `delete_action_instance`                                      | Automation                     | Delete an automation action run result                 |
| `get_event`                                                   | Events                         | Get Specific Event by ID                               |
| `get_kubernetes_info_events`                                  | Events                         | Get Kubernetes Info Events                             |
| `get_agent_monitoring_events`                                 | Events                         | Get Agent Monitoring Events                            |
| `get_issues`                                                  | Events                         | Get Issues                                             |
| `get_incidents`                                               | Events                         | Get Incidents                                          |
| `get_changes`                                                 | Events                         | Get Changes                                            |
| `get_events_by_ids`                                           | Events                         | Get Events by IDs                                      |
| `get_website_page_load`                                       | Website Metrics                | Get website monitoring beacons for a specific page load|
| `get_website_beacon_metrics_v2`                               | Website Metrics                | Get website beacon metrics using the v2 API            |
| `get_website_catalog_metrics`                                 | Website Catalog                | Get website monitoring metrics catalog                 |
| `get_website_catalog_tags`                                    | Website Catalog                | Get website monitoring tags catalog                    |
| `get_website_tag_catalog`                                     | Website Catalog                | Get website monitoring tag catalog                     |
| `get_website_beacon_groups`                                   | Website Analyze                | Get grouped website beacon metrics                     |
| `get_website_beacons`                                         | Website Analyze                | Get all website beacon metrics                         |
| `get_websites`                                                | Website Configuration          | Get all websites                                       |
| `get_website`                                                 | Website Configuration          | Get a specific website by ID                           |
| `create_website`                                              | Website Configuration          | Create a new website configuration                     |
| `delete_website`                                              | Website Configuration          | Delete a website configuration                         |
| `rename_website`                                              | Website Configuration          | Rename a website configuration                         |
| `get_website_geo_location_configuration`                      | Website Configuration          | Get geo-location configuration for a website           |
| `update_website_geo_location_configuration`                   | Website Configuration          | Update geo-location configuration for a website        |
| `get_website_ip_masking_configuration`                        | Website Configuration          | Get IP masking configuration for a website             |
| `update_website_ip_masking_configuration`                     | Website Configuration          | Update IP masking configuration for a website          |
| `get_website_geo_mapping_rules`                               | Website Configuration          | Get custom geo mapping rules for website               |
| `set_website_geo_mapping_rules`                               | Website Configuration          | Set custom geo mapping rules for website               |
| `upload_source_map_file`                                      | Website Configuration          | Upload source map file for a website                   |
| `clear_source_map_upload_configuration`                       | Website Configuration          | Clear source map upload configuration for a website    |


## Tool Filtering

The MCP server supports selective tool loading to optimize performance and reduce resource usage. You can enable only the tool categories you need for your specific use case.

### Available Tool Categories

- **`router`**: Unified application and infrastructure management
  - `manage_instana_resources`: Single tool for application metrics, alert configurations, settings, and catalog
  - Supports application perspectives, endpoints, services, and manual services
  - Manages both application-specific and global alert configurations
  - Provides access to application tag catalog and metric catalog

- **`dashboard`**: Custom dashboard management
  - `manage_custom_dashboards`: CRUD operations for custom dashboards
  - Supports dashboard creation, retrieval, updates, and deletion
  - Manages shareable users and API tokens for dashboards

- **`infra`**: Infrastructure analysis tools
  - `analyze_infrastructure_elicitation`: Two-pass infrastructure analysis with entity/metric elicitation
  - Supports multiple entity types (JVM, Kubernetes, Docker, hosts, databases, etc.)
  - Flexible metric aggregation, filtering, grouping, and time range queries

- **`automation`**: Automation action tools
  - Action catalog management and action execution
  - Action history and instance tracking

- **`events`**: Event monitoring tools
  - Events: Kubernetes events, agent monitoring, incidents, issues, changes and system event tracking

- **`website`**: Website monitoring tools
  - Website Metrics: Performance measurement for websites
  - Website Catalog: Website metadata and definitions
  - Website Analyze: Website performance analysis
  - Website Configuration: Website configuration management

### Usage Examples

#### Using CLI (PyPI Installation)

```bash
# Enable only router (unified app/infra management) and events tools
mcp-instana --tools router,events --transport streamable-http

# Enable only infrastructure analysis tools
mcp-instana --tools infra --transport streamable-http

# Enable router and infrastructure analysis
mcp-instana --tools router,infra --transport streamable-http

# Enable events and website tools
mcp-instana --tools events,website --transport streamable-http

# Enable dashboard and router tools
mcp-instana --tools dashboard,router --transport streamable-http

# Enable all tools (default behavior)
mcp-instana --transport streamable-http

# List all available tool categories and their tools
mcp-instana --list-tools
```

#### Using Development Installation

```bash
# Enable only router (unified app/infra management) and events tools
uv run src/core/server.py --tools router,events --transport streamable-http

# Enable only infrastructure analysis tools
uv run src/core/server.py --tools infra --transport streamable-http

# Enable router and infrastructure analysis
uv run src/core/server.py --tools router,infra --transport streamable-http

# Enable events and website tools
uv run src/core/server.py --tools events,website --transport streamable-http

# Enable dashboard and router tools
uv run src/core/server.py --tools dashboard,router --transport streamable-http

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
- Docker BuildKit for multi-architecture builds (enabled by default in recent Docker versions)

#### **Build Command**
```bash
# Build the optimized production image
docker build -t mcp-instana:latest .

# Build with a specific tag
docker build -t mcp-instana:< image_tag > .

#### **Run Command**
```bash
# Run the container (no credentials needed in the container)
docker run -p 8080:8080 mcp-instana

# Run with custom port
docker run -p 8081:8080 mcp-instana
```

## Troubleshooting

### **Docker Issues**

#### **Container Won't Start**
```bash
# Check container logs
docker logs <container_id>
# Common issues:
# 1. Port already in use
# 2. Invalid container image
# 3. Missing dependencies
# Credentials are passed via HTTP headers from the MCP client
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
```