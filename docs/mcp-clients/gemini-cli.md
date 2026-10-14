## Gemini CLI Setup

Gemini CLI supports both Streamable HTTP and Stdio modes for MCP integration.

### Step 1: Install Gemini CLI

Install Gemini CLI using Homebrew:

```bash
brew install gemini-cli
```

### Step 2: Launch Gemini CLI

Run:

```bash
gemini
```

On the first launch, Gemini CLI will prompt you to authenticate. Follow the on-screen instructions to sign in or provide your Gemini API key.

---

### Streamable HTTP Mode (Recommended)

The Streamable HTTP mode provides a REST API interface for MCP communication using JSON-RPC over HTTP.

**Step 1: Start the MCP Server in Streamable HTTP Mode**

Before configuring Gemini CLI, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](../../README.md#starting-the-local-mcp-server) section for detailed instructions.

**Step 2: Configure Gemini CLI**

Open the Gemini configuration file:

```bash
nano ~/.gemini/settings.json
```

Add the following configuration:

```json:.gemini/settings.json
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

**Note:** If your MCP server is running on a different port, replace `8080` in the URL accordingly (e.g., `http://localhost:9000/mcp`).

**Step 3: Verify the Connection**

Open a new terminal and start Gemini:

```bash
gemini
```

You can run `/mcp` to list available MCP servers and tools, and ask queries directly:

```
List my applications in instana.
```

If the configuration is correct, Gemini CLI will connect to your local Instana MCP server through `mcp-remote` and invoke the appropriate tools.

---

### Stdio Mode

Stdio mode runs the MCP server locally as a subprocess.

**Step 1: Configure Gemini CLI**

Open `~/.gemini/settings.json` and add the configuration for your installation method:

**Configuration using CLI (PyPI Installation - Recommended):**

```json:.gemini/settings.json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "/path/to/mcp-instana",
      "args": [
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

**Note:** Gemini CLI spawns the MCP server as a subprocess and may not inherit your shell's PATH. Always use the full path to `mcp-instana` in the `command` field. Find it by running:
```bash
which mcp-instana
```

**Configuration using Development Installation:**

```json:.gemini/settings.json
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
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token"
      }
    }
  }
}
```

**Note:** Gemini CLI may not inherit your shell's PATH. Use the full path to `uv` in the `command` field, and set `--directory` to the absolute path of your cloned `mcp-instana` folder. Find the `uv` path by running:
```bash
which uv
```

**Step 2: Verify the Connection**

Start Gemini CLI and run `/mcp`. You should see the Instana MCP Server in the list of available MCP servers. You can now prompt Gemini with Instana queries.