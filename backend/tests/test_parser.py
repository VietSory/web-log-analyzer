from pathlib import Path
import sys

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.parser import LOG_COLUMNS, parse_log_file, parse_log_line


def test_parse_combined_ipv4_log_line():
    line = (
        '127.0.0.1 - frank [10/Oct/2000:13:55:36 -0700] '
        '"GET /apache_pb.gif HTTP/1.0" 200 2326 '
        '"http://www.example.com/start.html" "Mozilla/4.08 [en]"'
    )

    event = parse_log_line(line)

    assert event is not None
    assert event.ip == "127.0.0.1"
    assert event.method == "GET"
    assert event.path == "/apache_pb.gif"
    assert event.protocol == "HTTP/1.0"
    assert event.status == 200
    assert event.size == 2326
    assert event.referrer == "http://www.example.com/start.html"
    assert event.user_agent == "Mozilla/4.08 [en]"
    assert event.source_format == "combined"
    assert event.datetime == pd.Timestamp("2000-10-10T13:55:36-07:00")


def test_parse_common_log_line_uses_missing_field_sentinels():
    line = (
        '192.0.2.10 - - [12/Feb/2026:06:15:04 +0700] '
        '"POST /login HTTP/1.1" 401 -'
    )

    event = parse_log_line(line)

    assert event is not None
    assert event.size == 0
    assert event.referrer == "-"
    assert event.user_agent == "-"
    assert event.source_format == "common"


def test_parse_combined_ipv6_log_line():
    line = (
        '2001:db8::1 - - [12/Feb/2026:06:15:04 +0700] '
        '"GET /health HTTP/1.1" 200 12 "-" "curl/8.0"'
    )

    event = parse_log_line(line)

    assert event is not None
    assert event.ip == "2001:db8::1"
    assert event.path == "/health"


def test_parse_combined_line_unescapes_quoted_and_backslash_fields():
    line = (
        '192.0.2.20 - - [12/Feb/2026:06:15:04 +0700] '
        '"GET /search?q=hello HTTP/1.1" 200 15 '
        '"https://example.test/\"quoted\"" "client\\agent \"v1\""'
    )

    event = parse_log_line(line)

    assert event is not None
    assert event.referrer == 'https://example.test/"quoted"'
    assert event.user_agent == 'client\\agent "v1"'


def test_rejects_malformed_timestamp_and_invalid_ip():
    malformed_timestamp = (
        '192.0.2.10 - - [not-a-date] "GET / HTTP/1.1" 200 1 "-" "curl"'
    )
    invalid_ip = (
        '999.999.999.999 - - [12/Feb/2026:06:15:04 +0700] '
        '"GET / HTTP/1.1" 200 1 "-" "curl"'
    )

    assert parse_log_line(malformed_timestamp) is None
    assert parse_log_line(invalid_ip) is None


def test_parse_file_skips_invalid_lines_and_preserves_schema(tmp_path):
    log_path = tmp_path / "access.log"
    log_path.write_text(
        "\n".join(
            [
                '127.0.0.1 - - [12/Feb/2026:06:15:04 +0700] '
                '"GET / HTTP/1.1" 200 42 "-" "curl/8.0"',
                "this is not an access log line",
                '2001:db8::5 - - [12/Feb/2026:06:16:04 +0700] '
                '"GET /v1 HTTP/2.0" 404 7',
            ]
        ),
        encoding="utf-8",
    )

    dataframe = parse_log_file(log_path)

    assert list(dataframe.columns) == LOG_COLUMNS
    assert len(dataframe) == 2
    assert dataframe["status"].tolist() == [200, 404]
    assert dataframe["size"].tolist() == [42, 7]


def test_empty_or_unparseable_file_returns_stable_schema(tmp_path):
    log_path = tmp_path / "invalid.log"
    log_path.write_text("garbage\n", encoding="utf-8")

    dataframe = parse_log_file(log_path)

    assert dataframe.empty
    assert list(dataframe.columns) == LOG_COLUMNS
