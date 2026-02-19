from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from core.ml_features import ARTIFACT_SCHEMA_VERSION, MODEL_FEATURES, prepare_model_frame


class ModelArtifactError(RuntimeError):
    pass


class InferenceError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LogAnomalyDetector:
    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.model: Any | None = None
        self.preprocessor: Any | None = None
        self.threshold: float | None = None
        self.metadata: dict[str, Any] | None = None

    @property
    def ready(self) -> bool:
        return (
            self.model is not None
            and self.preprocessor is not None
            and self.threshold is not None
            and self.metadata is not None
        )

    def load_resources(self) -> None:
        metadata_path = self.model_dir / "metadata.json"
        if not metadata_path.is_file():
            raise ModelArtifactError(f"Model metadata not found: {metadata_path}")

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelArtifactError("Model metadata is unreadable") from exc

        if metadata.get("artifact_schema_version") != ARTIFACT_SCHEMA_VERSION:
            raise ModelArtifactError("Unsupported model artifact schema version")
        if metadata.get("feature_schema") != list(MODEL_FEATURES):
            raise ModelArtifactError("Model feature schema does not match runtime schema")

        threshold = metadata.get("threshold", {}).get("value")
        if not isinstance(threshold, (int, float)) or not np.isfinite(threshold) or threshold <= 0:
            raise ModelArtifactError("Model threshold is missing or invalid")

        artifacts = metadata.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ModelArtifactError("Model artifact metadata is missing")

        model_path = self._validated_artifact_path(artifacts, "model")
        preprocessor_path = self._validated_artifact_path(artifacts, "preprocessor")

        try:
            from tensorflow.keras.models import load_model  # type: ignore

            model = load_model(model_path)
            preprocessor = joblib.load(preprocessor_path)
        except (OSError, ValueError, TypeError, ImportError) as exc:
            raise ModelArtifactError("Could not load model artifact bundle") from exc

        self.model = model
        self.preprocessor = preprocessor
        self.threshold = float(threshold)
        self.metadata = metadata

    def _validated_artifact_path(self, artifacts: dict[str, Any], key: str) -> Path:
        entry = artifacts.get(key)
        if not isinstance(entry, dict):
            raise ModelArtifactError(f"Missing {key} artifact metadata")

        filename = entry.get("filename")
        expected_digest = entry.get("sha256")
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ModelArtifactError(f"Invalid {key} artifact filename")
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            raise ModelArtifactError(f"Invalid {key} artifact digest")

        path = self.model_dir / filename
        if not path.is_file():
            raise ModelArtifactError(f"Missing {key} artifact: {path}")
        if _sha256(path) != expected_digest:
            raise ModelArtifactError(f"Checksum mismatch for {key} artifact")
        return path

    def preprocess_features(self, dataframe: pd.DataFrame) -> np.ndarray:
        if not self.ready:
            raise ModelArtifactError("Model resources have not been loaded")
        if dataframe.empty:
            return np.empty((0, len(MODEL_FEATURES)), dtype=np.float32)

        try:
            frame = prepare_model_frame(dataframe)
            values = self.preprocessor.transform(frame).astype(np.float32)
        except (KeyError, TypeError, ValueError) as exc:
            raise InferenceError("Could not preprocess log features") from exc

        if not np.isfinite(values).all():
            raise InferenceError("Preprocessed features contain non-finite values")
        return values

    def detect_anomalies(self, dataframe: pd.DataFrame) -> list[dict[str, Any]]:
        if dataframe.empty:
            return []
        if not self.ready:
            raise ModelArtifactError("Model resources have not been loaded")

        input_values = self.preprocess_features(dataframe)
        try:
            reconstructions = self.model.predict(input_values, verbose=0)
        except (ValueError, TypeError, RuntimeError) as exc:
            raise InferenceError("Model inference failed") from exc

        if reconstructions.shape != input_values.shape:
            raise InferenceError("Model reconstruction shape does not match input")

        errors = np.mean(np.square(input_values - reconstructions), axis=1)
        if not np.isfinite(errors).all():
            raise InferenceError("Model produced non-finite reconstruction errors")

        threshold = float(self.threshold)
        anomaly_indices = np.flatnonzero(errors > threshold)
        source = dataframe.reset_index(drop=True)
        threats: list[dict[str, Any]] = []

        for index in anomaly_indices:
            row = source.iloc[int(index)]
            loss = float(errors[int(index)])
            ratio = loss / threshold
            if ratio >= 4:
                severity = "critical"
            elif ratio >= 2:
                severity = "high"
            else:
                severity = "medium"

            threats.append(
                {
                    "ip": str(row.get("ip", "unknown")),
                    "type": "ml_anomaly",
                    "severity": severity,
                    "time": str(row.get("datetime", "")),
                    "reconstruction_error": round(loss, 6),
                    "threshold": round(threshold, 6),
                    "score_ratio": round(ratio, 4),
                    "details": f"Path: {row.get('path', 'unknown')}",
                }
            )

        return threats
