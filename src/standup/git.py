"""Thin wrapper around `git log` for collecting commit data."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone


class GitError(RuntimeError):
    """Raised when a git command fails or the path is not a repository."""


# Unique separators that are extremely unlikely to appear in commit metadata.
_FIELD_SEP = "\x1f"  # unit separator
_RECORD_SEP = "\x1e"  # record separator

# Each record begins with a record separator and ends every field (including the
# body) with a field separator, so the trailing numstat block is cleanly
# separated from the body even when the body spans multiple lines.
_PRETTY_FORMAT = _RECORD_SEP + _FIELD_SEP.join(
    ["%H", "%h", "%an", "%ae", "%aI", "%s", "%b"]
) + _FIELD_SEP


@dataclass
class Commit:
    """A single git commit."""

    sha: str
    short_sha: str
    author_name: str
    author_email: str
    date: datetime
    subject: str
    body: str = ""
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    files: list[str] = field(default_factory=list)

    @property
    def local_date(self) -> datetime:
        """Author date converted to the local timezone."""
        return self.date.astimezone()


def _run_git(args: list[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:  # git not installed
        raise GitError("git executable not found on PATH") from exc

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown git error"
        raise GitError(stderr)
    return result.stdout


def is_git_repo(path: str) -> bool:
    try:
        out = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    except GitError:
        return False
    return out.strip() == "true"


def _parse_iso(value: str) -> datetime:
    value = value.strip()
    # Python < 3.11's fromisoformat rejects the trailing 'Z' that newer git emits.
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_log(raw: str) -> list[Commit]:
    """Parse the raw output of `git log` using our custom pretty format."""
    commits: list[Commit] = []
    records = [r for r in raw.split(_RECORD_SEP) if r.strip()]
    for record in records:
        fields = record.split(_FIELD_SEP)
        if len(fields) < 6:
            continue
        sha, short_sha, name, email, date_str, subject = fields[:6]
        body = fields[6] if len(fields) > 6 else ""
        stat_block = fields[7] if len(fields) > 7 else ""

        commit = Commit(
            sha=sha,
            short_sha=short_sha,
            author_name=name,
            author_email=email,
            date=_parse_iso(date_str),
            subject=subject.strip(),
            body=body.strip(),
        )
        _apply_numstat(commit, stat_block)
        commits.append(commit)
    return commits


def _apply_numstat(commit: Commit, stat_block: str) -> None:
    for line in stat_block.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        commit.files.append(path)
        commit.files_changed += 1
        if added.isdigit():
            commit.insertions += int(added)
        if removed.isdigit():
            commit.deletions += int(removed)


def collect_commits(
    path: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
    branch: str | None = None,
    max_count: int | None = None,
) -> list[Commit]:
    """Collect commits from the repo at ``path`` matching the given filters."""
    if not is_git_repo(path):
        raise GitError(f"{path!r} is not a git repository")

    args = ["log", f"--pretty=format:{_PRETTY_FORMAT}", "--numstat", "--no-color"]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")
    if author:
        args.append(f"--author={author}")
    if max_count:
        args.append(f"--max-count={max_count}")
    if branch:
        args.append(branch)

    raw = _run_git(args, cwd=path)
    return parse_log(raw)
