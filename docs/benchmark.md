# Benchmark Methodology

Benchmarks in this repository are intended to make performance and model-quality claims reproducible. Do not publish throughput, latency, memory, or accuracy numbers unless the input, command, commit SHA, hardware, Python/library versions, and measurement method are recorded.

## Deterministic regression harness

A small synthetic rule-engine regression harness is included at `backend/benchmarks/benchmark_rules.py`. It is designed to catch parser/rule regressions and produce machine-readable JSON; it is **not** evidence of real-world detection efficacy.

Run it from the backend directory:

```bash
python benchmarks/benchmark_rules.py --iterations 1000 --output benchmark.json
```

The output reports parser/rule throughput on that machine plus TP/FP/TN/FN, precision, recall, and F1 for the fixed synthetic fixture. CI tests the metric logic and fixture classification but deliberately does not enforce timing thresholds because hosted-runner performance varies.

## Surfaces to measure

Measure parser/statistics throughput, rule-engine latency, ML inference latency, offline training cost, and HTTP API latency separately. Combining them into one throughput number hides the bottleneck.

## Data

Use a deterministic fixed-seed synthetic access-log fixture for regression testing. Record its row count and SHA-256. Include IPv4 and IPv6, common and combined format, several methods and paths, status-code and response-size variation, malformed lines, benign requests, and a separately identifiable set of rule-triggering rows. Synthetic traffic must not be presented as representative production traffic.

If representative real logs are used, sanitize private data before storing or sharing them. When the source cannot be published, record only its digest and aggregate characteristics.

## Environment record

Every result must include the repository commit SHA, OS/kernel, CPU, RAM, Python version, major dependency versions, container or bare-metal mode, TensorFlow device and deterministic-operation setting, input row count/digest, warmup count, and measured iteration count. Container measurements must also record image digests.

## Parser benchmark

Perform one unmeasured warmup and at least ten measured parses with `time.perf_counter()`. Report median and p95 duration plus rows/second. Verify each iteration returns the same schema and parsed-row count. Do not report only the fastest run.

## Detection benchmark

For rules, call `detect_rule_threats()` directly and report rows analyzed, median/p95 duration, and findings by rule ID. Keep known benign rows in the corpus so a speedup that increases obvious false positives is not treated as an improvement.

For ML, load one verified artifact bundle before timed inference. Report model-load, preprocessing, prediction, and end-to-end durations separately, along with artifact metadata digest, batch size, reconstruction-error median/p95/p99, threshold, and percentage above threshold. Percentage above threshold is not accuracy without ground-truth labels.

## Training benchmark

Use the same input file, seed, chronological split, epochs, batch size, and threshold quantile. Record split sizes, completed epochs, wall time, final train/validation loss, reconstruction-error summaries from `metadata.json`, calibrated threshold, test anomaly rate, and generated artifact hashes.

## API benchmark

Authenticate outside timed iterations and use an already uploaded fixed fixture. Keep concurrency explicit. Report median/p95/p99 latency, errors, and HTTP 429 responses separately. Record whether ML artifacts were available for scan requests.

## Quality evaluation

Supervised detection metrics require labels. When a labeled evaluation set exists, document label provenance and keep evaluation examples out of training and threshold calibration, then report precision, recall, F1, confusion matrix, and category-level results where sample sizes are meaningful.

Until then, restrict claims to reconstruction-error distributions, threshold behavior, rule regression tests, and explicitly labeled synthetic fixtures. The training metadata intentionally records supervised metrics as unavailable for unlabeled access logs.

## Regression policy

Start by publishing informational benchmark artifacts and establish normal variance across several runs. Add a blocking performance threshold only after that variance is understood. Never weaken correctness or security checks to improve benchmark numbers.
