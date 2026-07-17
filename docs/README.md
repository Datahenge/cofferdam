# cofferdam — Documentation

This directory is the **single source of truth** for `cofferdam`. Following the
[Scribe Coding](https://datahenge.com/blog/document-driven-ai-development/)
(document-driven) methodology, requirements are written and reviewed *before*
code, code references requirement identifiers, and design decisions are recorded
so they need not be re-litigated.

## How to read this

1. Start with the **[Ground Rules](00-ground-rules.md)** — how we work here.
2. Read the **[Overview](01-overview.md)** for the problem and the design rule.
3. The domain requirement documents (02–13) each own one concern and carry
   **business-rule identifiers** of the form `BR-<AREA>-<NNN>`. Code and tests
   cite these identifiers in docstrings and comments for traceability.
4. **[Architecture Decision Records](adr/)** capture *why* — each ADR is an
   immutable record of one decision, its context, and its consequences.

## Table of contents

### Requirements

| #  | Document | Owns |
|----|----------|------|
| 00 | [Ground Rules](00-ground-rules.md) | How the project is built (methodology) |
| 01 | [Overview](01-overview.md) | Problem, design rule, goals, non-goals |
| 02 | [Conceptual Model](02-conceptual-model.md) | Environments, kinds, integrations, operations |
| 03 | [Policy File Format](03-policy-file-format.md) | The TOML schema (`BR-CONFIG-*`, `BR-MODEL-*`) |
| 04 | [Decision Engine](04-decision-engine.md) | Fail-closed allow/deny rules (`BR-DECISION-*`, `BR-HOST-*`) |
| 05 | [Secret Handling](05-secret-handling.md) | Credential resolution & redaction (`BR-SECRET-*`) |
| 06 | [Host & URL Handling](06-host-url-handling.md) | Structured hostname checks (`BR-HOST-*`, `BR-HTTP-*`) |
| 07 | [Email Policy](07-email-policy.md) | Recipient/domain/sink rules (`BR-EMAIL-*`) |
| 08 | [Logging & Observability](08-logging-observability.md) | Structured, redacted logs (`BR-LOG-*`) |
| 09 | [Public API](09-public-api.md) | The supported programmatic surface (`BR-API-*`) |
| 10 | [CLI](10-cli.md) | `validate` / `inspect` / `decide` (`BR-CLI-*`) |
| 11 | [Frappe Integration](11-frappe-integration.md) | Site policy discovery (`BR-FRAPPE-*`) |
| 12 | [Validation](12-validation.md) | Schema vs. semantic checks (`BR-VALIDATE-*`) |
| 13 | [Testing](13-testing.md) | Required coverage (`BR-TEST-*`) |
| 14 | [Acceptance Criteria](14-acceptance-criteria.md) | Definition of "first usable version" |
| 15 | [Open Questions](15-open-questions.md) | Resolved decisions + what remains |

### Decisions

See **[docs/adr/](adr/)** for the full ADR index.

## Provenance

These requirements were derived from
`/home/sysop/erpnext_methodology/OUTBOUND_POLICY_LIBRARY_REQUIREMENTS.md`
(captured 2026-07-16). Where this documentation and the source differ, this
documentation and the ADRs are authoritative; the source is the historical
origin. Notable evolution: the project was named **`cofferdam`** (ADR-0003),
superseding the provisional `frappe-outbound-policy` / `outbound_policy` names.
