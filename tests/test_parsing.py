from datetime import datetime, timezone

from standup.git import _FIELD_SEP as FS
from standup.git import _RECORD_SEP as RS
from standup.git import Commit, parse_log


def _make_record(sha, short, name, email, date, subject, body="", numstat=""):
    record = RS + FS.join([sha, short, name, email, date, subject, body]) + FS
    if numstat:
        record += "\n" + numstat
    return record


def test_parse_single_commit():
    raw = _make_record(
        "abc123def", "abc123d", "Ada Lovelace", "ada@example.com",
        "2026-06-18T10:00:00+00:00", "feat: add engine", "longer body",
        "10\t2\tsrc/engine.py\n3\t0\tREADME.md",
    )
    commits = parse_log(raw)
    assert len(commits) == 1
    c = commits[0]
    assert isinstance(c, Commit)
    assert c.sha == "abc123def"
    assert c.short_sha == "abc123d"
    assert c.author_name == "Ada Lovelace"
    assert c.author_email == "ada@example.com"
    assert c.subject == "feat: add engine"
    assert c.body == "longer body"
    assert c.files_changed == 2
    assert c.insertions == 13
    assert c.deletions == 2
    assert c.files == ["src/engine.py", "README.md"]
    assert c.date == datetime(2026, 6, 18, 10, 0, tzinfo=timezone.utc)


def test_parse_multiple_commits():
    raw = (
        _make_record("a1", "a1", "Bob", "b@x.com", "2026-06-18T09:00:00+00:00", "fix: bug")
        + _make_record("a2", "a2", "Carol", "c@x.com", "2026-06-17T09:00:00+00:00", "docs: note")
    )
    commits = parse_log(raw)
    assert len(commits) == 2
    assert {c.author_name for c in commits} == {"Bob", "Carol"}


def test_parse_handles_binary_numstat():
    raw = _make_record(
        "a1", "a1", "Bob", "b@x.com", "2026-06-18T09:00:00+00:00", "chore: assets",
        numstat="-\t-\timage.png",
    )
    commits = parse_log(raw)
    assert commits[0].files_changed == 1
    assert commits[0].insertions == 0
    assert commits[0].deletions == 0


def test_parse_empty():
    assert parse_log("") == []


def test_naive_date_defaults_to_utc():
    raw = _make_record("a1", "a1", "Bob", "b@x.com", "2026-06-18T09:00:00", "x")
    assert parse_log(raw)[0].date.tzinfo is not None


def test_zulu_suffix_parsed():
    raw = _make_record("a1", "a1", "Bob", "b@x.com", "2026-06-18T09:00:00Z", "x")
    commit = parse_log(raw)[0]
    assert commit.date == datetime(2026, 6, 18, 9, 0, tzinfo=timezone.utc)
