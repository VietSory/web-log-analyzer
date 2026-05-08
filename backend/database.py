from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from config import get_settings
from core.security import hash_password


_DB_TIMEOUT_SECONDS = 10.0
_SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _configured_database_path() -> str:
    return get_settings().database_path


def get_db_connection(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = str(database_path) if database_path is not None else _configured_database_path()

    if path != ":memory:":
        expanded_path = Path(path).expanduser()
        expanded_path.parent.mkdir(parents=True, exist_ok=True)
        path = str(expanded_path)

    connection = sqlite3.connect(path, timeout=_DB_TIMEOUT_SECONDS)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def _create_current_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        f'''
        CREATE TABLE IF NOT EXISTS {_SCHEMA_MIGRATIONS_TABLE} (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS servers (
            id TEXT PRIMARY KEY,
            owner_id TEXT NOT NULL,
            name TEXT NOT NULL,
            ipv4 TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS logs (
            id TEXT PRIMARY KEY,
            server_id TEXT NOT NULL,
            status TEXT NOT NULL,
            contents TEXT NOT NULL,
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE
        );
        '''
    )


def _create_legacy_scan_schema(connection: sqlite3.Connection) -> None:
    """Create the normalized legacy scan tables only while migrating old databases."""
    connection.executescript(
        '''
        CREATE TABLE IF NOT EXISTS scan_history (
            id TEXT PRIMARY KEY,
            owner_id TEXT,
            filename TEXT NOT NULL,
            scan_date TEXT NOT NULL,
            total_requests INTEGER NOT NULL,
            unique_ips INTEGER NOT NULL,
            error_rate REAL NOT NULL,
            traffic_data TEXT NOT NULL,
            status_data TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scan_threats (
            id TEXT PRIMARY KEY,
            history_id TEXT NOT NULL,
            ip TEXT,
            severity TEXT NOT NULL,
            time TEXT,
            details TEXT,
            reconstruction_error REAL,
            FOREIGN KEY(history_id) REFERENCES scan_history(id) ON DELETE CASCADE
        );
        '''
    )


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def _migration_applied(connection: sqlite3.Connection, version: int) -> bool:
    row = connection.execute(
        f"SELECT 1 FROM {_SCHEMA_MIGRATIONS_TABLE} WHERE version = ?",
        (version,),
    ).fetchone()
    return row is not None


def _record_migration(connection: sqlite3.Connection, version: int) -> None:
    connection.execute(
        f"INSERT INTO {_SCHEMA_MIGRATIONS_TABLE} (version, applied_at) VALUES (?, ?)",
        (version, _utc_now()),
    )


def _migrate_legacy_password_storage(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }

    if "password" in columns and "password_hash" not in columns:
        connection.execute("ALTER TABLE users RENAME COLUMN password TO password_hash")
        columns.remove("password")
        columns.add("password_hash")

    if "password_hash" not in columns:
        raise RuntimeError("users table does not contain a password hash column")

    rows = connection.execute(
        "SELECT id, fullname, username, password_hash FROM users"
    ).fetchall()

    for row in rows:
        stored_value = row["password_hash"]
        if (
            row["username"] == "admin"
            and row["fullname"] == "Admin User"
            and stored_value == "admin"
        ):
            connection.execute("DELETE FROM users WHERE id = ?", (row["id"],))
            continue

        if not stored_value.startswith("$argon2id$"):
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(stored_value), row["id"]),
            )


def _table_rows(connection: sqlite3.Connection, table_name: str) -> list[dict]:
    return [
        dict(row)
        for row in connection.execute(f"SELECT * FROM {table_name}").fetchall()
    ]


def _needs_scan_table_rebuild(connection: sqlite3.Connection) -> bool:
    if not _table_exists(connection, "scan_history"):
        return False
    if not _table_exists(connection, "scan_threats"):
        return False

    history_columns = {
        row["name"]: (row["type"] or "").upper()
        for row in connection.execute("PRAGMA table_info(scan_history)").fetchall()
    }
    threat_columns = {
        row["name"]: (row["type"] or "").upper()
        for row in connection.execute("PRAGMA table_info(scan_threats)").fetchall()
    }

    required_history = {
        "id",
        "owner_id",
        "filename",
        "scan_date",
        "total_requests",
        "unique_ips",
        "error_rate",
        "traffic_data",
        "status_data",
    }
    required_threats = {
        "id",
        "history_id",
        "ip",
        "severity",
        "time",
        "details",
        "reconstruction_error",
    }

    return (
        not required_history.issubset(history_columns)
        or not required_threats.issubset(threat_columns)
        or history_columns.get("id") != "TEXT"
        or threat_columns.get("id") != "TEXT"
        or threat_columns.get("history_id") != "TEXT"
    )


def _migrate_legacy_scan_tables(connection: sqlite3.Connection) -> None:
    if not _needs_scan_table_rebuild(connection):
        return

    old_history = _table_rows(connection, "scan_history")
    old_threats = _table_rows(connection, "scan_threats")
    valid_owner_ids = {
        row["id"]
        for row in connection.execute("SELECT id FROM users").fetchall()
    }

    connection.execute("DROP TABLE scan_threats")
    connection.execute("DROP TABLE scan_history")
    _create_legacy_scan_schema(connection)

    history_id_map: dict[object, str] = {}
    for row in old_history:
        new_id = generate_uuid()
        history_id_map[row.get("id")] = new_id

        owner_id = row.get("owner_id")
        if owner_id not in valid_owner_ids:
            owner_id = None

        connection.execute(
            """
            INSERT INTO scan_history (
                id,
                owner_id,
                filename,
                scan_date,
                total_requests,
                unique_ips,
                error_rate,
                traffic_data,
                status_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                owner_id,
                str(row.get("filename") or "legacy.log"),
                str(row.get("scan_date") or _utc_now()),
                int(row.get("total_requests") or 0),
                int(row.get("unique_ips") or 0),
                float(row.get("error_rate") or 0.0),
                str(row.get("traffic_data") or "{}"),
                str(row.get("status_data") or "{}"),
            ),
        )

    for row in old_threats:
        new_history_id = history_id_map.get(row.get("history_id"))
        if new_history_id is None:
            continue

        connection.execute(
            """
            INSERT INTO scan_threats (
                id,
                history_id,
                ip,
                severity,
                time,
                details,
                reconstruction_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generate_uuid(),
                new_history_id,
                row.get("ip"),
                str(row.get("severity") or "unknown"),
                row.get("time"),
                row.get("details"),
                row.get("reconstruction_error"),
            ),
        )


def _create_indexes(connection: sqlite3.Connection) -> None:
    connection.executescript(
        '''
        CREATE INDEX IF NOT EXISTS idx_servers_owner_id
            ON servers(owner_id);
        CREATE INDEX IF NOT EXISTS idx_logs_server_id
            ON logs(server_id);
        '''
    )


def init_db(database_path: str | Path | None = None) -> None:
    connection = get_db_connection(database_path)
    try:
        effective_path = str(database_path) if database_path is not None else _configured_database_path()
        if effective_path != ":memory:":
            journal_mode = connection.execute("PRAGMA journal_mode = WAL").fetchone()[0]
            if str(journal_mode).lower() != "wal":
                raise RuntimeError("SQLite WAL mode could not be enabled")

        with connection:
            _create_current_schema(connection)

            if not _migration_applied(connection, 1):
                _migrate_legacy_password_storage(connection)
                _record_migration(connection, 1)

            if not _migration_applied(connection, 2):
                _migrate_legacy_scan_tables(connection)
                _record_migration(connection, 2)

            if not _migration_applied(connection, 3):
                _create_indexes(connection)
                _record_migration(connection, 3)
    finally:
        connection.close()


def generate_uuid() -> str:
    return str(uuid4())


def create_user(fullname, username, password_hash):
    connection = get_db_connection()
    user_id = generate_uuid()
    try:
        with connection:
            connection.execute(
                '''
                INSERT INTO users (id, fullname, username, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (user_id, fullname, username, password_hash, _utc_now()),
            )
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        connection.close()


def get_user_by_username(username):
    connection = get_db_connection()
    try:
        user = connection.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return dict(user) if user else None
    finally:
        connection.close()


def get_user_by_id(user_id):
    connection = get_db_connection()
    try:
        user = connection.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(user) if user else None
    finally:
        connection.close()


def set_user_password_hash(username, password_hash):
    connection = get_db_connection()
    try:
        with connection:
            cursor = connection.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (password_hash, username),
            )
        return cursor.rowcount > 0
    finally:
        connection.close()


def create_server(owner_id, name, ipv4=None):
    connection = get_db_connection()
    server_id = generate_uuid()
    try:
        with connection:
            connection.execute(
                '''
                INSERT INTO servers (id, owner_id, name, ipv4)
                VALUES (?, ?, ?, ?)
                ''',
                (server_id, owner_id, name, ipv4),
            )
        return server_id
    finally:
        connection.close()


def get_user_servers(owner_id):
    connection = get_db_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM servers WHERE owner_id = ? ORDER BY name, id",
            (owner_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_server_by_id(server_id):
    connection = get_db_connection()
    try:
        row = connection.execute(
            "SELECT * FROM servers WHERE id = ?",
            (server_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def delete_server(server_id):
    connection = get_db_connection()
    try:
        with connection:
            connection.execute("DELETE FROM logs WHERE server_id = ?", (server_id,))
            cursor = connection.execute(
                "DELETE FROM servers WHERE id = ?",
                (server_id,),
            )
        return cursor.rowcount > 0
    finally:
        connection.close()


def create_log(server_id, status, contents):
    connection = get_db_connection()
    log_id = generate_uuid()
    try:
        with connection:
            connection.execute(
                '''
                INSERT INTO logs (id, server_id, status, contents)
                VALUES (?, ?, ?, ?)
                ''',
                (log_id, server_id, status, contents),
            )
        return log_id
    finally:
        connection.close()


def get_server_logs(server_id):
    connection = get_db_connection()
    try:
        rows = connection.execute(
            "SELECT * FROM logs WHERE server_id = ? ORDER BY rowid DESC",
            (server_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_log_by_id(log_id):
    connection = get_db_connection()
    try:
        row = connection.execute(
            "SELECT * FROM logs WHERE id = ?",
            (log_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        connection.close()


def delete_log(log_id):
    connection = get_db_connection()
    try:
        with connection:
            cursor = connection.execute(
                "DELETE FROM logs WHERE id = ?",
                (log_id,),
            )
        return cursor.rowcount > 0
    finally:
        connection.close()
