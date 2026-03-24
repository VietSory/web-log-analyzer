# Threat Model

## Purpose and trust boundaries

This threat model covers the Web Log Analyzer application itself: the Streamlit client, FastAPI API, authentication, uploaded access logs, SQLite persistence, model artifacts, SMTP integration, container runtime, and CI supply chain. It does not assume the submitted web-server logs are trustworthy; log content is attacker-controlled input.

Primary trust boundaries are:

1. browser to frontend;
2. frontend to backend HTTP API;
3. authenticated user to owner-scoped data;
4. backend to filesystem/database/model artifacts;
5. backend to SMTP;
6. repository/CI to third-party actions, packages, base images, and generated artifacts.

## Assets

The assets requiring protection are user credentials and tokens, uploaded logs, scan history, server metadata, model integrity, SMTP credentials, application signing secrets, and the integrity of security findings presented to the operator.

## Attacker capabilities

The baseline attacker may be unauthenticated or may control one ordinary user account. They can send arbitrary HTTP requests, filenames, multipart bodies, access-log lines, paths, user agents, and log text; replay requests; submit malformed encodings; and attempt to infer or access other users' resources. Submitted logs may contain payload strings designed to exploit parsers, HTML/email rendering, detection rules, or model preprocessing.

The baseline attacker is not assumed to control the host, Docker daemon, GitHub repository administration, or production secret store. Compromise of those control planes is treated separately as an operational incident.

## Threats and controls

| Threat | Control | Residual risk |
|---|---|---|
| Plaintext credential disclosure | Argon2id password hashing; password hashes only in persistence; production rejects default JWT secret | Host/database compromise still exposes hashes for offline attack |
| Authentication brute force / resource exhaustion | Stricter auth rate limit plus general API rate limit; bounded request fields and upload sizes | Limiter is process-local; production with multiple replicas needs a shared edge/distributed limit |
| JWT forgery or stale credentials | Explicit HS256 algorithm, minimum secret length, short configurable expiration, authenticated dependency validates subject against current user | Token revocation list is not implemented; rotate signing secret for emergency global invalidation |
| Horizontal data access | Uploaded files, scan history, and server operations are scoped to authenticated owner IDs; missing/foreign resources return not-found behavior | Authorization remains application-code enforced and requires regression tests on every new resource type |
| Path traversal / unsafe uploaded filenames | Generated storage identifiers; extension/name validation; owner-scoped resolver; user paths are not used as filesystem paths | Filesystem permissions and deployment volume configuration remain defense-in-depth requirements |
| Oversized/binary upload DoS | Streaming byte limit, declared/actual size checks, NUL/binary rejection, cleanup of partial writes | Valid near-limit files still consume parser CPU/memory; edge request/body limits should complement application checks |
| Malformed/hostile log input | Strict access-log grammar, IP validation, timestamp/numeric conversion, bounded rule evidence, malformed-line skipping | Complex valid files can still be computationally expensive |
| Stored/rendered injection via log content | API returns data rather than executing it; warning email HTML escapes log/finding fields; rule evidence is bounded and line-normalized | Frontend components must continue using safe Streamlit rendering APIs and avoid unsafe HTML for attacker-controlled values |
| Detection evasion | URL decoding before selected rules, rule IDs/evidence, ML signal independent of rule signal, corroboration scoring | Heuristic signatures can be bypassed; the system is analytical, not a preventive WAF |
| Detection false positives | Explainable evidence, bounded risk scoring, ML/rule source attribution, conservative claims in documentation | Thresholds/rules require evaluation on representative data |
| ML artifact tampering | Generated artifacts not tracked; metadata schema and SHA-256 artifact checks before deserialization; runtime model directory mounted read-only in Compose | SHA-256 proves consistency with metadata, not publisher authenticity; a release signing/attestation mechanism is a future hardening step |
| Unsafe model deserialization | Only operator-provisioned artifact bundle is loaded; file names are constrained by metadata and hashes | `joblib` deserialization is unsafe for untrusted artifacts; never accept model bundles from end users |
| Training data leakage / temporal leakage | Chronological train/validation/test split; preprocessing fit only on training data; deterministic training configuration | Unlabeled log data cannot establish supervised detection quality |
| Email header/HTML injection | `EmailMessage` API, configured recipient/sender, HTML escaping, TLS context | SMTP account compromise and provider-side policy are outside application control |
| Secret leakage in repository | `.env` and runtime state ignored; examples contain development-only placeholders; CI secret scanning | Git history must still be reviewed before release because ignore rules do not erase previously committed secrets |
| Vulnerable dependencies/base images | Pinned direct dependencies, pinned Python base image digest, pip-audit, Trivy filesystem/image scans, CycloneDX SBOMs | Transitive dependencies can change only when direct pins are re-resolved; security workflow must remain green and pins require scheduled maintenance |
| CI action supply-chain compromise | Security workflow pins third-party actions to commit SHAs and limits token permissions | Maintainers must review intentional action SHA upgrades |
| Container privilege escalation | Non-root runtime, dropped capabilities, `no-new-privileges`, read-only root filesystem, dedicated writable mounts/tmpfs | Docker daemon/host compromise defeats container-level controls |
| Cross-origin abuse | Explicit CORS origins/methods/headers when credentials are enabled | CORS is a browser policy, not authorization; API auth remains mandatory |
| Sensitive information in telemetry/logs | Request logging records method/path/status/request ID/duration, not bearer tokens or bodies | URL paths themselves can contain secrets; upstream services should avoid credentials in URLs and future telemetry must sanitize captured headers |

## Abuse cases to test

Security regression coverage should include: another user requesting an owned upload/server/history record; traversal and double-extension upload names; streaming bodies that exceed the configured limit; NUL/binary files; malformed IPv4/IPv6/timestamps; encoded traversal and XSS/SQLi-like request data; false-positive benign paths; invalid/expired JWTs; default secret rejection in production; repeated login attempts hitting HTTP 429; corrupted model metadata/digests; and HTML-sensitive text in generated alert email.

## Operational assumptions

Production must supply a unique `AUTH_SECRET_KEY`, persistent database/upload storage, and a trusted model artifact bundle. SMTP remains disabled unless credentials are explicitly configured. If the API is deployed behind a reverse proxy, client-IP trust must be configured at the proxy/server layer; the application deliberately does not trust arbitrary `X-Forwarded-For` headers for rate-limit identity.

For multi-replica production, move rate limiting to a shared edge or datastore-backed implementation and replace local-only mutable storage as appropriate. Do not advertise the process-local limiter as a distributed security control.

## Review triggers

Revisit this model whenever the project adds a new log format, new upload type, external datastore, model-upload endpoint, multi-tenant role model, OAuth/OIDC provider, distributed deployment, telemetry exporter, blocking/response capability, or any third-party service that receives log content.
