from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from core.auth import get_current_user
from core.detection import detect_rule_threats
from core.ml_engine import InferenceError, ModelArtifactError
from core.ml_runtime import get_anomaly_detector
from core.parser import parse_log_file
from core.risk import unify_findings
from core.upload_storage import UploadValidationError, resolve_upload_path


router = APIRouter()
settings = get_settings()
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _get_uploaded_file(filename: str, owner_id: str) -> Path:
    try:
        file_path = resolve_upload_path(filename, settings.upload_dir, owner_id)
    except UploadValidationError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file_path


def analyze_dataframe(dataframe):
    rule_findings = detect_rule_threats(dataframe)
    ml_findings = []
    ml_status = "available"

    try:
        ml_findings = get_anomaly_detector().detect_anomalies(dataframe)
    except ModelArtifactError:
        ml_status = "unavailable"
    except InferenceError:
        ml_status = "error"

    findings, risk = unify_findings(rule_findings, ml_findings)
    analysis_status = "complete" if ml_status == "available" else "degraded"
    return {
        "analysis_status": analysis_status,
        "ml_status": ml_status,
        "threat_count": len(findings),
        "findings": findings,
        "threats": findings,
        "risk": risk,
    }


@router.post("/scan/{filename}")
def scan_file(filename: str, current_user: CurrentUser):
    dataframe = parse_log_file(_get_uploaded_file(filename, current_user["id"]))
    if dataframe.empty:
        return {
            "analysis_status": "complete",
            "ml_status": "not_run",
            "threat_count": 0,
            "findings": [],
            "threats": [],
            "risk": {
                "overall_risk_score": 0,
                "overall_risk_severity": "none",
                "finding_count": 0,
                "rule_finding_count": 0,
                "ml_finding_count": 0,
                "corroborated_finding_count": 0,
            },
        }
    return analyze_dataframe(dataframe)
