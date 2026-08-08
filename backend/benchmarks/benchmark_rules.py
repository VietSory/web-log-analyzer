from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from time import perf_counter
from typing import Iterable

import pandas as pd

from core.detection import detect_rule_threats
from core.parser import parse_log_line


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    line: str
    malicious: bool


@dataclass(frozen=True, slots=True)
class ConfusionMetrics:
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    precision: float
    recall: float
    f1: float


CASES: tuple[BenchmarkCase, ...] = (
    BenchmarkCase(
        '192.0.2.10 - - [10/Feb/2026:12:00:00 +0000] "GET / HTTP/1.1" 200 42 "-" "Mozilla/5.0"',
        False,
    ),
    BenchmarkCase(
        '192.0.2.11 - - [10/Feb/2026:12:00:01 +0000] "GET /products?page=2 HTTP/1.1" 200 512 "-" "Mozilla/5.0"',
        False,
    ),
    BenchmarkCase(
        '192.0.2.12 - - [10/Feb/2026:12:00:02 +0000] "POST /login HTTP/1.1" 401 128 "-" "Mozilla/5.0"',
        False,
    ),
    BenchmarkCase(
        '2001:db8::10 - - [10/Feb/2026:12:00:03 +0000] "GET /health HTTP/1.1" 200 12 "-" "curl/8.0"',
        False,
    ),
    BenchmarkCase(
        '192.0.2.13 - - [10/Feb/2026:12:00:04 +0000] "GET /docs/select-from-examples HTTP/1.1" 200 900 "-" "Mozilla/5.0"',
        False,
    ),
    BenchmarkCase(
        '198.51.100.10 - - [10/Feb/2026:12:01:00 +0000] "GET /../../etc/passwd HTTP/1.1" 404 20 "-" "scanner"',
        True,
    ),
    BenchmarkCase(
        '198.51.100.11 - - [10/Feb/2026:12:01:01 +0000] "GET /%252e%252e/%252e%252e/etc/passwd HTTP/1.1" 404 20 "-" "scanner"',
        True,
    ),
    BenchmarkCase(
        '198.51.100.12 - - [10/Feb/2026:12:01:02 +0000] "GET /search?q=%27%20UNION%20SELECT%20password%20FROM%20users-- HTTP/1.1" 500 20 "-" "scanner"',
        True,
    ),
    BenchmarkCase(
        '198.51.100.13 - - [10/Feb/2026:12:01:03 +0000] "GET /.env HTTP/1.1" 403 20 "-" "scanner"',
        True,
    ),
    BenchmarkCase(
        '198.51.100.14 - - [10/Feb/2026:12:01:04 +0000] "GET /wp-admin/ HTTP/1.1" 401 20 "-" "scanner"',
        True,
    ),
    BenchmarkCase(
        '198.51.100.15 - - [10/Feb/2026:12:01:05 +0000] "GET / HTTP/1.1" 200 20 "-" "<img src=x onerror=alert(1)>"',
        True,
    ),
)


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def confusion_metrics(
    labels: Iterable[bool],
    predictions: Iterable[bool],
) -> ConfusionMetrics:
    pairs = list(zip(labels, predictions, strict=True))
    true_positive = sum(label and prediction for label, prediction in pairs)
    false_positive = sum(not label and prediction for label, prediction in pairs)
    true_negative = sum(not label and not prediction for label, prediction in pairs)
    false_negative = sum(label and not prediction for label, prediction in pairs)

    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)

    return ConfusionMetrics(
        true_positive=true_positive,
        false_positive=false_positive,
        true_negative=true_negative,
        false_negative=false_negative,
        precision=round(precision, 6),
        recall=round(recall, 6),
        f1=round(f1, 6),
    )


def evaluate_cases(cases: Iterable[BenchmarkCase]) -> ConfusionMetrics:
    labels: list[bool] = []
    predictions: list[bool] = []

    for case in cases:
        event = parse_log_line(case.line)
        if event is None:
            raise ValueError("benchmark fixture contains an unparseable log line")
        detections = detect_rule_threats(pd.DataFrame([asdict(event)]))
        labels.append(case.malicious)
        predictions.append(bool(detections))

    return confusion_metrics(labels, predictions)


def benchmark(iterations: int) -> dict[str, object]:
    if iterations < 1:
        raise ValueError("iterations must be positive")

    parsed_events = []
    parser_started = perf_counter()
    for _ in range(iterations):
        for case in CASES:
            event = parse_log_line(case.line)
            if event is None:
                raise ValueError("benchmark fixture contains an unparseable log line")
            parsed_events.append(event)
    parser_seconds = perf_counter() - parser_started

    frame = pd.DataFrame([asdict(event) for event in parsed_events])
    rules_started = perf_counter()
    detect_rule_threats(frame)
    rules_seconds = perf_counter() - rules_started

    evaluated = evaluate_cases(CASES)
    total_events = len(parsed_events)
    return {
        "benchmark_type": "synthetic_regression",
        "fixture_cases": len(CASES),
        "iterations": iterations,
        "total_events": total_events,
        "parser": {
            "seconds": round(parser_seconds, 6),
            "events_per_second": round(total_events / parser_seconds, 2)
            if parser_seconds
            else None,
        },
        "rule_engine": {
            "seconds": round(rules_seconds, 6),
            "events_per_second": round(total_events / rules_seconds, 2)
            if rules_seconds
            else None,
            **asdict(evaluated),
        },
        "limitations": [
            "Synthetic fixtures are deterministic regression cases, not a real-world efficacy benchmark.",
            "No latency or throughput threshold is enforced because CI runner performance is variable.",
            "ML evaluation is handled by the training/evaluation pipeline and is not inferred when artifacts are absent.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic parser/rule regression benchmark")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    result = benchmark(args.iterations)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as output_file:
            output_file.write(rendered + "\n")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
