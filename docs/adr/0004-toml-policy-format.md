# ADR-0004 — Use TOML for the policy file

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

The policy is human-maintained by support and ops teams and is security
sensitive. Candidate formats: TOML, YAML, JSON, or a custom DSL.

## Decision

Use **TOML** as the required initial format.

- TOML supports **comments** (JSON does not) — essential for annotating *why* a
  rule exists ("never capture money outside production").
- TOML is **readable** by non-developers.
- TOML is **less surprising than YAML** for security-sensitive config (no
  implicit type coercion, no Norway problem, no anchors/aliases, no arbitrary
  object construction).
- TOML is a *configuration* format, not a general document serializer.
- Parsing uses stdlib `tomllib` on Python 3.11+ and the `tomli` backport on 3.10.

## Consequences

- Policies are commentable and reviewable.
- No new heavy dependency (stdlib on modern Python; tiny backport on 3.10).
- YAML may be added later if a project standard requires it, but TOML is the
  baseline. Supporting multiple formats later must not weaken validation.
