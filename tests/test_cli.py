import json
import subprocess

import pytest

from standup.cli import main


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "repo"
    path.mkdir()
    _git(["init", "-q"], path)
    _git(["config", "user.email", "ada@example.com"], path)
    _git(["config", "user.name", "Ada Lovelace"], path)
    _git(["config", "commit.gpgsign", "false"], path)

    (path / "a.txt").write_text("hello\n")
    _git(["add", "a.txt"], path)
    _git(["commit", "-q", "-m", "feat: initial commit"], path)

    (path / "b.txt").write_text("world\n")
    _git(["add", "b.txt"], path)
    _git(["commit", "-q", "-m", "fix: a bug"], path)
    return str(path)


def test_cli_standup(repo, capsys):
    code = main(["-C", repo, "--since", "10 years ago", "--no-color"])
    assert code == 0
    out = capsys.readouterr().out
    assert "feat: initial commit" in out
    assert "fix: a bug" in out
    assert "Ada Lovelace" in out


def test_cli_json(repo, capsys):
    code = main(["-C", repo, "--since", "10 years ago", "-f", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["commits"] == 2


def test_cli_changelog(repo, capsys):
    code = main(["-C", repo, "--since", "10 years ago", "-f", "changelog"])
    assert code == 0
    out = capsys.readouterr().out
    assert "## Features" in out
    assert "## Bug Fixes" in out


def test_cli_me_flag(repo, capsys):
    code = main(["-C", repo, "--since", "10 years ago", "--me", "-f", "json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["commits"] == 2


def test_cli_output_file(repo, tmp_path):
    out_file = tmp_path / "report.md"
    code = main(["-C", repo, "--since", "10 years ago", "-f", "markdown", "-o", str(out_file)])
    assert code == 0
    assert out_file.read_text().startswith("# Standup")


def test_cli_not_a_repo(tmp_path, capsys):
    code = main(["-C", str(tmp_path), "--since", "10 years ago"])
    assert code == 1
    assert "not a git repository" in capsys.readouterr().err
