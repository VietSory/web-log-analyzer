from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


Severity = Literal["none", "low", "medium", "high", "critical", "unknown"]


class RiskSummary(BaseModel):
    overall_risk_score: int = Field(ge=0, le=100)
    overall_risk_severity: Severity
    finding_count: int = Field(ge=0)
    rule_finding_count: int = Field(ge=0)
    ml_finding_count: int = Field(ge=0)
    corroborated_finding_count: int = Field(ge=0)


class AnalysisFinding(BaseModel):
    source: Literal["rule", "ml"]
    risk_score: int = Field(ge=0, le=100)
    risk_severity: Literal["low", "medium", "high", "critical"]
    corroborated: bool

    ip: str
    time: str
    severity: str

    rule_id: str | None = None
    title: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    evidence: str | None = None
    path: str | None = None

    type: str | None = None
    reconstruction_error: float | None = Field(default=None, ge=0)
    threshold: float | None = Field(default=None, gt=0)
    score_ratio: float | None = Field(default=None, gt=0)
    details: str | None = None

    @model_validator(mode="after")
    def validate_source_specific_fields(self) -> "AnalysisFinding":
        if self.source == "rule" and not self.rule_id:
            raise ValueError("rule findings require rule_id")
        if self.source == "ml":
            if not self.type:
                raise ValueError("ml findings require type")
            if self.reconstruction_error is None or self.threshold is None:
                raise ValueError("ml findings require reconstruction_error and threshold")
        return self


class AnalysisResponse(BaseModel):
    analysis_status: Literal["complete", "degraded"]
    ml_status: Literal["available", "unavailable", "error", "not_run"]
    threat_count: int = Field(ge=0)
    findings: list[AnalysisFinding]
    threats: list[AnalysisFinding]
    risk: RiskSummary

    @model_validator(mode="after")
    def validate_summary_consistency(self) -> "AnalysisResponse":
        if self.threat_count != len(self.findings):
            raise ValueError("threat_count must match findings length")
        if self.risk.finding_count != len(self.findings):
            raise ValueError("risk finding_count must match findings length")
        if self.threats != self.findings:
            raise ValueError("threats compatibility field must mirror findings")
        if self.ml_status == "available" and self.analysis_status != "complete":
            raise ValueError("available ML analysis must be complete")
        if self.ml_status in {"unavailable", "error"} and self.analysis_status != "degraded":
            raise ValueError("ML failure states must produce degraded analysis")
        return self


class ServerLogAnalysisResponse(BaseModel):
    status: Literal["success"] = "success"
    log_id: str
    log_status: Literal["safe", "warning"]
    is_anomaly: bool
    anomalies: list[AnalysisFinding]
    analysis: AnalysisResponse
    message: str

    @model_validator(mode="after")
    def validate_compatibility_fields(self) -> "ServerLogAnalysisResponse":
        has_findings = bool(self.analysis.findings)
        if self.is_anomaly != has_findings:
            raise ValueError("is_anomaly must match analysis findings")
        if self.anomalies != self.analysis.findings:
            raise ValueError("anomalies compatibility field must mirror analysis findings")
        expected_status = "warning" if has_findings else "safe"
        if self.log_status != expected_status:
            raise ValueError("log_status must match analysis findings")
        return self


def empty_risk_summary() -> dict[str, Any]:
    return {
        "overall_risk_score": 0,
        "overall_risk_severity": "none",
        "finding_count": 0,
        "rule_finding_count": 0,
        "ml_finding_count": 0,
        "corroborated_finding_count": 0,
    }
