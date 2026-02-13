from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder, StandardScaler


ARTIFACT_SCHEMA_VERSION = 1
CATEGORICAL_FEATURES = (
    "ip",
    "method",
    "path",
    "protocol",
    "referrer",
    "user_agent",
    "source_format",
)
NUMERIC_FEATURES = (
    "status",
    "size",
    "utc_hour",
    "utc_day_of_week",
)
MODEL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def prepare_model_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize parsed log rows into the stable feature schema used by ML."""
    if dataframe.empty:
        return pd.DataFrame(columns=MODEL_FEATURES)

    frame = dataframe.copy()
    timestamps = pd.to_datetime(frame.get("datetime"), errors="coerce", utc=True)
    if timestamps.isna().any():
        raise ValueError("ML input contains invalid timestamps")

    frame["utc_hour"] = timestamps.dt.hour.astype("int16")
    frame["utc_day_of_week"] = timestamps.dt.dayofweek.astype("int16")

    for column in CATEGORICAL_FEATURES:
        if column not in frame.columns:
            frame[column] = "unknown"
        frame[column] = frame[column].fillna("unknown").astype(str)

    for column, default in (("status", 200), ("size", 0)):
        if column not in frame.columns:
            frame[column] = default
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.isna().any():
            raise ValueError(f"ML input contains invalid numeric values in {column}")
        frame[column] = numeric.astype("float32")

    return frame.loc[:, MODEL_FEATURES]


def build_preprocessor() -> ColumnTransformer:
    """Create a training-only fitted transformer with explicit unseen-category behavior."""
    categorical = OrdinalEncoder(
        handle_unknown="use_encoded_value",
        unknown_value=-1,
        encoded_missing_value=-1,
        dtype="float32",
    )
    numeric = StandardScaler()
    return ColumnTransformer(
        transformers=[
            ("categorical", categorical, list(CATEGORICAL_FEATURES)),
            ("numeric", numeric, list(NUMERIC_FEATURES)),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def temporal_split(
    dataframe: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
    min_rows: int = 30,
) -> TemporalSplit:
    """Split chronologically so future rows never influence preprocessing or training."""
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
