from __future__ import annotations

from functools import lru_cache

from config import get_settings
from core.ml_engine import LogAnomalyDetector


@lru_cache(maxsize=1)
def get_anomaly_detector() -> LogAnomalyDetector:
    settings = get_settings()
    detector = LogAnomalyDetector(settings.model_dir)
    detector.load_resources()
    return detector
