from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Protocol
from uuid import uuid4


ALLOWED_LOG_EXTENSIONS = frozenset({".log", ".txt"})
_STORAGE_NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.(?:log|txt)$")
_CHUNK_SIZE = 64 * 1024


class UploadValidationError(ValueError):
    pass


class InvalidUploadNameError(UploadValidationError):
    pass


class UnsupportedUploadTypeError(UploadValidationError):
    pass


class UploadTooLargeError(UploadValidationError):
    pass


class BinaryUploadError(UploadValidationError):
    pass


class UploadStream(Protocol):
    filename: str | None
    size: int | None

    async def read(self, size: int = -1) -> bytes: ...

    async def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class StoredUpload:
    storage_name: str
    original_filename: str
    size: int


def _validate_original_filename(filename: str | None) -> tuple[str, str]:
    if filename is None:
        raise InvalidUploadNameError("A filename is required")

    name = filename.strip()
    if (
        not name
        or len(name) > 255
        or name in {".", ".."}
        or name.startswith(".")
        or "/" in name
        or "\\" in name
        or "\x00" in name
    ):
        raise InvalidUploadNameError("Invalid upload filename")

    extension = Path(name).suffix.lower()
    if extension not in ALLOWED_LOG_EXTENSIONS:
        raise UnsupportedUploadTypeError("Only .log and .txt files are accepted")

    return name, extension


def resolve_upload_path(storage_name: str, upload_dir: str | Path) -> Path:
    if _STORAGE_NAME_PATTERN.fullmatch(storage_name) is None:
        raise InvalidUploadNameError("Invalid stored upload name")

    root = Path(upload_dir).resolve()
    candidate = (root / storage_name).resolve()
    if candidate.parent != root:
        raise InvalidUploadNameError("Invalid stored upload path")

    return candidate


async def save_upload(
    upload: UploadStream,
    upload_dir: str | Path,
    max_bytes: int,
) -> StoredUpload:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    original_filename, extension = _validate_original_filename(upload.filename)
    if upload.size is not None and upload.size > max_bytes:
        raise UploadTooLargeError("Upload exceeds the configured size limit")

    root = Path(upload_dir)
    root.mkdir(parents=True, exist_ok=True)

    storage_name = f"{uuid4().hex}{extension}"
    target = resolve_upload_path(storage_name, root)
    total_bytes = 0

    try:
        with target.open("xb") as destination:
            while True:
                chunk = await upload.read(_CHUNK_SIZE)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise UploadTooLargeError("Upload exceeds the configured size limit")
                if b"\x00" in chunk:
                    raise BinaryUploadError("Binary content is not accepted")

                destination.write(chunk)

        if os.name == "posix":
            target.chmod(0o600)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return StoredUpload(
        storage_name=storage_name,
        original_filename=original_filename,
        size=total_bytes,
    )
