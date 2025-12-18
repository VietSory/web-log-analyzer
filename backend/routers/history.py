from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import clear_all_data, save_manual_report, get_all_history, get_scan_details, delete_scan_history

router = APIRouter()

class SavePayload(BaseModel):
    filename: str
    stats: Dict[str, Any]
    threats: List[Dict[str, Any]]

@router.get("/")
def get_history_list():
    try:
        return get_all_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{history_id}")
def get_history_detail(history_id: int):
    try:
        details = get_scan_details(history_id)
        if not details:
            raise HTTPException(status_code=404, detail="History not found")
        return details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save")
def save_history(payload: SavePayload):
    try:
        history_id = save_manual_report(payload.filename, payload.stats, payload.threats)
        return {"status": "success", "history_id": history_id, "id": history_id}
    except Exception as e:
        print(f"Error saving history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/clear-all")
def clear_all_endpoint():
    success = clear_all_data()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear data")
    return {"status": "success", "message": "All data cleared and IDs reset"}

@router.delete("/{history_id}")
def delete_history_endpoint(history_id: int):
    success = delete_scan_history(history_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete record")
    return {"status": "success", "deleted_id": history_id}
