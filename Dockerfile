# Stage 1: Build stage with minimal runtime dependencies
FROM python:3.11-slim AS builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy only the runtime dependency file and source code needed for the build
COPY pyproject-runtime.toml pyproject.toml
COPY src ./src
COPY README.md ./

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Install only runtime dependencies using the minimal pyproject-runtime.toml
RUN uv pip install --no-cache-dir --system .

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

# Set working directory
WORKDIR /app

# Create a non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Copy only the Python packages from builder (no source code needed)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only the source code needed for runtime
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

# Health check using container's internal network
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://127.0.0.1:8080/health', timeout=5)" || exit 1

# Run the server
ENTRYPOINT ["python", "-m", "src.core.server"]
CMD ["--transport", "streamable-http"]
