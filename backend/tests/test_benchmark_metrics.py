from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.benchmark_rules import CASES, benchmark, confusion_metrics, evaluate_cases


def test_confusion_metrics_handles_perfect_classification():
    metrics = confusion_metrics(
        [True, True, False, False],
        [True, True, False, False],
    )

    assert metrics.true_positive == 2
    assert metrics.false_positive == 0
    assert metrics.true_negative == 2
    assert metrics.false_negative == 0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_confusion_metrics_rejects_mismatched_input_lengths():
    with pytest.raises(ValueError):
        confusion_metrics([True], [True, False])


def test_synthetic_rule_fixture_is_fully_detected_without_false_positives():
    metrics = evaluate_cases(CASES)

    assert metrics.false_positive == 0
    assert metrics.false_negative == 0
    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_benchmark_returns_machine_readable_shape_without_timing_gate():
    result = benchmark(iterations=1)

    assert result["benchmark_type"] == "synthetic_regression"
    assert result["fixture_cases"] == len(CASES)
    assert result["total_events"] == len(CASES)
    assert result["parser"]["events_per_second"] is not None
    assert result["rule_engine"]["events_per_second"] is not None
    assert result["rule_engine"]["f1"] == 1.0
    assert result["limitations"]
