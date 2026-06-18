# standup

Generate **standup** and **changelog** reports straight from your git history.

No more scrolling through `git log` before your daily standup — `standup` groups
your recent commits by day, author, and (for changelogs) conventional-commit
type, and renders them as a terminal report, Markdown, or JSON.

```
$ standup --since "yesterday"
Standup report (4 commits, 1 author(s), +212/-37)

Thursday, Jun 18 2026 (3)
  Ada Lovelace
    - feat: add report renderer abc123d
    - fix: handle binary numstat 9f2a1c0
    - test: cover cli paths 4d5e6f7

Wednesday, Jun 17 2026 (1)
  Ada Lovelace
    - docs: write readme 1122aabb
```

## Install

```bash
pipx install standup-cli      # recommended
# or
pip install standup-cli
```

From source:

```bash
git clone https://github.com/reubenamuzu/standup
cd standup
pip install -e .
```

## Usage

```bash
standup [options]
```

| Option | Description | Default |
| --- | --- | --- |
| `-C, --repo PATH` | Path to the git repository | `.` |
| `-s, --since` | Only commits newer than this (`git --since` syntax) | `yesterday` |
| `-u, --until` | Only commits older than this | – |
| `-a, --author` | Filter by author pattern | – |
| `--me` | Filter to your configured `git user.email` | – |
| `-b, --branch` | Branch or revision range (e.g. `v1.0..HEAD`) | – |
| `-n, --max-count` | Max number of commits | – |
| `-f, --format` | `standup`, `markdown`, `changelog`, or `json` | `standup` |
| `-o, --output FILE` | Write to a file instead of stdout | stdout |
| `--title` | Title for the `changelog` format | `Changelog` |
| `--no-color` | Disable colored output | – |

### Examples

```bash
# What did I do this week?
standup --me --since "1 week ago"

# Generate a changelog for a release range
standup -f changelog -b v1.2.0..HEAD --title "v1.3.0" -o CHANGELOG_v1.3.0.md

# Machine-readable output for scripting / piping into jq
standup -f json --since "1 month ago" | jq '.summary'
```

## Changelog grouping

The `changelog` format groups commits using
[Conventional Commits](https://www.conventionalcommits.org/) prefixes
(`feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore`,
`style`). Anything that doesn't match lands under **Other**.

## Development

```bash
pip install -e ".[dev]" || pip install pytest ruff
pytest
ruff check .
```

## License

MIT
