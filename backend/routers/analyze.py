from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from core.auth import get_current_user
from core.ml_engine import LogAnomalyDetector
from core.parser import parse_log_file
from core.upload_storage import UploadValidationError, resolve_upload_path


router = APIRouter()
settings = get_settings()
CurrentUser = Annotated[dict, Depends(get_current_user)]

ai_engine = LogAnomalyDetector(model_dir="models")
print("⏳ Loading AI Model for Analyzer...")
try:
    ai_engine.load_resources()
except Exception as exc:
    print(f"⚠️ Warning: Could not load AI model: {exc}")


def _get_uploaded_file(filename: str) -> Path:
    try:
        file_path = resolve_upload_path(filename, settings.upload_dir)
    except UploadValidationError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return file_path


@router.post("/scan/{filename}")
def scan_file(filename: str, _current_user: CurrentUser):
    dataframe = parse_log_file(_get_uploaded_file(filename))
    if dataframe.empty:
        return {"threat_count": 0, "threats": []}

    try:
        threats = ai_engine.detect_anomalies(dataframe)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="AI engine failed") from exc

    return {"threat_count": len(threats), "threats": threats}
