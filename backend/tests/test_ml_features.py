from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.ml_features import (
    ARTIFACT_SCHEMA_VERSION,
    MODEL_FEATURES,
    build_preprocessor,
    prepare_model_frame,
    temporal_split,
)


def _rows(count: int) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01", periods=count, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "ip": [f"192.0.2.{index % 10 + 1}" for index in range(count)],
            "method": ["GET"] * count,
            "path": [f"/item/{index % 5}?page={index % 3}" for index in range(count)],
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
    invalid["datetime"] = invalid["datetime"].astype(object)
    invalid.loc[0, "datetime"] = "not-a-timestamp"
    with pytest.raises(ValueError, match="valid timestamps"):
        temporal_split(invalid)


def test_model_frame_uses_stable_behavioral_features_not_identifier_ordinals():
    frame = _rows(2)
    frame.loc[0, "method"] = "BREW"
    frame.loc[0, "ip"] = "2001:db8::1"
    frame.loc[0, "path"] = "/never-seen-before?token=abc"

    prepared = prepare_model_frame(frame)

    assert ARTIFACT_SCHEMA_VERSION == 2
    assert tuple(prepared.columns) == MODEL_FEATURES
    assert prepared.shape == (2, len(MODEL_FEATURES))
    assert prepared.loc[0, "method_other"] == 1.0
    assert "ip" not in prepared.columns
    assert "path" not in prepared.columns
    assert "referrer" not in prepared.columns
    assert np.isfinite(prepared.to_numpy()).all()


def test_preprocessor_is_fitted_only_on_training_feature_frame():
    split = temporal_split(_rows(40))
    train_features = prepare_model_frame(split.train)
    validation_features = prepare_model_frame(split.validation)

    preprocessor = build_preprocessor()
    transformed_train = preprocessor.fit_transform(train_features)
    transformed_validation = preprocessor.transform(validation_features)

    assert transformed_train.shape[1] == len(MODEL_FEATURES)
    assert transformed_validation.shape[1] == len(MODEL_FEATURES)
    assert np.isfinite(transformed_train).all()
    assert np.isfinite(transformed_validation).all()


def test_invalid_status_and_negative_size_fail_closed():
    invalid_status = _rows(1)
    invalid_status.loc[0, "status"] = 999
    with pytest.raises(ValueError, match="out-of-range"):
        prepare_model_frame(invalid_status)

    invalid_size = _rows(1)
    invalid_size.loc[0, "size"] = -1
    with pytest.raises(ValueError, match="response sizes"):
        prepare_model_frame(invalid_size)
