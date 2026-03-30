from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from database import get_db_connection


_REPORT_MIGRATIONS_TABLE = "report_store_migrations"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_dumps(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _json_loads(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _table_exists(connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def _create_schema(connection) -> None:
    connection.executescript(
        f'''
        CREATE TABLE IF NOT EXISTS {_REPORT_MIGRATIONS_TABLE} (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at TEXT NOT NULL,
            total_requests INTEGER NOT NULL,
            unique_ips INTEGER NOT NULL,
            error_rate REAL NOT NULL,
            analysis_status TEXT NOT NULL,
            ml_status TEXT NOT NULL,
            stats_json TEXT NOT NULL,
            risk_json TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS report_findings (
            id TEXT PRIMARY KEY,
            report_id TEXT NOT NULL,
            source TEXT NOT NULL,
            kind TEXT NOT NULL,
            severity TEXT NOT NULL,
            risk_score INTEGER,
            observed_at TEXT,
            ip TEXT,
            path TEXT,
            payload_json TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES reports(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_reports_owner_created
            ON reports(owner_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_report_findings_report
            ON report_findings(report_id);
        CREATE INDEX IF NOT EXISTS idx_report_findings_source_kind
            ON report_findings(source, kind);
        '''
    )


def _migration_applied(connection, version: int) -> bool:
    return (
        connection.execute(
            f"SELECT 1 FROM {_REPORT_MIGRATIONS_TABLE} WHERE version = ?",
            (version,),
        ).fetchone()
        is not None
    )


def _record_migration(connection, version: int) -> None:
    connection.execute(
        f"INSERT INTO {_REPORT_MIGRATIONS_TABLE} (version, applied_at) VALUES (?, ?)",
        (version, _utc_now()),
    )


def _legacy_finding_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "legacy",
        "type": "legacy_threat",
        "severity": str(row.get("severity") or "unknown"),
        "ip": row.get("ip"),
        "time": row.get("time"),
        "details": row.get("details"),
        "reconstruction_error": row.get("reconstruction_error"),
    }


def _migrate_legacy_reports(connection) -> None:
    if not _table_exists(connection, "scan_history"):
        return

    valid_owner_ids = {
        row["id"] for row in connection.execute("SELECT id FROM users").fetchall()
    }
    history_rows = [
        dict(row) for row in connection.execute("SELECT * FROM scan_history").fetchall()
    ]

    for row in history_rows:
        owner_id = row.get("owner_id")
        if owner_id not in valid_owner_ids:
            continue

        stats = {
            "total_requests": int(row.get("total_requests") or 0),
            "unique_ips": int(row.get("unique_ips") or 0),
            "error_rate": float(row.get("error_rate") or 0.0),
            "traffic_chart": _json_loads(row.get("traffic_data"), {}),
            "status_distribution": _json_loads(row.get("status_data"), {}),
        }
        risk = {
            "overall_risk_score": 0,
            "overall_risk_severity": "unknown",
            "finding_count": 0,
            "rule_finding_count": 0,
            "ml_finding_count": 0,
            "corroborated_finding_count": 0,
        }
        report_id = str(row.get("id") or uuid4())
        connection.execute(
            '''
            INSERT OR IGNORE INTO reports (
                id, owner_id, filename, created_at, total_requests, unique_ips,
                error_rate, analysis_status, ml_status, stats_json, risk_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                report_id,
                owner_id,
                str(row.get("filename") or "legacy.log"),
                str(row.get("scan_date") or _utc_now()),
                stats["total_requests"],
                stats["unique_ips"],
                stats["error_rate"],
                "legacy",
                "unknown",
                _json_dumps(stats),
                _json_dumps(risk),
            ),
        )

    if not _table_exists(connection, "scan_threats"):
        return

    for row in map(
        dict,
        connection.execute("SELECT * FROM scan_threats").fetchall(),
    ):
        report_id = str(row.get("history_id") or "")
        if not report_id:
            continue
        if (
            connection.execute(
                "SELECT 1 FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
            is None
        ):
            continue

        payload = _legacy_finding_payload(row)
        connection.execute(
            '''
            INSERT OR IGNORE INTO report_findings (
                id, report_id, source, kind, severity, risk_score,
                observed_at, ip, path, payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                str(row.get("id") or uuid4()),
                report_id,
                "legacy",
                "legacy_threat",
                payload["severity"],
                None,
                payload.get("time"),
                payload.get("ip"),
                None,
                _json_dumps(payload),
            ),
        )


def init_report_store() -> None:
    connection = get_db_connection()
    try:
        with connection:
            _create_schema(connection)
            if not _migration_applied(connection, 1):
                _migrate_legacy_reports(connection)
                _record_migration(connection, 1)
    finally:
        connection.close()


def _validated_stats(stats: dict[str, Any]) -> tuple[int, int, float]:
    total_requests = int(stats["total_requests"])
    unique_ips = int(stats["unique_ips"])
    error_rate = float(stats["error_rate"])
    if total_requests < 0 or unique_ips < 0:
        raise ValueError("report statistics must be non-negative")
    if not 0.0 <= error_rate <= 100.0:
        raise ValueError("error_rate must be between 0 and 100")
    return total_requests, unique_ips, error_rate


def _risk_score(finding: dict[str, Any]) -> int | None:
    value = finding.get("risk_score")
    if value is None:
        return None
    score = int(value)
    if not 0 <= score <= 100:
        raise ValueError("finding risk_score must be between 0 and 100")
    return score


def save_report(
    *,
    owner_id: str,
    filename: str,
    stats: dict[str, Any],
    findings: list[dict[str, Any]],
    analysis_status: str,
    ml_status: str,
    risk: dict[str, Any],
) -> str:
    if not owner_id:
        raise ValueError("owner_id is required")
    filename = filename.strip()
    if not filename:
        raise ValueError("filename is required")

    total_requests, unique_ips, error_rate = _validated_stats(stats)
    overall_score = int(risk.get("overall_risk_score", 0))
    if not 0 <= overall_score <= 100:
        raise ValueError("overall risk score must be between 0 and 100")

    stats_json = _json_dumps(stats)
    risk_json = _json_dumps(risk)
    report_id = str(uuid4())
    connection = get_db_connection()

    try:
        with connection:
            connection.execute(
                '''
                INSERT INTO reports (
                    id, owner_id, filename, created_at, total_requests, unique_ips,
                    error_rate, analysis_status, ml_status, stats_json, risk_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    report_id,
                    owner_id,
                    filename,
                    _utc_now(),
                    total_requests,
                    unique_ips,
                    error_rate,
                    str(analysis_status),
                    str(ml_status),
                    stats_json,
                    risk_json,
                ),
            )

            for finding in findings:
                payload_json = _json_dumps(finding)
                source = str(finding.get("source") or "unknown")[:32]
                kind = str(
                    finding.get("rule_id")
                    or finding.get("type")
                    or "unknown"
                )[:96]
                severity = str(
                    finding.get("risk_severity")
                    or finding.get("severity")
                    or "unknown"
                )[:32]
                connection.execute(
                    '''
                    INSERT INTO report_findings (
                        id, report_id, source, kind, severity, risk_score,
                        observed_at, ip, path, payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        str(uuid4()),
                        report_id,
                        source,
                        kind,
                        severity,
                        _risk_score(finding),
                        finding.get("time"),
                        finding.get("ip"),
                        finding.get("path"),
                        payload_json,
                    ),
                )
    finally:
        connection.close()

    return report_id


def list_reports(owner_id: str) -> list[dict[str, Any]]:
    connection = get_db_connection()
    try:
        rows = connection.execute(
            '''
            SELECT id, filename, created_at, total_requests, unique_ips,
                   error_rate, analysis_status, ml_status, risk_json
            FROM reports
            WHERE owner_id = ?
            ORDER BY created_at DESC, id DESC
            ''',
            (owner_id,),
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            risk = _json_loads(item.pop("risk_json"), {})
            item["overall_risk_score"] = int(risk.get("overall_risk_score", 0))
            item["overall_risk_severity"] = str(
                risk.get("overall_risk_severity", "unknown")
            )
            result.append(item)
        return result
    finally:
        connection.close()


def get_report(report_id: str, owner_id: str) -> dict[str, Any] | None:
    connection = get_db_connection()
    try:
        report = connection.execute(
            "SELECT * FROM reports WHERE id = ? AND owner_id = ?",
            (report_id, owner_id),
        ).fetchone()
        if report is None:
            return None

        finding_rows = connection.execute(
            '''
            SELECT payload_json
            FROM report_findings
            WHERE report_id = ?
            ORDER BY risk_score DESC, rowid ASC
            ''',
            (report_id,),
        ).fetchall()

        result = dict(report)
        result["stats"] = _json_loads(result.pop("stats_json"), {})
        result["risk"] = _json_loads(result.pop("risk_json"), {})
        findings = [
            _json_loads(row["payload_json"], {})
            for row in finding_rows
        ]
        result["findings"] = findings
        result["threats"] = findings
        return result
    finally:
        connection.close()


def delete_report(report_id: str, owner_id: str) -> bool:
    connection = get_db_connection()
    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM reports WHERE id = ? AND owner_id = ?",
                (report_id, owner_id),
            )
        return cursor.rowcount > 0
    finally:
        connection.close()


def clear_reports(owner_id: str) -> int:
    connection = get_db_connection()
    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM reports WHERE owner_id = ?",
                (owner_id,),
            )
        return max(cursor.rowcount, 0)
    finally:
        connection.close()
