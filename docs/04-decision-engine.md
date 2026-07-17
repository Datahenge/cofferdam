# 04 — Decision Engine

Implemented in `cofferdam.decisions`. The engine is **fail-closed**
([ADR-0005](adr/0005-fail-closed-by-default.md)): a side effect is allowed only
when the policy *explicitly* permits every dimension the caller supplies.

## Evaluation order

`decide(policy, integration=..., kind=..., operation=..., method=..., host=..., credential=...)`
returns a `Decision`. Only the dimensions the caller passes are enforced; each
enforced dimension must appear in the integration's explicit allowlist.

1. **BR-DECISION-001** — Missing policy file → deny (raised at load time as
   `PolicyFileNotFoundError` unless the caller opted into a fallback).
   *(BR-DECISION-002: identifier retired.)*
2. **BR-DECISION-003** — Unknown integration → deny (`unknown_integration`).
3. **BR-DECISION-004** — Disabled integration → deny (`integration_disabled`).
4. **BR-DECISION-005** — Kind mismatch (caller's `kind` ≠ policy's) → deny
   (`kind_mismatch`).
5. **BR-DECISION-006** — Credential reference missing from policy → deny
   (`missing_credential`); credential does not match the integration's pinned
   credential → deny (`credential_mismatch`).
6. **BR-DECISION-007** — Operation not in `allowed_operations` → deny
   (`operation_not_allowed`). *Empty list denies.*
7. **BR-DECISION-008** — Payment `authorize`/`capture` without the matching
   `allow_authorize`/`allow_capture` gate → deny.
8. **BR-DECISION-009** — HTTP method not in `allowed_methods` → deny
   (`method_not_allowed`). *Empty list denies.* Case-insensitive.
9. **BR-DECISION-010** — Host not in `allowed_hosts` → deny (`host_not_allowed`).
   Whole-hostname match only ([06](06-host-url-handling.md)). *Empty list denies.*
10. Otherwise → **allow** (`explicitly_allowed`).

## Reason codes

Every `Decision` carries a stable, machine-readable `reason_code`:

`unknown_integration`, `integration_disabled`, `kind_mismatch`,
`missing_credential`, `credential_mismatch`, `operation_not_allowed`,
`payment_authorize_not_allowed`, `payment_capture_not_allowed`,
`method_not_allowed`, `host_not_allowed`, `explicitly_allowed`.

These codes are part of the public contract: CLI output, logs, and
`PolicyDeniedError` all surface them.

## Production is still explicit (`BR-DECISION-011`)

`environment = "production"` is **not** a blanket allow-all. Production policies
must permit side effects explicitly, exactly like every other environment. A
production policy with `default_decision = "allow"` is rejected by validation
([12](12-validation.md), `BR-VALIDATE-009`).

## API surface

- `decide(...) -> Decision` — never raises for a denial; inspect `.allowed`.
- `assert_allowed(...) -> Decision` — raises `PolicyDeniedError` on denial,
  returns the allowing decision otherwise.
- `Decision.to_exception()`, `Decision.as_log_dict()`, `Decision.message()`.

See [09 — Public API](09-public-api.md) for the full signatures.
