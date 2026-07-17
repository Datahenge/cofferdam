# 15 — Open Questions & Resolutions

The source requirements (§20) left seven questions open. This document records
how each was **resolved as a working default** (with an ADR), and flags where I
would still value your confirmation. Defaults are chosen for a professional
open-source PyPI package and are all reversible before 1.0.

## Resolved (with rationale)

| # | Question | Resolution | ADR |
|---|----------|------------|-----|
| Q1 | Final package name | **`cofferdam`** for distribution, import, and CLI | [0003](adr/0003-package-and-cli-name-cofferdam.md) |
| Q2 | Allow raw `secret_value` in v1? | Parsed but **rejected by default**; opt-in only | [0007](adr/0007-env-var-credentials.md) |
| Q3 | HTTP helper: `requests`, `httpx`, both? | **`httpx`**, as an optional `cofferdam[http]` extra | [0008](adr/0008-httpx-optional-http-helper.md) |
| Q4 | Redirect following default | **Disabled by default**; re-validate host if enabled | [0008](adr/0008-httpx-optional-http-helper.md) |
| Q5 | Email helpers: Frappe API in v1 or policy-only? | **Policy-only** in the library; Frappe email intercepted in `cofferdam-app` (see Q8) | [0007](adr/0007-env-var-credentials.md) (scope), [0011](adr/0011-frappe-app-first-release.md) |
| Q6 | Policy caching: mtime or explicit reload? | **Explicit reload** in v1; mtime deferred | [0010](adr/0010-frappe-isolation.md) |
| Q7 | Schema validation: Pydantic/attrs/dataclasses/typeddict? | **Pydantic v2** | [0006](adr/0006-pydantic-v2-schema-validation.md) |
| Q8 | Ship a Frappe app, and if so when? | **Yes, in the first release**, as `cofferdam-app` (`datahenge/cofferdam-app`). Intercepts Frappe's native outbound paths via hooks + monkey-patching. Named to avoid Frappe Technologies trademark concerns. | [0011](adr/0011-frappe-app-first-release.md) |

## Where your confirmation would help

1. **Package name `cofferdam` on PyPI** — ✅ **CONFIRMED 2026-07-17.** Base
   library and CLI publish as `cofferdam`. The Frappe app (`cofferdam-app`) is
   NOT on PyPI; Frappe apps cannot be installed via pip.
2. **Minimum Python** — ✅ **CONFIRMED 2026-07-17. 3.10+** (with `tomli` backport).
   Frappe v15 requires `>=3.10,<3.15`; bumping to 3.11+ would break v15 sites
   still on 3.10. stdlib `tomllib` deferred.
3. **License** — ✅ **CONFIRMED 2026-07-17. Apache-2.0.** Chosen for the explicit
   patent grant, which is appropriate for a security-adjacent library used in
   commercial ERP deployments.
4. **Repository namespace** — ✅ **CONFIRMED 2026-07-17.** `github.com/datahenge/cofferdam`.

Items 1–4 are resolved. Q9 below is newly opened.

## New open questions

### Q10 — Email decoration ✅ CONFIRMED 2026-07-17

**Context:** Non-production emails can look identical to Production emails —
same sender, same content — giving recipients no way to know the source.

**Resolution:** `cofferdam.mail` provides pure functions (`decorate_subject`,
`decorate_body`, `decorate_email`, `should_decorate`) that mutate subject and
body before send. All decisions confirmed:

| Decision | Resolution |
|----------|------------|
| Environment label | Actual environment name, uppercased (`STAGING`, `TEST`, `DEV`) |
| Subject format | `{ENV} - {original subject}` |
| Body format | Detect HTML vs plain-text; HTML → `<div>` banner after `<body>` or prepended; plain-text → notice line + blank line |
| HTML detection | Case-insensitive substring match for `<html` or `<body`; no external parser |
| Default behavior | **On by default** for all non-production envs and all mail modes; opt out via `decorate = false` in `[mail]` |
| Production | Never decorates regardless of `decorate` setting |
| Where logic lives | `cofferdam.mail` pure functions — fully unit-testable without Frappe |

Spec: `docs/07-email-policy.md` (`BR-EMAIL-DECORATE-001` – `BR-EMAIL-DECORATE-006`).
Schema change: `MailPolicy.decorate: bool = True` in `cofferdam.models`.

### Q9 — `cofferdam-app` branch strategy ✅ CONFIRMED 2026-07-17

**Resolution:** Option A — two long-lived branches in one repo (`version-15`,
`version-16`), mirroring the branch convention used by `frappe/frappe` and
`frappe/erpnext` themselves. Users install via `bench get-app ... --branch
version-15` or `version-16`. Fixes are cherry-picked across branches as needed.

Item 12 (app scaffold) may now proceed.

### Q11 — ERPNext-specific outbound interception ⏳ OPEN

**Context:** Item 14 intercepts Frappe's generic "Webhook Request Log" mechanism.
ERPNext (by far the most widely deployed Frappe app) has its own outbound paths
that bypass that mechanism entirely. ERPNext is the primary reason most Frappe
sites exist, so this gap matters in practice.

**Known outbound surfaces, by risk:**

| Risk | Surface | Mechanism |
|------|---------|-----------|
| Critical | Payment gateways (Stripe, Razorpay, PayPal, Braintree) | Direct `requests` calls; some via `frappe.integrations.utils` |
| Critical | Shipping carriers (FedEx, UPS, DHL, Shipstation) | Direct `requests` or `frappe.integrations.utils` |
| High | E-commerce connectors (Shopify, WooCommerce) | Direct API sync; bidirectional — staging can write back to production storefronts |
| High | SMS gateways (Twilio, Exotel) | Direct calls |
| High | Slack (`erpnext/support/doctype/slack_webhook_url/`) | `requests.post()` directly; no Webhook Request Log entry |
| Medium | Cloud backups (S3, Dropbox, Google Drive) | boto3 / provider SDK directly |
| Low | Currency exchange rate fetching | Read-only external API |
| Low | Google Maps / geocoding | Read-only |

The cofferdam decision engine already has explicit `allow_authorize` /
`allow_capture` gates (BR-DECISION-008) designed for the payment gateway risk.
The gap is that ERPNext calls processor APIs directly rather than through
Frappe's generic webhook mechanism.

**High-leverage interception point:** Frappe's `"Integration Request"` DocType
(`frappe/integrations/doctype/integration_request/`) is written by
`frappe.integrations.utils.make_request()` / `make_post_request()` /
`make_get_request()` before making outbound calls. A single `doc_events` hook
on `"Integration Request" before_insert` would intercept a large portion of the
above list. Integrations that call `requests` directly (some payment gateways,
Shopify connector) would still escape it and require per-DocType hooks.

**Preference (2026-07-17):** Strong intent to support ERPNext interception.

**Proposed approach:** Conditional import with graceful fallback — if ERPNext is
not installed on the bench, the ERPNext-specific hooks simply do not register.

```python
try:
    import erpnext  # noqa: F401
    _ERPNEXT_AVAILABLE = True
except ImportError:
    _ERPNEXT_AVAILABLE = False
```

Hook registration in `hooks.py` would be conditional on `_ERPNEXT_AVAILABLE`,
or handler functions would early-return when it is False.

**Open sub-questions:**
1. Should `"Integration Request" before_insert` be implemented first as the
   highest-leverage single hook, with per-DocType hooks added incrementally?
2. Should the ERPNext-specific `doc_events` live in a separate
   `cofferdam_app/erpnext.py` module to keep the Frappe-only surface clean
   and independently testable?
3. Is the graceful-import pattern sufficient, or does bench's app ordering
   guarantee ERPNext is importable when cofferdam_app initializes?

## Implementation sequence (document-driven)

**`cofferdam` library (`datahenge/cofferdam`)**

1. ✅ TOML schema + example policy
2. ✅ Config loading + typed policy objects
3. ✅ Schema + semantic validation
4. ✅ Decision engine
5. ✅ Env-var credential resolution + redaction
6. ✅ CLI `validate` / `inspect` / `decide`
7. ✅ Policy-checked HTTP helper (send path + redirect re-validation)
8. ✅ Email policy checks + decoration
9. ❌ Frappe helper module — cancelled (ADR-0012). Site discovery belongs in `cofferdam-app`; core library has no Frappe dependency.
10. ✅ Restore-safety + host-parsing tests (Frappe leg removed per ADR-0012; HTTP and email legs covered in test_http.py and test_mail.py)
11. ✅ README rewritten: ecosystem-agnostic framing, cofferdam-app link, Apache-2.0 license (ERPNext usage examples belong in cofferdam-app docs)

**`cofferdam-app` Frappe app (`datahenge/cofferdam-app`)**

12. ✅ App scaffold (bench app structure, `pyproject.toml` declaring `cofferdam` dependency; targets Frappe v16 / Python 3.14+; `version-15` backport deferred)
13. ✅ `frappe.sendmail` interception via `doc_events` on Email Queue `before_insert`, routed through policy + decoration engine
14. ✅ Webhook delivery interception via `doc_events` on Webhook Request Log `before_insert`; policy key `integrations.frappe_webhooks`
15. ✅ App tests (28 tests; Frappe stubbed via sys.modules — no bench required; covers policy cache, email interception, webhook interception, all fail-closed paths)
16. ✅ App README and install guide (installation, policy examples for all modes, decoration, reload, coverage table, dev workflow)
