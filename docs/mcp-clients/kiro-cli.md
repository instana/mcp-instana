## Kiro CLI Setup

Kiro CLI provides an interactive terminal interface to work with MCP servers.

**Step 1:** Download and install Kiro CLI for your operating system from [Kiro CLI Installation](https://kiro.dev/docs/getting-started/installation/#cli).

**Step 2:** Once installed, configure `kiro-cli` to connect to MCP servers by adding your server configuration to the `mcp.json` file.

**Step 3:** Choose whether you want to set it up for your workspace or at a global level. See the [Kiro MCP Configuration Guide](https://kiro.dev/docs/mcp/configuration/#cli) for more details.

**Step 4:** Choose one of the configurations below based on whether your Instana MCP server is running in Streamable HTTP or stdio mode.

**Step 5:** After saving your configuration in `mcp.json`, launch the CLI with `kiro-cli`.

**Step 6:** Run `/mcp` from within `kiro-cli`. You should see your Instana MCP server listed along with the number of available tools.

### Streamable HTTP Mode

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

If your MCP server is running on a different port, replace `8080` in the `url` accordingly (the default is `8080`).

### Stdio Mode

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": [
        "--transport",
        "stdio"
      ],
      "env": {
        "INSTANA_BASE_URL": "YOUR_INSTANA_BASE_URL",
        "INSTANA_API_TOKEN": "YOUR_INSTANA_API_TOKEN"
      }
    }
  }
}
```

### Development mode 

You can run the MCP Instana server in development mode using `uv` as shown below.

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "uv",
      "args": [
        "run",
        "src/core/server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

Note: Replace `src/core/server.py` with the absolute path if running `kiro-cli` from a different directory than MCP Instana base directory.