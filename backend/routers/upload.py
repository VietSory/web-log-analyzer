from __future__ import annotations

from contextlib import asynccontextmanager
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from config import get_settings
from core.auth import get_current_user
from core.upload_storage import (
    BinaryUploadError,
    InvalidUploadNameError,
    InvalidUploadOwnerError,
    UnsupportedUploadTypeError,
    UploadTooLargeError,
    resolve_upload_path,
    save_upload,
)
from core.upload_store import (
    delete_upload_metadata,
    get_upload,
    init_upload_store,
    list_uploads,
    record_upload,
)
from schemas.uploads import UploadDeleteResponse, UploadRecord, UploadResponse


settings = get_settings()
CurrentUser = Annotated[dict, Depends(get_current_user)]


@asynccontextmanager
async def upload_lifespan(_: object):
    init_upload_store()
    yield


router = APIRouter(lifespan=upload_lifespan)


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> UploadResponse:
    try:
        stored = await save_upload(
            file,
            upload_dir=settings.upload_dir,
            max_bytes=settings.upload_max_bytes,
            owner_id=current_user["id"],
        )
    except (InvalidUploadNameError, InvalidUploadOwnerError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (UnsupportedUploadTypeError, BinaryUploadError) as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not persist upload") from exc

    try:
        metadata = record_upload(
            owner_id=current_user["id"],
            storage_name=stored.storage_name,
            original_filename=stored.original_filename,
            size=stored.size,
        )
    except sqlite3.Error as exc:
        try:
            resolve_upload_path(
                stored.storage_name,
                settings.upload_dir,
                current_user["id"],
            ).unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="Could not record upload") from exc

    return UploadResponse(
        status="success",
        filename=stored.storage_name,
        **metadata,
    )


@router.get("/uploads", response_model=list[UploadRecord])
def get_uploads(current_user: CurrentUser) -> list[dict[str, object]]:
    return list_uploads(current_user["id"])


@router.delete("/uploads/{storage_name}", response_model=UploadDeleteResponse)
def delete_upload(storage_name: str, current_user: CurrentUser) -> UploadDeleteResponse:
    metadata = get_upload(storage_name, current_user["id"])
    if metadata is None:
        raise HTTPException(status_code=404, detail="Upload not found")

    try:
        file_path = resolve_upload_path(
            storage_name,
            settings.upload_dir,
            current_user["id"],
        )
        file_path.unlink(missing_ok=True)
    except (InvalidUploadNameError, InvalidUploadOwnerError) as exc:
        raise HTTPException(status_code=404, detail="Upload not found") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not delete upload") from exc

    if not delete_upload_metadata(storage_name, current_user["id"]):
        raise HTTPException(status_code=404, detail="Upload not found")

    return UploadDeleteResponse(filename=storage_name)
