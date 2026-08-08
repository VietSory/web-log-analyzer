from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.ml_features import build_preprocessor, prepare_model_frame, temporal_split


def _rows(count: int) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=count, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "ip": [f"192.0.2.{index % 10 + 1}" for index in range(count)],
            "method": ["GET"] * count,
            "path": [f"/item/{index % 5}" for index in range(count)],
            "protocol": ["HTTP/1.1"] * count,
            "status": [200] * count,
            "size": list(range(count)),
            "referrer": ["-"] * count,
            "user_agent": ["pytest"] * count,
            "source_format": ["combined"] * count,
        }
    )


def test_temporal_split_preserves_chronological_boundaries():
    shuffled = _rows(40).sample(frac=1.0, random_state=7).reset_index(drop=True)
    split = temporal_split(shuffled)

    train_end = pd.to_datetime(split.train["datetime"], utc=True).max()
    validation_start = pd.to_datetime(split.validation["datetime"], utc=True).min()
    validation_end = pd.to_datetime(split.validation["datetime"], utc=True).max()
    test_start = pd.to_datetime(split.test["datetime"], utc=True).min()

    assert len(split.train) == 28
    assert len(split.validation) == 6
    assert len(split.test) == 6
    assert train_end < validation_start
    assert validation_end < test_start


def test_temporal_split_rejects_small_or_invalid_timestamp_data():
    with pytest.raises(ValueError, match="At least 30"):
        temporal_split(_rows(10))

    invalid = _rows(30)
    invalid.loc[0, "datetime"] = "not-a-timestamp"
    with pytest.raises(ValueError, match="valid timestamps"):
        temporal_split(invalid)


def test_preprocessor_handles_unseen_categories_without_aliasing_known_class():
    train_frame = prepare_model_frame(_rows(30))
    preprocessor = build_preprocessor()
    preprocessor.fit(train_frame)

    unseen = _rows(1)
    unseen.loc[0, "ip"] = "2001:db8::1"
    unseen.loc[0, "path"] = "/never-seen-before"
    transformed = preprocessor.transform(prepare_model_frame(unseen))

    assert transformed.shape == (1, 11)
    assert np.isfinite(transformed).all()
    assert transformed[0, 0] == -1
    assert transformed[0, 2] == -1


def test_prepare_model_frame_converts_timezone_aware_timestamp_to_utc_features():
    frame = _rows(1)
    frame.loc[0, "datetime"] = pd.Timestamp("2026-01-05T23:30:00-05:00")

    prepared = prepare_model_frame(frame)

    assert prepared.loc[0, "utc_hour"] == 4
    assert prepared.loc[0, "utc_day_of_week"] == 1
