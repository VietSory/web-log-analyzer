from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from routers import history, servers


def test_history_detail_hides_unowned_or_missing_reports(monkeypatch):
    monkeypatch.setattr(history, "get_report", lambda _report_id, _owner_id: None)

    with pytest.raises(HTTPException) as exc_info:
        history.get_history_detail("h1", {"id": "current-user"})

    assert exc_info.value.status_code == 404


def test_history_detail_returns_owner_scoped_report(monkeypatch):
    report = {"id": "h1", "owner_id": "current-user"}
    monkeypatch.setattr(
        history,
        "get_report",
        lambda report_id, owner_id: report
        if (report_id, owner_id) == ("h1", "current-user")
        else None,
    )

    assert history.get_history_detail("h1", {"id": "current-user"}) is report


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
