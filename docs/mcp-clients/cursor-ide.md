## Cursor IDE

Cursor is an AI-powered IDE that runs as a desktop application. It can connect to the Instana MCP server using these transport methods:

- Streamable HTTP
- stdio

### Streamable HTTP Mode

**Step 1: Start the MCP Server in Streamable HTTP Mode**

Before configuring Cursor, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](../../README.md#starting-the-local-mcp-server) section for detailed instructions.

**Step 2: Configure Cursor**

Use the configuration below to connect Cursor to the Instana MCP server running in Streamable HTTP mode.

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://0.0.0.0:8080/mcp/",
        "--allow-http",
        "--header",
        "instana-base-url: https://your-instana-instance.instana.io",
        "--header",
        "instana-api-token: your_instana_api_token"
      ]
    }
  }
}
```

**Note:** Replace the following values with your actual configuration:
- `instana-base-url`: Your Instana instance URL
- `instana-api-token`: Your Instana API token

### Remote Server

Use the configuration below to connect to an Instana MCP server running on a remote host.

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "url": "http://instana_mcp_server_host:8080/mcp",
      "headers": {
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

In the above configuration, replace `8080` with the actual port configured for your Instana MCP server (default is `8080`).

### Stdio Mode

Stdio transport runs the MCP server as a local child process on your machine. 

**Configuration using CLI (PyPI Installation - Recommended):**

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "type": "stdio",
      "command": "mcp-instana",
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

**Note:** If you encounter "command not found" errors, use the full path to `mcp-instana`. Find it with `which mcp-instana` and use that path instead.

You can also customize behaviour using the `args` parameter. For example, to enable debug-level logging:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "type": "stdio",
      "command": "mcp-instana",
      "args": ["--debug"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

Run `mcp-instana --help` to see all supported command-line options.

### Development Installation

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

For more information about MCP configuration in Cursor, see the [Cursor MCP documentation](https://cursor.com/docs/mcp).