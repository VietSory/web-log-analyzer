from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from urllib.parse import unquote

import pandas as pd


_SEVERITY_POINTS = {
    "low": 20,
    "medium": 40,
    "high": 70,
    "critical": 90,
}

_SQLI_PATTERN = re.compile(
    r"(?:\bunion\s+(?:all\s+)?select\b|\bselect\b.{0,80}\bfrom\b|"
    r"\b(?:or|and)\b\s+['\"0-9][^\r\n]{0,40}=|"
    r"\b(?:sleep|benchmark)\s*\()",
    re.IGNORECASE,
)
_XSS_PATTERN = re.compile(
    r"(?:<\s*script\b|javascript\s*:|on(?:error|load|click|mouseover)\s*=|"
    r"<\s*(?:img|svg|iframe)\b[^>]{0,120}(?:on\w+|javascript\s*:))",
    re.IGNORECASE,
)
_SENSITIVE_PATH_PATTERN = re.compile(
    r"(?:^|/)(?:\.env|\.git(?:/|$)|wp-admin(?:/|$)|phpmyadmin(?:/|$)|"
    r"server-status(?:/|$)|actuator(?:/|$)|\.aws(?:/|$))",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Detection:
    rule_id: str
    title: str
    severity: str
    score: int
    evidence: str
    ip: str
    time: str
    path: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _canonicalize_path(value: object) -> str:
    text = str(value or "")
    for _ in range(2):
        decoded = unquote(text)
        if decoded == text:
            break
        text = decoded
    return text


def _evidence(value: str, *, limit: int = 180) -> str:
    single_line = value.replace("\r", "\\r").replace("\n", "\\n")
    return single_line if len(single_line) <= limit else single_line[: limit - 3] + "..."


def _detection(
    *,
    rule_id: str,
    title: str,
    severity: str,
    row: pd.Series,
    evidence: str,
    path: str,
) -> Detection:
    return Detection(
        rule_id=rule_id,
        title=title,
        severity=severity,
        score=_SEVERITY_POINTS[severity],
        evidence=_evidence(evidence),
        ip=str(row.get("ip", "unknown")),
        time=str(row.get("datetime", "")),
        path=path,
    )


def detect_rule_threats(dataframe: pd.DataFrame) -> list[dict[str, object]]:
    """Return explainable request-level detections without blocking traffic."""
    detections: list[Detection] = []

    for _, row in dataframe.iterrows():
        path = _canonicalize_path(row.get("path", ""))
        user_agent = str(row.get("user_agent", ""))
        inspection_text = f"{path}\n{user_agent}"
        lowered = path.lower().replace("\\", "/")

        segments = [segment for segment in lowered.split("/") if segment not in ("", ".")]
        if ".." in segments:
            detections.append(
                _detection(
                    rule_id="WEB-TRAVERSAL-001",
                    title="Path traversal sequence",
                    severity="high",
                    row=row,
                    evidence=path,
                    path=path,
                )
            )

        sqli_match = _SQLI_PATTERN.search(inspection_text)
        if sqli_match is not None:
            detections.append(
                _detection(
                    rule_id="WEB-SQLI-001",
                    title="SQL injection-like payload",
                    severity="high",
                    row=row,
                    evidence=f"matched={sqli_match.group(0)}",
                    path=path,
                )
            )

        xss_match = _XSS_PATTERN.search(inspection_text)
        if xss_match is not None:
            detections.append(
                _detection(
                    rule_id="WEB-XSS-001",
                    title="Cross-site scripting-like payload",
                    severity="high",
                    row=row,
                    evidence=f"matched={xss_match.group(0)}",
                    path=path,
                )
            )

        if _SENSITIVE_PATH_PATTERN.search(lowered):
            detections.append(
                _detection(
                    rule_id="WEB-PROBE-001",
                    title="Sensitive endpoint probe",
                    severity="medium",
                    row=row,
                    evidence=path,
                    path=path,
                )
            )

        status = row.get("status")
        if isinstance(status, (int, float)) and int(status) in (401, 403):
            if _SENSITIVE_PATH_PATTERN.search(lowered):
                detections.append(
                    _detection(
                        rule_id="WEB-PROBE-002",
                        title="Denied sensitive endpoint probe",
                        severity="high",
                        row=row,
                        evidence=f"status={int(status)} path={path}",
                        path=path,
                    )
                )

    return [detection.to_dict() for detection in detections]


def severity_points(severity: str) -> int:
    return _SEVERITY_POINTS.get(severity.lower(), 0)
