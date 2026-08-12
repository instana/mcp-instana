# Stage 1: Build stage with minimal runtime dependencies
FROM docker.io/library/python:3.11-slim AS builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files and source code needed for the build
COPY pyproject.toml pyproject.toml
COPY src ./src
COPY README.md ./

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Install runtime dependencies
RUN pip install --no-cache-dir .

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Copy only the Python packages from builder (no source code needed)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only the source code and schema files needed for runtime
COPY src ./src

# Set ownership to non-root user
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose the default port (configurable via PORT env var)
EXPOSE 8080

# Set environment variables (no hardcoded secrets)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check: send a real MCP initialize request and confirm a valid JSON-RPC
# result comes back. This exercises the full stack (uvicorn → fastmcp → app)
# and requires no Instana credentials.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "\
import urllib.request, json, sys; \
req = urllib.request.Request( \
    'http://127.0.0.1:8080/mcp', \
    data=json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'healthcheck','version':'1.0'}}}).encode(), \
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}, \
    method='POST'); \
resp = urllib.request.urlopen(req, timeout=5).read().decode(); \
sys.exit(0 if 'serverInfo' in resp else 1)" || exit 1

# Run the server
ENTRYPOINT ["python", "-m", "src.core.server"]
CMD ["--transport", "streamable-http"]
