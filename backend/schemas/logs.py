from __future__ import annotations

from pydantic import BaseModel, Field


class LogStats(BaseModel):
    total_requests: int = Field(ge=0)
    unique_ips: int = Field(ge=0)
    avg_body_size: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=100)
    status_distribution: dict[str, int]
    traffic_chart: dict[str, int]


class LogRecord(BaseModel):
    ip: str
    datetime: str
    method: str
    path: str
    protocol: str
    status: int = Field(ge=100, le=599)
    size: int = Field(ge=0)
    referrer: str
    user_agent: str
    source_format: str
