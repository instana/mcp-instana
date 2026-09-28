## GitHub Copilot CLI Setup

GitHub Copilot CLI (`copilot`) brings AI-powered coding assistance directly to your terminal with native MCP support. For installation instructions, see the [GitHub Copilot CLI documentation](https://docs.github.com/copilot/concepts/agents/about-copilot-cli).

**Configuration file locations:**

- **User-level (global):** `~/.copilot/mcp-config.json` — applies to all sessions
- **Workspace-level:** `.mcp.json` in your repository root — applies to that project only

**Step 1:** Choose one of the configurations below based on whether your Instana MCP server is running in Streamable HTTP or Stdio mode, and add it to the appropriate config file.

**Step 2:** Launch the CLI with `copilot`.

**Step 3:** Run `/mcp` from within `copilot`. You should see the Instana MCP Server listed along with the number of available tools.

### Streamable HTTP Mode

Streamable HTTP is the recommended transport for remote MCP servers.

**Step 1: Start the MCP Server in Streamable HTTP Mode**

Before configuring Copilot CLI, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](../../README.md#starting-the-local-mcp-server) section for detailed instructions.

**Step 2: Configure Copilot CLI**

Add the following configuration to `~/.copilot/mcp-config.json`:

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

**Step 3: Test the Connection**

Launch `copilot` and run `/mcp`. You should now see the Instana MCP Server in the list of available MCP servers.

### Stdio Mode

Stdio transport runs the MCP server as a local child process on your machine.

#### Configuration using CLI (PyPI Installation - Recommended)

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "/path/to/mcp-instana",
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

**Note:** Copilot CLI spawns the MCP server as a subprocess and may not inherit your shell's `PATH`. Always specify the full path to `mcp-instana`. Find it using:

```bash
which mcp-instana
```

#### Configuration using Development Installation

You can run the MCP Instana server in development mode using `uv` as shown below:

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--directory",
        "/path/to/mcp-instana",
        "src/core/server.py",
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

**Note:**
- Copilot CLI spawns the subprocess and may not inherit your shell's `PATH`. Always specify the full path to `uv`. Find it using:
  ```bash
  which uv
  ```
- Replace `/path/to/mcp-instana` with the absolute path to your `mcp-instana` project directory.
