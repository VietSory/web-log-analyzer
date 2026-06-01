# Release Runbook

## Release invariants

A release is cut only from a revision that has passed the repository's quality and security gates. `main` is the publish branch; feature or maintenance branches are reviewed and merged only after their final tree has been verified.

The application ships source code and configuration, not generated runtime state. Local SQLite databases, uploads, caches, training inputs, and generated ML artifacts must remain outside Git unless a release process explicitly promotes an artifact through a controlled channel.

## Pre-release gate

Before publishing a release:

1. Confirm the working tree is clean and the release candidate is based on the expected `main` revision.
2. Run Python compilation, Ruff, pytest/coverage, dependency audit, repository scanning, container builds/scans, and SBOM generation. Investigate failures instead of bypassing gates.
3. Review the README, architecture, threat model, benchmark methodology, environment examples, Dockerfiles, Compose configuration, and dependency pins against the candidate code.
4. Confirm production configuration uses a unique `AUTH_SECRET_KEY`, explicit CORS origins, persistent data storage, and a trusted model artifact bundle when ML inference is enabled.
5. Confirm generated `.keras`, joblib, metadata outputs, local training data, uploads, SQLite state, caches, secrets, and temporary scan output are not tracked.
6. Review dependency, base-image, and GitHub Action pin updates for provenance and expected security impact.

A green CI run is necessary but does not replace a maintainer review of the final diff and runtime configuration.

## Local verification

From the repository root, run:

```bash
python -m compileall -q backend frontend
ruff check backend frontend
cd backend
pytest -q --cov=. --cov-report=term-missing
```

When Docker is available, also validate the deployment profile:

```bash
docker compose config
docker compose build
```

Start the stack with a non-default authentication secret and verify the health endpoints:

```bash
export AUTH_SECRET_KEY="$(openssl rand -hex 32)"
docker compose up -d
curl --fail http://127.0.0.1:8000/health/live
curl --fail http://127.0.0.1:8000/health/ready
```

Exercise at least one authenticated upload/scan/report flow before tagging a release candidate intended for demonstration or deployment.

## Security evidence

The security workflow is expected to produce or enforce:

- Python dependency audit results;
- repository vulnerability, secret, and misconfiguration scanning;
- backend and frontend container vulnerability scans;
- SARIF uploads for code-scanning visibility;
- CycloneDX dependency and image SBOM artifacts.

High/critical findings that trip an enforced gate must be investigated. Do not convert an enforcement step to `continue-on-error` merely to make a release green. If a finding is accepted, document the rationale and compensating controls in the release record.

## Model artifacts

Model files are generated release inputs rather than source files. Build the bundle from a documented training input and command. Preserve the generated `metadata.json`, including schema, training configuration, threshold calibration, evaluation values, runtime versions, and artifact hashes.

Runtime hash validation proves consistency with the metadata bundle; it does not establish publisher authenticity. Distribute model artifacts only through a trusted release/artifact channel. Never load model bundles supplied by end users because TensorFlow/joblib deserialization is not a safe untrusted-input boundary.

## Publish sequence

1. Record the current `main` SHA and the release-candidate SHA.
2. Ensure required CI and security workflows succeeded on the exact release candidate.
3. Merge or fast-forward the reviewed candidate according to the repository's branch policy.
4. Re-check the resulting `main` SHA and workflow status.
5. Create the version tag from that verified `main` commit.
6. Attach release notes and any approved binary/model artifacts through the release channel rather than committing generated state to source control.

Do not rewrite a published shared branch as a routine release operation. Prefer a normal corrective commit and follow-up release when a post-publish defect is found.

## Rollback

Keep the pre-release `main` SHA in the release record. For an application defect, revert the offending change or deploy the last known-good release according to the environment's deployment mechanism. For a credential or signing-secret incident, rotate the affected secret independently of source rollback.

Database migrations in this project are forward application migrations. Before a production-like upgrade with important data, take an external backup of the SQLite database and uploaded files. Source rollback alone is not a database recovery strategy.

## Release evidence

Keep the following with the release record when available:

- final `main` and tag SHAs;
- CI/security run identifiers;
- coverage artifact;
- dependency and image SBOMs;
- SARIF/code-scanning status;
- built image digest(s);
- model metadata and artifact digests;
- benchmark environment/results;
- accepted limitations or security exceptions.
