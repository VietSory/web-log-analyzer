from pathlib import Path
import sys

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.detection import detect_rule_threats


def _frame(path: str, *, status: int = 200, user_agent: str = "pytest") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ip": "2001:db8::1",
                "datetime": "2026-02-01T12:00:00Z",
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "status": status,
                "size": 123,
                "referrer": "-",
                "user_agent": user_agent,
                "source_format": "combined",
            }
        ]
    )


def _rule_ids(path: str, **kwargs) -> set[str]:
    return {item["rule_id"] for item in detect_rule_threats(_frame(path, **kwargs))}


def test_detects_plain_and_encoded_path_traversal():
    assert "WEB-TRAVERSAL-001" in _rule_ids("/../../etc/passwd")
    assert "WEB-TRAVERSAL-001" in _rule_ids("/%252e%252e/%252e%252e/etc/passwd")


def test_detects_sqli_and_xss_signatures_with_evidence():
    sqli = detect_rule_threats(_frame("/search?q=' UNION SELECT password FROM users--"))
    assert sqli[0]["rule_id"] == "WEB-SQLI-001"
    assert "UNION SELECT" in sqli[0]["evidence"]
    assert sqli[0]["severity"] == "high"

    assert "WEB-XSS-001" in _rule_ids("/search?q=%3Cscript%3Ealert(1)%3C/script%3E")


def test_sensitive_probe_escalates_when_access_is_denied():
    rule_ids = _rule_ids("/.env", status=403)
    assert rule_ids == {"WEB-PROBE-001", "WEB-PROBE-002"}


def test_benign_requests_do_not_trigger_rules():
    assert detect_rule_threats(_frame("/products?page=2")) == []
    assert detect_rule_threats(_frame("/docs/select-from-examples")) == []


def test_evidence_is_bounded_and_single_line():
    payload = "/.env?value=" + "x" * 400 + "\nforged"
    detection = detect_rule_threats(_frame(payload))[0]
    assert len(detection["evidence"]) <= 180
    assert "\n" not in detection["evidence"]
