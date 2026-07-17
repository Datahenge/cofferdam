# 11 — Frappe Integration

Implemented in `cofferdam.frappe` — the **only** Frappe-aware module. `import
frappe` is attempted lazily and inside a guard, so the rest of the package
installs, imports, and tests with no Bench present
([ADR-0002](adr/0002-python-library-not-frappe-app.md),
[ADR-0010](adr/0010-frappe-isolation.md)).

## Behavior (`BR-FRAPPE-*`)

- **BR-FRAPPE-001 — Locate the site policy.** Resolve
  `sites/{site_name}/environment_policy.toml` for the current (or named) site.
- **BR-FRAPPE-002 — Honor an override.** If `site_config.json` sets
  `outbound_policy_path`, use it (resolved relative to the site directory). The
  policy itself is never stored in `site_config.json` (`BR-CONFIG-003`), and the
  resolved path must not fall under `/files/private` (`BR-CONFIG-002`).
- **BR-FRAPPE-003 — `get_policy()`** loads and **caches for the process lifetime**
  (appropriate for a long-lived worker).
- **BR-FRAPPE-004 — `reload_policy()`** discards the cache and reloads from disk,
  for tests and administrative scripts.
- **BR-FRAPPE-005 — Logging.** Use Frappe's logger when available; otherwise
  stdlib `logging` ([08](08-logging-observability.md)).
- **BR-FRAPPE-006 — Server-friendly errors.** Raise clear `cofferdam` exceptions
  suitable for server-side ERPNext code; fail closed.

## `site_config.json` override

```json
{
  "outbound_policy_path": "environment_policy.toml"
}
```

## Caching decision

v1 caches per process via explicit `reload_policy()`; mtime-based auto-invalidation
is deferred. See [ADR-0010](../adr/0010-frappe-isolation.md) for rationale.

