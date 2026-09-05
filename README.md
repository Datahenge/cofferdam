# cofferdam

> Block outbound side effects — email, API calls, payments, webhooks — from
> non-production environments.

A **cofferdam** is a temporary watertight enclosure pumped dry so work can
happen on a submerged foundation. This library is the software equivalent: it
holds back outbound side effects from development, staging, and test
environments so they cannot reach real customers, payment processors, or live
vendor APIs.

## The problem

When a non-production environment is refreshed from a production database
backup, the restored data includes live email accounts, API credentials,
payment configuration, webhook endpoints, and scheduled job settings. Without
a guard, the non-production environment behaves like production — emailing
customers, charging cards, and calling live APIs against real data.

## How it works

`cofferdam` reads a **local TOML policy file** that lives on the environment's
filesystem — never in the database, never in a backup. That file is the
execution authority for every outbound action.

> **Restored data owns business intent. Local environment config owns
> execution authority.**

The engine answers one question per outbound action:

> *Is this specific side effect permitted **here**?*

It **fails closed**: absent, incomplete, or invalid policy denies the action.

## Installation

```console
$ pip install cofferdam            # core library + CLI
$ pip install "cofferdam[http]"    # adds the policy-checked HTTP helper (httpx)
```

Requires Python 3.10+.

## Quick start

```python
from cofferdam import load_policy

policy = load_policy("environment_policy.toml")

# Raise PolicyDeniedError if this side effect is not explicitly permitted here.
policy.assert_allowed(
    integration="windmill",
    kind="vendor_api",
    operation="write",
    method="POST",
    host="sandbox.windmill.dev",
    credential="windmill_default",
)

# Or inspect the decision without raising.
decision = policy.decide(integration="stripe", kind="payment", operation="capture")
if not decision.allowed:
    print(decision.reason_code)   # e.g. "operation_not_allowed"
```

Policy-checked HTTP — host validated against the policy before any bytes leave
(optional `cofferdam[http]` extra):

```python
from cofferdam.http import request

response = request(
    policy=policy,
    integration="windmill",
    operation="write",
    method="POST",
    url="https://sandbox.windmill.dev/api/jobs/run",
    credential="windmill_default",
    json=payload,
)
```

## Email decoration

When an email is sent from a non-production environment, `cofferdam` decorates
the subject and body so recipients immediately know the source:

- **Subject:** `STAGING - Weekly Sales Report`
- **Body:** a warning banner (HTML) or a notice line (plain text) prepended to
  the original content

Decoration is on by default for any non-production environment and can be
disabled with `decorate = false` under `[mail]`.

## Example policy

```toml
environment = "staging"
default_decision = "deny"

[mail]
mode = "sink"
sink = "dev-inbox@example.internal"   # all outbound mail redirected here

[integrations.windmill]
enabled = true
kind = "vendor_api"
credential = "windmill_default"
allowed_hosts = ["sandbox.windmill.dev"]
allowed_methods = ["GET", "POST"]
allowed_operations = ["read", "write"]

[credentials.windmill_default]
profile = "staging"
secret_env = "WINDMILL_API_KEY"

[integrations.stripe]
enabled = true
kind = "payment"
credential = "stripe_default"
allowed_hosts = ["api.stripe.com"]
allow_authorize = true
allow_capture = false            # never capture money outside Production

[credentials.stripe_default]
profile = "sandbox"
secret_env = "STRIPE_SANDBOX_SECRET_KEY"

# Non-secret, environment-specific settings live in their own section; the
# credential names only where the key material comes from (ADR-0014).
[integrations.object_store]
enabled = true
kind = "file_transfer"
credential = "object_store_keys"
config = "object_store_staging"
allowed_hosts = ["s3.staging.example.internal"]
allowed_methods = ["GET", "PUT", "DELETE"]

[configs.object_store_staging]
endpoint_url = "https://s3.staging.example.internal"
bucket_name = "example-erpnext-staging"
region_name = "auto"
presigned_get_expiry_seconds = 300

[credentials.object_store_keys]
profile = "staging"

[credentials.object_store_keys.env]   # a credential may carry several secrets
access_key_id = "OBJECT_STORE_ACCESS_KEY_ID"
secret_access_key = "OBJECT_STORE_SECRET_ACCESS_KEY"

[effects.email.customer]
enabled = false                  # no customer email in Staging

[effects.email.internal]
enabled = true
allow_domains = ["example.internal"]
```

A second, fuller example — object storage with structured config and a
multi-part credential — ships at
[`examples/environment_policy.dev-r2.toml`](examples/environment_policy.dev-r2.toml).

## Policy file reference

Every section and key the policy file accepts. **Unknown keys are rejected**:
a typo fails at load with the offending key and the permitted keys named, rather
than silently disabling a guard.

### Top level

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `environment` | `production` \| `staging` \| `test` \| `dev` | *required* | Which environment this policy governs |
| `default_decision` | `allow` \| `deny` | `deny` | Verdict when nothing more specific matches. `allow` in production is rejected |
| `[mail]` | table | — | Environment-wide mail handling |
| `[integrations.<name>]` | table | — | What each named integration may do |
| `[configs.<name>]` | table | — | Structured, **non-secret** settings |
| `[credentials.<name>]` | table | — | Where secret material comes from |
| `[effects.<kind>.<scope>]` | table | — | Scoped rules for effect classes that are not one named integration |

### `[integrations.<name>]`

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `enabled` | bool | `false` | A disabled integration always denies |
| `kind` | enum | *required* | `vendor_api`, `email`, `payment`, `webhook`, `report_delivery`, `file_transfer` |
| `credential` | string | — | Name of a `[credentials.*]` table |
| `config` | string | — | Name of a `[configs.*]` table |
| `allowed_hosts` | list[str] | `[]` | Bare hostnames — not URLs |
| `allowed_methods` | list[str] | `[]` | HTTP methods |
| `allowed_operations` | list[str] | `[]` | Application-defined operation names |
| `allow_authorize` | bool | `false` | `kind = "payment"`: permit authorization |
| `allow_capture` | bool | `false` | `kind = "payment"`: permit capture |

> **An empty allowlist denies.** If you pass a host, method, or operation to
> `decide()` and the matching allowlist is empty, the answer is *deny*. Listing
> nothing is not "no opinion" — it is "nothing is permitted".

### `[configs.<name>]` — structured, non-secret settings

Environment-specific settings your application needs but that are **not secret**:
an endpoint, a bucket, a region, a prefix, a timeout, a feature switch. Values
may be any TOML scalar, array, or nested table, and cofferdam does not interpret
them — no policy decision depends on a config value.

```toml
[configs.object_store_dev]
endpoint_url = "https://abc123.r2.cloudflarestorage.com"
bucket_name = "foo-erpnext-dev"
region_name = "auto"
attachment_prefix = "sites/foo/attachments/"
presigned_get_expiry_seconds = 300
delete_on_file_delete = false
allowed_extensions = ["pdf", "png"]

[configs.object_store_dev.retry]      # nested tables are fine
maxAttempts = 3                       # so is CamelCase — keys are never rewritten
```

- **Keys keep their exact casing.** Nothing is lower- or upper-cased, so a key
  your vendor's SDK spells `maxAttempts` stays `maxAttempts`.
- **Do not put secrets here.** `cofferdam validate --strict` rejects config keys
  whose *names* indicate secret material (`password`, `secret`, `token`,
  `api_key`, `private_key`, …) and points you at `[credentials.*]`. Identifiers
  are exempt: `account_id` and `access_key_id` pass, `secret_access_key` does
  not. The check reads key names only, never values.
- A reference from an integration must resolve: `config = "typo_here"` fails at
  load, not at 3 a.m.

### `[credentials.<name>]` — where secret material comes from

A credential names *where* a secret lives. It is not the secret. `profile` is a
free-form label recorded in the policy and shown by `cofferdam inspect`; the
decision engine does not interpret it.

**One secret, from the environment** — the common case:

```toml
[credentials.windmill_default]
profile = "staging"
secret_env = "WINDMILL_API_KEY"
```

**Several related secrets** — an access-key pair, for example. The `env`
sub-table maps a logical name you choose to the variable holding it:

```toml
[credentials.object_store_keys]
profile = "dev"

[credentials.object_store_keys.env]
access_key_id = "R2_ACCESS_KEY_ID"
secret_access_key = "R2_SECRET_ACCESS_KEY"
```

**A raw inline secret** — parses, but is refused unless you explicitly opt in at
the call site, and `--strict` rejects it outright. Using it makes the policy file
itself secret material:

```toml
[credentials.legacy]
profile = "dev"
secret_value = "…"        # discouraged; see ADR-0007
```

A credential uses the `env` table *or* a single-valued source, never both —
declaring both is a load-time error rather than a silent precedence rule.

### `[mail]`

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `mode` | `deny` \| `sink` \| `allow_internal` | `deny` | How outbound mail is handled |
| `sink` | string | — | Address everything is redirected to when `mode = "sink"` |
| `allow_domains` | list[str] | `[]` | Domains permitted when `mode = "allow_internal"` |
| `decorate` | bool | `true` | Label non-production subject and body; `false` opts out |

### `[effects.<kind>.<scope>]`

| Key | Type | Default | Meaning |
|-----|------|---------|---------|
| `enabled` | bool | `false` | Whether that scoped class of effect is permitted |
| `allow_domains` | list[str] | `[]` | Domains permitted for that scope |

## Resolving config and secrets

An integration can name both a config and a credential, and your application
resolves each independently — settings from the policy file, secrets from the
process environment:

```python
integration = policy.integrations["object_store"]
config  = policy.resolve_config(integration.config)           # -> dict, keys as written
secrets = policy.resolve_credentials(integration.credential)  # -> {logical name: secret}

client = S3Client(
    endpoint_url=config["endpoint_url"],
    bucket_name=config["bucket_name"],
    region_name=config.get("region_name", "auto"),
    access_key_id=secrets["access_key_id"],
    secret_access_key=secrets["secret_access_key"],
)
```

| Call | Returns | Raises |
|------|---------|--------|
| `policy.resolve_config(name)` | A copy of the config table; mutating it cannot alter the policy | `ConfigError` if undefined — a typo fails closed instead of yielding an empty dict |
| `policy.resolve_secret(name)` | One secret, from `secret_env` | `SecretResolutionError` if the variable is unset |
| `policy.resolve_credentials(name)` | Every secret in the `env` table | `SecretResolutionError` naming the first unset variable |
| `policy.resolve_json_secret(name)` | A secret that is itself a JSON object, parsed | `SecretResolutionError` if it is not a JSON object — the value is never echoed |

No resolver ever puts a secret value into a log line, an exception message, or a
traceback.

## CLI

```console
$ cofferdam validate  path/to/environment_policy.toml
$ cofferdam inspect   path/to/environment_policy.toml
$ cofferdam decide    path/to/environment_policy.toml \
      --integration windmill --kind vendor_api --operation write \
      --method POST --url https://sandbox.windmill.dev/api/jobs/run \
      --credential windmill_default
```

`validate` exits non-zero on invalid policy. `inspect` prints a redacted
summary — secrets are never shown. `decide` prints allow/deny and a stable
reason code.

## Local development

A real policy file can reference many credentials — one `secret_env` per
integration. Each of those environment variables has to be present in every
process that resolves it: the web server, every worker, and whatever shell a
developer or an AI pair-programming agent is using while writing integration
code. Prefixing every command with a wall of `SECRET_X=... SECRET_Y=...`
doesn't scale, and `cofferdam` deliberately doesn't solve this for you —
`resolve_secret` only ever reads `os.environ`, never an adjacent `.env` file
or a path named in the policy ([ADR-0013](docs/adr/0013-no-secret-autoloading-direnv-docs.md)).
That keeps "missing env var" a real, fail-closed condition (ADR-0005) and
keeps the policy file itself free of secret-custody concerns (ADR-0007).

Instead, provision local secrets at the shell level with
**[direnv](https://direnv.net/)**, so every tool started from your project
directory — an interactive shell, `bench start`, `pytest`, `cofferdam decide`,
or an AI agent's own shell — inherits the same variables automatically.

**Install:**

```console
$ brew install direnv        # macOS
$ sudo apt install direnv    # Debian/Ubuntu
```

Then hook it into your shell (add to `~/.bashrc` or `~/.zshrc`):

```bash
eval "$(direnv hook bash)"   # or: eval "$(direnv hook zsh)"
```

Open a new shell (or `source` the rc file) after adding the hook.

**Use:** create a `.envrc` file next to `environment_policy.toml` (or at the
project root) exporting one variable per `secret_env` your policy references:

```bash
# .envrc — never commit this file
export WINDMILL_API_KEY="sk_test_..."
export STRIPE_SANDBOX_SECRET_KEY="sk_test_..."
```

Then authorize it once per directory:

```console
$ direnv allow
```

From then on, `cd`-ing into that directory loads those variables into the
shell, and leaving it unloads them again — no manual exporting, no per-tool
setup. Add `.envrc` to `.gitignore` immediately; it holds real secret values.

`direnv` is a local-development convenience only — it affects shells it hooks
into, not processes started by a process manager. Staging/production workers
and the web server should get their env vars from the process manager instead
(systemd `EnvironmentFile=`, supervisor `environment=`) or a real secrets
manager, not from `.envrc`.

## Frappe / ERPNext

`cofferdam` was designed with ERPNext and Frappe Framework in mind — the
database restore pattern is a daily reality for that ecosystem. The core
library has no dependency on Frappe and works with any Python application.

For full Frappe/ERPNext integration — automatic policy discovery by bench
site, interception of `frappe.sendmail`, and webhook delivery gating — see
**[cofferdam-app](https://github.com/Datahenge/cofferdam-app)**, a companion
Frappe app that installs into a bench alongside your ERPNext site.

## Requirements specification

This library is built with a document-driven workflow. See [`docs/`](docs/)
for the full requirements specification and [`docs/adr/`](docs/adr/) for
architecture decisions.

## License

Apache-2.0 © 2026 Brian Pond / Datahenge LLC
