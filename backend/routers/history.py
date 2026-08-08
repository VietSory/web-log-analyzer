from __future__ import annotations

import sqlite3
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.report_store import (
    clear_reports,
    delete_report,
    get_report,
    list_reports,
    save_report,
)


router = APIRouter()
CurrentUser = Annotated[dict, Depends(get_current_user)]


class SavePayload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    stats: dict[str, Any]
    findings: list[dict[str, Any]] = Field(default_factory=list, max_length=10_000)
    analysis_status: Literal["complete", "degraded"]
    ml_status: Literal["available", "unavailable", "error", "not_run"]
    risk: dict[str, Any]


@router.get("/list")
def get_history_list(current_user: CurrentUser):
    return list_reports(current_user["id"])


@router.get("/detail/{report_id}")
def get_history_detail(report_id: str, current_user: CurrentUser):
    report = get_report(report_id, current_user["id"])
    if report is None:
        raise HTTPException(status_code=404, detail="History not found")
    return report


@router.post("/save", status_code=status.HTTP_201_CREATED)
def save_history(payload: SavePayload, current_user: CurrentUser):
    try:
        report_id = save_report(
            owner_id=current_user["id"],
            filename=payload.filename,
            stats=payload.stats,
            findings=payload.findings,
            analysis_status=payload.analysis_status,
            ml_status=payload.ml_status,
            risk=payload.risk,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid report payload") from exc
    except (sqlite3.Error, OSError) as exc:
        raise HTTPException(status_code=500, detail="Could not save report") from exc

    return {"status": "success", "history_id": report_id, "id": report_id}


@router.delete("/clear-all")
def clear_history(current_user: CurrentUser):
    deleted = clear_reports(current_user["id"])
    return {"status": "success", "deleted": deleted}


@router.delete("/{report_id}")
def delete_history_endpoint(report_id: str, current_user: CurrentUser):
    if not delete_report(report_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="History not found")
    return {"status": "success", "deleted_id": report_id}
