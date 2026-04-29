from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from core.detection import detect_rule_threats
from core.ml_engine import InferenceError, LogAnomalyDetector, ModelArtifactError
from core.ml_runtime import get_anomaly_detector
from core.risk import unify_findings
from schemas.analysis import AnalysisResponse, empty_risk_summary


RuleDetector = Callable[[pd.DataFrame], list[dict[str, object]]]
DetectorProvider = Callable[[], LogAnomalyDetector]


def analyze_dataframe(
    dataframe: pd.DataFrame,
    *,
    rule_detector: RuleDetector = detect_rule_threats,
    detector_provider: DetectorProvider = get_anomaly_detector,
) -> AnalysisResponse:
    """Run deterministic rule analysis and optional ML inference for normalized logs."""
    if dataframe.empty:
        return AnalysisResponse(
            analysis_status="complete",
            ml_status="not_run",
            threat_count=0,
            findings=[],
            threats=[],
            risk=empty_risk_summary(),
        )

    rule_findings = rule_detector(dataframe)
    ml_findings: list[dict[str, object]] = []
    ml_status = "available"

    try:
        ml_findings = detector_provider().detect_anomalies(dataframe)
    except ModelArtifactError:
        ml_status = "unavailable"
    except InferenceError:
        ml_status = "error"

    findings, risk = unify_findings(rule_findings, ml_findings)
    analysis_status = "complete" if ml_status == "available" else "degraded"

    return AnalysisResponse(
        analysis_status=analysis_status,
        ml_status=ml_status,
        threat_count=len(findings),
        findings=findings,
        threats=findings,
        risk=risk,
    )
