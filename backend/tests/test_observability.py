from pathlib import Path
import sys

from fastapi import FastAPI

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.observability import TelemetryRuntime, configure_observability


def test_disabled_observability_does_not_create_sdk_providers():
    runtime = configure_observability(
        FastAPI(),
        enabled=False,
        service_name="test-service",
    )

    assert isinstance(runtime, TelemetryRuntime)
    assert runtime.enabled is False
    assert runtime.tracer_provider is None
    assert runtime.meter_provider is None
    runtime.shutdown()
