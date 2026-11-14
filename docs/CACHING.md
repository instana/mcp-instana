# Catalog Response Caching

The server caches Instana catalog API responses (metrics and tags) in memory to avoid repeated round-trips during analysis workflows. Catalog data is stable within a tenant and changes only when new integrations are deployed, so cached responses are safe to reuse until their TTL expires.

- **Default TTL:** 1800 seconds (30 minutes).
- **Isolation:** each combination of Instana base URL, operation, and operation parameters has its own cache entry, so different tenants (base URLs) never share cached data.
- **Errors are never cached:** a transient failure cannot poison the cache.
- **Scope:** the cache is in-process. It is not shared between server instances and is cleared when the server restarts.
- **Not cached:** the infrastructure plugin list (`get_infrastructure_catalog_plugins`) and all non-catalog calls (traces, events, metrics queries, and so on).

## Table of Contents

- [Cached Catalog Operations](#cached-catalog-operations)
- [Configuration Options](#configuration-options)
- [Stdio Mode](#stdio-mode)
- [Streamable HTTP Mode](#streamable-http-mode)
  - [Setting Cache Headers in the MCP Client Config](#setting-cache-headers-in-the-mcp-client-config)
  - [Disabling Caching for a Client](#disabling-caching-for-a-client)
- [Verifying Cache Behavior](#verifying-cache-behavior)

## Cached Catalog Operations

| Domain | Operation | Cache key parameters |
|---|---|---|
| Application | Get metric catalog | — |
| Application | Get tag catalog | `use_case`, `data_source` |
| Website | Get metrics catalog | — |
| Website | Get tag catalog | `beacon_type`, `use_case` |
| Mobile App | Get metric catalog | — |
| Mobile App | Get tag catalog | `beacon_type`, `use_case` |
| Synthetic | Get metrics catalog | — |
| Synthetic | Get tag catalog | `use_case` |
| Infrastructure | Get metrics catalog | `plugin`, `filter` |
| Infrastructure | Get tag catalog | `plugin` |

Two calls to the same operation share a cache entry only if the Instana base URL and all of their cache key parameters match.

The metric catalogs are also fetched internally for pre-flight metric validation (when a metrics query is checked against the catalog). That internal fetch uses the same in-process store, but it always uses the default TTL and is **not** affected by `INSTANA_CACHE_ENABLED`, `INSTANA_CACHE_TTL`, or the per-request headers described below.

## Configuration Options

| Setting | Environment variable | HTTP header (streamable HTTP only) | Default |
|---|---|---|---|
| Enable or disable caching | `INSTANA_CACHE_ENABLED` | `instana-cache-enabled` | enabled |
| Time-to-live in seconds | `INSTANA_CACHE_TTL` | `instana-cache-ttl` | `1800` |

- Caching is **disabled** when the value is `false`, `0`, or `no` (case-insensitive). Any other value, including an empty one, keeps caching **enabled**.
- The TTL must be an integer number of seconds. An invalid value is logged as a warning and ignored: an invalid `INSTANA_CACHE_TTL` falls back to `1800`, and an invalid `instana-cache-ttl` header falls back to the process-level TTL. Negative values are treated as `0`.
- Environment variables set the process-level defaults and are read once at startup.
- Headers apply per request and take precedence over the process-level defaults.
- The TTL is applied when an entry is written. Changing the TTL later does not shorten or extend entries that are already cached.
- Disabling caching (by environment variable or header) bypasses the cache for that call. It does not clear entries that are already stored.

## Stdio Mode

In stdio mode only the environment variables are used, because there are no HTTP requests to carry headers. Changes take effect when the server process restarts.

```bash
# Disable caching entirely
export INSTANA_CACHE_ENABLED=false

# Override the TTL to 5 minutes (default: 1800)
export INSTANA_CACHE_TTL=300
```

To set these persistently for a client such as Bob, add them to the `env` block of the server entry in the MCP config file (for example `.bob/mcp.json`). The client restarts the server when the configuration changes.

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "command": "mcp-instana",
      "args": ["--transport", "stdio"],
      "env": {
        "INSTANA_BASE_URL": "https://your-instana-instance.instana.io",
        "INSTANA_API_TOKEN": "your_instana_api_token",
        "INSTANA_CACHE_ENABLED": "true",
        "INSTANA_CACHE_TTL": "1800"
      }
    }
  }
}
```

## Streamable HTTP Mode

The environment variables above still set the server-wide defaults. In addition, each HTTP request can override them with headers, so caching can be turned on or off, or the TTL changed, without restarting the server.

```text
instana-cache-enabled: false
instana-cache-ttl: 300
```

### Setting Cache Headers in the MCP Client Config

To apply cache settings to every request from a client, add the headers alongside the existing Instana headers. The key used for the server address (`url`, `httpURL`, and so on) depends on your MCP client; see the [client-specific guides](./mcp-clients/) for the correct format.

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "url": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "https://your-instana-instance.example.com",
        "instana-api-token": "YOUR_API_TOKEN",
        "instana-cache-enabled": "true",
        "instana-cache-ttl": "1800"
      }
    }
  }
}
```

### Disabling Caching for a Client

To bypass the cache for a specific client connection, add `instana-cache-enabled` with the value `false` (leave `instana-cache-ttl` out):

```json
{
  "mcpServers": {
    "Instana MCP Server": {
      "url": "http://localhost:8080/mcp/",
      "headers": {
        "instana-base-url": "https://your-instana-instance.example.com",
        "instana-api-token": "YOUR_API_TOKEN",
        "instana-cache-enabled": "false"
      }
    }
  }
}
```

## Verifying Cache Behavior

Start the server with debug logging (`--debug` or `--log-level DEBUG`). On every cached catalog call the server then logs the effective cache state (enabled or disabled, and the TTL), followed by whether the call was a cache `HIT`, a `MISS`, or a `BYPASS` because caching is disabled. Example output:

```text
ttl_cached [get_application_tag_catalog] caching=ENABLED ttl=1800s
ttl_cached MISS key=https://your-instana-instance.instana.io|get_application_tag_catalog|...
```

Repeating the same call should log `HIT` until the TTL expires.
