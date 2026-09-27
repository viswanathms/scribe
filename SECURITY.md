# Security Policy

## Supported Versions

Scribe is a small, actively-developed personal tool without formal version
releases yet. Security fixes are applied to the `main` branch only.

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report it privately using one of these channels:
- [GitHub Security Advisories](https://github.com/viswanathms/scribe/security/advisories/new)
  for this repository (preferred), or
- Contact the maintainer directly via their GitHub profile
  ([@viswanathms](https://github.com/viswanathms)).

Please include:
- A description of the vulnerability and its potential impact
- Steps to reproduce, or a proof of concept
- Any suggested remediation, if you have one

You should expect an initial response within a few days. This is a
maintained-in-spare-time project, so please be patient.

## Notes on this project's threat model

- Scribe stores your `ANTHROPIC_API_KEY` (and, in `scribe-desktop`,
  potentially an OpenAI key) in a local `.env` file or
  `~/Library/Application Support/SCRIBE/config.json`. These are **not**
  encrypted at rest — treat them like any other local secret file
  (`chmod 600`, never commit `.env`, never share your SQLite DB or config
  publicly if it might contain a key).
- The web UI (`src/webapp` / `scribe-desktop/webapp`) binds to
  `127.0.0.1` and is intended for local, single-user use only. It is not
  designed or hardened to be exposed to a network or the public internet —
  do not put it behind a reverse proxy without adding authentication first.
- The arXiv crawler only fetches allow-listed, publicly documented paths
  and respects arXiv's `robots.txt` `Crawl-delay`. Modifying the crawler to
  bypass `robots.txt` or hammer arXiv's servers is out of scope for this
  project and won't be accepted.
