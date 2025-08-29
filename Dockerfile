# Stage 1: Build stage
FROM python:3.11-slim AS builder

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files and README.md needed for the build
COPY pyproject.toml uv.lock README.md ./

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Install dependencies directly with uv using --system flag
RUN uv pip install --no-cache-dir --system .

# Stage 2: Runtime stage
FROM python:3.11-slim AS runtime

# Set working directory
WORKDIR /app

# Create a non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Copy the Python packages from builder
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

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Run the server
ENTRYPOINT ["python", "-m", "src.core.server"]
CMD ["--transport", "streamable-http"]
