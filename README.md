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

[effects.email.customer]
enabled = false                  # no customer email in Staging

[effects.email.internal]
enabled = true
allow_domains = ["example.internal"]
```

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
