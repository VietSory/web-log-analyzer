from pathlib import Path
import sqlite3
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import get_settings
from core.report_store import (
    clear_reports,
    delete_report,
    get_report,
    init_report_store,
    list_reports,
    save_report,
)
from core.security import hash_password
import database


@pytest.fixture
def report_database(tmp_path, monkeypatch):
    database_path = tmp_path / "reports.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    get_settings.cache_clear()
    database.init_db()
    init_report_store()
    owner_id = database.create_user(
        "Report Owner",
        "report-owner",
        hash_password("a sufficiently long report password"),
    )
    other_id = database.create_user(
        "Other Owner",
        "other-owner",
        hash_password("another sufficiently long password"),
    )
    assert owner_id is not None
    assert other_id is not None
    yield database_path, owner_id, other_id
    get_settings.cache_clear()


def _stats():
    return {
        "total_requests": 12,
        "unique_ips": 4,
        "error_rate": 8.33,
        "traffic_chart": {"2026-02-01 12:00": 12},
        "status_distribution": {"200": 10, "500": 2},
    }


def _risk():
    return {
        "overall_risk_score": 80,
        "overall_risk_severity": "high",
        "finding_count": 2,
        "rule_finding_count": 1,
        "ml_finding_count": 1,
        "corroborated_finding_count": 2,
    }


def _findings():
    return [
        {
            "source": "rule",
            "rule_id": "WEB-SQLI-001",
            "severity": "high",
            "risk_score": 80,
            "risk_severity": "high",
            "corroborated": True,
            "ip": "192.0.2.10",
            "time": "2026-02-01T12:00:00Z",
            "path": "/search?q=union+select",
            "evidence": "matched=UNION SELECT",
        },
        {
            "source": "ml",
            "type": "ml_anomaly",
            "severity": "high",
            "risk_score": 80,
            "risk_severity": "high",
            "corroborated": True,
            "ip": "192.0.2.10",
            "time": "2026-02-01T12:00:00Z",
            "details": "Path: /search?q=union+select",
            "reconstruction_error": 0.42,
            "threshold": 0.1,
            "score_ratio": 4.2,
        },
    ]


def test_save_and_load_structured_report_preserves_findings(report_database):
    _, owner_id, _ = report_database

    report_id = save_report(
        owner_id=owner_id,
        filename="access.log",
        stats=_stats(),
        findings=_findings(),
        analysis_status="complete",
        ml_status="available",
        risk=_risk(),
    )

    loaded = get_report(report_id, owner_id)
    assert loaded is not None
    assert loaded["filename"] == "access.log"
    assert loaded["stats"] == _stats()
    assert loaded["risk"] == _risk()
    assert loaded["analysis_status"] == "complete"
    assert loaded["ml_status"] == "available"
    assert loaded["findings"] == _findings()
    assert loaded["threats"] == _findings()

    summaries = list_reports(owner_id)
    assert len(summaries) == 1
    assert summaries[0]["id"] == report_id
    assert summaries[0]["overall_risk_score"] == 80
    assert summaries[0]["overall_risk_severity"] == "high"


def test_report_queries_are_owner_scoped(report_database):
    _, owner_id, other_id = report_database
    report_id = save_report(
        owner_id=owner_id,
        filename="private.log",
        stats=_stats(),
        findings=[],
        analysis_status="degraded",
        ml_status="unavailable",
        risk={"overall_risk_score": 0, "overall_risk_severity": "none"},
    )

    assert get_report(report_id, other_id) is None
    assert list_reports(other_id) == []
    assert delete_report(report_id, other_id) is False
    assert get_report(report_id, owner_id) is not None


def test_clear_reports_deletes_only_current_owner(report_database):
    _, owner_id, other_id = report_database
    for user_id in (owner_id, other_id):
        save_report(
            owner_id=user_id,
            filename=f"{user_id}.log",
            stats=_stats(),
            findings=[],
            analysis_status="complete",
            ml_status="available",
            risk={"overall_risk_score": 0, "overall_risk_severity": "none"},
        )

    assert clear_reports(owner_id) == 1
    assert list_reports(owner_id) == []
    assert len(list_reports(other_id)) == 1


def test_report_validation_rejects_invalid_risk_and_stats(report_database):
    _, owner_id, _ = report_database

    with pytest.raises(ValueError, match="overall risk"):
        save_report(
            owner_id=owner_id,
            filename="bad.log",
            stats=_stats(),
            findings=[],
            analysis_status="complete",
            ml_status="available",
            risk={"overall_risk_score": 101},
        )

    invalid_stats = _stats()
    invalid_stats["error_rate"] = 101
    with pytest.raises(ValueError, match="error_rate"):
        save_report(
            owner_id=owner_id,
            filename="bad.log",
            stats=invalid_stats,
            findings=[],
            analysis_status="complete",
            ml_status="available",
            risk={"overall_risk_score": 0},
        )


def test_legacy_owned_reports_are_migrated_once(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy-report.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    get_settings.cache_clear()
    database.init_db()
    owner_id = database.create_user(
        "Legacy Owner",
        "legacy-owner",
        hash_password("a sufficiently long legacy password"),
    )
    assert owner_id is not None

    connection = database.get_db_connection(database_path)
    try:
        with connection:
            database._create_legacy_scan_schema(connection)
            connection.execute(
                '''
                INSERT INTO scan_history (
                    id, owner_id, filename, scan_date, total_requests,
                    unique_ips, error_rate, traffic_data, status_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    "legacy-report",
                    owner_id,
                    "legacy.log",
                    "2026-01-01T00:00:00+00:00",
                    5,
                    2,
                    0.0,
                    "{}",
                    '{"200":5}',
                ),
            )
            connection.execute(
                '''
                INSERT INTO scan_threats (
                    id, history_id, ip, severity, time, details,
                    reconstruction_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    "legacy-finding",
                    "legacy-report",
                    "192.0.2.1",
                    "high",
                    "2026-01-01T00:00:00Z",
                    "legacy anomaly",
                    0.5,
                ),
            )
    finally:
        connection.close()

    init_report_store()
    init_report_store()

    migrated = get_report("legacy-report", owner_id)
    assert migrated is not None
    assert migrated["analysis_status"] == "legacy"
    assert migrated["stats"]["total_requests"] == 5
    assert len(migrated["findings"]) == 1
    assert migrated["findings"][0]["source"] == "legacy"

    connection = sqlite3.connect(database_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM report_findings").fetchone()[0] == 1
    finally:
        connection.close()
    get_settings.cache_clear()
