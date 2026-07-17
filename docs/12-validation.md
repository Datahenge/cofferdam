# 12 — Validation

Validation happens in two layers and **distinguishes syntax errors from semantic
policy errors** (`BR-VALIDATE-011`).

## Layer 1 — schema (Pydantic, `cofferdam.models`)

- **BR-VALIDATE-001 — Missing `environment`** → error.
- **BR-VALIDATE-002 — Invalid environment name** → error.
- **BR-VALIDATE-003 — Unknown keys** (typos) → error (`extra="forbid"`).
- Malformed TOML → `PolicyValidationError` (a *syntax* error, raised in
  `cofferdam.config` before model validation).

## Layer 2 — semantic (`cofferdam.validators`)

Applied on every load; extra checks under `strict=True`.

| ID | Check | Strict only |
|----|-------|:-----------:|
| `BR-VALIDATE-004` | Integration references a **defined** credential | |
| `BR-VALIDATE-005` | `allowed_hosts` entries are bare hostnames, not URLs | |
| `BR-VALIDATE-006` | `allowed_methods` are known HTTP methods | |
| `BR-VALIDATE-009` | Production is not a blanket allow-all (`default_decision != "allow"`) | |
| `BR-VALIDATE-007` | Every `secret_env` variable is **set** | ✓ |
| `BR-VALIDATE-010` | No raw `secret_value` present | ✓ |

`PolicyValidationError` aggregates all problems in its `.problems` list so a
single run reports everything wrong, not just the first issue.

## Strict mode

`load_policy(path, strict=True)` (and `cofferdam validate --strict`) enable the
strict checks. Strict mode is intended for CI and the `validate` CLI — the run
that gates a deploy — not the request hot path, where env vars are resolved
lazily and a missing var fails closed at resolution time
([05](05-secret-handling.md)).

## What validation is for

Validation exists to make an *unsafe* policy fail *loudly at load* rather than
silently at runtime. A policy that parses but is semantically unsafe (dangling
credential, production allow-all, a URL where a hostname belongs) is a bug the
author should hear about immediately.
