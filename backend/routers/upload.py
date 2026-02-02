from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from config import get_settings
from core.auth import get_current_user
from core.upload_storage import (
    BinaryUploadError,
    InvalidUploadNameError,
    UnsupportedUploadTypeError,
    UploadTooLargeError,
    save_upload,
)


router = APIRouter()
settings = get_settings()
CurrentUser = Annotated[dict, Depends(get_current_user)]


@router.post("/upload")
async def upload_file(
    _current_user: CurrentUser,
    file: UploadFile = File(...),
):
    try:
        stored = await save_upload(
            file,
            upload_dir=settings.upload_dir,
            max_bytes=settings.upload_max_bytes,
        )
    except InvalidUploadNameError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except (UnsupportedUploadTypeError, BinaryUploadError) as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Could not persist upload") from exc

    return {
        "status": "success",
        "filename": stored.storage_name,
        "original_filename": stored.original_filename,
        "size": stored.size,
    }
