from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def risk_severity(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _finding_path(finding: dict[str, Any]) -> str:
    path = finding.get("path")
    if path is not None:
        return str(path)
    details = str(finding.get("details", ""))
    return details[6:] if details.startswith("Path: ") else details


def _finding_key(finding: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(finding.get("ip", "unknown")),
        str(finding.get("time", "")),
        _finding_path(finding),
    )


def _ml_risk_score(finding: dict[str, Any]) -> int:
    ratio = finding.get("score_ratio")
    if not isinstance(ratio, (int, float)) or ratio <= 1:
        return 60
    return min(95, max(60, round(40 + 20 * float(ratio))))


def unify_findings(
    rule_findings: Iterable[dict[str, Any]],
    ml_findings: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize rule and ML findings onto a shared 0-100 risk scale."""
    normalized: list[dict[str, Any]] = []

    for finding in rule_findings:
        score = finding.get("score", 0)
        risk_score = int(score) if isinstance(score, (int, float)) else 0
        risk_score = max(0, min(100, risk_score))
        normalized.append(
            {
                **finding,
                "source": "rule",
                "risk_score": risk_score,
                "risk_severity": risk_severity(risk_score),
            }
        )

    for finding in ml_findings:
        risk_score = _ml_risk_score(finding)
        normalized.append(
            {
                **finding,
                "source": "ml",
                "risk_score": risk_score,
                "risk_severity": risk_severity(risk_score),
            }
        )

    sources_by_key: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for finding in normalized:
        sources_by_key[_finding_key(finding)].add(str(finding["source"]))

    for finding in normalized:
        if len(sources_by_key[_finding_key(finding)]) > 1:
            corroborated_score = min(100, int(finding["risk_score"]) + 10)
            finding["risk_score"] = corroborated_score
            finding["risk_severity"] = risk_severity(corroborated_score)
            finding["corroborated"] = True
        else:
            finding["corroborated"] = False

    normalized.sort(
        key=lambda item: (
            -int(item["risk_score"]),
            str(item.get("time", "")),
            str(item.get("rule_id", item.get("type", ""))),
        )
    )

    overall_score = max((int(item["risk_score"]) for item in normalized), default=0)
    summary = {
        "overall_risk_score": overall_score,
        "overall_risk_severity": risk_severity(overall_score) if normalized else "none",
        "finding_count": len(normalized),
        "rule_finding_count": sum(item["source"] == "rule" for item in normalized),
        "ml_finding_count": sum(item["source"] == "ml" for item in normalized),
        "corroborated_finding_count": sum(bool(item["corroborated"]) for item in normalized),
    }
    return normalized, summary
