
## Mistral AI

Mistral AI supports MCP integration exclusively through Streamable HTTP mode.

**Step 1: Launch the MCP Server in Streamable HTTP Mode**

Start the MCP server in Streamable HTTP mode by providing your Instana credentials. Run the following command:

```bash
uv run src/core/server.py --transport streamable-http \
  --api-token "your_instana_api_token" \
  --base-url "https://your-instana-instance.instana.io" \
  --port 8080
```

**Step 2: Set Up Port Forwarding with Ngrok**

Configure port forwarding to expose your local server. Follow the [Ngrok setup documentation](https://dashboard.ngrok.com/get-started/setup/macos) for detailed instructions.

**Step 3: Configure Mistral AI**

1. Navigate to the **Intelligence** tab in the left sidebar and select **Connectors**.
   ![Mistral HomePage](../../images/mistral-homepage.png)

2. Click **Add Connector**.
   ![Connector](../../images/mistral-connector.png)

3. Create a custom connector by entering a connector name and the Ngrok-forwarded MCP server URL.
   ![Custom Connector](../../images/mistral-custom-connector.png)

4. Start a new chat session and verify that MCP tools are enabled. You can test your queries and view responses directly in the chat interface:
   ![Testing MCP connection](../../images/mistral-new-chat.png)
   ![Response](../../images/mistral-response.png)