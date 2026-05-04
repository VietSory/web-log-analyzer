from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from core.auth import get_current_user
from core.parser import parse_log_file
from core.upload_storage import UploadValidationError, resolve_upload_path
from schemas.logs import LogRecord, LogStats
from services.statistics import compute_log_stats, serialize_log_records


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


@router.get("/stats/{filename}", response_model=LogStats)
def get_stats(filename: str, current_user: CurrentUser) -> LogStats:
    dataframe = parse_log_file(_get_uploaded_file(filename, current_user["id"]))
    return compute_log_stats(dataframe)


@router.get("/logs/{filename}", response_model=list[LogRecord])
def get_logs(filename: str, current_user: CurrentUser) -> list[dict[str, object]]:
    dataframe = parse_log_file(_get_uploaded_file(filename, current_user["id"]))
    return serialize_log_records(dataframe)
