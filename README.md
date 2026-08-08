# Web Log Analyzer

A security-focused web access-log analysis system built with FastAPI, Streamlit, deterministic anomaly detection, explainable rules, and auditable risk scoring.

The project analyzes Apache/Nginx access logs after ingestion. It is **not** an inline WAF and does not claim to prove compromise from an anomaly score. Findings are intended to help an operator prioritize investigation.

## What it does

- Parses Apache/Nginx common and combined access logs into a stable typed schema, including IPv4 and IPv6.
- Rejects unsafe uploads and stores files under generated owner-scoped identifiers.
- Detects explainable web attack indicators such as traversal, SQL-injection-like payloads, XSS-like payloads, and sensitive endpoint probing.
- Optionally runs a deterministic TensorFlow/Keras autoencoder for unsupervised anomaly signals.
- Combines rule and ML findings on a shared 0-100 risk scale while preserving evidence and detection source.
- Stores users, servers, scan history, and findings in migrated SQLite persistence with foreign keys and WAL mode.
- Uses Argon2id password hashing and JWT bearer authentication with owner-scoped authorization.
- Provides health/readiness endpoints, request correlation IDs, CORS constraints, upload/request validation, and configurable API rate limiting.
- Ships hardened non-root Docker images and a Compose stack.
- Runs CI, lint, tests/coverage, dependency audit, repository/container scanning, CycloneDX SBOM generation, and SARIF upload.

## Architecture

```text
Browser
  |
  v
Streamlit frontend :8501
  |
  | HTTP + Bearer token
  v
FastAPI backend :8000
  |        |        |
  |        |        +--> optional SMTP alerts
  |        +----------> verified ML artifact bundle
  +-------------------> SQLite + owner-scoped upload storage
```

The backend treats rule detection and ML inference as independent sources. If the ML artifact bundle is unavailable, rule analysis can still run in a degraded mode rather than silently substituting a fake threshold.

See [Architecture](docs/architecture.md) and [Threat Model](docs/threat-model.md) for design boundaries and residual risks.

## Detection model

### Explainable rules

Rule findings include a stable rule ID, severity, evidence, source IP, timestamp, and request path. Current coverage includes encoded/plain path traversal, SQL-injection-like request payloads, XSS-like payloads, and sensitive endpoint probes.

### ML anomaly detection

Training is offline and chronological:

```text
70% train -> 15% validation -> 15% test
```

Preprocessing is fitted on the training partition only and explicitly handles unseen categories. TensorFlow deterministic operations and a fixed seed are enabled, rows are not shuffled, and the anomaly threshold is calibrated from validation reconstruction-error quantiles.

Generated artifacts are deliberately excluded from Git. A valid bundle contains:

```text
model.keras
preprocessor.joblib
metadata.json
```

`metadata.json` records feature/schema versioning, input SHA-256, split sizes, training options, threshold calibration, reconstruction-error evaluation, runtime versions, and artifact digests. Runtime loading validates the schema and SHA-256 digests before deserializing the bundle.

Because ordinary access logs do not provide trustworthy anomaly labels, the project does not fabricate supervised precision/recall metrics. See [Benchmark Methodology](docs/benchmark.md) for how model and performance claims should be evaluated.

## Repository layout

```text
.
├── backend/
│   ├── core/              # auth, parser, detection, ML, risk, uploads, rate limits
│   ├── models/            # README only; generated model bundle is ignored
│   ├── routers/           # FastAPI endpoints
│   ├── tests/             # backend regression/security tests
│   ├── config.py          # typed Pydantic settings
│   ├── database.py        # SQLite schema, migrations, persistence
│   ├── main.py            # FastAPI application
│   └── train_model.py     # deterministic offline training CLI
├── frontend/              # Streamlit client
├── docs/                  # architecture, threat model, benchmark, release/replay docs
├── .github/workflows/     # quality and supply-chain security pipelines
├── compose.yaml
└── README.md
```

## Local development

Python 3.12 is the tested project baseline. Direct dependencies are pinned in each service requirements file.

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
cp backend/.env.example backend/.env
cd backend
uvicorn main:app --reload
```

For Windows PowerShell, activate the virtual environment with `.venv\Scripts\Activate.ps1`.

The development `.env.example` contains a development-only JWT secret. Production configuration rejects the default development secret.

### Frontend

From a separate shell:

```bash
source .venv/bin/activate
python -m pip install -r frontend/requirements.txt
cd frontend
streamlit run app.py
```

The frontend defaults to `http://127.0.0.1:8000`. Override it with `WEB_LOG_ANALYZER_API_URL`.

## Train a local model bundle

Training expects a raw Apache/Nginx access log and at least enough parsed rows for chronological train/validation/test partitions.

```bash
cd backend
python train_model.py \
  --data /path/to/access.log \
  --output models \
  --epochs 50 \
  --batch-size 128 \
  --seed 42 \
  --threshold-quantile 0.995
```

Do not commit the generated files. Production/release environments should receive a separately controlled and verified artifact bundle.

## Docker Compose

Set a non-default authentication secret before starting the stack:

```bash
export AUTH_SECRET_KEY="$(openssl rand -hex 32)"
docker compose up --build
```

Services:

- frontend: `http://localhost:8501`
- backend API: `http://localhost:8000`
- liveness: `http://localhost:8000/health/live`
- readiness: `http://localhost:8000/health/ready`

The containers run non-root, drop Linux capabilities, use `no-new-privileges`, and use read-only root filesystems with explicit writable mounts/tmpfs. The frontend waits for backend readiness before startup.

The bundled rate limiter is process-local. A multi-replica production deployment must add a shared edge/distributed limiter instead of treating it as a cross-node control.

## Verification

Run backend checks locally from the repository root:

```bash
python -m compileall -q backend frontend
ruff check backend frontend
cd backend
pytest -q --cov=. --cov-report=term-missing
```

GitHub Actions additionally performs Python dependency auditing, repository vulnerability/secret/misconfiguration scanning, container scanning, SARIF upload, and CycloneDX SBOM generation.

## Security model

Important design choices include:

- Argon2id password hashes; no plaintext credential comparison.
- Explicit JWT algorithm and production-secret validation.
- Owner-scoped file/history/server authorization.
- Generated upload storage IDs and bounded streaming uploads.
- Explicit CORS origins/methods/headers when credentials are enabled.
- Bounded Pydantic request fields and API rate limits.
- HTML escaping in warning emails.
- Versioned/checksummed ML artifacts and no silent inference fallback.
- Pinned container base-image digest and pinned third-party security workflow actions.

Read [Threat Model](docs/threat-model.md) before deploying or extending a trust boundary.

## Persistence and scaling boundaries

SQLite is intentional for the current portfolio deployment profile. The backend enables foreign keys, busy timeout, WAL mode, migrations, and indexes. It is not presented as a horizontally distributed database.

For multi-host production, replace local filesystem state and process-local rate limiting with shared infrastructure and select a database appropriate to the required concurrency and durability model.

## Release history reconstruction

This repository uses `portfolio-rebuild-workspace` only as an engineering workspace. The final dated portfolio history is produced from `docs/replay-manifest.json`; bookkeeping-only manifest/audit commits are not replayed. The workspace branch is never merged directly into `main`.

See [Release and Publishing Runbook](docs/release.md) for the verified replay and publication procedure.

## Current limitations

- Rule signatures are intentionally focused and do not replace a maintained WAF/IDS ruleset.
- Unsupervised reconstruction error is an investigation signal, not a ground-truth verdict.
- Model artifact hashes provide integrity relative to metadata but not publisher authenticity; release signing/attestation is a future hardening step.
- The bundled Compose profile is a single-node deployment model.
- Representative labeled security evaluation data is still required before making supervised accuracy claims.
