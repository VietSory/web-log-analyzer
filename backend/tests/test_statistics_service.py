from pathlib import Path
import sys

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.statistics import compute_log_stats, serialize_log_records


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ip": "192.0.2.1",
                "datetime": pd.Timestamp("2026-02-01T12:05:00Z"),
                "method": "GET",
                "path": "/",
                "protocol": "HTTP/1.1",
                "status": 200,
                "size": 1024,
                "referrer": "-",
                "user_agent": "pytest",
                "source_format": "combined",
            },
            {
                "ip": "192.0.2.2",
                "datetime": pd.Timestamp("2026-02-01T12:35:00Z"),
                "method": "GET",
                "path": "/error",
                "protocol": "HTTP/1.1",
                "status": 503,
                "size": 2048,
                "referrer": "-",
                "user_agent": "pytest",
                "source_format": "combined",
            },
            {
                "ip": "192.0.2.1",
                "datetime": pd.Timestamp("2026-02-01T13:00:00Z"),
                "method": "POST",
                "path": "/submit",
                "protocol": "HTTP/1.1",
                "status": 201,
                "size": 0,
                "referrer": "-",
                "user_agent": "pytest",
                "source_format": "combined",
            },
        ]
    )


def test_compute_log_stats_returns_stable_zero_summary_for_empty_data():
    stats = compute_log_stats(pd.DataFrame())

    assert stats.total_requests == 0
    assert stats.unique_ips == 0
    assert stats.avg_body_size == 0.0
    assert stats.error_rate == 0.0
    assert stats.status_distribution == {}
    assert stats.traffic_chart == {}


def test_compute_log_stats_uses_5xx_error_rate_and_hourly_buckets():
    stats = compute_log_stats(_frame())

    assert stats.total_requests == 3
    assert stats.unique_ips == 2
    assert stats.avg_body_size == 1.0
    assert stats.error_rate == 33.33
    assert stats.status_distribution == {"200": 1, "503": 1, "201": 1}
    assert stats.traffic_chart == {
        "2026-02-01 12:00": 2,
        "2026-02-01 13:00": 1,
    }


def test_serialize_log_records_is_bounded_and_converts_timestamps_to_strings():
    rows = serialize_log_records(_frame(), limit=2)

    assert len(rows) == 2
    assert rows[0]["datetime"].startswith("2026-02-01 12:05:00")
    assert rows[1]["status"] == 503


def test_serialize_log_records_rejects_invalid_limit():
    with pytest.raises(ValueError, match="limit must be positive"):
        serialize_log_records(_frame(), limit=0)
