# ADR-0012 — Remove `cofferdam.frappe` from the core library

- **Status:** Accepted
- **Date:** 2026-07-17
- **Supersedes:** [ADR-0010](0010-frappe-isolation.md)

## Context

ADR-0010 isolated all Frappe-aware code into a single `cofferdam.frappe`
module, anticipating that users would call `get_policy()` directly from Frappe
server-side scripts without needing a companion app.

Two decisions changed the calculus:

1. **`cofferdam-app` ships in the first release** (ADR-0011). Every
   Frappe/ERPNext user who wants deep integration will install the app; calling
   the library directly from a custom script is the exception, not the rule.
2. **`cofferdam-app` has native site context.** Inside a running bench the app
   has direct access to `frappe.local.site` and does not need the filesystem
   heuristics `cofferdam.frappe` was designed to provide.

Keeping a Frappe-specific module in the core library violates the clean
separation the library is otherwise built around. Site discovery and
Frappe-aware logging are Frappe concerns; they belong in the Frappe app.

## Decision

- Remove `cofferdam.frappe` from the `cofferdam` package entirely.
- Frappe site discovery, per-process policy caching, and Frappe-aware logging
  are responsibilities of `cofferdam-app`.
- The `cofferdam` core library has no Frappe-specific code at any layer.

## Consequences

- `cofferdam` is a pure Python library with zero Frappe dependency.
- `cofferdam-app` owns all Frappe-specific integration logic.
- Users calling `cofferdam` from a custom Frappe script (without
  `cofferdam-app`) must call `load_policy(path)` with an explicit path.
  Site auto-discovery is the app's responsibility, not the library's.
