from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from config import get_settings
from core.auth import get_current_user
from core.ml_engine import InferenceError, ModelArtifactError
from core.ml_runtime import get_anomaly_detector
from core.parser import parse_log_file
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


@router.post("/scan/{filename}")
def scan_file(filename: str, current_user: CurrentUser):
    dataframe = parse_log_file(_get_uploaded_file(filename, current_user["id"]))
    if dataframe.empty:
        return {"threat_count": 0, "threats": []}

    try:
        threats = get_anomaly_detector().detect_anomalies(dataframe)
    except ModelArtifactError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI model is not available",
        ) from exc
    except InferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI inference failed",
        ) from exc

    return {"threat_count": len(threats), "threats": threats}
