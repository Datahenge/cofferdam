# 12 — Validation

Validation happens in two layers and **distinguishes syntax errors from semantic
policy errors** (`BR-VALIDATE-011`).

## Layer 1 — schema (Pydantic, `cofferdam.models`)

- **BR-VALIDATE-001 — Missing `environment`** → error.
- **BR-VALIDATE-002 — Invalid environment name** → error.
- **BR-VALIDATE-003 — Unknown keys** (typos) → error (`extra="forbid"`).
- **BR-VALIDATE-014 — An unknown-key error names the offending key and the
  permitted keys** for that section, e.g. `credentials.r2: unknown key
  'secret_acces_key_env' (permitted: profile, secret_env, env, secret_value)`.
  Pydantic reports the location but not the alternatives; cofferdam adds them,
  because the mistake this check exists to catch is almost always a near-miss on
  a real key name.
- Malformed TOML → `PolicyValidationError` (a *syntax* error, raised in
  `cofferdam.config` before model validation).

## Layer 2 — semantic (`cofferdam.validators`)

Applied on every load; extra checks under `strict=True`.

| ID | Check | Strict only |
|----|-------|:-----------:|
| `BR-VALIDATE-004` | Integration references a **defined** credential | |
| `BR-VALIDATE-012` | Integration references a **defined** config | |
| `BR-VALIDATE-015` | A credential's `env` table is not combined with `secret_env` / `secret_value` | |
| `BR-VALIDATE-005` | `allowed_hosts` entries are bare hostnames, not URLs | |
| `BR-VALIDATE-006` | `allowed_methods` are known HTTP methods | |
| `BR-VALIDATE-009` | Production is not a blanket allow-all (`default_decision != "allow"`) | |
| `BR-VALIDATE-007` | Every `secret_env` variable is **set** | ✓ |
| `BR-VALIDATE-010` | No raw `secret_value` present | ✓ |
| `BR-VALIDATE-013` | No secret-shaped key names under `configs.*` | ✓ |

`PolicyValidationError` aggregates all problems in its `.problems` list so a
single run reports everything wrong, not just the first issue.

### `BR-VALIDATE-013` — secret-shaped config keys

`configs.*` is non-secret by contract (`BR-CONFIG-006`,
[ADR-0014](adr/0014-structured-site-local-config.md)). Strict validation rejects
a config key whose *name* indicates secret material — `password`, `passwd`,
`secret`, `token`, `api_key`, `apikey`, `private_key`, `access_key`,
`client_secret`, `credentials`, and forms containing them — at any nesting depth.

The check reads key names only, never values, and reports the offending path
(`configs.r2_dev.api_key`). It is a heuristic and can fire on an innocuous name;
the remedy is to rename the key, or to move the value where it belongs. There is
deliberately **no** per-key suppression flag: an override would be reached for
first in exactly the case where the finding is correct.

Because it is strict-only, it gates `cofferdam validate --strict` and CI, not
the request hot path.

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
