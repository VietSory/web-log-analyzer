from pathlib import Path
import sqlite3
import sys

import pytest
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from routers import history


@pytest.fixture
def valid_payload() -> history.SavePayload:
    return history.SavePayload(
        filename="access.log",
        stats={
            "total_requests": 1,
            "unique_ips": 1,
            "error_rate": 0.0,
        },
        findings=[],
        analysis_status="complete",
        ml_status="not_run",
        risk={"overall_risk_score": 0},
    )


def test_save_history_maps_invalid_report_payload_to_422(monkeypatch, valid_payload):
    def invalid_report(**_kwargs):
        raise ValueError("invalid report")

    monkeypatch.setattr(history, "save_report", invalid_report)

    with pytest.raises(HTTPException) as exc_info:
        history.save_history(valid_payload, {"id": "user-1"})

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Invalid report payload"


def test_save_history_maps_database_failures_to_500(monkeypatch, valid_payload):
    def database_failure(**_kwargs):
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(history, "save_report", database_failure)

    with pytest.raises(HTTPException) as exc_info:
        history.save_history(valid_payload, {"id": "user-1"})

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Could not save report"


def test_save_history_does_not_hide_unexpected_programming_errors(
    monkeypatch,
    valid_payload,
):
    def programming_error(**_kwargs):
        raise RuntimeError("unexpected invariant failure")

    monkeypatch.setattr(history, "save_report", programming_error)

    with pytest.raises(RuntimeError, match="unexpected invariant failure"):
        history.save_history(valid_payload, {"id": "user-1"})
