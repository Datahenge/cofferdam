# ADR-0006 — Validate the schema with Pydantic v2

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

The policy schema needs typed parsing, clear per-field error messages, rejection
of unknown keys, and enum validation. Candidates: Pydantic v2, attrs +
hand-written validators, stdlib dataclasses + manual checks, or `TypedDict` +
external validation.

## Decision

Use **Pydantic v2** for the schema models in `cofferdam.models`.

- Rich, structured validation errors that map cleanly onto our
  `PolicyValidationError.problems` list.
- `extra="forbid"` gives us fail-closed rejection of unknown keys for free
  (`BR-VALIDATE-003`), catching typos that would otherwise silently disable a
  guard.
- Enum coercion for `environment`, `kind`, and `default_decision`.
- Frozen models give us immutable, hashable policy objects.

Semantic checks that span multiple sections (dangling credential references,
production allow-all, hostname sanity) remain in `cofferdam.validators`, keeping
schema shape and cross-cutting policy separate.

## Consequences

- One well-maintained runtime dependency (`pydantic>=2.6`), already ubiquitous.
- Excellent error messages for policy authors.
- Slightly heavier than dataclasses; judged worth it for a security tool where
  input validation quality is a feature, not overhead.
