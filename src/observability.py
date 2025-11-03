import os
import sys


def workflow(name=None):
    def decorator(func):
        return func
    return decorator

def task(name=None):
    def decorator(func):
        return func
    return decorator

TRACELOOP_ENABLED = os.getenv("ENABLE_MCP_OBSERVABILITY", "false").lower() in ("true", "1", "yes", "on")

if TRACELOOP_ENABLED:
    try:
        from traceloop.sdk import Traceloop
        from traceloop.sdk.decorators import task as traceloop_task
        from traceloop.sdk.decorators import workflow as traceloop_workflow
        Traceloop.init(app_name="Instana-MCP-Server")
        print("Traceloop enabled and initialized for MCP Client", file=sys.stderr)
        # Override the no-op decorators with real ones
        workflow = traceloop_workflow
        task = traceloop_task
    except ImportError:
        print("Traceloop requested but not installed. Install with: pip install traceloop-sdk", file=sys.stderr)
        TRACELOOP_ENABLED = False
