# Contributing to PHISHES PDP

Thank you for your interest in contributing! This guide explains how to get started.

## Getting Started

### 1. Install the hooks (do this first)

```bash
pip install pre-commit
pre-commit install
```

This fixes formatting, trailing whitespace and missing final newlines
automatically on every commit, using the exact tool versions CI uses.

Do not skip it. If you contribute from a fork, **this is the only automatic
fixer you get** — a pull request from a fork runs with a read-only token, so
nothing in CI can tidy your branch for you.

### 2. Get a branch

Which path you take depends on whether you have write access to `DHI/phishes-pdp`.

#### DHI members (write access) — branch in this repository

```bash
git clone https://github.com/DHI/phishes-pdp.git
cd phishes-pdp
git switch -c my-feature origin/main
```

Preferred if you have access. Your branch tracks `main` directly, so you find
out about conflicting work when it happens rather than at merge time. A fork
that sits on a stale `main` is the most expensive mistake available here: if
someone renames or moves a directory while you are working, git will relocate
your *edits* to existing files but silently leave your *new* files at the old
path, and the pull request will look clean.

#### External collaborators — fork

```bash
git clone https://github.com/<you>/phishes-pdp.git
cd phishes-pdp
git remote add upstream https://github.com/DHI/phishes-pdp.git
git switch -c my-feature upstream/main
```

Before you open a pull request, and again if review takes a while:

```bash
git fetch upstream
git rebase upstream/main
```

We do not hand out write access to avoid this step. A fork pull request runs
with a read-only token and no access to repository secrets, which is exactly
the isolation we want for code we have not reviewed yet.

### 3. Set up the module you are working on

Each module is an independent project with its own environment:

```bash
cd data-download-tool          # or: cd model-trains/MSHE-Ecolab-PGM
uv sync --link-mode copy
```

`--link-mode copy` is required on OneDrive-synced directories.

Each module carries a `.python-version` of `3.11`, matching CI — uv downloads
that interpreter for you if you do not have it. Do not override it: several
geospatial dependencies (`fiona`, `rasterio`) publish no wheels for the newest
Python, and `uv sync` will try to build them against a system GDAL you almost
certainly do not have.

See the module READMEs for details:

- [data-download-tool/README.md](data-download-tool/README.md)
- [model-trains/MSHE-Ecolab-PGM/README.md](model-trains/MSHE-Ecolab-PGM/README.md)

## Development Workflow

1. Make your changes
2. Run the blocking checks — **these are byte-for-byte what CI runs**, from the
   module directory:

   ```bash
   uv run ruff check .
   uv run pytest -q
   ```

   Use `uv run`, not a system-wide `ruff`. `uv run` picks up the ruff version
   pinned in the module's `pyproject.toml`; a different version enforces a
   different rule set and will disagree with CI.

3. If you changed notebooks, verify they run end-to-end with a clean kernel restart
4. Commit with a clear, descriptive message

## Which checks can block your pull request

Only failures that mean the change is **wrong** block a merge. Failures that
mean it is merely **untidy** are reported as suggestions in the job summary and
do not block.

| Check | Blocking? | What it means |
|---|---|---|
| `Lint and Test (<module>)` | **yes** | Real defects: undefined names, unused imports, failing tests |
| `File Size Check (10 MB)` | **yes** | Something large was committed, probably model output |
| `Secret Scan (trufflehog)` | **yes** | A verified credential is in the diff |
| `Dependency Audit (<module>)` | **yes** | A known CVE, or bandit found a security issue |
| `Format (advisory)` | no | Run `uv run ruff format .` — or let the hooks do it |
| `Markdown Lint (advisory)` | no | Usually whitespace; the hooks fix it |
| `Notebook Lint (advisory)` | no | Notebook idioms sometimes trip Python rules |

If a blocking check fails for a reason you cannot connect to your change, say so
in the pull request rather than reverse-engineering it. That has been our bug
before now, not yours.

## Pull Request Process

1. Open a PR against `main`
2. Fill out the [PR template](.github/PULL_REQUEST_TEMPLATE.md) completely
3. Ensure the blocking checks pass
4. Wait for review from a [code owner](.github/CODEOWNERS)
5. Address any review feedback
6. Merge after approval

## Code Style

- **Python**: [PEP 8](https://peps.python.org/pep-0008/), enforced by `ruff`
  (line length 100). Each module pins its ruff version and declares its rules in
  `[tool.ruff]`; both modules use `select = ["E", "F", "W", "I", "N"]`. Never
  rely on ruff's defaults — they widen between releases, which silently changes
  what CI enforces.
- **Markdown**: `markdownlint-cli2`. See [.markdownlint-cli2.jsonc](.markdownlint-cli2.jsonc).
- **Notebooks**: code cells are linted with `nbqa ruff`, using each module's config.
- Prefer `pathlib.Path` and `Path.joinpath()` over the `/` operator; use
  `pd.Timestamp` over `datetime`. See [CLAUDE.md](CLAUDE.md) for the full list.

## What to Contribute

- Bug fixes and improvements to existing modules
- New dataset integrations for the Data Download Tool
- New model trains under `model-trains/<train-name>/`
- Documentation improvements
- Test coverage

## Reporting Issues

- Use the [issue templates](.github/ISSUE_TEMPLATE/) to report bugs or request features
- Search existing issues before opening a new one
- Include steps to reproduce for bug reports

## Security

- **Never** commit secrets, API keys, or credentials
- Report security vulnerabilities privately — see [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
