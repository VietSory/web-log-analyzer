from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from config import get_settings
from core.auth import get_current_user
from core.parser import parse_log_file
from core.upload_storage import UploadValidationError, resolve_upload_path

router = APIRouter()
settings = get_settings()
CurrentUser = Annotated[dict, Depends(get_current_user)]


def _get_uploaded_file(filename: str) -> Path:
    try:
        file_path = resolve_upload_path(filename, settings.upload_dir)
    except UploadValidationError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return file_path


@router.get("/stats/{filename}")
def get_stats(filename: str, _current_user: CurrentUser):
    dataframe = parse_log_file(_get_uploaded_file(filename))
    if dataframe.empty:
        return {"error": "No data parsed"}

    total_requests = len(dataframe)
    unique_ips = int(dataframe["ip"].nunique())
    avg_size = round(float(dataframe["size"].mean()) / 1024, 2)
    server_errors = dataframe[dataframe["status"] >= 500].shape[0]
    error_rate = round((server_errors / total_requests) * 100, 2)

    status_counts = dataframe["status"].value_counts().head(5)
    status_distribution = {str(key): int(value) for key, value in status_counts.items()}

    traffic_chart: dict[str, int] = {}
    timed = dataframe.dropna(subset=["datetime"]).copy()
    if not timed.empty:
        traffic = timed.resample("h", on="datetime").size()
        for timestamp, count in traffic.items():
            if count > 0:
                traffic_chart[timestamp.strftime("%Y-%m-%d %H:%M")] = int(count)

    return {
        "total_requests": total_requests,
        "unique_ips": unique_ips,
        "avg_body_size": avg_size,
        "error_rate": error_rate,
        "status_distribution": status_distribution,
        "traffic_chart": traffic_chart,
    }


@router.get("/logs/{filename}")
def get_logs(filename: str, _current_user: CurrentUser):
    dataframe = parse_log_file(_get_uploaded_file(filename))
    if dataframe.empty:
        return []
    response_frame = dataframe.head(10000).copy()
    response_frame["datetime"] = response_frame["datetime"].astype(str)
    return response_frame.to_dict(orient="records")
