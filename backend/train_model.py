from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import platform

import joblib
import numpy as np
import sklearn
import tensorflow as tf

from core.ml_features import (
    ARTIFACT_SCHEMA_VERSION,
    MODEL_FEATURES,
    build_preprocessor,
    prepare_model_frame,
    temporal_split,
)
from core.parser import parse_log_file


DEFAULT_SEED = 42
DEFAULT_THRESHOLD_QUANTILE = 0.995


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_autoencoder(input_dim: int) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(input_dim,), name="features")
    encoded = tf.keras.layers.Dense(16, activation="relu", name="encoder_16")(inputs)
    encoded = tf.keras.layers.Dense(8, activation="relu", name="encoder_8")(encoded)
    decoded = tf.keras.layers.Dense(16, activation="relu", name="decoder_16")(encoded)
    outputs = tf.keras.layers.Dense(input_dim, activation="linear", name="reconstruction")(decoded)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="web_log_autoencoder")
    model.compile(optimizer=tf.keras.optimizers.Adam(), loss="mse")
    return model


def _reconstruction_errors(model: tf.keras.Model, values: np.ndarray) -> np.ndarray:
    reconstructed = model.predict(values, verbose=0)
    return np.mean(np.square(values - reconstructed), axis=1)


def _error_metrics(errors: np.ndarray) -> dict[str, float]:
    return {
        "mean": float(np.mean(errors)),
        "median": float(np.median(errors)),
        "p95": float(np.quantile(errors, 0.95)),
        "p99": float(np.quantile(errors, 0.99)),
        "max": float(np.max(errors)),
    }


def train(
    data_path: Path,
    output_dir: Path,
    *,
    epochs: int = 50,
    batch_size: int = 128,
    seed: int = DEFAULT_SEED,
    threshold_quantile: float = DEFAULT_THRESHOLD_QUANTILE,
) -> dict:
    if not 0.90 <= threshold_quantile < 1.0:
        raise ValueError("threshold_quantile must be in [0.90, 1.0)")
    if epochs < 1:
        raise ValueError("epochs must be positive")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    dataframe = parse_log_file(data_path)
    split = temporal_split(dataframe)

    tf.keras.utils.set_random_seed(seed)
    tf.config.experimental.enable_op_determinism()

    train_frame = prepare_model_frame(split.train)
    validation_frame = prepare_model_frame(split.validation)
    test_frame = prepare_model_frame(split.test)

    preprocessor = build_preprocessor()
    train_values = preprocessor.fit_transform(train_frame).astype(np.float32)
    validation_values = preprocessor.transform(validation_frame).astype(np.float32)
    test_values = preprocessor.transform(test_frame).astype(np.float32)

    model = _build_autoencoder(train_values.shape[1])
    history = model.fit(
        train_values,
        train_values,
        validation_data=(validation_values, validation_values),
        epochs=epochs,
        batch_size=batch_size,
        shuffle=False,
        verbose=2,
    )

    train_errors = _reconstruction_errors(model, train_values)
    validation_errors = _reconstruction_errors(model, validation_values)
    threshold = float(np.quantile(validation_errors, threshold_quantile))
    test_errors = _reconstruction_errors(model, test_values)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.keras"
    preprocessor_path = output_dir / "preprocessor.joblib"
    metadata_path = output_dir / "metadata.json"

    model.save(model_path)
    joblib.dump(preprocessor, preprocessor_path)

    test_anomaly_rate = float(np.mean(test_errors > threshold))
    metadata = {
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "model_type": "dense_autoencoder",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "filename": data_path.name,
            "sha256": _sha256(data_path),
            "parsed_rows": int(len(dataframe)),
        },
        "feature_schema": list(MODEL_FEATURES),
        "splits": {
            "strategy": "chronological_70_15_15",
            "train_rows": int(len(split.train)),
            "validation_rows": int(len(split.validation)),
            "test_rows": int(len(split.test)),
        },
        "training": {
            "seed": seed,
            "epochs": epochs,
            "epochs_completed": len(history.history.get("loss", [])),
            "batch_size": batch_size,
            "shuffle": False,
            "tensorflow_op_determinism": True,
        },
        "threshold": {
            "method": "validation_reconstruction_error_quantile",
            "quantile": threshold_quantile,
            "value": threshold,
        },
        "evaluation": {
            "train_reconstruction_error": _error_metrics(train_errors),
            "validation_reconstruction_error": _error_metrics(validation_errors),
            "test_reconstruction_error": _error_metrics(test_errors),
            "test_anomaly_rate": test_anomaly_rate,
            "supervised_metrics": None,
            "note": "No ground-truth anomaly labels are present in raw access logs; classification precision/recall are intentionally not fabricated.",
        },
        "runtime": {
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
        },
        "artifacts": {
            "model": {"filename": model_path.name, "sha256": _sha256(model_path)},
            "preprocessor": {
                "filename": preprocessor_path.name,
                "sha256": _sha256(preprocessor_path),
            },
        },
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the web-log anomaly detector")
    parser.add_argument("--data", type=Path, required=True, help="Raw Apache/Nginx access log")
    parser.add_argument("--output", type=Path, default=Path("models"))
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--threshold-quantile",
        type=float,
        default=DEFAULT_THRESHOLD_QUANTILE,
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    metadata = train(
        args.data,
        args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        threshold_quantile=args.threshold_quantile,
    )
    print(json.dumps(metadata["evaluation"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
