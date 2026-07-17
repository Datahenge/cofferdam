# ADR-0005 — Fail closed by default

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

The library exists to *prevent* accidental Production side effects in
non-Production. The cost asymmetry is stark: a wrongly-denied sandbox call is a
minor inconvenience; a wrongly-allowed action can email real customers or move
real money. Ambiguity must therefore resolve to denial.

## Decision

The engine **fails closed**. A side effect is allowed only when the policy
*explicitly* permits every dimension the caller supplies. Deny on any of:

missing policy file (unless the caller explicitly opts into a fallback), missing
environment, unknown integration, disabled integration, unknown/mismatched kind,
disallowed operation, disallowed method, disallowed host, missing credential
reference, mismatched credential profile, missing secret source, or invalid
schema. **An empty allowlist denies.** Unknown keys in the policy are rejected
rather than ignored. `environment = "production"` is *not* a blanket allow-all —
production must permit side effects explicitly, and `default_decision = "allow"`
in production is rejected by validation.

## Consequences

- Safety is the default; permission is the deliberate act.
- Misconfigurations surface as denials (loud, safe) rather than silent allows.
- Authors must enumerate what is permitted — more verbose policies, by design.
- Every fail-closed branch is covered by an explicit test (`BR-TEST-*`).
