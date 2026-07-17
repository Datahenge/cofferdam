# 09 — Public API

The supported programmatic surface. Anything not listed here is internal and may
change without notice.

## Top-level imports

```python
from cofferdam import (
    load_policy, loads_policy,           # config
    Policy, Environment, SideEffectKind, # models
    Decision,                            # decisions
    CofferdamError, PolicyDeniedError, PolicyFileNotFoundError,
    PolicyValidationError, CredentialError, SecretResolutionError,  # errors
)
```

## Loading (`BR-API-001`)

```python
policy = load_policy("sites/staging.example.com/environment_policy.toml")
policy = load_policy(path, strict=True)   # CI/validation: stricter semantic checks
policy = loads_policy(toml_text)          # from a string
```

## Decisions (`BR-API-002`)

```python
# Raise on denial:
policy.assert_allowed(
    integration="windmill", kind="vendor_api", operation="write",
    method="POST", host="sandbox.windmill.dev", credential="windmill_default",
)

# Inspect without raising:
decision = policy.decide(integration="stripe", kind="payment", operation="capture")
if not decision.allowed:
    log.warning("blocked", extra=decision.as_log_dict())
    raise decision.to_exception()
```

`Decision` fields: `allowed`, `reason_code`, `environment`, `integration`,
`kind`, `operation`, `method`, `host`, `credential`, `detail`.
Methods: `as_log_dict()`, `message()`, `to_exception()`.

## Credentials (`BR-API-003`)

```python
secret = policy.resolve_secret("windmill_default")            # from $WINDMILL_API_KEY
secret = policy.resolve_secret("legacy", allow_raw=True)      # opt-in to raw value
```

## Policy-checked HTTP (`BR-API-004`, optional extra)

```python
from cofferdam.http import request     # requires: pip install "cofferdam[http]"

response = request(
    policy=policy, integration="windmill", operation="write",
    method="POST", url="https://sandbox.windmill.dev/api/jobs/run",
    credential="windmill_default", json=payload,
)
```

The host is parsed from `url` and evaluated *before* any request is sent
([06](06-host-url-handling.md)). Redirects are not followed by default.

## Email decoration (`BR-EMAIL-DECORATE-*`, optional)

```python
from cofferdam.mail import decorate_subject, decorate_body, decorate_email, should_decorate

# Check once whether this policy/environment decorates
if should_decorate(policy):
    subject = decorate_subject("Weekly Sales Report", environment="staging")
    # → "STAGING - Weekly Sales Report"

    body = decorate_body(body_text, environment="staging")
    # plain-text body → notice prepended
    # HTML body      → <div> banner injected after <body> tag

# Convenience: checks should_decorate internally; returns originals if inactive
subject, body = decorate_email(subject, body_text, policy=policy)
```

`should_decorate(policy)` returns `False` for `production` or when
`policy.mail.decorate = false`; `True` otherwise (including when `policy.mail`
is absent). `decorate_email` is a no-op passthrough in those cases.

## Stability

Pre-1.0 the API may change between minor versions; breaking changes are recorded
in the [CHANGELOG](../CHANGELOG.md). At 1.0 this surface is frozen under SemVer.
