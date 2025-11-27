# Docker Guide for MCP Instana

This guide documents everything Docker-related for MCP Instana. Use it when you need more than the quick blurb in `README.md`.

## Overview

- Two-stage image defined in `Dockerfile`: a builder installs only runtime dependencies (via `pyproject-runtime.toml` + `uv`), and the runtime stage copies the installed packages plus `src/`.
- Runtime image is `python:3.11-slim`, runs as non-root `mcpuser`, exposes `8080`, and ships with a health check that curls `http://127.0.0.1:8080/health`.
- Entry point runs `python -m src.core.server --transport streamable-http`, so clients provide Instana credentials over HTTP headers rather than baking them into the container.
- `build_multiplatform.sh` automates multi-architecture builds (amd64 + arm64) with Docker Buildx, QEMU, and optional pushes.

## Quickstart

```bash
# Build a local image (single architecture)
docker build -t mcp-instana .

# Run it (streamable HTTP transport on port 8080)
docker run --rm -p 8080:8080 mcp-instana

# Override the HTTP port exposed by the container
docker run --rm -e PORT=9090 -p 9090:9090 mcp-instana
```

### Docker Compose snippet

```yaml
version: '3.8'
services:
  mcp-instana:
    build: .
    ports:
      - "8080:8080"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://127.0.0.1:8080/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Image anatomy (`Dockerfile`)

| Component | Details |
| --- | --- |
| Builder stage | Based on `python:3.11-slim`, installs `uv`, copies `pyproject-runtime.toml`, `pyproject.toml`, `src/`, `README.md`, then runs `pip install .` (runtime deps only). |
| Runtime stage | Reuses `python:3.11-slim`, copies site-packages and binaries from builder, then copies `src/` only. |
| User | Non-root `mcpuser` owns `/app`. |
| Entry point | `python -m src.core.server --transport streamable-http`. Override with `docker run ... -- entrypoint` or `CMD`. |
| Health check | `python -c "import requests; requests.get('http://127.0.0.1:8080/health', timeout=5)"` every 30s with retries. |
| Exposed port | `8080` (override with `PORT`). |

### Configuration reference

| Variable / flag | Default | Notes |
| --- | --- | --- |
| `PORT` | `8080` | Align host port mapping when overriding. |
| `PYTHONUNBUFFERED` | `1` | Keeps logs unbuffered. Usually leave as-is. |
| `PYTHONPATH` | `/app` | Ensures `src/` is importable. |
| `--transport` (CMD arg) | `streamable-http` | Change via `docker run ... -- --transport <mode>`. |

## Building images

### Single-architecture build (default Docker)

```bash
docker build -t mcp-instana .
```

### Manual multi-architecture build with Buildx

```bash
# One-time builder setup
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap

# Build & push (amd64 + arm64)
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t username/mcp-instana:latest \
  --push .
```

### Using `build_multiplatform.sh`

```bash
chmod +x build_multiplatform.sh
# Build local arch (loads result when host is linux/*)
./build_multiplatform.sh

# Build and push multi-arch manifest
./build_multiplatform.sh --registry username/ --tag v1.0 --push
```

The script:

1. Installs QEMU emulation via `tonistiigi/binfmt` (required on macOS/Windows for cross-builds).
2. Creates/bootstraps a Buildx builder named `multiplatform`.
3. Disables SBOM/attestation for faster builds (can be re-enabled if needed).
4. Builds the requested platforms; if `--push` is omitted on non-Linux hosts, it falls back to building only the current platform and warns accordingly.
5. When `--push` is set, it verifies the manifest and performs `docker pull` for both amd64/arm64.

#### Script options

| Flag | Description | Default |
| --- | --- | --- |
| `-n, --name` | Image name | `mcp-instana` |
| `-t, --tag` | Image tag | `latest` |
| `-r, --registry` | Registry prefix (e.g., `username/` or `registry.example.com/`) | empty |
| `-p, --platforms` | Comma-separated platforms | `linux/amd64,linux/arm64` |
| `--push` | Push manifest to the registry | disabled |
| `-h, --help` | Show usage and exit | — |

## Security posture

- Non-root runtime user (`mcpuser`) limits container privileges.
- Health check ensures orchestration platforms can restart unhealthy pods.
- No credentials or secrets inside the image; MCP clients supply Instana headers at request time.
- Runtime dependency set trimmed to ~20 packages, yielding ~266 MB images vs >1 GB for dev installs.
- Multi-stage build keeps compilers and build artifacts out of the final layer.

## Testing & troubleshooting

```bash
# Inspect container status (health column)
docker ps

# Hit MCP endpoint directly
curl http://localhost:8080/mcp/

# Test using MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8080/mcp/

# Logs
docker logs -f <container_id>

# Debug shell (container already has /bin/bash from python:slim)
docker exec -it <container_id> /bin/bash
```

## Production deployment

1. Keep Instana credentials outside the container; pass them through MCP-compatible clients (Claude Desktop, GitHub Copilot, etc.).
2. Rely on the built-in HTTP health endpoint (`/health`) for orchestration probes.
3. Configure persistent logging/metrics at the orchestrator level (CloudWatch, ELK, etc.).
4. Run at least two replicas and enable rolling updates to avoid downtime.
5. Regularly rebuild to pick up upstream `python:3.11-slim` security patches.

### Kubernetes example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-instana
spec:
  replicas: 2
  selector:
    matchLabels:
      app: mcp-instana
  template:
    metadata:
      labels:
        app: mcp-instana
    spec:
      containers:
      - name: mcp-instana
        image: mcp-instana:latest
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```
