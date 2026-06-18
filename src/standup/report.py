"""Group commits and render standup / changelog reports."""

from __future__ import annotations

import json
import re
from collections import OrderedDict, defaultdict
from datetime import date

from .git import Commit

# Conventional-commit style prefixes -> human readable changelog sections.
_TYPE_SECTIONS: OrderedDict[str, str] = OrderedDict(
    [
        ("feat", "Features"),
        ("fix", "Bug Fixes"),
        ("perf", "Performance"),
        ("refactor", "Refactoring"),
        ("docs", "Documentation"),
        ("test", "Tests"),
        ("build", "Build"),
        ("ci", "CI"),
        ("chore", "Chores"),
        ("style", "Style"),
    ]
)
_OTHER_SECTION = "Other"

_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<desc>.+)$",
    re.IGNORECASE,
)


def commit_type(commit: Commit) -> str:
    """Return the conventional-commit type for a commit, or '' if none."""
    match = _CONVENTIONAL_RE.match(commit.subject)
    if not match:
        return ""
    return match.group("type").lower()


def _section_for(commit: Commit) -> str:
    return _TYPE_SECTIONS.get(commit_type(commit), _OTHER_SECTION)


def group_by_day(commits: list[Commit]) -> OrderedDict[date, list[Commit]]:
    grouped: dict[date, list[Commit]] = defaultdict(list)
    for commit in commits:
        grouped[commit.local_date.date()].append(commit)
    return OrderedDict(sorted(grouped.items(), reverse=True))


def group_by_author(commits: list[Commit]) -> OrderedDict[str, list[Commit]]:
    grouped: dict[str, list[Commit]] = defaultdict(list)
    for commit in commits:
        grouped[commit.author_name].append(commit)
    ordered = sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0].lower()))
    return OrderedDict(ordered)


def group_by_section(commits: list[Commit]) -> OrderedDict[str, list[Commit]]:
    grouped: dict[str, list[Commit]] = defaultdict(list)
    for commit in commits:
        grouped[_section_for(commit)].append(commit)
    section_order = list(_TYPE_SECTIONS.values()) + [_OTHER_SECTION]
    ordered = OrderedDict()
    for name in section_order:
        if name in grouped:
            ordered[name] = grouped[name]
    return ordered


def summary_stats(commits: list[Commit]) -> dict[str, int]:
    return {
        "commits": len(commits),
        "authors": len({c.author_email for c in commits}),
        "files_changed": sum(c.files_changed for c in commits),
        "insertions": sum(c.insertions for c in commits),
        "deletions": sum(c.deletions for c in commits),
    }


# --- Renderers ---------------------------------------------------------------


def _clean_desc(commit: Commit) -> str:
    match = _CONVENTIONAL_RE.match(commit.subject)
    if match:
        scope = match.group("scope")
        desc = match.group("desc").strip()
        return f"**{scope}:** {desc}" if scope else desc
    return commit.subject


def render_standup(commits: list[Commit], *, color: bool = True) -> str:
    if not commits:
        return "No commits found for the given filters."

    use_color = color
    bold = "\033[1m" if use_color else ""
    dim = "\033[2m" if use_color else ""
    cyan = "\033[36m" if use_color else ""
    reset = "\033[0m" if use_color else ""

    lines: list[str] = []
    stats = summary_stats(commits)
    lines.append(
        f"{bold}Standup report{reset} "
        f"{dim}({stats['commits']} commits, {stats['authors']} author(s), "
        f"+{stats['insertions']}/-{stats['deletions']}){reset}"
    )
    lines.append("")

    for day, day_commits in group_by_day(commits).items():
        lines.append(f"{bold}{day:%A, %b %d %Y}{reset} {dim}({len(day_commits)}){reset}")
        for author, ac in group_by_author(day_commits).items():
            lines.append(f"  {cyan}{author}{reset}")
            for commit in ac:
                lines.append(f"    - {commit.subject} {dim}{commit.short_sha}{reset}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_changelog(commits: list[Commit], *, title: str = "Changelog") -> str:
    lines = [f"# {title}", ""]
    if not commits:
        lines.append("_No commits found for the given filters._")
        return "\n".join(lines) + "\n"

    for section, section_commits in group_by_section(commits).items():
        lines.append(f"## {section}")
        lines.append("")
        for commit in section_commits:
            lines.append(f"- {_clean_desc(commit)} (`{commit.short_sha}`)")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_markdown_standup(commits: list[Commit]) -> str:
    lines = ["# Standup", ""]
    if not commits:
        lines.append("_No commits found for the given filters._")
        return "\n".join(lines) + "\n"

    for day, day_commits in group_by_day(commits).items():
        lines.append(f"## {day:%A, %b %d %Y}")
        lines.append("")
        for author, ac in group_by_author(day_commits).items():
            lines.append(f"### {author}")
            for commit in ac:
                lines.append(f"- {commit.subject} (`{commit.short_sha}`)")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json(commits: list[Commit]) -> str:
    payload = {
        "summary": summary_stats(commits),
        "commits": [
            {
                "sha": c.sha,
                "short_sha": c.short_sha,
                "author_name": c.author_name,
                "author_email": c.author_email,
                "date": c.date.isoformat(),
                "subject": c.subject,
                "body": c.body,
                "type": commit_type(c),
                "files_changed": c.files_changed,
                "insertions": c.insertions,
                "deletions": c.deletions,
                "files": c.files,
            }
            for c in commits
        ],
    }
    return json.dumps(payload, indent=2) + "\n"
