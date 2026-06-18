import json
from datetime import datetime, timezone

from standup.git import Commit
from standup.report import (
    commit_type,
    group_by_author,
    group_by_day,
    group_by_section,
    render_changelog,
    render_json,
    render_standup,
    summary_stats,
)


def _commit(subject, name="Ada", email=None, day=18, ins=1, dele=0):
    if email is None:
        email = f"{name.lower()}@x.com"
    return Commit(
        sha="0" * 40,
        short_sha="0000000",
        author_name=name,
        author_email=email,
        date=datetime(2026, 6, day, 12, 0, tzinfo=timezone.utc),
        subject=subject,
        insertions=ins,
        deletions=dele,
        files_changed=1,
    )


def test_commit_type_detection():
    assert commit_type(_commit("feat: x")) == "feat"
    assert commit_type(_commit("fix(api): y")) == "fix"
    assert commit_type(_commit("just a message")) == ""


def test_group_by_day_sorted_desc():
    commits = [_commit("a", day=16), _commit("b", day=18), _commit("c", day=17)]
    days = list(group_by_day(commits).keys())
    assert days == sorted(days, reverse=True)


def test_group_by_author_orders_by_count():
    commits = [
        _commit("a", name="Ada"),
        _commit("b", name="Bob"),
        _commit("c", name="Bob"),
    ]
    authors = list(group_by_author(commits).keys())
    assert authors[0] == "Bob"


def test_group_by_section():
    commits = [_commit("feat: a"), _commit("fix: b"), _commit("random thing")]
    sections = group_by_section(commits)
    assert "Features" in sections
    assert "Bug Fixes" in sections
    assert "Other" in sections


def test_summary_stats():
    commits = [_commit("a", ins=5, dele=2), _commit("b", name="Bob", ins=1, dele=1)]
    stats = summary_stats(commits)
    assert stats["commits"] == 2
    assert stats["authors"] == 2
    assert stats["insertions"] == 6
    assert stats["deletions"] == 3


def test_render_standup_plain_contains_subject():
    out = render_standup([_commit("feat: add thing")], color=False)
    assert "feat: add thing" in out
    assert "\033[" not in out  # no ansi codes when color disabled


def test_render_standup_empty():
    assert "No commits" in render_standup([])


def test_render_changelog_sections_and_scope():
    out = render_changelog([_commit("feat(api): add endpoint"), _commit("fix: crash")])
    assert "## Features" in out
    assert "## Bug Fixes" in out
    assert "**api:** add endpoint" in out


def test_render_json_roundtrip():
    out = render_json([_commit("feat: a", ins=3, dele=1)])
    data = json.loads(out)
    assert data["summary"]["commits"] == 1
    assert data["commits"][0]["type"] == "feat"
    assert data["commits"][0]["insertions"] == 3
