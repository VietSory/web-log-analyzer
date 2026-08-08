# Portfolio Rebuild Roadmap

Working branch: `portfolio-rebuild`

Goal: turn Web Log Analyzer from a demo project into a portfolio-grade security/backend/ML project with a reviewable engineering history.

## Rules

- Keep `main` stable; work on `portfolio-rebuild` until milestones are reviewable.
- Each commit should represent one coherent engineering change.
- Prefer tests and measurable behavior over feature count.
- Do not commit runtime data, local databases, caches, secrets, or generated ML artifacts.
- Update this checklist as work is completed.

## Phase 1 — Repository hygiene and correctness

- [x] Expand `.gitignore` for Python caches, virtualenvs, local DBs, uploads, backups, and generated model artifacts.
- [ ] Remove already tracked generated/cache/runtime files from the working branch.
- [ ] Centralize application settings and environment configuration.
- [ ] Introduce a normalized log event schema.
- [ ] Refactor parser to support malformed input, IPv6, and common/combined log formats.
- [ ] Add parser unit tests.
- [ ] Add Ruff + Pytest CI.

## Phase 2 — Detection engine

- [ ] Extract rule-based threat detection from route/orchestration code.
- [ ] Add explicit rule IDs, evidence, and severity.
- [ ] Add upload validation and file-size/type constraints.
- [ ] Standardize API errors and response models.
- [ ] Add FastAPI integration tests.

## Phase 3 — ML engineering

- [ ] Fix timestamp/hour extraction in model training.
- [ ] Make training deterministic and reproducible.
- [ ] Split train/validation/test data explicitly.
- [ ] Improve feature engineering and unseen-category handling.
- [ ] Train anomaly model on a documented normal-traffic baseline.
- [ ] Calibrate threshold from validation data.
- [ ] Add precision, recall, F1, false-positive-rate and detection-rate evaluation.
- [ ] Add model metadata/versioning.
- [ ] Combine rule and anomaly outputs into a unified risk score.

## Phase 4 — Persistence, security and production readiness

- [ ] Refactor persistence behind a repository/service layer.
- [ ] Add schema migrations.
- [ ] Harden authentication and credential handling.
- [ ] Add rate limits, CORS policy, and request constraints.
- [ ] Add end-to-end scan workflow tests.
- [ ] Containerize backend and frontend.
- [ ] Add Docker Compose development stack.
- [ ] Add health/readiness endpoints and structured observability.

## Phase 5 — CI, supply-chain security and presentation

- [ ] Add lint/test/build CI pipeline.
- [ ] Add dependency/SCA scanning.
- [ ] Generate SBOM.
- [ ] Publish SARIF-compatible security results where supported.
- [ ] Add dependency/container scanning.
- [ ] Rewrite README with architecture, threat model, quick start, demo, benchmark, screenshots, CI/security badges, and roadmap.
- [ ] Create a release-ready pull request into `main`.

## Definition of done

The rebuild is complete when the repository has passing automated tests/CI, documented detection behavior and ML evaluation, reproducible local startup, production-oriented security/observability basics, and a README that makes the project understandable within a few minutes to a recruiter or engineer.
