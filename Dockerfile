# Stage 1: Build stage with ONLY runtime dependencies
FROM python:3.11-slim AS builder

# Install minimal system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Install ONLY the 5 core runtime dependencies directly
# This bypasses the project build and installs only what we need
RUN uv pip install --no-cache-dir --system \
    fastmcp==2.10.3 \
    instana_client==1.0.0 \
    requests==2.32.4 \
    python-dotenv==1.1.0 \
    pydantic==2.11.7

# Stage 2: Runtime stage - ultra minimal
FROM python:3.11-slim AS runtime

# Install only essential runtime system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python packages from builder (only runtime deps)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code and environment file
COPY src ./src
COPY README.md ./
COPY .env ./

# Set environment variables from .env file
ENV INSTANA_BASE_URL="https://qa-instana.instana.io"
ENV INSTANA_API_TOKEN="2SI6SKDcQW-yZ8ep5OLbjQ"
ENV WATSONX_CHAT_MODEL="meta-llama/llama-3-405b-instruct"
ENV WATSONX_URL="https://us-south.ml.cloud.ibm.com"
ENV WATSONX_API_KEY="5cSMM-2lAi040vKauIMv3Pp_zf6EP_Gse-D7z0CC03KV"
ENV WATSONX_PROJECT_ID="7df21499-6277-4938-af57-a409852ae8f1"

# Set other environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Run the MCP server
ENTRYPOINT ["python", "src/core/server.py"]
CMD ["--port", "8080"]
