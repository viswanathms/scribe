# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to adopt [Semantic Versioning](https://semver.org/)
once it has its first tagged release.

## [Unreleased]

### Added
- Open source project scaffolding: LICENSE (MIT), CONTRIBUTING.md,
  CODE_OF_CONDUCT.md, SECURITY.md, issue/PR templates, CI lint workflow,
  Dependabot config.

### Fixed
- Removed an unnecessary f-string prefix with no placeholders in
  `src/db.py` (`ruff` F541).

## [0.2.0] - scribe-desktop

- Added SCRIBE desktop app: multi-provider (Anthropic/OpenAI/Ollama) Mac
  app with onboarding, per-user criteria, native window via `pywebview`.
- Added Daily Report / By Subject / Calendar / Interests tabs, UI rework
  (pagination, search, alignment fixes, theme refresh), multi-category
  tracking.

## [0.1.0] - Initial commit

- Initial SCRIBE arXiv paper tracker: daily `cs.AI` crawler
  (`src/crawler.py`), Claude-based importance scoring (`src/reviewer.py`),
  SQLite storage (`src/db.py`), CLI (`src/cli.py`), local Flask web UI
  (`webapp/`), and a macOS `launchd` daily scheduler.

[Unreleased]: https://github.com/viswanathms/scribe/compare/main...HEAD
