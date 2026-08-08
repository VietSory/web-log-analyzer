from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from routers import servers
from schemas.analysis import AnalysisResponse


def _rule_analysis() -> AnalysisResponse:
    finding = {
        "source": "rule",
        "rule_id": "WEB-PROBE-001",
        "title": "Sensitive endpoint probe",
        "severity": "medium",
        "score": 40,
        "evidence": "/.env",
        "ip": "192.0.2.10",
        "time": "2026-02-10T12:00:00Z",
        "path": "/.env",
        "risk_score": 40,
        "risk_severity": "medium",
        "corroborated": False,
    }
    return AnalysisResponse(
        analysis_status="degraded",
        ml_status="unavailable",
        threat_count=1,
        findings=[finding],
        threats=[finding],
        risk={
            "overall_risk_score": 40,
            "overall_risk_severity": "medium",
            "finding_count": 1,
            "rule_finding_count": 1,
            "ml_finding_count": 0,
            "corroborated_finding_count": 0,
        },
    )


def _safe_analysis() -> AnalysisResponse:
    return AnalysisResponse(
        analysis_status="complete",
        ml_status="available",
        threat_count=0,
        findings=[],
        threats=[],
        risk={
            "overall_risk_score": 0,
            "overall_risk_severity": "none",
            "finding_count": 0,
            "rule_finding_count": 0,
            "ml_finding_count": 0,
            "corroborated_finding_count": 0,
        },
    )


def _request() -> servers.LogAnalyzeRequest:
    return servers.LogAnalyzeRequest(
        log_content='192.0.2.10 - - [10/Feb/2026:12:00:00 +0000] "GET /.env HTTP/1.1" 403 12',
        ip="192.0.2.10",
        method="GET",
        path="/.env",
        protocol="HTTP/1.1",
        status=403,
        size=12,
        user_agent="pytest",
        datetime="2026-02-10T12:00:00Z",
    )


def test_server_analysis_uses_hybrid_service_even_when_ml_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        servers,
        "get_server_by_id",
        lambda _server_id: {"id": "server-1", "owner_id": "user-1", "name": "prod"},
    )
    monkeypatch.setattr(servers, "analyze_dataframe", lambda _frame: _rule_analysis())

    persisted = {}
    monkeypatch.setattr(
        servers,
        "create_log",
        lambda server_id, log_status, content: persisted.update(
            server_id=server_id,
            log_status=log_status,
            content=content,
        )
        or "log-1",
    )
    delivered = {}
    monkeypatch.setattr(
        servers.mail_service,
        "send_warning_alert",
        lambda **kwargs: delivered.update(kwargs) or True,
    )

    response = servers.analyze_log_endpoint(
        "server-1",
        _request(),
        {"id": "user-1"},
    )

    assert response.log_status == "warning"
    assert response.analysis.analysis_status == "degraded"
    assert response.analysis.ml_status == "unavailable"
    assert persisted["log_status"] == "warning"
    assert delivered["anomaly_details"][0]["rule_id"] == "WEB-PROBE-001"


def test_server_analysis_does_not_send_alert_for_safe_result(monkeypatch):
    monkeypatch.setattr(
        servers,
        "get_server_by_id",
        lambda _server_id: {"id": "server-1", "owner_id": "user-1", "name": "prod"},
    )
    monkeypatch.setattr(servers, "analyze_dataframe", lambda _frame: _safe_analysis())
    monkeypatch.setattr(servers, "create_log", lambda *_args: "log-safe")

    called = False

    def send_warning_alert(**_kwargs):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(servers.mail_service, "send_warning_alert", send_warning_alert)

    response = servers.analyze_log_endpoint(
        "server-1",
        _request(),
        {"id": "user-1"},
    )

    assert response.log_status == "safe"
    assert response.is_anomaly is False
    assert called is False
