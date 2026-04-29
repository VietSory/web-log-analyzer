from pathlib import Path
import sys

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.ml_engine import InferenceError, ModelArtifactError
from services.analysis import analyze_dataframe


class FakeDetector:
    def __init__(self, findings=None, error: Exception | None = None):
        self.findings = findings or []
        self.error = error

    def detect_anomalies(self, _dataframe):
        if self.error is not None:
            raise self.error
        return self.findings


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ip": "192.0.2.10",
                "datetime": "2026-02-10T12:00:00Z",
                "method": "GET",
                "path": "/.env",
                "status": 403,
                "size": 12,
                "user_agent": "pytest",
            }
        ]
    )


def _rule_findings(_dataframe):
    return [
        {
            "rule_id": "WEB-PROBE-002",
            "title": "Denied sensitive endpoint probe",
            "severity": "high",
            "score": 70,
            "evidence": "status=403 path=/.env",
            "ip": "192.0.2.10",
            "time": "2026-02-10T12:00:00Z",
            "path": "/.env",
        }
    ]


def _ml_findings():
    return [
        {
            "ip": "192.0.2.10",
            "type": "ml_anomaly",
            "severity": "high",
            "time": "2026-02-10T12:00:00Z",
            "reconstruction_error": 0.4,
            "threshold": 0.1,
            "score_ratio": 4.0,
            "details": "Path: /.env",
        }
    ]


def test_empty_dataframe_skips_ml_and_returns_stable_response():
    called = False

    def detector_provider():
        nonlocal called
        called = True
        return FakeDetector()

    response = analyze_dataframe(pd.DataFrame(), detector_provider=detector_provider)

    assert response.analysis_status == "complete"
    assert response.ml_status == "not_run"
    assert response.threat_count == 0
    assert response.findings == []
    assert response.risk.overall_risk_severity == "none"
    assert called is False


def test_available_ml_and_rule_findings_are_unified_and_corroborated():
    response = analyze_dataframe(
        _frame(),
        rule_detector=_rule_findings,
        detector_provider=lambda: FakeDetector(_ml_findings()),
    )

    assert response.analysis_status == "complete"
    assert response.ml_status == "available"
    assert response.threat_count == 2
    assert response.risk.finding_count == 2
    assert response.risk.rule_finding_count == 1
    assert response.risk.ml_finding_count == 1
    assert response.risk.corroborated_finding_count == 2
    assert all(finding.corroborated for finding in response.findings)
    assert response.threats == response.findings


def test_missing_model_degrades_without_hiding_rule_findings():
    response = analyze_dataframe(
        _frame(),
        rule_detector=_rule_findings,
        detector_provider=lambda: FakeDetector(error=ModelArtifactError("missing")),
    )

    assert response.analysis_status == "degraded"
    assert response.ml_status == "unavailable"
    assert response.threat_count == 1
    assert response.findings[0].source == "rule"


def test_inference_error_degrades_without_hiding_rule_findings():
    response = analyze_dataframe(
        _frame(),
        rule_detector=_rule_findings,
        detector_provider=lambda: FakeDetector(error=InferenceError("failed")),
    )

    assert response.analysis_status == "degraded"
    assert response.ml_status == "error"
    assert response.threat_count == 1
    assert response.findings[0].source == "rule"
