from __future__ import annotations

import pandas as pd

from schemas.logs import LogStats


def compute_log_stats(dataframe: pd.DataFrame) -> LogStats:
    """Compute dashboard statistics from normalized log rows."""
    if dataframe.empty:
        return LogStats(
            total_requests=0,
            unique_ips=0,
            avg_body_size=0.0,
            error_rate=0.0,
            status_distribution={},
            traffic_chart={},
        )

    total_requests = len(dataframe)
    unique_ips = int(dataframe["ip"].nunique())
    avg_size_kib = round(float(dataframe["size"].mean()) / 1024, 2)
    server_errors = int((dataframe["status"] >= 500).sum())
    error_rate = round((server_errors / total_requests) * 100, 2)

    status_counts = dataframe["status"].value_counts().head(5)
    status_distribution = {
        str(int(status_code)): int(count)
        for status_code, count in status_counts.items()
    }

    traffic_chart: dict[str, int] = {}
    timed = dataframe.dropna(subset=["datetime"])
    if not timed.empty:
        traffic = timed.resample("h", on="datetime").size()
        traffic_chart = {
            timestamp.strftime("%Y-%m-%d %H:%M"): int(count)
            for timestamp, count in traffic.items()
            if count > 0
        }

    return LogStats(
        total_requests=total_requests,
        unique_ips=unique_ips,
        avg_body_size=avg_size_kib,
        error_rate=error_rate,
        status_distribution=status_distribution,
        traffic_chart=traffic_chart,
    )


def serialize_log_records(
    dataframe: pd.DataFrame,
    *,
    limit: int = 10_000,
) -> list[dict[str, object]]:
    if limit < 1:
        raise ValueError("limit must be positive")
    if dataframe.empty:
        return []

    response_frame = dataframe.head(limit).copy()
    response_frame["datetime"] = response_frame["datetime"].astype(str)
    return response_frame.to_dict(orient="records")
