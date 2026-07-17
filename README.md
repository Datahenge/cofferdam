# cofferdam

> Hold back Production outbound side effects from flooding non-Production
> Frappe/ERPNext environments after a database restore.

A **cofferdam** is a temporary watertight enclosure pumped dry so crews can
build on a submerged foundation. This library is the software equivalent: when
you restore a Production database into Staging, Test, or Dev, it holds back the
Production outbound behavior — customer emails, live API calls, payment
captures, webhooks, scheduled report delivery — so the restored data can be
worked on safely without leaking real-world side effects.

`cofferdam` is a **plain Python library and CLI**. It is **not a Frappe app**:
it defines no DocTypes, no MariaDB tables, no migrations, and the core package
never `import frappe`. It runs and tests as an ordinary Python package.

## The problem

ERPNext/Frappe environments are routinely refreshed by restoring Production
MariaDB backups into Dev/Test/Staging. That restored database carries Production
**integration settings, email accounts, API endpoints, encrypted credentials,
payment configuration, webhooks, and scheduled jobs**. If the non-Production
environment is allowed to act on those values, it behaves as if it were
Production — mailing customers, charging cards, and calling live vendor APIs
against real data.

## The design rule

> **Restored SQL owns business intent. Local environment config owns execution
> authority.**

`cofferdam` puts execution authority in a **local TOML policy file** that lives
on the environment's filesystem — never in the database, never restored from a
backup. The engine answers one question for every outbound action:

> *Is this specific side effect allowed **here**?*

It **fails closed**: absent, incomplete, or invalid policy denies the action.

## Example policy

```toml
environment = "staging"
default_decision = "deny"

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

## Usage (planned public API)

```python
from cofferdam import load_policy

policy = load_policy("sites/staging.example.com/environment_policy.toml")

# Raise if this side effect is not explicitly permitted here.
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

Policy-checked HTTP (optional `cofferdam[http]` extra):

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

Inside a Frappe site (no Frappe app required):

```python
from cofferdam.frappe import get_policy

policy = get_policy()   # locates sites/{site}/environment_policy.toml
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

`validate` exits non-zero on invalid policy. `inspect` prints a **redacted**
summary. `decide` prints allow/deny plus a reason code, never a secret.

## Status

Early development. This repository is being built with a document-driven
("Scribe Coding") workflow: see [`docs/`](docs/) for the requirements
specification and [`docs/adr/`](docs/adr/) for the architecture decisions.

## Installation

```console
$ pip install cofferdam            # core library + CLI
$ pip install "cofferdam[http]"    # adds the policy-checked HTTP helper (httpx)
```

## License

MIT © 2026 Brian Pond / Datahenge LLC
