## Bob CLI (Bob Shell) Setup

Bob Shell is IBM's AI-powered CLI with native MCP support. It allows you to interact with MCP servers directly from your terminal.

**Step 1:** Install Bob Shell. Installation instructions are available [here](https://bob.ibm.com/docs/shell/getting-started/install-and-setup)

**Step 2:** Choose whether you want to configure the MCP server globally (available in all workspaces) or at the project level (current workspace only):

- **Global:** `~/.bob/settings/mcp.json:`
- **Project:** `.bob/mcp.json` in your project root directory

Both can coexist — project-level settings take precedence over global settings for the same server name.

**Step 3:** Choose one of the configurations below based on whether your Instana MCP server is running in Streamable HTTP, SSE, or stdio mode, and add it to the appropriate config file.

**Step 4:** Bob Shell picks up configuration changes on save. Run a query to verify the server is connected.

### Streamable HTTP Mode

Streamable HTTP is the recommended transport for remote MCP servers. Bob Shell connects natively using the `httpURL` key — no bridge process required.

Before configuring Bob Shell, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](../../README.md#starting-the-local-mcp-server) section for detailed instructions.

**Local Configuration:**

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "httpURL": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "YOUR_INSTANA_BASE_URL",
        "instana-api-token": "YOUR_INSTANA_API_TOKEN"
      }
    }
  }
}
```

If your MCP server is running on a different port, replace `8080` in the URL accordingly (the default is `8080`).

**Remote Configuration:**

Configure Bob Shell to connect to a remote Instana MCP server (e.g., deployed on IBM Code Engine):

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "httpURL": "https://your-instana-instance.instana.io",
      "headers": {
        "instana-base-url": "YOUR_INSTANA_BASE_URL",
        "instana-api-token": "YOUR_INSTANA_API_TOKEN"
      }
    }
  }
}
```

### SSE Mode (Legacy)

SSE transport connects to remote MCP servers over HTTP/HTTPS using the `url` key. For new deployments, prefer Streamable HTTP above.

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "url": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "YOUR_INSTANA_BASE_URL",
        "instana-api-token": "YOUR_INSTANA_API_TOKEN"
      }
    }
  }
}
```

### Stdio Mode

Stdio transport runs the MCP server as a local child process on your machine. Bob Shell spawns it automatically using the `command` and `args` fields.

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

**Note:** If you encounter "command not found" errors, use the full path to `mcp-instana`. Find it with `which mcp-instana` and use that path instead.

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

For more information about Bob Shell and MCP configuration, visit [here](https://bob.ibm.com/docs/shell/configuration/mcp/mcp-bobshell)
