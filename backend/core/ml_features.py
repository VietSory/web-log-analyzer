from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


ARTIFACT_SCHEMA_VERSION = 2
_METHOD_BUCKETS = (
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "HEAD",
    "OPTIONS",
    "OTHER",
)
MODEL_FEATURES = (
    "utc_hour_sin",
    "utc_hour_cos",
    "utc_weekday_sin",
    "utc_weekday_cos",
    *tuple(f"method_{method.lower()}" for method in _METHOD_BUCKETS),
    "status_code",
    "is_client_error",
    "is_server_error",
    "size_log1p",
    "path_length",
    "query_length",
    "user_agent_length",
)


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def _method_bucket(value: object) -> str:
    method = str(value or "").upper()
    return method if method in _METHOD_BUCKETS[:-1] else "OTHER"


def prepare_model_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build bounded behavioral features without ordinal identifiers."""
    if dataframe.empty:
        return pd.DataFrame(columns=MODEL_FEATURES, dtype=np.float32)

    frame = pd.DataFrame(index=dataframe.index)
    timestamps = pd.to_datetime(dataframe.get("datetime"), errors="coerce", utc=True)
    if timestamps.isna().any():
        raise ValueError("ML input contains invalid timestamps")

    hours = timestamps.dt.hour.astype(float)
    weekdays = timestamps.dt.dayofweek.astype(float)
    hour_angle = 2.0 * np.pi * hours / 24.0
    weekday_angle = 2.0 * np.pi * weekdays / 7.0
    frame["utc_hour_sin"] = np.sin(hour_angle)
    frame["utc_hour_cos"] = np.cos(hour_angle)
    frame["utc_weekday_sin"] = np.sin(weekday_angle)
    frame["utc_weekday_cos"] = np.cos(weekday_angle)

    if "method" in dataframe.columns:
        methods = dataframe["method"].map(_method_bucket)
    else:
        methods = pd.Series("OTHER", index=dataframe.index)
    for method in _METHOD_BUCKETS:
        frame[f"method_{method.lower()}"] = (methods == method).astype(float)

    if "status" in dataframe.columns:
        status = pd.to_numeric(dataframe["status"], errors="coerce")
    else:
        status = pd.Series(0.0, index=dataframe.index)
    if status.isna().any():
        raise ValueError("ML input contains invalid status values")
    if ((status < 100) | (status > 599)).any():
        raise ValueError("ML input contains out-of-range HTTP status values")
    frame["status_code"] = status.astype(float)
    frame["is_client_error"] = ((status >= 400) & (status < 500)).astype(float)
    frame["is_server_error"] = (status >= 500).astype(float)

    if "size" in dataframe.columns:
        size = pd.to_numeric(dataframe["size"], errors="coerce")
    else:
        size = pd.Series(0.0, index=dataframe.index)
    if size.isna().any() or (size < 0).any():
        raise ValueError("ML input contains invalid response sizes")
    frame["size_log1p"] = np.log1p(size.astype(float))

    if "path" in dataframe.columns:
        paths = dataframe["path"].fillna("").astype(str)
    else:
        paths = pd.Series("", index=dataframe.index)
    frame["path_length"] = paths.str.len().clip(upper=4096).astype(float)
    frame["query_length"] = paths.str.partition("?")[2].str.len().clip(upper=4096).astype(float)

    if "user_agent" in dataframe.columns:
        user_agents = dataframe["user_agent"].fillna("").astype(str)
    else:
        user_agents = pd.Series("", index=dataframe.index)
    frame["user_agent_length"] = user_agents.str.len().clip(upper=4096).astype(float)

    return frame.loc[:, MODEL_FEATURES].astype(np.float32)


def build_preprocessor() -> StandardScaler:
    """Return a scaler that must be fitted on training rows only."""
    return StandardScaler()


def temporal_split(
    dataframe: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
    min_rows: int = 30,
) -> TemporalSplit:
    """Split chronologically so future rows never influence model fitting."""
    if len(dataframe) < min_rows:
        raise ValueError(f"At least {min_rows} parsed rows are required for training")
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1")
    if not 0 < validation_fraction < 1:
        raise ValueError("validation_fraction must be between 0 and 1")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must leave a non-empty test split")

    timestamps = pd.to_datetime(dataframe.get("datetime"), errors="coerce", utc=True)
    if timestamps.isna().any():
        raise ValueError("Training rows must contain valid timestamps")

    ordered = dataframe.assign(_ml_timestamp=timestamps).sort_values(
        "_ml_timestamp",
        kind="stable",
    )
    ordered = ordered.drop(columns=["_ml_timestamp"]).reset_index(drop=True)

    train_end = int(len(ordered) * train_fraction)
    validation_end = train_end + int(len(ordered) * validation_fraction)
    if train_end == 0 or validation_end <= train_end or validation_end >= len(ordered):
        raise ValueError("Training split configuration produced an empty partition")

    return TemporalSplit(
        train=ordered.iloc[:train_end].copy(),
        validation=ordered.iloc[train_end:validation_end].copy(),
        test=ordered.iloc[validation_end:].copy(),
    )
