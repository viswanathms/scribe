# Contributing to Scribe

Thanks for considering a contribution! Scribe is a small, focused tool, so
the bar for contributing is low — this doc just sets expectations.

## Before you start

- For anything more than a typo fix, please open an issue first to discuss
  the change. This avoids wasted effort on approaches that don't fit the
  project's scope (see the "Not done yet" sections in the READMEs for things
  that were deliberately left out).
- Check open issues and PRs to avoid duplicating work.

## Development setup

```bash
git clone https://github.com/viswanathms/scribe.git
cd scribe
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
```

The `scribe-desktop/` app is a separate, independent project with its own
venv and `requirements.txt` — set it up the same way from inside that
directory if you're working on it.

## Making changes

1. Fork the repo and create a branch off `main`:
   `git checkout -b fix/short-description`
2. Make your change. Keep it focused — one logical change per PR.
3. Run lint before committing:
   ```bash
   pip install ruff
   ruff check src webapp scribe-desktop/src scribe-desktop/webapp
   ```
4. There is no automated test suite yet; manually verify the CLI/web UI
   paths your change touches (see the README's "CLI reference" section).
   If you're adding non-trivial logic, a small test is welcome (there's no
   `tests/` directory yet — feel free to start one with `pytest`).
5. Write a clear commit message describing *why*, not just *what*.

## Submitting a pull request

- Open the PR against `main`.
- Fill in the PR template — what changed, why, and how you tested it.
- Link the issue it addresses, if any.
- Be responsive to review feedback; small, iterative PRs merge faster than
  large ones.

## Code style

- Python, no enforced formatter yet — match the surrounding code's style.
- `ruff check` (config in `pyproject.toml`) must pass in CI.
- Prefer explicit, readable code over cleverness — this is a personal-scale
  tool, not a library with a public API to preserve.

## Reporting bugs / requesting features

Use the issue templates. Include:
- What you expected vs. what happened
- Steps to reproduce (for bugs)
- Your OS/Python version if relevant (this project targets macOS primarily,
  especially `scribe-desktop` and the launchd scheduler)

## Security issues

Please do **not** open a public issue for security vulnerabilities — see
[SECURITY.md](SECURITY.md) instead.

## License

By contributing, you agree that your contributions will be licensed under
the project's [MIT License](LICENSE).
