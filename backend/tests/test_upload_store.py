from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import get_settings
from core.security import hash_password
from core.upload_store import (
    delete_upload_metadata,
    get_upload,
    init_upload_store,
    list_uploads,
    record_upload,
)
import database


@pytest.fixture
def upload_database(tmp_path, monkeypatch):
    database_path = tmp_path / "uploads.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    get_settings.cache_clear()
    database.init_db()
    init_upload_store()
    owner_id = database.create_user(
        "Upload Owner",
        "upload-owner",
        hash_password("a sufficiently long upload password"),
    )
    other_id = database.create_user(
        "Other Owner",
        "other-upload-owner",
        hash_password("another sufficiently long password"),
    )
    assert owner_id is not None
    assert other_id is not None
    yield owner_id, other_id
    get_settings.cache_clear()


def test_upload_metadata_round_trip_is_owner_scoped(upload_database):
    owner_id, other_id = upload_database
    storage_name = "a" * 32 + ".log"

    record = record_upload(
        owner_id=owner_id,
        storage_name=storage_name,
        original_filename="access.log",
        size=123,
    )

    assert record["storage_name"] == storage_name
    assert record["original_filename"] == "access.log"
    assert get_upload(storage_name, owner_id) == record
    assert get_upload(storage_name, other_id) is None
    assert list_uploads(owner_id) == [record]
    assert list_uploads(other_id) == []


def test_deleting_upload_metadata_cannot_cross_owner_boundary(upload_database):
    owner_id, other_id = upload_database
    storage_name = "b" * 32 + ".txt"
    record_upload(
        owner_id=owner_id,
        storage_name=storage_name,
        original_filename="access.txt",
        size=10,
    )

    assert delete_upload_metadata(storage_name, other_id) is False
    assert get_upload(storage_name, owner_id) is not None
    assert delete_upload_metadata(storage_name, owner_id) is True
    assert get_upload(storage_name, owner_id) is None


def test_upload_metadata_rejects_invalid_size(upload_database):
    owner_id, _ = upload_database

    with pytest.raises(ValueError, match="size must be non-negative"):
        record_upload(
            owner_id=owner_id,
            storage_name="c" * 32 + ".log",
            original_filename="access.log",
            size=-1,
        )


def test_upload_store_initialization_is_idempotent(upload_database):
    init_upload_store()
    init_upload_store()
