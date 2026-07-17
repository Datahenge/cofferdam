# ADR-0010 — Isolate Frappe behind one guarded module

- **Status:** Superseded by [ADR-0012](0012-remove-cofferdam-frappe-module.md)
- **Date:** 2026-07-16
- **Related:** [ADR-0002](0002-python-library-not-frappe-app.md)

## Context

`cofferdam` must be usable *inside* Frappe/ERPNext (locating a site's policy,
honoring a `site_config.json` override, using Frappe's logger) while remaining a
plain Python package that installs and tests with no Bench. If `import frappe`
leaked into the core, the package would fail to import outside a Bench and would
be untestable in ordinary CI.

## Decision

- **All** Frappe-aware code lives in the single module `cofferdam.frappe`.
- Even there, `import frappe` is **lazy and guarded**, attempted only when a
  Frappe helper is actually called — never at module import time.
- No other module imports Frappe, directly or indirectly. This is a project
  invariant, enforceable by a simple grep/import-lint in CI.
- Policy caching in the Frappe helper is **explicit-reload** in v1
  (`get_policy()` caches per process; `reload_policy()` clears it). Automatic
  mtime-based invalidation is deferred: Frappe runs multiple worker processes, so
  a shared in-memory auto-refresh would be inconsistent and surprising. Explicit
  reload is predictable and adequate for the restore/refresh workflow.

## Consequences

- The library imports and its full suite runs with no Bench (`BR-TEST-004`).
- Frappe users still get zero-app site-policy discovery and Frappe-aware logging.
- Picking up an edited policy in a running worker requires an explicit
  `reload_policy()` (or a worker restart) — acceptable for an infrequent,
  deliberate refresh operation. Revisit if hot-reload demand emerges.
