## GitHub Copilot

GitHub Copilot supports MCP integration through VS Code configuration.
For GitHub Copilot integration with VS Code, refer to this [setup guide](https://code.visualstudio.com/docs/copilot/setup).

### Streamable HTTP Mode

**Step 1: Start the MCP Server in Streamable HTTP Mode**

Before configuring VS Code, you need to start the MCP server in Streamable HTTP mode. Please refer to the [Starting the Local MCP Server](../../README.md#starting-the-local-mcp-server) section for detailed instructions.

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


### Stdio Mode

**Step 1: Create VS Code MCP Configuration**

**Using CLI (PyPI Installation - Recommended):**

Create `.vscode/mcp.json` in your project root:

**Option 1: Using environment variables in config:**
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

**Option 2: Using --env flag (alternative method):**
```json:.vscode/mcp.json
{
  "servers": {
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

**Using Development Installation:**

Create `.vscode/mcp.json` in your project root:

**Option 1: Using environment variables in config:**
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

**Option 2: Using --env flag (alternative method):**
```json:.vscode/mcp.json
{
  "servers": {
    "Instana MCP Server": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/your/project/mcp-instana",
        "run",
        "src/core/server.py",
        "--env", "INSTANA_BASE_URL=https://your-instana-instance.instana.io",
        "--env", "INSTANA_API_TOKEN=your_instana_api_token"
      ]
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

1. **Open `.vscode/mcp.json`** - You will see server management controls at the top.
2. **Click `Start`** next to `Instana MCP Server` to start the server.
3. A running status along with the number of tools indicates that the server is running.

**Step 3: Test Integration**

Switch to Agent Mode in GitHub Copilot and reload tools.
Here is an example of a GitHub Copilot response:

![GitHub Copilot Response](../../images/copilotResponse.png)
