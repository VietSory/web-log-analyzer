import sqlite3
from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import get_settings
from core.security import hash_password, verify_password
import database


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    get_settings.cache_clear()
    database.init_db()
    yield database_path
    get_settings.cache_clear()


def test_init_db_enables_foreign_keys_and_does_not_seed_admin(isolated_database):
    connection = database.get_db_connection(isolated_database)
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        assert "password_hash" in columns
        assert "password" not in columns

        admin = connection.execute(
            "SELECT 1 FROM users WHERE username = 'admin'"
        ).fetchone()
        assert admin is None
    finally:
        connection.close()


def test_legacy_passwords_are_migrated_and_seeded_admin_is_removed(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        '''
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        INSERT INTO users VALUES
            ('legacy-admin', 'Admin User', 'admin', 'admin', '2025-01-01 00:00:00'),
            ('legacy-user', 'Legacy User', 'legacy', 'legacy secret passphrase', '2025-01-01 00:00:00');
        '''
    )
    connection.commit()
    connection.close()

    database.init_db(database_path)

    migrated = database.get_db_connection(database_path)
    try:
        columns = {
            row["name"]
            for row in migrated.execute("PRAGMA table_info(users)").fetchall()
        }
        assert "password_hash" in columns
        assert "password" not in columns

        assert migrated.execute(
            "SELECT 1 FROM users WHERE id = 'legacy-admin'"
        ).fetchone() is None

        user = migrated.execute(
            "SELECT password_hash FROM users WHERE id = 'legacy-user'"
        ).fetchone()
        assert user is not None
        assert user["password_hash"].startswith("$argon2id$")
        assert verify_password("legacy secret passphrase", user["password_hash"])
    finally:
        migrated.close()


def test_existing_argon2_hash_is_preserved_during_migration(tmp_path):
    database_path = tmp_path / "legacy-hashed.db"
    existing_hash = hash_password("already secure passphrase")

    connection = sqlite3.connect(database_path)
    connection.executescript(
        '''
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        '''
    )
    connection.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
        ("user-1", "User One", "user1", existing_hash, "2025-01-01 00:00:00"),
    )
    connection.commit()
    connection.close()

    database.init_db(database_path)

    migrated = database.get_db_connection(database_path)
    try:
        stored = migrated.execute(
            "SELECT password_hash FROM users WHERE id = 'user-1'"
        ).fetchone()["password_hash"]
        assert stored == existing_hash
    finally:
        migrated.close()


def test_crud_uses_configured_database_and_enforces_references(isolated_database):
    password_hash = hash_password("a sufficiently long passphrase")
    user_id = database.create_user("Example User", "example", password_hash)
    assert user_id is not None

    stored_user = database.get_user_by_username("example")
    assert stored_user is not None
    assert stored_user["password_hash"] == password_hash

    server_id = database.create_server(user_id, "web-01", "192.0.2.10")
    assert database.get_server_by_id(server_id)["owner_id"] == user_id

    with pytest.raises(sqlite3.IntegrityError):
        database.create_server("missing-user", "invalid-server")

    log_id = database.create_log(server_id, "safe", "GET / HTTP/1.1")
    assert database.get_log_by_id(log_id)["server_id"] == server_id

    assert database.delete_server(server_id)
    assert database.get_log_by_id(log_id) is None


def test_duplicate_username_returns_none(isolated_database):
    password_hash = hash_password("a sufficiently long passphrase")
    assert database.create_user("First User", "duplicate", password_hash)
    assert database.create_user("Second User", "duplicate", password_hash) is None


def test_legacy_integer_scan_tables_are_rebuilt_without_losing_records(tmp_path):
    database_path = tmp_path / "legacy-scan.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        INSERT INTO users VALUES (
            'owner-1',
            'Owner One',
            'owner1',
            'legacy owner passphrase',
            '2025-01-01 00:00:00'
        );

        CREATE TABLE scan_history (
            id INTEGER PRIMARY KEY,
            owner_id TEXT,
            filename TEXT NOT NULL,
            scan_date TEXT,
            total_requests INTEGER,
            unique_ips INTEGER,
            error_rate REAL,
            traffic_data TEXT,
            status_data TEXT
        );
        INSERT INTO scan_history VALUES (
            7,
            'owner-1',
            'access.log',
            '2025-12-01 10:00:00',
            12,
            3,
            8.5,
            '{"10:00": 12}',
            '{"200": 11, "500": 1}'
        );

        CREATE TABLE scan_threats (
            history_id INTEGER,
            ip TEXT,
            time TEXT,
            details TEXT,
            reconstruction_error REAL
        );
        INSERT INTO scan_threats VALUES (
            7,
            '192.0.2.10',
            '2025-12-01 10:00:00',
            'legacy threat',
            0.42
        );
        """
    )
    connection.commit()
    connection.close()

    database.init_db(database_path)

    migrated = database.get_db_connection(database_path)
    try:
        history = migrated.execute("SELECT * FROM scan_history").fetchall()
        threats = migrated.execute("SELECT * FROM scan_threats").fetchall()

        assert len(history) == 1
        assert history[0]["owner_id"] == "owner-1"
        assert history[0]["filename"] == "access.log"
        assert history[0]["total_requests"] == 12

        assert len(threats) == 1
        assert threats[0]["history_id"] == history[0]["id"]
        assert threats[0]["severity"] == "unknown"
        assert threats[0]["details"] == "legacy threat"

        history_schema = {
            row["name"]: row["type"]
            for row in migrated.execute("PRAGMA table_info(scan_history)").fetchall()
        }
        threat_schema = {
            row["name"]: row["type"]
            for row in migrated.execute("PRAGMA table_info(scan_threats)").fetchall()
        }
        assert history_schema["id"].upper() == "TEXT"
        assert threat_schema["id"].upper() == "TEXT"
        assert threat_schema["history_id"].upper() == "TEXT"
    finally:
        migrated.close()
