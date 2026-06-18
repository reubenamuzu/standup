"""Command-line interface for standup."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__
from .git import GitError, collect_commits
from .report import (
    render_changelog,
    render_json,
    render_markdown_standup,
    render_standup,
)

_FORMATS = ("standup", "markdown", "changelog", "json")


def _supports_color(stream) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="standup",
        description="Generate standup and changelog reports from your git history.",
    )
    parser.add_argument(
        "-C",
        "--repo",
        default=".",
        metavar="PATH",
        help="Path to the git repository (default: current directory).",
    )
    parser.add_argument(
        "-s",
        "--since",
        default="yesterday",
        help="Only include commits more recent than this date "
        '(git --since syntax, e.g. "yesterday", "2 weeks ago"). Default: yesterday.',
    )
    parser.add_argument(
        "-u",
        "--until",
        default=None,
        help="Only include commits older than this date (git --until syntax).",
    )
    parser.add_argument(
        "-a",
        "--author",
        default=None,
        help="Only include commits by authors matching this pattern.",
    )
    parser.add_argument(
        "--me",
        action="store_true",
        help="Shortcut for --author set to your configured git user.email.",
    )
    parser.add_argument(
        "-b",
        "--branch",
        default=None,
        help="Limit to a branch or revision range (e.g. main, v1.0..HEAD).",
    )
    parser.add_argument(
        "-n",
        "--max-count",
        type=int,
        default=None,
        help="Maximum number of commits to include.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=_FORMATS,
        default="standup",
        help="Output format (default: standup).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        default=None,
        help="Write output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--title",
        default="Changelog",
        help="Title for the changelog format.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored terminal output.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _resolve_author(args: argparse.Namespace) -> str | None:
    if args.author:
        return args.author
    if args.me:
        from .git import _run_git  # local import to avoid widening public API

        try:
            email = _run_git(["config", "user.email"], cwd=args.repo).strip()
        except GitError:
            email = ""
        if not email:
            raise GitError("--me requires git user.email to be configured")
        return email
    return None


def render(args: argparse.Namespace, commits) -> str:
    if args.format == "json":
        return render_json(commits)
    if args.format == "markdown":
        return render_markdown_standup(commits)
    if args.format == "changelog":
        return render_changelog(commits, title=args.title)
    color = not args.no_color and (args.output is None and _supports_color(sys.stdout))
    return render_standup(commits, color=color)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        author = _resolve_author(args)
        commits = collect_commits(
            args.repo,
            since=args.since,
            until=args.until,
            author=author,
            branch=args.branch,
            max_count=args.max_count,
        )
    except GitError as exc:
        print(f"standup: error: {exc}", file=sys.stderr)
        return 1

    output = render(args, commits)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(output)
        except OSError as exc:
            print(f"standup: error: could not write {args.output}: {exc}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
