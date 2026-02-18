from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.ml_engine import InferenceError, LogAnomalyDetector, ModelArtifactError
from core.ml_features import MODEL_FEATURES


class _FakePreprocessor:
    def transform(self, frame):
        return np.ones((len(frame), len(MODEL_FEATURES)), dtype=np.float32)


class _ZeroModel:
    def predict(self, values, verbose=0):
        return np.zeros_like(values)


class _WrongShapeModel:
    def predict(self, values, verbose=0):
        return np.zeros((len(values), 1), dtype=np.float32)


def _input_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "datetime": ["2026-01-02T03:04:05Z"],
            "ip": ["2001:db8::1"],
            "method": ["GET"],
            "path": ["/admin"],
            "protocol": ["HTTP/1.1"],
            "status": [401],
            "size": [512],
            "referrer": ["-"],
            "user_agent": ["pytest"],
            "source_format": ["combined"],
        }
    )


def _ready_detector(model) -> LogAnomalyDetector:
    detector = LogAnomalyDetector("unused")
    detector.model = model
    detector.preprocessor = _FakePreprocessor()
    detector.threshold = 0.5
    detector.metadata = {"artifact_schema_version": 2}
    return detector


def test_inference_requires_loaded_artifact_bundle():
    detector = LogAnomalyDetector("missing")
    with pytest.raises(ModelArtifactError, match="not been loaded"):
        detector.detect_anomalies(_input_frame())


def test_detection_exposes_threshold_ratio_and_stable_severity():
    detector = _ready_detector(_ZeroModel())

    threats = detector.detect_anomalies(_input_frame())

    assert len(threats) == 1
    assert threats[0]["severity"] == "high"
    assert threats[0]["reconstruction_error"] == 1.0
    assert threats[0]["threshold"] == 0.5
    assert threats[0]["score_ratio"] == 2.0
    assert threats[0]["ip"] == "2001:db8::1"


def test_inference_rejects_reconstruction_shape_mismatch():
    detector = _ready_detector(_WrongShapeModel())
    with pytest.raises(InferenceError, match="shape"):
        detector.detect_anomalies(_input_frame())


def test_preprocessing_rejects_invalid_timestamp_instead_of_assuming_hour_zero():
    detector = _ready_detector(_ZeroModel())
    invalid = _input_frame()
    invalid.loc[0, "datetime"] = "not-a-time"

    with pytest.raises(InferenceError, match="preprocess"):
        detector.detect_anomalies(invalid)
