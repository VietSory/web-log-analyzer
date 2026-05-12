from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database import get_db_connection


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_upload_store() -> None:
    connection = get_db_connection()
    try:
        with connection:
            connection.executescript(
                '''
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    storage_name TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    size INTEGER NOT NULL CHECK(size >= 0),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_uploaded_files_owner_created
                    ON uploaded_files(owner_id, created_at DESC);
                '''
            )
    finally:
        connection.close()


def record_upload(
    *,
    owner_id: str,
    storage_name: str,
    original_filename: str,
    size: int,
) -> dict[str, Any]:
    if not owner_id:
        raise ValueError("owner_id is required")
    if not original_filename:
        raise ValueError("original_filename is required")
    if size < 0:
        raise ValueError("size must be non-negative")

    created_at = _utc_now()
    connection = get_db_connection()
    try:
        with connection:
            connection.execute(
                '''
                INSERT INTO uploaded_files (
                    storage_name, owner_id, original_filename, size, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ''',
                (storage_name, owner_id, original_filename, size, created_at),
            )
    finally:
        connection.close()

    return {
        "storage_name": storage_name,
        "original_filename": original_filename,
        "size": size,
        "created_at": created_at,
    }


def list_uploads(owner_id: str) -> list[dict[str, Any]]:
    connection = get_db_connection()
    try:
        rows = connection.execute(
            '''
            SELECT storage_name, original_filename, size, created_at
            FROM uploaded_files
            WHERE owner_id = ?
            ORDER BY created_at DESC, storage_name DESC
            ''',
            (owner_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_upload(storage_name: str, owner_id: str) -> dict[str, Any] | None:
    connection = get_db_connection()
    try:
        row = connection.execute(
            '''
            SELECT storage_name, original_filename, size, created_at
            FROM uploaded_files
            WHERE storage_name = ? AND owner_id = ?
            ''',
            (storage_name, owner_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def delete_upload_metadata(storage_name: str, owner_id: str) -> bool:
    connection = get_db_connection()
    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM uploaded_files WHERE storage_name = ? AND owner_id = ?",
                (storage_name, owner_id),
            )
        return cursor.rowcount > 0
    finally:
        connection.close()
