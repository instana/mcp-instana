import builtins
import importlib
import os
import sys
import types
from contextlib import contextmanager
from io import StringIO
from unittest.mock import patch


@contextmanager
def patched_environ(**updates):
    original = os.environ.copy()
    os.environ.update(updates)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


def unload_observability_modules():
    for module_name in [
        "src.observability",
        "traceloop",
        "traceloop.sdk",
        "traceloop.sdk.decorators",
    ]:
        sys.modules.pop(module_name, None)


class TestObservabilityModule:
    def test_default_mode_uses_noop_decorators(self):
        unload_observability_modules()

        with patched_environ(ENABLE_MCP_OBSERVABILITY="false"):
            module = importlib.import_module("src.observability")

        @module.workflow(name="wf")
        def sample_workflow():
            return "workflow"

        @module.task(name="tsk")
        def sample_task():
            return "task"

        assert module.TRACELOOP_ENABLED is False
        assert sample_workflow() == "workflow"
        assert sample_task() == "task"

    def test_enabled_mode_with_missing_traceloop_falls_back(self):
        unload_observability_modules()
        stderr_buffer = StringIO()
        original_stderr = sys.stderr
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("traceloop"):
                raise ImportError("forced missing traceloop")
            return original_import(name, globals, locals, fromlist, level)

        with patched_environ(ENABLE_MCP_OBSERVABILITY="true"):
            sys.stderr = stderr_buffer
            try:
                with patch("builtins.__import__", side_effect=fake_import):
                    module = importlib.import_module("src.observability")
            finally:
                sys.stderr = original_stderr

        @module.workflow()
        def sample():
            return "ok"

        assert module.TRACELOOP_ENABLED is False
        assert sample() == "ok"
        assert "Traceloop requested but not installed" in stderr_buffer.getvalue()

    def test_enabled_mode_with_traceloop_uses_real_decorators(self):
        unload_observability_modules()

        init_calls = []
        workflow_calls = []
        task_calls = []

        traceloop_module = types.ModuleType("traceloop")
        sdk_module = types.ModuleType("traceloop.sdk")
        decorators_module = types.ModuleType("traceloop.sdk.decorators")

        class FakeTraceloop:
            @staticmethod
            def init(app_name):
                init_calls.append(app_name)

        def fake_workflow(name=None):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    workflow_calls.append(name)
                    return func(*args, **kwargs)
                return wrapper
            return decorator

        def fake_task(name=None):
            def decorator(func):
                def wrapper(*args, **kwargs):
                    task_calls.append(name)
                    return func(*args, **kwargs)
                return wrapper
            return decorator

        sdk_module.Traceloop = FakeTraceloop
        decorators_module.workflow = fake_workflow
        decorators_module.task = fake_task

        sys.modules["traceloop"] = traceloop_module
        sys.modules["traceloop.sdk"] = sdk_module
        sys.modules["traceloop.sdk.decorators"] = decorators_module

        stderr_buffer = StringIO()
        original_stderr = sys.stderr

        with patched_environ(ENABLE_MCP_OBSERVABILITY="yes"):
            sys.stderr = stderr_buffer
            try:
                module = importlib.import_module("src.observability")
            finally:
                sys.stderr = original_stderr

        @module.workflow(name="wf-name")
        def workflow_func():
            return "workflow-result"

        @module.task(name="task-name")
        def task_func():
            return "task-result"

        assert module.TRACELOOP_ENABLED is True
        assert init_calls == ["Instana-MCP-Server"]
        assert workflow_func() == "workflow-result"
        assert task_func() == "task-result"
        assert workflow_calls == ["wf-name"]
        assert task_calls == ["task-name"]
        assert "Traceloop enabled and initialized for MCP Client" in stderr_buffer.getvalue()

    def test_truthy_environment_variants_enable_flag_before_import_handling(self):
        unload_observability_modules()

        traceloop_module = types.ModuleType("traceloop")
        sdk_module = types.ModuleType("traceloop.sdk")
        decorators_module = types.ModuleType("traceloop.sdk.decorators")

        class FakeTraceloop:
            @staticmethod
            def init(_app_name):
                return None

        def fake_workflow(name=None):
            def decorator(func):
                return func
            return decorator

        def fake_task(name=None):
            def decorator(func):
                return func
            return decorator

        sdk_module.Traceloop = FakeTraceloop
        decorators_module.workflow = fake_workflow
        decorators_module.task = fake_task

        sys.modules["traceloop"] = traceloop_module
        sys.modules["traceloop.sdk"] = sdk_module
        sys.modules["traceloop.sdk.decorators"] = decorators_module

        with patched_environ(ENABLE_MCP_OBSERVABILITY="on"):
            module = importlib.import_module("src.observability")

        assert hasattr(module, "TRACELOOP_ENABLED")

