# Changelog

All notable changes to `cofferdam` are recorded here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Per the Scribe Coding methodology, this changelog also records **design
decisions and their rationale**, so that later work can resolve conflicts by
reading the record rather than re-litigating settled questions. Architecture
decisions are captured in full under `docs/adr/`.

## [Unreleased]

### Added

- Initial project scaffolding: `src/` layout, `docs/`, `tests/`, packaging
  (`pyproject.toml`, `LICENSE`, `.gitignore`).
- Requirements documentation set under `docs/` with a table of contents and
  business-rule identifiers (`BR-*`).
- Architecture Decision Records (ADR-0001 … ADR-0010) under `docs/adr/`.
- Package skeleton: `errors`, `models`, `config`, `validators`, `decisions`,
  `credentials`, `http`, `mail`, `frappe`, `cli`.

### Decided

- Project, distribution, import, and CLI name is **`cofferdam`** (ADR-0003),
  superseding the provisional `frappe-outbound-policy` / `outbound_policy`
  names from the source requirements.
- Ship a **pure Python library, not a Frappe app** (ADR-0002).
- **TOML** is the policy file format (ADR-0004).
- The engine is **fail-closed by default** (ADR-0005).
- Schema is modeled and validated with **Pydantic v2** (ADR-0006).
- Credentials resolve from **environment variables**; raw `secret_value` in
  TOML is **rejected by default** and only permitted behind an explicit opt-in
  (ADR-0007).
- The HTTP helper wraps **`httpx`** and is an **optional dependency**
  (`cofferdam[http]`) (ADR-0008).
- Host matching uses a **structured URL parser** comparing hostnames, never
  substrings (ADR-0009).
- Frappe-specific behavior is **isolated in `cofferdam.frappe`**; the core
  never imports `frappe` (ADR-0010).

[Unreleased]: https://github.com/datahenge/cofferdam/commits/main
