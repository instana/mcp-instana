## Kiro Setup

Kiro is an agentic IDE, not an extension that can be downloaded into VS Code or other IDEs.

**Step 1: Download and install Kiro for your operating system from https://kiro.dev/.**

**Step 2: After installation, launch Kiro and open any project in the IDE.**
![Open Kiro](../../images/open-kiro.png)

**Step 3: Click the Kiro (Ghost) icon on the left sidebar to access Kiro's features.**
![Kiro Features](../../images/kiro-features.png)

**Step 4: Select the Edit Config icon in the top right corner of the MCP Servers section.**
![Edit Kiro Config](../../images/edir-kiro-config.png)

**Step 5: Open the MCP server configuration file (mcp.json) and configure it based on your preferred transport mode:**

### Streamable HTTP Mode (Recommended for Kiro)

```json
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

**Note:** Make sure to start the MCP server in streamable-http mode before using this configuration:
```bash
mcp-instana --transport streamable-http
```

### Stdio Mode

**Option 1: Using environment variables in config:**
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

**Option 2: Using --env flag (alternative method):**
```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": [
        "--transport", "stdio",
        "--env", "INSTANA_BASE_URL=https://your-instana-instance.instana.io",
        "--env", "INSTANA_API_TOKEN=your_instana_api_token"
      ]
    }
  }
}
```

**Step 6: After saving the file, click the Enable MCP button and you will see your MCP server and its available tools appear in the bottom-left section of Kiro.**
![Enable MCP in Kiro](../../images/enable-kiro-mcp.png)

**Step 7: Go to the AI Chat panel, enter a prompt related to your MCP server, and view the response directly within Kiro.**
![Kiro Prompt Response](../../images/kiro-prompt.png)
