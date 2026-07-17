# 03 — Policy File Format

## Format and location

- **Format:** TOML ([ADR-0004](adr/0004-toml-policy-format.md)). TOML supports
  comments, reads cleanly for support teams, and is less surprising than YAML for
  security-sensitive configuration.
- **Default path (`BR-CONFIG-001`):** `sites/{site_name}/environment_policy.toml`.
- **BR-CONFIG-002 — The policy file must NOT live under `/files/private`.** That
  directory is web-served/backed up as site data; policy is environment authority
  and must live outside it.
- **BR-CONFIG-003 — The policy is a local file**, never stored in the database and
  never in `site_config.json` (a path *override* key is allowed; see
  [11](11-frappe-integration.md)).

## Schema

Modeled with Pydantic v2 in `cofferdam.models` ([ADR-0006](adr/0006-pydantic-v2-schema-validation.md)).
Unknown keys are rejected (`extra="forbid"`, `BR-VALIDATE-003`) so typos fail
loudly rather than silently disabling a guard.

### Top level

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `environment` | enum | *required* | `production` \| `staging` \| `test` \| `dev` |
| `default_decision` | enum | `deny` | `allow` \| `deny`; `allow` in production is rejected (`BR-VALIDATE-009`) |
| `mail` | table | — | see below and [07](07-email-policy.md) |
| `credentials.<name>` | table | — | see below |
| `integrations.<name>` | table | — | see below |
| `effects.<kind>.<scope>` | table | — | scoped effect rules |

### `[mail]`

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `mode` | string | `deny` | `deny` \| `sink` \| `allow_internal` |
| `sink` | string | — | sink address used when `mode = "sink"` |
| `allow_domains` | list[str] | `[]` | domains permitted when `mode = "allow_internal"` |
| `decorate` | bool | `true` | prepend environment label to subject and body in non-Production; set `false` to opt out (`BR-EMAIL-DECORATE-002`) |

### `credentials.<name>` (`BR-SECRET-001`)

| Key | Type | Notes |
|-----|------|-------|
| `profile` | string | logical profile, e.g. `staging`, `sandbox` |
| `secret_env` | string | env var holding the secret (**preferred**) |
| `secret_value` | string | raw inline secret — **rejected by default** ([ADR-0007](adr/0007-env-var-credentials.md)) |

### `integrations.<name>`

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `enabled` | bool | `false` | disabled integrations always deny |
| `kind` | enum | *required* | a `SideEffectKind` |
| `credential` | string | — | must reference a defined credential |
| `allowed_hosts` | list[str] | `[]` | bare hostnames; empty denies any host check |
| `allowed_methods` | list[str] | `[]` | HTTP methods; empty denies any method check |
| `allowed_operations` | list[str] | `[]` | empty denies any operation check |
| `allow_authorize` | bool | `false` | payment: permit authorization |
| `allow_capture` | bool | `false` | payment: permit capture |

> **Empty allowlist means deny.** If the caller supplies a dimension (host,
> method, operation) and the corresponding allowlist is empty, the decision is
> **deny** — fail-closed ([04](04-decision-engine.md)).

### `effects.<kind>.<scope>`

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `enabled` | bool | `false` | whether the scoped effect class is permitted |
| `allow_domains` | list[str] | `[]` | domains permitted for that scope |

## Canonical example

The reference policy lives at
[`examples/environment_policy.staging.toml`](../examples/environment_policy.staging.toml)
and is used verbatim as a test fixture. It permits Windmill sandbox reads/writes,
Stripe *authorize* but not *capture*, internal email to `example.internal`,
and denies customer email and external scheduled reports.
