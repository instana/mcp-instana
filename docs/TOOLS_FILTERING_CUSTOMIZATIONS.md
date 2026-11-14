# Tool Filtering & Customizations

By default, the MCP server exposes all available tools. Use the options below to load or show only the tool categories you need.

## Table of Contents

- [Available Categories](#available-categories)
- [Filtering Options](#filtering-options)
- [Command-Line Examples](#command-line-examples)
  - [Using CLI (PyPI Installation)](#using-cli-pypi-installation)
  - [Using Development Installation](#using-development-installation)
- [Tool Filtering in Stdio Mode](#tool-filtering-in-stdio-mode)
  - [Allowlist with `--tools`](#allowlist-with---tools)
  - [Denylist with `--omit-tools`](#denylist-with---omit-tools)
  - [Combining both](#combining-both)
- [Tool Filtering via HTTP Headers (Streamable HTTP Mode)](#tool-filtering-via-http-headers-streamable-http-mode)
  - [Allowlist with `select-tools`](#allowlist-with-select-tools)
  - [Denylist with `omit-tools`](#denylist-with-omit-tools)
  - [Combining both headers](#combining-both-headers)
  - [Notes](#notes)
- [Benefits of Tool Filtering](#benefits-of-tool-filtering)

## Available Categories

`app`, `infra`, `events`, `website`, `mobile_app`, `slo`, `synthetic`, `releases`, `maintenance_windows`, `automation`, `custom_dashboards`, `alert_channels`

Run `--list-tools` to print every category together with the tools it contains.

## Filtering Options

| Option | Applies to | Behaviour |
|---|---|---|
| `--tools <categories>` | CLI flag (stdio and streamable HTTP) | **Allowlist**: load only the listed categories |
| `--omit-tools <categories>` | CLI flag (stdio and streamable HTTP) | **Denylist**: load everything except the listed categories |
| `select-tools` header | Streamable HTTP only | Per-client **allowlist** |
| `omit-tools` header | Streamable HTTP only | Per-client **denylist** |

All options accept a comma-separated list of category names. When an allowlist and a denylist are combined, the allowlist is applied first and the denylist then removes categories from that set.

## Command-Line Examples

The examples below start the server in streamable HTTP mode. The `--tools` and `--omit-tools` flags work the same way in stdio mode (see [Tool Filtering in Stdio Mode](#tool-filtering-in-stdio-mode)).

### Using CLI (PyPI Installation)

```bash
# Enable only application monitoring tools
mcp-instana --tools app --transport streamable-http

# Enable only infrastructure analysis tools
mcp-instana --tools infra --transport streamable-http

# Enable application and infrastructure tools
mcp-instana --tools app,infra --transport streamable-http

# Enable events and website tools
mcp-instana --tools events,website --transport streamable-http

# Enable custom dashboards and app tools
mcp-instana --tools custom_dashboards,app --transport streamable-http

# Enable releases and events tools
mcp-instana --tools releases,events --transport streamable-http

# Enable maintenance window and events tools
mcp-instana --tools maintenance_windows,events --transport streamable-http

# Enable automation and app tools
mcp-instana --tools automation,app --transport streamable-http

# Enable SLO management tools
mcp-instana --tools slo --transport streamable-http

# Enable synthetic monitoring tools
mcp-instana --tools synthetic --transport streamable-http

# Enable mobile app monitoring tools
mcp-instana --tools mobile_app --transport streamable-http

# Enable all tools (default behavior)
mcp-instana --transport streamable-http

# Disable specific categories (all others remain enabled)
mcp-instana --transport streamable-http --omit-tools maintenance_windows,slo

# Combine --tools and --omit-tools
mcp-instana --transport streamable-http --tools app,infra,events --omit-tools events

# List all available tool categories and their tools
mcp-instana --list-tools
```

### Using Development Installation

```bash
# Enable only application monitoring tools
uv run src/core/server.py --tools app --transport streamable-http

# Enable only infrastructure analysis tools
uv run src/core/server.py --tools infra --transport streamable-http

# Enable application and infrastructure tools
uv run src/core/server.py --tools app,infra --transport streamable-http

# Enable events and website tools
uv run src/core/server.py --tools events,website --transport streamable-http

# Enable custom dashboards and app tools
uv run src/core/server.py --tools custom_dashboards,app --transport streamable-http

# Enable releases and events tools
uv run src/core/server.py --tools releases,events --transport streamable-http

# Enable maintenance window and events tools
uv run src/core/server.py --tools maintenance_windows,events --transport streamable-http

# Enable automation and app tools
uv run src/core/server.py --tools automation,app --transport streamable-http

# Enable SLO management tools
uv run src/core/server.py --tools slo --transport streamable-http

# Enable synthetic monitoring tools
uv run src/core/server.py --tools synthetic --transport streamable-http

# Enable mobile app monitoring tools
uv run src/core/server.py --tools mobile_app --transport streamable-http

# Enable all tools (default behavior)
uv run src/core/server.py --transport streamable-http

# Disable specific categories (all others remain enabled)
uv run src/core/server.py --transport streamable-http --omit-tools maintenance_windows,slo

# Combine --tools and --omit-tools
uv run src/core/server.py --transport streamable-http --tools app,infra,events --omit-tools events

# List all available tool categories and their tools
uv run src/core/server.py --list-tools
```

## Tool Filtering in Stdio Mode

In stdio mode the MCP client spawns the server as a child process, so flags are passed directly through the `args` array in `mcp.json`.

### Allowlist with `--tools`

Show only the listed categories:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": ["--transport", "stdio", "--tools", "infra,events"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

### Denylist with `--omit-tools`

Show everything except the listed categories:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": ["--transport", "stdio", "--omit-tools", "maintenance_windows,slo"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

### Combining both

Select a subset, then remove from it:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": ["--transport", "stdio", "--tools", "app,infra,events", "--omit-tools", "events"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

## Tool Filtering via HTTP Headers (Streamable HTTP Mode)

When the server is running in streamable HTTP mode, each MCP client can control which tool categories it sees without restarting the server or running a separate instance. Two complementary headers are supported:

| Header | Behaviour |
|---|---|
| `select-tools` | **Allowlist**: show only the listed categories |
| `omit-tools` | **Denylist**: show everything *except* the listed categories |

Both headers accept a comma-separated list of category names identical to those used by the `--tools` / `--omit-tools` CLI flags. They can be combined: `select-tools` is applied first to build the visible set, then `omit-tools` removes from it.

### Allowlist with `select-tools`

Show only the specified categories:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "httpURL": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "https://your-instana-instance.example.com",
        "instana-api-token": "YOUR_API_TOKEN",
        "select-tools": "infra,events"
      }
    }
  }
}
```

### Denylist with `omit-tools`

Show everything except the specified categories. This is useful when you want most tools but need to hide one or two:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "httpURL": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "https://your-instana-instance.example.com",
        "instana-api-token": "YOUR_API_TOKEN",
        "omit-tools": "maintenance_windows,slo"
      }
    }
  }
}
```

### Combining both headers

Select a subset first, then remove from it:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "httpURL": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "https://your-instana-instance.example.com",
        "instana-api-token": "YOUR_API_TOKEN",
        "select-tools": "app,infra,events,website",
        "omit-tools": "website"
      }
    }
  }
}
```

### Notes

- The server filters the `tools/list` response for that client connection on every request. Other clients connected to the same server process are unaffected.
- Unknown category names are logged as warnings and ignored.
- If neither header is present, all registered tools are returned (default behaviour).
- These headers have no effect in stdio mode. Use the `--tools` / `--omit-tools` CLI flags instead.
- The key used for the server address (`httpURL`, `url`, and so on) depends on your MCP client. See the [client-specific guides](./mcp-clients/) for the correct format.

## Benefits of Tool Filtering

- **Performance**: reduced startup time and memory usage
- **Security**: limit exposure to only necessary APIs
- **Clarity**: focus on specific use cases (for example, only infrastructure monitoring)
- **Resource efficiency**: lower CPU and network usage

For usage examples and prompts, see [Example Prompts](TOOLS_AND_EXAMPLES.md).
