from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from routers import history, servers


def test_history_owner_check_hides_other_users_records(monkeypatch):
    monkeypatch.setattr(
        history,
        "get_scan_details",
        lambda _history_id: {"id": "h1", "owner_id": "other-user"},
    )

    with pytest.raises(HTTPException) as exc_info:
        history._owned_history("h1", {"id": "current-user"})

    assert exc_info.value.status_code == 404


def test_history_owner_check_returns_owned_record(monkeypatch):
    record = {"id": "h1", "owner_id": "current-user"}
    monkeypatch.setattr(history, "get_scan_details", lambda _history_id: record)

    assert history._owned_history("h1", {"id": "current-user"}) is record


def test_server_owner_check_hides_other_users_servers(monkeypatch):
    monkeypatch.setattr(
        servers,
        "get_server_by_id",
        lambda _server_id: {"id": "s1", "owner_id": "other-user"},
    )

    with pytest.raises(HTTPException) as exc_info:
        servers._owned_server("s1", {"id": "current-user"})

    assert exc_info.value.status_code == 404


def test_server_owner_check_returns_owned_server(monkeypatch):
    server = {"id": "s1", "owner_id": "current-user"}
    monkeypatch.setattr(servers, "get_server_by_id", lambda _server_id: server)

    assert servers._owned_server("s1", {"id": "current-user"}) is server
