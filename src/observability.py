"""
OTel instrumentation for the Instana MCP Server.

Set ENABLE_MCP_OBSERVABILITY=true to activate tracing.
When active, spans are exported via OTLP to the endpoint set in
OTEL_EXPORTER_OTLP_ENDPOINT (default: http://localhost:4317).

When the flag is not set (the default), every call in this module
is a no-op — zero overhead.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Public helpers — imported by server.py and utils.py
# ---------------------------------------------------------------------------

def get_tracer():
    """Return the module-level OTel Tracer (real or no-op)."""
    return _tracer


# ---------------------------------------------------------------------------
# Internal setup
# ---------------------------------------------------------------------------

ENABLE_MCP_OBSERVABILITY = (
    os.getenv("ENABLE_MCP_OBSERVABILITY", "false").lower()
    in ("true", "1", "yes", "on")
)

_tracer = None  # will be replaced below if observability is enabled

if ENABLE_MCP_OBSERVABILITY:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Build the resource that identifies this service in any OTel backend
        resource = Resource.create(
            {"service.name": os.getenv("OTEL_SERVICE_NAME", "instana-mcp-server")}
        )

        # OTLP gRPC exporter — destination controlled entirely by env vars:
        #   OTEL_EXPORTER_OTLP_ENDPOINT  (default: http://localhost:4317)
        #   OTEL_EXPORTER_OTLP_HEADERS   (e.g. x-instana-key=<key> for Instana)
        #   OTEL_EXPORTER_OTLP_INSECURE  (set to "true" for self-signed certs)
        exporter = OTLPSpanExporter()

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        _tracer = trace.get_tracer("instana-mcp-server")

        print(
            "[mcp-instana] OTel tracing enabled — exporting to "
            f"{os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317')}",
            file=sys.stderr,
        )

    except ImportError as exc:
        print(
            f"[mcp-instana] ENABLE_MCP_OBSERVABILITY=true but OTel SDK not installed: {exc}\n"
            "Install with: uv add opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc",
            file=sys.stderr,
        )

# ---------------------------------------------------------------------------
# No-op tracer fallback
# ---------------------------------------------------------------------------
# If observability is disabled, or the SDK import failed, _tracer stays None.
# get_tracer() returns None and all call-sites guard with `if tracer:`.
