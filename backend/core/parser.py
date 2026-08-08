from __future__ import annotations

from dataclasses import asdict, dataclass
from ipaddress import ip_address
from pathlib import Path
import re

import pandas as pd


LOG_COLUMNS = [
    "ip",
    "datetime",
    "method",
    "path",
    "protocol",
    "status",
    "size",
    "referrer",
    "user_agent",
    "source_format",
]

_PREFIX = (
    r"^(?P<ip>\S+)\s+"
    r"(?P<ident>\S+)\s+"
    r"(?P<user>\S+)\s+"
    r"\[(?P<timestamp>[^\]]+)\]\s+"
    r'"(?P<request>(?:\\.|[^"])*)"\s+'
    r"(?P<status>\d{3})\s+"
    r"(?P<size>\d+|-)"
)

_COMBINED_PATTERN = re.compile(
    _PREFIX
    + r'\s+"(?P<referrer>(?:\\.|[^"])*)"\s+"(?P<user_agent>(?:\\.|[^"])*)"\s*$'
)
_COMMON_PATTERN = re.compile(_PREFIX + r"\s*$")


@dataclass(frozen=True, slots=True)
class LogEvent:
    ip: str
    datetime: pd.Timestamp
    method: str
    path: str
    protocol: str
    status: int
    size: int
    referrer: str
    user_agent: str
    source_format: str


def _unescape_log_value(value: str) -> str:
    return value.replace(r'\"', '"').replace(r"\\", "\")


def _split_request(request: str) -> tuple[str, str, str]:
    if not request or request == "-":
        return "unknown", "unknown", ""

    parts = request.split(maxsplit=2)
    if len(parts) == 1:
        return parts[0], "unknown", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""

    return parts[0], parts[1], parts[2]


def parse_log_line(line: str) -> LogEvent | None:
    """Parse an Apache/Nginx common or combined access-log line."""
    stripped = line.strip()
    if not stripped:
        return None

    match = _COMBINED_PATTERN.fullmatch(stripped)
    source_format = "combined"

    if match is None:
        match = _COMMON_PATTERN.fullmatch(stripped)
        source_format = "common"

    if match is None:
        return None

    values = match.groupdict()

    try:
        parsed_ip = str(ip_address(values["ip"]))
        timestamp = pd.to_datetime(
            values["timestamp"],
            format="%d/%b/%Y:%H:%M:%S %z",
            errors="raise",
        )
        status = int(values["status"])
        size = 0 if values["size"] == "-" else int(values["size"])
    except (TypeError, ValueError):
        return None

    method, path, protocol = _split_request(_unescape_log_value(values["request"]))

    return LogEvent(
        ip=parsed_ip,
        datetime=timestamp,
        method=method,
        path=path,
        protocol=protocol,
        status=status,
        size=size,
        referrer=_unescape_log_value(values.get("referrer") or "-"),
        user_agent=_unescape_log_value(values.get("user_agent") or "-"),
        source_format=source_format,
    )


def parse_log_file(filepath: str | Path) -> pd.DataFrame:
    """Parse a log file while skipping malformed individual lines."""
    records: list[dict[str, object]] = []

    with Path(filepath).open("r", encoding="utf-8", errors="replace") as log_file:
        for line in log_file:
            event = parse_log_line(line)
            if event is not None:
                records.append(asdict(event))

    if not records:
        return pd.DataFrame(columns=LOG_COLUMNS)

    return pd.DataFrame.from_records(records, columns=LOG_COLUMNS)
