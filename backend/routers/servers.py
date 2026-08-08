from __future__ import annotations

from datetime import datetime, timezone
from ipaddress import IPv4Address
from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.mail_service import mail_service
from database import (
    create_log,
    create_server,
    delete_server,
    get_server_by_id,
    get_server_logs,
    get_user_servers,
)
from schemas.analysis import ServerLogAnalysisResponse
from services.analysis import analyze_dataframe


router = APIRouter()
CurrentUser = Annotated[dict, Depends(get_current_user)]


class CreateServerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    ipv4: IPv4Address | None = None


class LogAnalyzeRequest(BaseModel):
    log_content: str = Field(min_length=1, max_length=20_000)
    ip: str | None = Field(default=None, max_length=64)
    method: str | None = Field(default=None, min_length=1, max_length=16)
    path: str | None = Field(default=None, max_length=4096)
    protocol: str | None = Field(default=None, max_length=32)
    status: int | None = Field(default=None, ge=100, le=599)
    size: int | None = Field(default=None, ge=0)
    referrer: str | None = Field(default=None, max_length=4096)
    user_agent: str | None = Field(default=None, max_length=2048)
    datetime: str | None = Field(default=None, max_length=128)


def _owned_server(server_id: str, current_user: dict) -> dict:
    server = get_server_by_id(server_id)
    if not server or server.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.post("/servers", status_code=status.HTTP_201_CREATED)
def create_server_endpoint(request: CreateServerRequest, current_user: CurrentUser):
    server_id = create_server(
        current_user["id"],
        request.name.strip(),
        str(request.ipv4) if request.ipv4 else None,
    )
    return {
        "status": "success",
        "message": "Server created successfully",
        "server_id": server_id,
    }


@router.get("/servers")
def get_user_servers_endpoint(current_user: CurrentUser):
    return get_user_servers(current_user["id"])


@router.get("/servers/{server_id}")
def get_server_endpoint(server_id: str, current_user: CurrentUser):
    return _owned_server(server_id, current_user)


@router.delete("/servers/{server_id}")
def delete_server_endpoint(server_id: str, current_user: CurrentUser):
    _owned_server(server_id, current_user)
    if not delete_server(server_id):
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "success", "message": "Server deleted successfully"}


@router.get("/servers/{server_id}/logs")
def get_server_logs_endpoint(server_id: str, current_user: CurrentUser):
    server = _owned_server(server_id, current_user)
    logs = get_server_logs(server_id)
    return {"server": server, "logs": logs, "total_logs": len(logs)}


@router.get("/servers/{server_id}/stats")
def get_server_stats_endpoint(server_id: str, current_user: CurrentUser):
    server = _owned_server(server_id, current_user)
    logs = get_server_logs(server_id)

    total_logs = len(logs)
    warning_logs = [log for log in logs if str(log.get("status", "")).lower() == "warning"]
    safe_logs = [log for log in logs if str(log.get("status", "")).lower() == "safe"]

    status_counts: dict[str, int] = {}
    for log in logs:
        log_status = str(log.get("status", "unknown"))
        status_counts[log_status] = status_counts.get(log_status, 0) + 1

    warning_count = len(warning_logs)
    safe_count = len(safe_logs)
    warning_percentage = (warning_count / total_logs * 100) if total_logs else 0.0
    safe_percentage = (safe_count / total_logs * 100) if total_logs else 0.0

    return {
        "server": server,
        "total_logs": total_logs,
        "warning_count": warning_count,
        "safe_count": safe_count,
        "warning_percentage": round(warning_percentage, 2),
        "safe_percentage": round(safe_percentage, 2),
        "status_distribution": status_counts,
        "warning_logs": warning_logs[:10],
    }


@router.post(
    "/servers/{server_id}/analyze",
    response_model=ServerLogAnalysisResponse,
)
def analyze_log_endpoint(
    server_id: str,
    request: LogAnalyzeRequest,
    current_user: CurrentUser,
) -> ServerLogAnalysisResponse:
    server = _owned_server(server_id, current_user)
    event_time = request.datetime or datetime.now(timezone.utc).isoformat(timespec="seconds")
    log_data = {
        "ip": request.ip or "unknown",
        "method": request.method or "GET",
        "path": request.path or "/",
        "protocol": request.protocol or "unknown",
        "status": request.status if request.status is not None else 200,
        "size": request.size if request.size is not None else 0,
        "referrer": request.referrer or "-",
        "user_agent": request.user_agent or "unknown",
        "datetime": event_time,
        "source_format": "api",
    }

    analysis = analyze_dataframe(pd.DataFrame([log_data]))
    has_findings = bool(analysis.findings)
    log_status = "warning" if has_findings else "safe"
    log_id = create_log(server_id, log_status, request.log_content)

    if has_findings:
        mail_service.send_warning_alert(
            server_name=server.get("name", "Unknown Server"),
            server_id=server_id,
            log_content=request.log_content,
            anomaly_details=[finding.model_dump() for finding in analysis.findings],
        )

    return ServerLogAnalysisResponse(
        log_id=log_id,
        log_status=log_status,
        is_anomaly=has_findings,
        anomalies=analysis.findings,
        analysis=analysis,
        message=f"Log analyzed and saved as '{log_status}'",
    )
