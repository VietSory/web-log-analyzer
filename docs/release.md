# Release and Publishing Runbook

## Release invariants

`main` is the publish target, not the development workspace. Product work is prepared and reviewed on `portfolio-rebuild-workspace`. That branch must never be merged directly into `main` because the final portfolio history is reconstructed from `docs/replay-manifest.json` with planned author and committer dates.

Bookkeeping-only commits that modify the replay manifest or engineering audit notes are workspace metadata. They are explicitly excluded from the replay set and must not recursively list themselves as product commits.

## Pre-release gate

Before creating the dated history:

1. Confirm the workspace branch is based on the recorded original base commit and inspect every commit after that base.
2. Confirm every intended product commit appears exactly once in `docs/replay-manifest.json`, in dependency order, with workspace SHA, commit message, planned Asia/Bangkok author date, planned committer date, rationale, and verification notes.
3. Confirm bookkeeping-only commits are excluded from replay.
4. Run the current backend compile, Ruff, pytest/coverage, dependency-audit, repository scan, container build/scan, and SBOM workflows. Investigate failures rather than bypassing gates.
5. Review generated model policy: generated `.keras`, joblib, threshold, local training data, uploads, SQLite state, caches, and secrets must not be tracked.
6. Review README, architecture, threat model, benchmark methodology, and this runbook against the actual final code.

A green CI run is necessary but not sufficient; the final replayed branch must be tested again after reconstruction.

## Reconstruct the dated branch

Perform the replay in a clean local clone with Git available so author and committer dates can be controlled explicitly.

1. Fetch the repository and verify the expected `main`, workspace HEAD, and recorded base SHA.
2. Create the final dated branch from the original base commit recorded by the manifest, never from the workspace HEAD.
3. For each manifest product entry in order:
   - apply that workspace commit with `git cherry-pick --no-commit <workspace-sha>` or an equivalent patch application;
   - inspect the staged diff and ensure it matches the intended product change;
   - create the commit with the manifest message and user GitHub-linked author identity;
   - set both `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` to the manifest timestamps.
4. Do not replay manifest/audit bookkeeping commits.
5. Do not create empty commits to fill contribution days.

If a patch no longer applies cleanly, stop that replay step and investigate the manifest/product ordering. Do not silently resolve conflicts by accepting whichever side is convenient.

## Verify reconstructed history

Before pushing the dated branch, verify all of the following locally:

```bash
git log --format=fuller --reverse <base>..HEAD
git diff --stat <base>..HEAD
git status --short
```

Then verify:

- every replayed commit has the intended message, author identity, author date, and committer date;
- timestamps are monotonically coherent with the planned development history;
- no bookkeeping-only workspace commits appear;
- the final product tree is equivalent to the workspace product tree, excluding only designated bookkeeping files;
- no generated/runtime artifacts or secrets became tracked during replay;
- compile, lint, backend tests, and relevant security/static checks pass on the dated branch;
- Docker/Compose configuration still validates and images build when Docker is available.

For tree equivalence, compare file lists and content rather than relying only on equal commit counts. Commit SHAs are expected to differ because dates/parents differ.

## Publish sequence

1. Push the dated branch without force.
2. Inspect the branch on GitHub: commit order, contribution attribution, Actions results, file tree, and security scan results.
3. Only after those checks pass, fast-forward `main` to the verified dated branch.
4. Do not force-push `main` unless an exceptional recovery requires it and the repository owner explicitly approves that action.
5. Create a release tag only from the verified `main` commit.

## Model artifacts

Model files are generated release inputs, not source files. A production model bundle must be built from a documented training input and command, preserve its generated `metadata.json`, and be transferred through a controlled release/artifact channel. Runtime loading verifies schema and SHA-256 consistency, but release operators remain responsible for provenance of the bundle itself.

## Rollback

Because `main` is updated only after the dated branch has been independently verified, the previous `main` SHA should be recorded before the final fast-forward. If a post-publish issue is found, prefer a normal corrective commit/release or an explicit branch rollback plan; do not rewrite published history casually.

## Release evidence

Keep the following with the release record when available: final `main` SHA, dated-branch SHA, CI/security run links, coverage artifact, dependency/image SBOMs, SARIF/code-scanning status, container image digest, model metadata digest, benchmark environment/result artifact, and any known limitations accepted for that release.
