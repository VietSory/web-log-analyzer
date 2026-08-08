# Architecture

## Scope

Web Log Analyzer is a two-service web application for ingesting Apache/Nginx access logs, computing descriptive statistics, applying explainable detection rules, and optionally running an unsupervised anomaly detector. The project is intentionally a log-analysis system, not an inline WAF or IDS: it analyzes submitted records and reports findings; it does not claim to block attacks.

## Runtime topology

```text
Browser
  |
  v
Streamlit frontend :8501
  |
  | HTTP + Bearer token
  v
FastAPI backend :8000
  |       |        |
  |       |        +--> optional SMTP alert delivery
  |       |
  |       +--> versioned ML artifact bundle (read-only at runtime)
  |
  +--> SQLite database (WAL, foreign keys, migrations)
  |
  +--> owner-scoped uploaded log storage
```

`compose.yaml` starts the frontend only after the backend readiness check succeeds. Both images run as non-root users with dropped Linux capabilities and read-only root filesystems; mutable database/upload state is mounted separately.

## Backend boundaries

### API layer

FastAPI routers own HTTP concerns: authentication dependencies, Pydantic request validation, status codes, and response serialization. Shared business behavior belongs under `backend/core/` or `backend/services/` rather than being copied between routers.

The application middleware provides a validated request correlation ID and process-local rate limiting. Health endpoints are deliberately separate:

- `/health/live` proves the process can answer HTTP.
- `/health/ready` checks the configured database and reports ML artifact availability separately. The ML model is optional for rule-based analysis, so missing model artifacts degrade ML capability without making the database-backed service itself unavailable.

### Authentication and authorization

Passwords are stored as Argon2id hashes. Login verifies hashes and opportunistically rehashes when parameters need upgrading. Access tokens are signed JWT bearer tokens containing the user identifier. Resource access is owner-scoped: uploaded files, scan history, and server objects must resolve through the authenticated user's identity.

### Upload and parsing path

The upload service never persists a user-supplied path as the storage identifier. It validates the original filename, accepted extension, configured byte limit, and binary/NUL content, then generates an owner-scoped storage name. Later reads resolve through the same storage validation boundary.

`core/parser.py` normalizes common and combined Apache/Nginx access-log records into a stable schema:

- `ip`
- `datetime`
- `method`
- `path`
- `protocol`
- `status`
- `size`
- `referrer`
- `user_agent`
- `source_format`

Addresses are validated with Python's `ipaddress`, so both IPv4 and IPv6 are supported. Malformed individual lines are skipped; an unreadable file is not silently converted into an empty successful parse.

### Detection pipeline

Analysis has two independent sources of findings.

1. **Rules** inspect canonicalized request data for explainable patterns such as traversal sequences, SQL-injection-like payloads, XSS-like payloads, and sensitive endpoint probes. Each result carries a stable rule ID, evidence, severity, source IP, timestamp, and path.
2. **ML** computes reconstruction error from a dense autoencoder when a valid model artifact bundle is available. Runtime loading validates artifact schema version, feature schema, filenames, and SHA-256 digests before deserializing the model/preprocessor.

`core/risk.py` normalizes rule and ML findings onto one 0-100 risk scale. Findings that refer to the same request and are corroborated by both sources receive a bounded score bonus. API responses retain the source of each finding rather than hiding how a conclusion was produced.

## ML lifecycle

Training is offline. `backend/train_model.py` parses raw access logs, sorts records chronologically, and creates 70/15/15 train/validation/test partitions so later events do not influence earlier preprocessing or fitting.

The model frame uses stable behavioral/request features rather than assigning arbitrary ordinal meaning to raw identifiers. Preprocessing is fit only on the training partition and handles unseen categorical values explicitly. TensorFlow seeds and deterministic operations are enabled; training does not shuffle rows.

The anomaly threshold is calibrated from validation reconstruction-error quantiles. Test reconstruction statistics and test anomaly rate are recorded separately. Because ordinary access logs do not contain trustworthy anomaly labels, the training code does not fabricate supervised precision/recall metrics.

A generated artifact directory contains:

- `model.keras`
- `preprocessor.joblib`
- `metadata.json`

Metadata records the schema version, feature schema, input data SHA-256, chronological split sizes, training seed/options, threshold method/value, evaluation statistics, runtime library versions, and artifact hashes. Generated artifacts are excluded from Git; releases must supply a verified bundle separately.

## Persistence

SQLite is used deliberately for the current portfolio deployment profile. Connections enable foreign keys and a busy timeout; file-backed databases use WAL mode. A `schema_migrations` table records ordered application migrations. Current migrations cover legacy password storage, legacy scan-history table shape/identifier conversion, and indexes.

This design is appropriate for one backend process and modest write concurrency. Scaling to several writers or multiple hosts should replace SQLite and the process-local rate limiter with shared infrastructure rather than pretending the existing components are distributed.

## Failure behavior

The design prefers explicit degradation over hidden fallbacks:

- missing or checksum-invalid ML artifacts produce an explicit ML-unavailable state rather than a made-up threshold;
- inference/preprocessing errors are distinct from model-artifact errors;
- SMTP alert delivery is best-effort and cannot roll back an already persisted analysis;
- upload persistence failures return an error and partial files are cleaned up;
- database readiness failure returns HTTP 503;
- malformed access-log rows are ignored individually while valid rows in the same file remain analyzable.

## Build and verification

Direct Python dependencies are pinned. GitHub Actions compiles sources, runs Ruff correctness checks, executes pytest with coverage, audits Python dependencies, performs repository/container vulnerability and secret scans, uploads SARIF to code scanning, and publishes CycloneDX SBOM artifacts.

Release candidates are expected to pass those gates on the exact revision being published. See [Release Runbook](release.md) for the maintainer verification, security-evidence, publishing, and rollback procedure.

## Known scaling boundaries

The following are deliberate constraints, not hidden promises:

- SQLite and the in-memory rate limiter are single-process/single-node mechanisms.
- Uploaded logs are local filesystem state unless an external durable volume is supplied.
- ML training can be memory/CPU intensive and is not run inside request handlers.
- The rule engine is evidence-oriented heuristics, not a complete signature database.
- The anomaly model is unsupervised; a high reconstruction score is a signal for investigation, not proof of compromise.
