# ADR-0003 — Name the package, import, and CLI `cofferdam`

- **Status:** Accepted
- **Date:** 2026-07-16
- **Supersedes:** provisional names `frappe-outbound-policy` /
  `erpnext-outbound-policy` (PyPI) and `outbound_policy` (module) from the source
  requirements.

## Context

The source requirements used provisional names describing the *mechanism*
(outbound policy). During requirements discussion the project acquired a
metaphor-driven name, **cofferdam**: a temporary watertight enclosure pumped dry
so work can proceed on a submerged foundation — precisely what the library does
for a restored database. A single, memorable name across distribution, import,
and CLI reduces cognitive load.

## Decision

Use **`cofferdam`** as:

- the PyPI distribution name,
- the importable module (`import cofferdam`),
- the console script (`cofferdam validate|inspect|decide`).

Discoverability for Frappe/ERPNext users is preserved through package keywords
and classifiers rather than a `frappe-` name prefix.

## Consequences

- One name to learn, publish, and document.
- The provisional `outbound_policy` module name and `outbound-policy` CLI are
  retired; docs and examples use `cofferdam` throughout.
- The `frappe`/`erpnext` substrings are absent from the name; mitigated with
  keywords. Revisit before 1.0 if PyPI search discoverability proves weak
  (tracked in [15 — Open Questions](../15-open-questions.md)).
