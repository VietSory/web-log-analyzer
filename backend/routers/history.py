from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth import get_current_user
from database import (
    delete_scan_history,
    get_all_history,
    get_scan_details,
    save_manual_report,
)


router = APIRouter()
CurrentUser = Annotated[dict, Depends(get_current_user)]


class SavePayload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    stats: dict[str, Any]
    threats: list[dict[str, Any]] = Field(default_factory=list)


def _owned_history(history_id: str, current_user: dict) -> dict:
    details = get_scan_details(history_id)
    if not details or details.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="History not found")
    return details


@router.get("/list")
def get_history_list(current_user: CurrentUser):
    return get_all_history(owner_id=current_user["id"])


@router.get("/detail/{history_id}")
def get_history_detail(history_id: str, current_user: CurrentUser):
    return _owned_history(history_id, current_user)


@router.post("/save", status_code=status.HTTP_201_CREATED)
def save_history(payload: SavePayload, current_user: CurrentUser):
    try:
        history_id = save_manual_report(
            payload.filename,
            payload.stats,
            payload.threats,
            current_user["id"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid report payload") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Could not save report") from exc

    return {"status": "success", "history_id": history_id, "id": history_id}


@router.delete("/clear-all")
def clear_history(current_user: CurrentUser):
    records = get_all_history(owner_id=current_user["id"])
    deleted = 0
    for record in records:
        if delete_scan_history(record["id"]):
            deleted += 1

    return {"status": "success", "deleted": deleted}


@router.delete("/{history_id}")
def delete_history_endpoint(history_id: str, current_user: CurrentUser):
    _owned_history(history_id, current_user)
    if not delete_scan_history(history_id):
        raise HTTPException(status_code=404, detail="History not found")
    return {"status": "success", "deleted_id": history_id}
