from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.risk import risk_severity, unify_findings


def test_risk_severity_boundaries_are_stable():
    assert risk_severity(0) == "low"
    assert risk_severity(40) == "medium"
    assert risk_severity(65) == "high"
    assert risk_severity(85) == "critical"


def test_unifies_rule_and_ml_scores_and_sorts_highest_first():
    rules = [
        {
            "rule_id": "WEB-PROBE-001",
            "severity": "medium",
            "score": 40,
            "ip": "192.0.2.1",
            "time": "2026-02-01T12:00:00Z",
            "path": "/.env",
        }
    ]
    ml = [
        {
            "type": "ml_anomaly",
            "severity": "high",
            "score_ratio": 1.5,
            "ip": "192.0.2.2",
            "time": "2026-02-01T12:01:00Z",
            "details": "Path: /login",
        }
    ]

    findings, summary = unify_findings(rules, ml)

    assert [finding["source"] for finding in findings] == ["ml", "rule"]
    assert findings[0]["risk_score"] == 70
    assert summary == {
        "overall_risk_score": 70,
        "overall_risk_severity": "high",
        "finding_count": 2,
        "rule_finding_count": 1,
        "ml_finding_count": 1,
        "corroborated_finding_count": 0,
    }


def test_corroborated_rule_and_ml_findings_receive_bounded_bonus():
    common = {
        "ip": "2001:db8::1",
        "time": "2026-02-01T12:00:00Z",
    }
    rules = [
        {
            **common,
            "rule_id": "WEB-SQLI-001",
            "score": 70,
            "severity": "high",
            "path": "/search?q=union+select",
        }
    ]
    ml = [
        {
            **common,
            "type": "ml_anomaly",
            "score_ratio": 2.0,
            "severity": "high",
            "details": "Path: /search?q=union+select",
        }
    ]

    findings, summary = unify_findings(rules, ml)

    assert all(finding["corroborated"] for finding in findings)
    assert [finding["risk_score"] for finding in findings] == [90, 80]
    assert summary["overall_risk_score"] == 90
    assert summary["overall_risk_severity"] == "critical"
    assert summary["corroborated_finding_count"] == 2


def test_empty_findings_have_explicit_none_severity():
    findings, summary = unify_findings([], [])
    assert findings == []
    assert summary["overall_risk_score"] == 0
    assert summary["overall_risk_severity"] == "none"
