# Changelog

All notable changes to `cofferdam` are recorded here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Per the Scribe Coding methodology, this changelog also records **design
decisions and their rationale**, so that later work can resolve conflicts by
reading the record rather than re-litigating settled questions. Architecture
decisions are captured in full under `docs/adr/`.

## [Unreleased]

## [0.2.0] — 2026-09-05

### Added

- **Structured site-local configuration** (issue #4, ADR-0014): a top-level
  `[configs.<name>]` section for environment-specific, **non-secret** settings —
  endpoints, buckets, regions, prefixes — kept separate from credentials.
  Values may be any TOML scalar, array, or nested table, and key casing is
  preserved exactly (`BR-CONFIG-004`, `BR-CONFIG-005`).
- `integrations.<name>.config`, a validated reference to a `configs.<name>`
  table, alongside the existing `credential` reference (`BR-VALIDATE-012`).
- Multi-part credentials: a `[credentials.<name>.env]` sub-table mapping a
  logical secret name to the environment variable holding it, for credentials
  that carry a set (an access-key pair, say) (`BR-SECRET-004`).
- Three resolution helpers on `Policy` (`BR-API-005`): `resolve_config(name)`,
  `resolve_credentials(name)`, and `resolve_json_secret(name)`.
- `ConfigError`, raised when a config reference is undefined — fail-closed, so a
  typo raises rather than yielding an empty mapping.
- `cofferdam validate --strict` rejects secret-shaped **key names** under
  `configs.*` (`BR-VALIDATE-013`), and now checks every environment variable a
  multi-part credential names (`BR-VALIDATE-007`).
- `cofferdam inspect` lists configs by name and key names — never values.

### Documentation

- README gained a **Policy file reference**: every section and key the policy
  file accepts, with types, defaults, and the fail-closed rules that bite
  (empty allowlist denies; unknown keys rejected; secrets never in `configs.*`),
  plus a **Resolving config and secrets** section covering all four resolvers
  and what each raises.
- New worked example `examples/environment_policy.dev-r2.toml` — object storage
  with structured config and a multi-part credential. Every file in `examples/`
  is now parsed and validated by the test suite, so a shipped example cannot go
  stale silently.

### Changed

- An unknown-key (`extra="forbid"`) error now names the offending key *and* the
  permitted keys for that section (`BR-VALIDATE-014`); the mistake it catches is
  almost always a near-miss on a real key name.

### Decided

- Non-secret configuration is a **first-class section**, not a JSON bundle
  smuggled through `secret_value` with `allow_raw=True` (ADR-0014). The
  workaround made `allow_raw=True` habitual, eroding the opt-in ADR-0007 made
  deliberately rare.
- Multi-part credentials use an explicit `env` sub-table rather than free-form
  `<name>_env` keys on the credential table: the latter would require relaxing
  `extra="forbid"` to a suffix rule and would give up the typo protection of
  `BR-VALIDATE-003`.
- `resolve_json_secret` raises an error **fully detached** from
  `json.JSONDecodeError` rather than merely chaining with `from None`: that
  exception carries the entire secret document on its `.doc` attribute, so
  suppressing the chain for *display* would still leave the secret reachable on
  `__context__` (`BR-SECRET-005`, `BR-LOG-002`).

## [0.1.0] — 2026-07-17

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

[Unreleased]: https://github.com/datahenge/cofferdam/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/datahenge/cofferdam/compare/v0.1.1...v0.2.0
[0.1.0]: https://github.com/datahenge/cofferdam/releases/tag/v0.1.0
