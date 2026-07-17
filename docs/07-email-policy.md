# 07 — Email Policy

Implemented in `cofferdam.mail`. v1 provides **policy checks**, not a replacement
for Frappe's email subsystem ([ADR-0011](adr/0011-frappe-app-first-release.md)).
Project-specific ERPNext email code calls these checks to avoid unsafe sends.

## Supported dispositions (`BR-EMAIL-*`)

- **BR-EMAIL-001 — Top-level mail mode.** `mail.mode` is one of `deny` (default),
  `sink` (redirect all mail to a sink address, e.g. Mailpit), or an
  internal-only allowance. `mail.sink` names the sink; `mail.allow_domains` lists
  internal domains.
- **BR-EMAIL-002 — Recipient decision.** `check_recipient(policy, recipient=...,
  recipient_class=...)` returns a `MailDecision` (`allowed`, `reason_code`,
  optional `redirect_to`, optional `subject_prefix`). Fails closed when no rule
  permits the recipient.
- **BR-EMAIL-003 — Deny external mail in non-Production** unless a rule permits it.
- **BR-EMAIL-004 — Allow internal domains** listed in `allow_domains`.
- **BR-EMAIL-005 — Redirect to a sink address** when `mail.mode = "sink"`.
- **BR-EMAIL-006 — Decorate subject and body** in non-Production to make the
  environment of origin unambiguous. See `BR-EMAIL-DECORATE-*` below for the
  full specification.
- **BR-EMAIL-007 — Block customer/supplier recipient classes** (`effects.email.customer`
  disabled) while allowing internal (`effects.email.internal`).
- **BR-EMAIL-008 — Allow explicit test recipients.**

## Scoped effect rules

Email interacts with `effects.email.<scope>`:

```toml
[effects.email.customer]
enabled = false            # never mail customers in Staging

[effects.email.internal]
enabled = true
allow_domains = ["example.internal"]
```

## Email decoration (`BR-EMAIL-DECORATE-*`)

Non-production environments can send emails that look identical to Production
emails — same sender address, same content, same formatting. A recipient has no
way to distinguish them. Decoration solves this by mutating subject and body
before send so the environment of origin is unmistakable.

### When decoration applies

- **BR-EMAIL-DECORATE-001** — Decoration applies to **all** non-production
  environments (`staging`, `test`, `dev`) regardless of mail mode (`deny`,
  `sink`, `allow_internal`, or any future mode). It never applies to
  `production`.
- **BR-EMAIL-DECORATE-002** — Decoration is **on by default**. Add
  `decorate = false` under `[mail]` to disable it. Setting `decorate = true`
  on a `production` policy is a no-op. If no `[mail]` section is present,
  decoration is still active.

```toml
[mail]
mode = "sink"
sink = "mailpit"
decorate = false          # opt out of decoration for this environment
```

### Subject decoration

- **BR-EMAIL-DECORATE-003** — Prepend `{ENVIRONMENT} - ` to the original
  subject, where `ENVIRONMENT` is the policy `environment` value in uppercase.

  | Environment | Original subject | Decorated subject |
  |------------|-----------------|-------------------|
  | `staging`  | `Weekly Sales Report` | `STAGING - Weekly Sales Report` |
  | `test`     | `Invoice #1042 Ready` | `TEST - Invoice #1042 Ready` |
  | `dev`      | `Password Reset` | `DEV - Password Reset` |

### Body decoration

- **BR-EMAIL-DECORATE-004 — HTML detection.** The body is treated as HTML if it
  contains the substring `<html` or `<body` (case-insensitive). Otherwise it is
  treated as plain text. No external parser is used.
- **BR-EMAIL-DECORATE-005 — HTML banner.** Inject the following `<div>` banner
  immediately after the first `<body` tag (case-insensitive). If no `<body` tag
  is present, prepend the banner to the body string.

  ```html
  <div style="background:#f59e0b;color:#000;padding:8px 12px;font-family:sans-serif;font-weight:bold;margin-bottom:8px;">
    ⚠ This email was sent from the STAGING environment — not Production.
  </div>
  ```

  The environment name in the banner uses the same uppercased value as the
  subject prefix.

- **BR-EMAIL-DECORATE-006 — Plain-text notice.** Prepend the following two lines
  to the body (note the blank line separator):

  ```
  [STAGING] This email was sent from the staging environment — not Production.

  {original body}
  ```

### Public API

```python
from cofferdam.mail import decorate_subject, decorate_body, decorate_email, should_decorate

# Check whether decoration is active for this policy
if should_decorate(policy):
    subject = decorate_subject(subject, environment=policy.environment.value)
    body    = decorate_body(body, environment=policy.environment.value)

# Or use the combined helper
subject, body = decorate_email(subject, body, policy=policy)
```

`decorate_email` is a convenience wrapper: it calls `should_decorate` and
returns the original strings unchanged when decoration is disabled or the
environment is production.

