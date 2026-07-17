# ADR-0002 — Ship a Python library, not a Frappe app

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

The problem — preventing restored Production configuration from producing
Production side effects in non-Production — arises inside Frappe/ERPNext. The
obvious instinct is to build a Frappe app. But the core need (load a local
policy, decide allow/deny, resolve a credential) requires none of Frappe's
machinery: no DocTypes, MariaDB tables, migrations, hooks, fixtures, scheduled
jobs, or Desk UI. A Frappe app would also make the code untestable without a
Bench and unusable outside Frappe.

## Decision

Ship a **plain Python package** (`cofferdam`) distributed on PyPI. The core
package **must not `import frappe`**. Frappe-specific conveniences (site policy
discovery, `frappe.conf` override, Frappe logging) are isolated in a single
module, `cofferdam.frappe`, where `import frappe` is attempted lazily behind a
guard (see [ADR-0010](0010-frappe-isolation.md)). A thin optional Frappe *app*
may be added later if Desk UI, fixtures, or Bench commands are needed.

## Consequences

- The library installs, imports, and tests as an ordinary Python package with no
  Bench present (`BR-OVERVIEW-009`, `BR-TEST-004`).
- It is reusable beyond Frappe (any Python service with the same refresh hazard).
- Frappe users get helpers without a mandatory app install.
- Frappe niceties (Desk diagnostics, fixtures, Bench commands) are out of scope
  for the core library. A companion Frappe app (`cofferdam-app`) ships alongside
  it — see [ADR-0011](0011-frappe-app-first-release.md).
