from __future__ import annotations

from pydantic import BaseModel, Field


class UploadRecord(BaseModel):
    storage_name: str = Field(pattern=r"^[0-9a-f]{32}\.(?:log|txt)$")
    original_filename: str = Field(min_length=1, max_length=255)
    size: int = Field(ge=0)
    created_at: str


class UploadResponse(UploadRecord):
    status: str = "success"
    filename: str


class UploadDeleteResponse(BaseModel):
    status: str = "success"
    filename: str
