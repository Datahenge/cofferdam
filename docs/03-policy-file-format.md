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
| `configs.<name>` | table | — | structured non-secret settings; see below |
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
| `env` | table | multi-part secrets: logical name → env var (`BR-SECRET-004`) |
| `secret_value` | string | raw inline secret — **rejected by default** ([ADR-0007](adr/0007-env-var-credentials.md)) |

A credential carrying **more than one** related secret — an access-key pair, for
example — declares them in an `env` sub-table instead of `secret_env`
([ADR-0014](adr/0014-structured-site-local-config.md), `BR-SECRET-004`):

```toml
[credentials.cloudflare_r2_keys]
profile = "dev"

[credentials.cloudflare_r2_keys.env]
access_key_id     = "R2_ACCESS_KEY_ID"
secret_access_key = "R2_SECRET_ACCESS_KEY"
```

Resolved as a whole with `policy.resolve_credentials("cloudflare_r2_keys")`
([05](05-secret-handling.md)). The logical keys are application-defined and are
never case-normalized. A credential declares the `env` table **or** a
single-valued source (`secret_env` / `secret_value`), never both
(`BR-VALIDATE-015`).

### `configs.<name>` (`BR-CONFIG-004`)

Structured, environment-specific, **non-secret** settings for an application —
endpoints, bucket names, regions, prefixes, timeouts, feature switches. Values
may be any TOML scalar, array, or nested table; cofferdam stores and returns
them without interpreting them, and **no decision depends on a config value**.

```toml
[configs.cloudflare_r2_dev]
account_id = "abc123"
endpoint_url = "https://abc123.r2.cloudflarestorage.com"
bucket_name = "foo-erpnext-dev"
region_name = "auto"
attachment_prefix = "sites/foo/attachments/"
presigned_get_expiry_seconds = 300
delete_from_r2_on_file_delete = false
```

- **BR-CONFIG-005 — Config keys keep their exact casing.** Application config
  keys are never lower- or upper-cased on the write or the read path. (Contrast
  `allowed_methods`, which *is* case-folded: HTTP methods are cofferdam's own
  vocabulary, config keys are the application's.)
- **BR-CONFIG-006 — A config holds no secret material.** The policy file is
  reviewable and commit-safe ([ADR-0007](adr/0007-env-var-credentials.md)); a
  config section is not a place to paste an API key. Strict validation rejects
  keys whose names indicate secret material (`BR-VALIDATE-013`,
  [12](12-validation.md)). Secrets belong in `credentials.<name>`.
- Config names live in their own namespace; a config and a credential may share
  a name, though distinct names read better.

Read with `policy.resolve_config("cloudflare_r2_dev")` ([09](09-public-api.md)).

### `integrations.<name>`

| Key | Type | Default | Notes |
|-----|------|---------|-------|
| `enabled` | bool | `false` | disabled integrations always deny |
| `kind` | enum | *required* | a `SideEffectKind` |
| `credential` | string | — | must reference a defined credential (`BR-VALIDATE-004`) |
| `config` | string | — | must reference a defined config (`BR-VALIDATE-012`) |
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
Stripe *authorize* but not *capture*, object-storage transfers against a
`configs`-supplied endpoint, and internal email to `example.internal`; it denies
customer email and external scheduled reports.

A second example,
[`examples/environment_policy.dev-r2.toml`](../examples/environment_policy.dev-r2.toml),
is a worked object-storage case (Cloudflare R2) showing `[integrations.*]`,
`[configs.*]`, and a multi-part `[credentials.*.env]` credential together. Every
file in `examples/` is validated by the test suite ([13](13-testing.md)).
