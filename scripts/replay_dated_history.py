#!/usr/bin/env python3
"""Validate and reconstruct the portfolio's dated Git history.

This tool never pushes and never updates ``main``. By default it only validates
``docs/replay-manifest.json`` against the local Git history. Pass ``--execute``
from a clean local clone to create the dated branch and replay product commits.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable
from urllib.parse import urlparse


EXPECTED_REPOSITORY = "VietSory/web-log-analyzer"
BOOKKEEPING_ONLY_PATHS = {
    "docs/replay-manifest.json",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
GITHUB_HTTPS_RE = re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$")
GITHUB_SSH_RE = re.compile(r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$")


class ReplayError(RuntimeError):
    """Raised when a replay invariant is violated."""


@dataclass(frozen=True)
class Entry:
    workspace_sha: str
    message: str
    author_date: str
    committer_date: str
    rationale: str
    verification: tuple[str, ...]


@dataclass(frozen=True)
class Manifest:
    base_commit: str
    workspace_branch: str
    final_branch: str
    timezone: str
    author_name: str
    author_email: str
    excluded_workspace_commits: frozenset[str]
    entries: tuple[Entry, ...]


def git(
    *args: str,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = ["git", *args]
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip()
        raise ReplayError(f"{' '.join(command)} failed: {details}")
    return completed


def git_output(*args: str, cwd: Path) -> str:
    return git(*args, cwd=cwd).stdout.strip()


def load_manifest(path: Path) -> Manifest:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayError(f"Cannot read manifest {path}: {exc}") from exc

    if raw.get("version") != 2:
        raise ReplayError("Manifest version must be 2")

    author = raw.get("author")
    if not isinstance(author, dict):
        raise ReplayError("Manifest author must be an object")

    excluded = raw.get("excluded_workspace_commits", [])
    if not isinstance(excluded, list):
        raise ReplayError("excluded_workspace_commits must be a list")

    entries_raw = raw.get("entries")
    if not isinstance(entries_raw, list) or not entries_raw:
        raise ReplayError("Manifest entries must be a non-empty list")

    entries: list[Entry] = []
    for index, item in enumerate(entries_raw, start=1):
        if not isinstance(item, dict):
            raise ReplayError(f"Entry {index} must be an object")
        verification = item.get("verification")
        if not isinstance(verification, list) or not all(
            isinstance(value, str) and value.strip() for value in verification
        ):
            raise ReplayError(f"Entry {index} verification must be non-empty strings")
        try:
            entry = Entry(
                workspace_sha=str(item["workspace_sha"]),
                message=str(item["message"]),
                author_date=str(item["author_date"]),
                committer_date=str(item["committer_date"]),
                rationale=str(item["rationale"]),
                verification=tuple(verification),
            )
        except KeyError as exc:
            raise ReplayError(f"Entry {index} is missing {exc.args[0]}") from exc
        entries.append(entry)

    excluded_shas: set[str] = set()
    for item in excluded:
        if not isinstance(item, dict) or "workspace_sha" not in item:
            raise ReplayError("Each excluded workspace commit must contain workspace_sha")
        excluded_shas.add(str(item["workspace_sha"]))

    manifest = Manifest(
        base_commit=str(raw.get("base_commit", "")),
        workspace_branch=str(raw.get("workspace_branch", "")),
        final_branch=str(raw.get("final_branch", "")),
        timezone=str(raw.get("timezone", "")),
        author_name=str(author.get("name", "")),
        author_email=str(author.get("email", "")),
        excluded_workspace_commits=frozenset(excluded_shas),
        entries=tuple(entries),
    )
    validate_manifest_shape(manifest)
    return manifest


def parse_iso_date(value: str, *, expected_timezone: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ReplayError(f"Invalid ISO-8601 date: {value}") from exc
    if parsed.tzinfo is None:
        raise ReplayError(f"Date must include an explicit timezone: {value}")
    rendered_offset = parsed.strftime("%z")
    normalized_expected = expected_timezone.replace(":", "")
    if rendered_offset != normalized_expected:
        raise ReplayError(
            f"Date {value} does not use manifest timezone {expected_timezone}"
        )
    return parsed


def validate_manifest_shape(manifest: Manifest) -> None:
    if not SHA_RE.fullmatch(manifest.base_commit):
        raise ReplayError("base_commit must be a full 40-character SHA")
    if not manifest.workspace_branch or not manifest.final_branch:
        raise ReplayError("workspace_branch and final_branch are required")
    if manifest.workspace_branch == manifest.final_branch:
        raise ReplayError("workspace and final branches must differ")
    if manifest.final_branch == "main":
        raise ReplayError("The replay tool refuses to target main")
    if not manifest.author_name.strip() or "@" not in manifest.author_email:
        raise ReplayError("A valid author name and email are required")
    if not re.fullmatch(r"[+-]\d{2}:\d{2}", manifest.timezone):
        raise ReplayError("timezone must look like +07:00")

    seen_shas: set[str] = set()
    previous_date: datetime | None = None
    for index, entry in enumerate(manifest.entries, start=1):
        if not SHA_RE.fullmatch(entry.workspace_sha):
            raise ReplayError(f"Entry {index} has an invalid workspace SHA")
        if entry.workspace_sha in seen_shas:
            raise ReplayError(f"Duplicate workspace SHA: {entry.workspace_sha}")
        if entry.workspace_sha in manifest.excluded_workspace_commits:
            raise ReplayError(
                f"Commit is both replayed and excluded: {entry.workspace_sha}"
            )
        if not entry.message.strip() or "\n" in entry.message:
            raise ReplayError(f"Entry {index} must use a one-line commit message")
        if not entry.rationale.strip():
            raise ReplayError(f"Entry {index} requires a rationale")

        author_date = parse_iso_date(
            entry.author_date,
            expected_timezone=manifest.timezone,
        )
        committer_date = parse_iso_date(
            entry.committer_date,
            expected_timezone=manifest.timezone,
        )
        if author_date != committer_date:
            raise ReplayError(
                f"Entry {index} author and committer dates must match"
            )
        if previous_date is not None and author_date <= previous_date:
            raise ReplayError(
                f"Entry {index} date is not strictly later than the previous entry"
            )
        previous_date = author_date
        seen_shas.add(entry.workspace_sha)


def normalize_github_remote(url: str) -> str | None:
    for pattern in (GITHUB_HTTPS_RE, GITHUB_SSH_RE):
        match = pattern.fullmatch(url.strip())
        if match:
            return match.group("repo")
    parsed = urlparse(url)
    if parsed.scheme == "ssh" and parsed.hostname == "github.com":
        return parsed.path.strip("/").removesuffix(".git")
    return None


def changed_paths(commit: str, *, cwd: Path) -> set[str]:
    output = git_output(
        "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        commit,
        cwd=cwd,
    )
    return {line for line in output.splitlines() if line}


def is_bookkeeping_commit(
    commit: str,
    *,
    cwd: Path,
    manifest: Manifest,
) -> bool:
    if commit in manifest.excluded_workspace_commits:
        return True
    paths = changed_paths(commit, cwd=cwd)
    return bool(paths) and paths.issubset(BOOKKEEPING_ONLY_PATHS)


def require_clean_worktree(repo: Path) -> None:
    status = git_output("status", "--porcelain", cwd=repo)
    if status:
        raise ReplayError("Working tree must be clean before validation or replay")


def require_expected_remote(repo: Path, remote: str) -> None:
    remote_url = git_output("remote", "get-url", remote, cwd=repo)
    repository = normalize_github_remote(remote_url)
    if repository != EXPECTED_REPOSITORY:
        raise ReplayError(
            f"{remote} points to {remote_url!r}, expected {EXPECTED_REPOSITORY}"
        )


def resolve_workspace_ref(
    repo: Path,
    *,
    manifest: Manifest,
    remote: str,
    override: str | None,
) -> str:
    candidates = [
        override,
        f"refs/remotes/{remote}/{manifest.workspace_branch}",
        f"{remote}/{manifest.workspace_branch}",
        manifest.workspace_branch,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        result = git("rev-parse", "--verify", candidate, cwd=repo, check=False)
        if result.returncode == 0:
            return candidate
    raise ReplayError(
        f"Cannot resolve workspace branch {manifest.workspace_branch!r}"
    )


def verify_manifest_against_git(
    repo: Path,
    *,
    manifest: Manifest,
    workspace_ref: str,
) -> list[str]:
    git("cat-file", "-e", f"{manifest.base_commit}^{{commit}}", cwd=repo)
    workspace_sha = git_output("rev-parse", workspace_ref, cwd=repo)

    ancestor = git(
        "merge-base",
        "--is-ancestor",
        manifest.base_commit,
        workspace_sha,
        cwd=repo,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ReplayError("Recorded base commit is not an ancestor of workspace")

    history = git_output(
        "rev-list",
        "--reverse",
        "--first-parent",
        f"{manifest.base_commit}..{workspace_sha}",
        cwd=repo,
    ).splitlines()

    history_set = set(history)
    replay_set = {entry.workspace_sha for entry in manifest.entries}

    for index, entry in enumerate(manifest.entries, start=1):
        if entry.workspace_sha not in history_set:
            raise ReplayError(
                f"Entry {index} SHA is not on workspace first-parent history: "
                f"{entry.workspace_sha}"
            )
        actual_message = git_output(
            "show",
            "-s",
            "--format=%s",
            entry.workspace_sha,
            cwd=repo,
        )
        if actual_message != entry.message:
            raise ReplayError(
                f"Entry {index} message mismatch for {entry.workspace_sha}: "
                f"manifest={entry.message!r}, git={actual_message!r}"
            )

    uncovered: list[str] = []
    for commit in history:
        if commit in replay_set:
            continue
        if is_bookkeeping_commit(commit, cwd=repo, manifest=manifest):
            continue
        message = git_output("show", "-s", "--format=%s", commit, cwd=repo)
        paths = ", ".join(sorted(changed_paths(commit, cwd=repo)))
        uncovered.append(f"{commit} {message} [{paths}]")

    if uncovered:
        raise ReplayError(
            "Workspace contains non-bookkeeping commits missing from manifest:\n  "
            + "\n  ".join(uncovered)
        )

    return history


def validate_remote_main_is_base(
    repo: Path,
    *,
    manifest: Manifest,
    remote: str,
) -> None:
    main_ref = f"refs/remotes/{remote}/main"
    result = git("rev-parse", "--verify", main_ref, cwd=repo, check=False)
    if result.returncode != 0:
        raise ReplayError(f"Cannot resolve {remote}/main")
    remote_main = result.stdout.strip()
    if remote_main != manifest.base_commit:
        raise ReplayError(
            f"{remote}/main moved to {remote_main}; expected {manifest.base_commit}. "
            "Do not replay until the divergence is reviewed."
        )


def verify_replayed_history(
    repo: Path,
    *,
    manifest: Manifest,
    final_branch: str,
) -> None:
    lines = git_output(
        "log",
        "--reverse",
        "--format=%H%x09%an%x09%ae%x09%aI%x09%cn%x09%ce%x09%cI%x09%s",
        f"{manifest.base_commit}..{final_branch}",
        cwd=repo,
    ).splitlines()
    if len(lines) != len(manifest.entries):
        raise ReplayError(
            f"Replayed history has {len(lines)} commits; "
            f"manifest has {len(manifest.entries)}"
        )

    for index, (line, entry) in enumerate(zip(lines, manifest.entries), start=1):
        parts = line.split("\t", 7)
        if len(parts) != 8:
            raise ReplayError(f"Could not parse replayed commit {index}")
        (
            _,
            author_name,
            author_email,
            author_date,
            committer_name,
            committer_email,
            committer_date,
            message,
        ) = parts
        expected = (
            manifest.author_name,
            manifest.author_email,
            entry.author_date,
            manifest.author_name,
            manifest.author_email,
            entry.committer_date,
            entry.message,
        )
        actual = (
            author_name,
            author_email,
            author_date,
            committer_name,
            committer_email,
            committer_date,
            message,
        )
        if actual != expected:
            raise ReplayError(
                f"Replayed commit {index} metadata mismatch:\n"
                f"  expected={expected!r}\n"
                f"  actual={actual!r}"
            )


def verify_product_tree_equivalence(
    repo: Path,
    *,
    workspace_ref: str,
    final_branch: str,
) -> None:
    result = git(
        "diff",
        "--quiet",
        final_branch,
        workspace_ref,
        "--",
        ".",
        ":(exclude)docs/replay-manifest.json",
        cwd=repo,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise ReplayError("Tree-equivalence comparison failed")
    if result.returncode == 1:
        details = git_output(
            "diff",
            "--name-status",
            final_branch,
            workspace_ref,
            "--",
            ".",
            ":(exclude)docs/replay-manifest.json",
            cwd=repo,
        )
        raise ReplayError(
            "Final branch does not match workspace product tree:\n" + details
        )


def create_dated_history(
    repo: Path,
    *,
    manifest: Manifest,
    workspace_ref: str,
    final_branch: str,
) -> None:
    if final_branch in {"main", manifest.workspace_branch}:
        raise ReplayError(f"Refusing unsafe final branch name: {final_branch}")

    existing = git(
        "show-ref",
        "--verify",
        f"refs/heads/{final_branch}",
        cwd=repo,
        check=False,
    )
    if existing.returncode == 0:
        raise ReplayError(
            f"Local branch {final_branch!r} already exists; remove or rename it manually"
        )

    git("switch", "--create", final_branch, manifest.base_commit, cwd=repo)

    try:
        for index, entry in enumerate(manifest.entries, start=1):
            print(
                f"[{index:02d}/{len(manifest.entries):02d}] "
                f"{entry.author_date} {entry.message}"
            )
            git("cherry-pick", "--no-commit", entry.workspace_sha, cwd=repo)

            staged = git("diff", "--cached", "--quiet", cwd=repo, check=False)
            if staged.returncode == 0:
                raise ReplayError(
                    f"Entry {index} produced an empty diff: {entry.workspace_sha}"
                )
            if staged.returncode not in (0, 1):
                raise ReplayError(
                    f"Could not inspect staged diff for {entry.workspace_sha}"
                )

            env = os.environ.copy()
            env.update(
                {
                    "GIT_AUTHOR_NAME": manifest.author_name,
                    "GIT_AUTHOR_EMAIL": manifest.author_email,
                    "GIT_AUTHOR_DATE": entry.author_date,
                    "GIT_COMMITTER_NAME": manifest.author_name,
                    "GIT_COMMITTER_EMAIL": manifest.author_email,
                    "GIT_COMMITTER_DATE": entry.committer_date,
                }
            )
            git(
                "commit",
                "--no-gpg-sign",
                "--message",
                entry.message,
                cwd=repo,
                env=env,
            )
    except Exception:
        git("cherry-pick", "--abort", cwd=repo, check=False)
        raise

    verify_replayed_history(
        repo,
        manifest=manifest,
        final_branch=final_branch,
    )
    verify_product_tree_equivalence(
        repo,
        workspace_ref=workspace_ref,
        final_branch=final_branch,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate or reconstruct the dated portfolio history."
    )
    parser.add_argument(
        "--manifest",
        default="docs/replay-manifest.json",
        help="Manifest path relative to the repository root.",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="Git remote expected to point at VietSory/web-log-analyzer.",
    )
    parser.add_argument(
        "--workspace-ref",
        help="Override the workspace ref used for validation.",
    )
    parser.add_argument(
        "--final-branch",
        help="Override the final branch name from the manifest.",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Do not fetch the configured remote before validation.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Create the dated branch. Without this flag the tool is read-only.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(
        git_output("rev-parse", "--show-toplevel", cwd=Path.cwd())
    ).resolve()
    manifest_path = (repo / args.manifest).resolve()
    try:
        manifest_path.relative_to(repo)
    except ValueError as exc:
        raise ReplayError("Manifest path must stay inside the repository") from exc

    manifest = load_manifest(manifest_path)
    require_clean_worktree(repo)
    require_expected_remote(repo, args.remote)

    if not args.skip_fetch:
        git("fetch", "--prune", args.remote, cwd=repo)

    workspace_ref = resolve_workspace_ref(
        repo,
        manifest=manifest,
        remote=args.remote,
        override=args.workspace_ref,
    )
    history = verify_manifest_against_git(
        repo,
        manifest=manifest,
        workspace_ref=workspace_ref,
    )

    final_branch = args.final_branch or manifest.final_branch
    if final_branch == "main":
        raise ReplayError("The replay tool refuses to target main")

    print(
        f"Manifest OK: {len(manifest.entries)} replay commits, "
        f"{len(history)} workspace commits after base."
    )
    print(
        f"Base: {manifest.base_commit}\n"
        f"Workspace: {git_output('rev-parse', workspace_ref, cwd=repo)}\n"
        f"Author: {manifest.author_name} <{manifest.author_email}>"
    )

    if not args.execute:
        print("Validation only; no branch or commit was created.")
        return 0

    validate_remote_main_is_base(
        repo,
        manifest=manifest,
        remote=args.remote,
    )
    create_dated_history(
        repo,
        manifest=manifest,
        workspace_ref=workspace_ref,
        final_branch=final_branch,
    )
    print(
        f"Dated branch {final_branch!r} created and verified locally.\n"
        "No push was performed and main was not modified.\n"
        f"Review with: git log --format=fuller --reverse "
        f"{manifest.base_commit}..{final_branch}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReplayError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
