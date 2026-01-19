from io import BytesIO
from pathlib import Path
import asyncio
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.upload_storage import (
    UploadTooLargeError,
    UploadValidationError,
    resolve_upload_path,
    save_upload,
)


class FakeUpload:
    def __init__(
        self,
        filename: str | None,
        content: bytes,
        size: int | None = None,
    ):
        self.filename = filename
        self.size = len(content) if size is None else size
        self._stream = BytesIO(content)
        self.closed = False

    async def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    async def close(self) -> None:
        self.closed = True


def test_save_upload_generates_server_controlled_name(tmp_path):
    content = b"127.0.0.1 - - sample\n"
    upload = FakeUpload("access.log", content)

    stored = asyncio.run(save_upload(upload, tmp_path, max_bytes=1024))

    assert stored.original_filename == "access.log"
    assert stored.storage_name.endswith(".log")
    assert stored.storage_name != stored.original_filename
    assert stored.size == len(content)
    assert resolve_upload_path(stored.storage_name, tmp_path).read_bytes() == content
    assert upload.closed is True


def test_rejects_path_traversal_and_unsupported_extensions(tmp_path):
    for filename in (
        "../access.log",
        r"..\access.log",
        ".hidden.log",
        "payload.py",
        "access.log.exe",
    ):
        upload = FakeUpload(filename, b"test")

        try:
            asyncio.run(save_upload(upload, tmp_path, max_bytes=1024))
        except UploadValidationError:
            pass
        else:
            raise AssertionError(f"{filename!r} should have been rejected")


def test_rejects_declared_oversized_upload_without_writing(tmp_path):
    upload = FakeUpload("access.log", b"small", size=2048)

    try:
        asyncio.run(save_upload(upload, tmp_path, max_bytes=1024))
    except UploadTooLargeError:
        pass
    else:
        raise AssertionError("oversized upload should have been rejected")

    assert list(tmp_path.iterdir()) == []


def test_enforces_streaming_size_limit_and_removes_partial_file(tmp_path):
    upload = FakeUpload("access.txt", b"a" * 2048)
    upload.size = None

    try:
        asyncio.run(save_upload(upload, tmp_path, max_bytes=1024))
    except UploadTooLargeError:
        pass
    else:
        raise AssertionError("oversized stream should have been rejected")

    assert list(tmp_path.iterdir()) == []
    assert upload.closed is True


def test_rejects_binary_null_bytes_and_removes_partial_file(tmp_path):
    upload = FakeUpload("access.log", b"valid prefix\n\x00binary")

    try:
        asyncio.run(save_upload(upload, tmp_path, max_bytes=1024))
    except UploadValidationError:
        pass
    else:
        raise AssertionError("binary upload should have been rejected")

    assert list(tmp_path.iterdir()) == []


def test_resolve_upload_path_rejects_user_controlled_names(tmp_path):
    for storage_name in ("../x.log", "x.log", "a" * 32 + ".py"):
        try:
            resolve_upload_path(storage_name, tmp_path)
        except UploadValidationError:
            pass
        else:
            raise AssertionError(f"{storage_name!r} should have been rejected")
