# 02 — Conceptual Model

`cofferdam` evaluates whether a specific outbound side effect is permitted in the
current runtime environment. A decision considers up to seven dimensions.

## Dimensions

| Dimension | Values (examples) | Model type |
|-----------|-------------------|------------|
| **Environment** (`BR-MODEL-001`) | `production`, `staging`, `test`, `dev` | `Environment` |
| **Side-effect kind** (`BR-MODEL-002`) | `vendor_api`, `email`, `payment`, `webhook`, `report_delivery`, `file_transfer` | `SideEffectKind` |
| **Integration name** | `windmill`, `stripe`, `mailgun`, … | key in `integrations` |
| **Operation** | `read`, `write`, `authorize`, `capture`, `send_email`, `sync`, … | `allowed_operations` |
| **HTTP method** (where relevant) | `GET`, `POST`, … | `allowed_methods` |
| **Target host** (where relevant) | `sandbox.windmill.dev` | `allowed_hosts` |
| **Credential reference** | `windmill_default` | key in `credentials` |

Recipient/customer/supplier scope is modeled separately for email (see
[07](07-email-policy.md)).

## The single question

The engine answers **"Is this specific side effect allowed here?"** — never a
single global side-effect flag. Two integrations of the same kind can have
different verdicts; one operation on an integration can be allowed while another
is denied (e.g. Stripe `authorize` permitted, `capture` denied in Staging).

## Relationships

```
Policy
├── environment            (exactly one)
├── default_decision       (allow | deny; deny is the safe default)
├── mail                   (optional MailPolicy)
├── credentials[name]      -> Credential  (profile + secret source)
├── integrations[name]     -> Integration (kind, credential ref, allowlists)
└── effects[kind][scope]   -> EffectRule  (e.g. effects.email.customer)
```

- An **Integration** may reference a **Credential** by name; the reference is
  validated (the credential must exist, [12](12-validation.md)).
- A **Credential** names a *source* of a secret (an env var), not the secret.
- **Effects** express scoped allow/deny rules for classes that are not a single
  named integration (customer email, internal email, external scheduled reports).

## Why not one global switch

A global on/off flag is too coarse: teams legitimately need sandbox API calls and
payment *authorization* while blocking customer email and payment *capture*. The
per-integration / per-operation model expresses the minimum necessary precision.
See [ADR-0005](adr/0005-fail-closed-by-default.md) for the full rationale.
