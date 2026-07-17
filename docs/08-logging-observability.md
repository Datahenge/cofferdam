# 08 — Logging & Observability

## Structured decision info (`BR-LOG-001`)

Every decision is expressible as a structured, redacted record via
`Decision.as_log_dict()`:

| Field | Example |
|-------|---------|
| `allowed` | `false` |
| `reason_code` | `host_not_allowed` |
| `environment` | `staging` |
| `integration` | `windmill` |
| `kind` | `vendor_api` |
| `operation` | `write` |
| `method` | `POST` |
| `host` | `windmill.prod.example.com` |
| `credential` | `windmill_default` *(reference name only)* |
| `detail` | free-text, secret-free |

## Never logged (`BR-LOG-002`)

Logs must **never** include: API keys, tokens, passwords, `Authorization`
headers, full request bodies (by default), or sensitive query parameters. This is
enforced by construction — the log record carries reference *names*, and secret
values never enter `Decision`, exceptions, or CLI output.

## Logger (`BR-LOG-003`)

- The **core library uses the standard `logging` module** under the logger name
  `cofferdam` (and child loggers such as `cofferdam.decisions`). It never
  configures handlers itself; the host application owns configuration.
- In **Frappe integration mode** ([11](11-frappe-integration.md)), logging may use
  Frappe's logging facilities *when available*, but the core path stays on stdlib
  `logging` so the package works with no Bench.

## Emission policy

The engine returns decisions; it does not force logging. Callers (including the
`http` helper and the CLI) decide when to emit `as_log_dict()`. This keeps the
decision function pure and side-effect free, which also makes it trivially
testable ([13](13-testing.md)).
