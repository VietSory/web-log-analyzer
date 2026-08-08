#!/usr/bin/env python3
"""Rebuild the dated portfolio history with an irregular, human-looking schedule.

Workspace-only helper. It never pushes and never updates main.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys

EXPECTED_REPOSITORY = "VietSory/web-log-analyzer"
BASE_COMMIT = "8b0e3c6b9dfe1c0e6f7f41cc6c2d98683ad06e2c"
PRODUCT_WORKSPACE_HEAD = "293a8f31bb733cc721e51ab96de2e349c85de4c9"
EXPECTED_CURRENT_MAIN = "7591074f2e1bdebe02f340f9effd6099740631a3"
FINAL_BRANCH = "portfolio-rebuild-dated-v2"
AUTHOR_NAME = "Vietsory"
AUTHOR_EMAIL = "121284939+VietSory@users.noreply.github.com"
TIMEZONE = "+07:00"

DATES = (
    "2026-01-06T19:37:00+07:00",
    "2026-01-08T18:31:00+07:00",
    "2026-01-12T18:49:00+07:00",
    "2026-01-13T19:08:00+07:00",
    "2026-01-13T22:23:00+07:00",
    "2026-01-16T18:49:00+07:00",
    "2026-01-21T20:18:00+07:00",
    "2026-01-25T20:43:00+07:00",
    "2026-01-27T20:18:00+07:00",
    "2026-01-30T22:24:00+07:00",
    "2026-02-02T18:54:00+07:00",
    "2026-02-04T21:54:00+07:00",
    "2026-02-05T18:26:00+07:00",
    "2026-02-05T21:23:00+07:00",
    "2026-02-10T20:43:00+07:00",
    "2026-02-13T21:49:00+07:00",
    "2026-02-16T19:13:00+07:00",
    "2026-02-19T18:08:00+07:00",
    "2026-02-19T21:14:00+07:00",
    "2026-02-22T11:07:00+07:00",
    "2026-02-25T19:07:00+07:00",
    "2026-02-27T22:07:00+07:00",
    "2026-03-03T18:37:00+07:00",
    "2026-03-04T18:54:00+07:00",
    "2026-03-07T20:31:00+07:00",
    "2026-03-09T18:13:00+07:00",
    "2026-03-12T19:13:00+07:00",
    "2026-03-15T21:24:00+07:00",
    "2026-03-17T22:13:00+07:00",
    "2026-03-23T20:43:00+07:00",
    "2026-03-24T18:08:00+07:00",
    "2026-03-24T21:32:00+07:00",
    "2026-03-27T20:37:00+07:00",
    "2026-03-28T15:43:00+07:00",
    "2026-04-01T19:54:00+07:00",
    "2026-04-05T17:07:00+07:00",
    "2026-04-07T22:13:00+07:00",
    "2026-04-10T19:18:00+07:00",
    "2026-04-13T18:37:00+07:00",
    "2026-04-15T18:34:00+07:00",
    "2026-04-15T22:23:00+07:00",
    "2026-04-18T21:31:00+07:00",
    "2026-04-21T19:24:00+07:00",
    "2026-04-24T19:31:00+07:00",
    "2026-04-27T18:49:00+07:00",
    "2026-04-30T21:49:00+07:00",
    "2026-05-02T17:43:00+07:00",
    "2026-05-05T20:07:00+07:00",
    "2026-05-06T19:52:00+07:00",
    "2026-05-06T21:23:00+07:00",
    "2026-05-10T19:31:00+07:00",
    "2026-05-12T22:43:00+07:00",
    "2026-05-14T19:43:00+07:00",
    "2026-05-17T21:24:00+07:00",
    "2026-05-18T19:17:00+07:00",
    "2026-05-18T22:14:00+07:00",
    "2026-05-23T17:13:00+07:00",
    "2026-05-26T18:54:00+07:00",
    "2026-05-29T20:43:00+07:00",
    "2026-06-01T19:13:00+07:00",
    "2026-06-03T21:49:00+07:00",
    "2026-06-05T20:49:00+07:00",
)

HTTPS_RE = re.compile(r"^https://github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?/?$")
SSH_RE = re.compile(r"^git@github\.com:(?P<repo>[^/]+/[^/]+?)(?:\.git)?$")


class ReplayError(RuntimeError):
    pass


def run(*args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    if check and cp.returncode != 0:
        details = cp.stderr.strip() or cp.stdout.strip()
        raise ReplayError(f"git {' '.join(args)} failed: {details}")
    return cp


def out(*args: str) -> str:
    return run(*args).stdout.strip()


def require_clean_repo() -> Path:
    root = Path(out("rev-parse", "--show-toplevel")).resolve()
    if out("status", "--porcelain"):
        raise ReplayError("working tree must be clean")
    return root


def require_expected_remote() -> None:
    url = out("remote", "get-url", "origin").strip()
    match = HTTPS_RE.fullmatch(url) or SSH_RE.fullmatch(url)
    if not match or match.group("repo") != EXPECTED_REPOSITORY:
        raise ReplayError(f"origin points to {url!r}, expected {EXPECTED_REPOSITORY}")


def load_entries(repo: Path) -> list[dict[str, object]]:
    path = repo / "docs" / "replay-manifest.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("base_commit") != BASE_COMMIT:
        raise ReplayError("manifest base commit changed")
    if raw.get("author", {}).get("email") != AUTHOR_EMAIL:
        raise ReplayError("manifest author email changed")
    entries = raw.get("entries")
    if not isinstance(entries, list) or len(entries) != len(DATES):
        raise ReplayError(f"expected {len(DATES)} manifest entries")
    return entries


def validate_schedule() -> None:
    previous: datetime | None = None
    active_days: set[str] = set()
    day_counts: dict[str, int] = {}
    for value in DATES:
        parsed = datetime.fromisoformat(value)
        if parsed.strftime("%z") != TIMEZONE.replace(":", ""):
            raise ReplayError(f"wrong timezone: {value}")
        if previous is not None and parsed <= previous:
            raise ReplayError(f"schedule not strictly increasing: {value}")
        previous = parsed
        day = value[:10]
        active_days.add(day)
        day_counts[day] = day_counts.get(day, 0) + 1

    if len(active_days) != 55:
        raise ReplayError(f"expected 55 active days, got {len(active_days)}")
    if sorted(day_counts.values()).count(2) != 7 or max(day_counts.values()) != 2:
        raise ReplayError("expected exactly seven two-commit days and no heavier day")


def verify_workspace_history(entries: list[dict[str, object]]) -> None:
    history = out(
        "rev-list",
        "--reverse",
        "--first-parent",
        f"{BASE_COMMIT}..{PRODUCT_WORKSPACE_HEAD}",
    ).splitlines()
    positions = {sha: index for index, sha in enumerate(history)}

    previous_position = -1
    for index, entry in enumerate(entries, start=1):
        sha = str(entry.get("workspace_sha", ""))
        message = str(entry.get("message", ""))
        if sha not in positions:
            raise ReplayError(f"entry {index} is not on workspace first-parent history: {sha}")
        if positions[sha] <= previous_position:
            raise ReplayError(f"entry {index} is out of workspace order")
        previous_position = positions[sha]
        actual_message = out("show", "-s", "--format=%s", sha)
        if actual_message != message:
            raise ReplayError(
                f"entry {index} message mismatch: manifest={message!r} git={actual_message!r}"
            )

    if str(entries[-1].get("workspace_sha")) != PRODUCT_WORKSPACE_HEAD:
        raise ReplayError("final manifest product commit is not the frozen workspace product head")


def verify_remote_state() -> None:
    run("fetch", "--prune", "origin")
    remote_main = out("rev-parse", "refs/remotes/origin/main")
    if remote_main != EXPECTED_CURRENT_MAIN:
        raise ReplayError(
            f"origin/main moved to {remote_main}; expected {EXPECTED_CURRENT_MAIN}. "
            "Do not rewrite main until the divergence is reviewed."
        )
    backup = run(
        "rev-parse",
        "--verify",
        "refs/remotes/origin/backup/main-before-date-fix",
        check=False,
    )
    if backup.returncode == 0 and backup.stdout.strip() != EXPECTED_CURRENT_MAIN:
        raise ReplayError("remote date-fix backup does not point to the current published main")


def verify_final(entries: list[dict[str, object]]) -> None:
    lines = out(
        "log",
        "--reverse",
        "--format=%H%x09%an%x09%ae%x09%aI%x09%cn%x09%ce%x09%cI%x09%s",
        f"{BASE_COMMIT}..{FINAL_BRANCH}",
    ).splitlines()
    if len(lines) != len(entries):
        raise ReplayError(f"final branch has {len(lines)} commits, expected {len(entries)}")

    for index, (line, entry, expected_date) in enumerate(zip(lines, entries, DATES), start=1):
        parts = line.split("\t", 7)
        if len(parts) != 8:
            raise ReplayError(f"cannot parse final commit {index}")
        _, an, ae, ad, cn, ce, cd, subject = parts
        expected = (
            AUTHOR_NAME,
            AUTHOR_EMAIL,
            expected_date,
            AUTHOR_NAME,
            AUTHOR_EMAIL,
            expected_date,
            str(entry["message"]),
        )
        actual = (an, ae, ad, cn, ce, cd, subject)
        if actual != expected:
            raise ReplayError(f"metadata mismatch at final commit {index}")

    tree_diff = run(
        "diff",
        "--quiet",
        FINAL_BRANCH,
        PRODUCT_WORKSPACE_HEAD,
        "--",
        ".",
        ":(exclude)docs/replay-manifest.json",
        check=False,
    )
    if tree_diff.returncode == 1:
        details = out(
            "diff",
            "--name-status",
            FINAL_BRANCH,
            PRODUCT_WORKSPACE_HEAD,
            "--",
            ".",
            ":(exclude)docs/replay-manifest.json",
        )
        raise ReplayError("final product tree differs from workspace:\n" + details)
    if tree_diff.returncode not in (0, 1):
        raise ReplayError("tree-equivalence check failed")


def main() -> int:
    repo = require_clean_repo()
    require_expected_remote()
    validate_schedule()
    entries = load_entries(repo)
    verify_workspace_history(entries)
    verify_remote_state()

    existing = run("show-ref", "--verify", f"refs/heads/{FINAL_BRANCH}", check=False)
    if existing.returncode == 0:
        raise ReplayError(
            f"local branch {FINAL_BRANCH!r} already exists; delete it only after reviewing it"
        )

    run("switch", "--create", FINAL_BRANCH, BASE_COMMIT)

    try:
        for index, (entry, date) in enumerate(zip(entries, DATES), start=1):
            sha = str(entry["workspace_sha"])
            message = str(entry["message"])
            print(f"[{index:02d}/{len(entries):02d}] {date} {message}")
            run("cherry-pick", "--no-commit", sha)

            staged = run("diff", "--cached", "--quiet", check=False)
            if staged.returncode == 0:
                raise ReplayError(f"entry {index} produced an empty diff")
            if staged.returncode != 1:
                raise ReplayError(f"could not inspect staged diff for entry {index}")

            env = os.environ.copy()
            env.update(
                {
                    "GIT_AUTHOR_NAME": AUTHOR_NAME,
                    "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
                    "GIT_AUTHOR_DATE": date,
                    "GIT_COMMITTER_NAME": AUTHOR_NAME,
                    "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
                    "GIT_COMMITTER_DATE": date,
                }
            )
            run("commit", "--no-gpg-sign", "--message", message, env=env)
    except Exception:
        run("cherry-pick", "--abort", check=False)
        raise

    verify_final(entries)
    print(
        f"OK: {FINAL_BRANCH} rebuilt with 62 commits across 55 active days; "
        "7 days contain two coherent commits.\n"
        "No push was performed. main was not modified."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReplayError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
