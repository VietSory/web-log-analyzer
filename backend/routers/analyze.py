from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from core.auth import get_current_user
from core.parser import parse_log_file
from core.upload_storage import UploadValidationError, resolve_upload_path
from schemas.analysis import AnalysisResponse
from services.analysis import analyze_dataframe


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


@router.post("/scan/{filename}", response_model=AnalysisResponse)
def scan_file(filename: str, current_user: CurrentUser) -> AnalysisResponse:
    dataframe = parse_log_file(_get_uploaded_file(filename, current_user["id"]))
    return analyze_dataframe(dataframe)
