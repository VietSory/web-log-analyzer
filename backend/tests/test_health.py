from pathlib import Path
import sqlite3
import sys

from fastapi.responses import JSONResponse

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import main


def test_liveness_is_process_only():
    assert main.liveness() == {"status": "ok"}


def test_readiness_reports_database_ready_and_optional_components(tmp_path, monkeypatch):
    database_path = tmp_path / "health.db"

    def connection_factory():
        return sqlite3.connect(database_path)

    monkeypatch.setattr(main, "get_db_connection", connection_factory)
    monkeypatch.setattr(main.settings, "model_dir", tmp_path / "missing-model")

    response = main.readiness()

    assert response == {
        "status": "ready",
        "components": {
            "database": "ready",
            "ml_model": "unavailable",
            "telemetry": "disabled",
        },
    }


def test_readiness_returns_503_when_database_is_unavailable(tmp_path, monkeypatch):
    def fail_connection():
        raise sqlite3.OperationalError("database unavailable")

    monkeypatch.setattr(main, "get_db_connection", fail_connection)
    monkeypatch.setattr(main.settings, "model_dir", tmp_path / "model")

    response = main.readiness()

    assert isinstance(response, JSONResponse)
    assert response.status_code == 503
