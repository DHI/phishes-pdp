# Contributing to PHISHES PDP

Thank you for your interest in contributing! This guide explains how to get started.

## Getting Started

1. **Fork & clone** the repository
2. **Create a branch** from `main` for your work
3. **Set up** the module you're working on (see module READMEs):
   - [PDP/DataDownloadTool/README.md](PDP/DataDownloadTool/README.md)
   - [PDP/PlantGrowthModule/README.md](PDP/PlantGrowthModule/README.md)

## Development Workflow

1. Install dependencies with `uv sync --link-mode copy` inside the relevant module folder
2. Make your changes
3. Run linting and formatting checks:

   ```bash
   ruff check .
   black --check .
   ```

4. If you changed notebooks, verify they run end-to-end with a clean kernel restart
5. Commit with a clear, descriptive message

## Pull Request Process

1. Open a PR against `main`
2. Fill out the [PR template](.github/PULL_REQUEST_TEMPLATE.md) completely
3. Ensure all CI checks pass (linting, security scan, notebook lint, file size)
4. Wait for review from a [code owner](.github/CODEOWNERS)
5. Address any review feedback
6. Merge after approval

## Code Style

- **Python**: Follow [PEP 8](https://peps.python.org/pep-0008/). We use `ruff` for linting and `black` for formatting (line length 100).
- **Markdown**: Must pass `markdownlint-cli2`. See [.markdownlint-cli2.jsonc](.markdownlint-cli2.jsonc) for config.
- **Notebooks**: Code cells are linted with `nbqa ruff`.

## What to Contribute

- Bug fixes and improvements to existing modules
- New dataset integrations for the Data Download Tool
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
