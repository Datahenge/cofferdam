# 07 — Email Policy

Implemented in `cofferdam.mail`. v1 provides **policy checks**, not a replacement
for Frappe's email subsystem ([ADR-0007](adr/0007-env-var-credentials.md) scope
note). Project-specific ERPNext email code calls these checks to avoid unsafe
sends.

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
- **BR-EMAIL-006 — Prefix subjects** in non-Production (e.g. `[STAGING]`) via
  `subject_prefix`.
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

## Scope note

The library does not replace Frappe's entire email system in the first release.
It provides enough policy checks and helper functions for ERPNext custom code to
avoid unsafe sends. A deeper Frappe email hook may come later behind the optional
Frappe layer.

> **Status:** signatures are frozen here; the `cofferdam.mail` bodies are
> implemented in the email milestone (see [implementation sequence](15-open-questions.md)).
