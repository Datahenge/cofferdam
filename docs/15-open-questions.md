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
| Q5 | Email helpers: Frappe API in v1 or policy-only? | **Policy-only** in v1 | [0007](adr/0007-env-var-credentials.md) (scope) |
| Q6 | Policy caching: mtime or explicit reload? | **Explicit reload** in v1; mtime deferred | [0010](adr/0010-frappe-isolation.md) |
| Q7 | Schema validation: Pydantic/attrs/dataclasses/typeddict? | **Pydantic v2** | [0006](adr/0006-pydantic-v2-schema-validation.md) |

## Where your confirmation would help

1. **Package name `cofferdam` on PyPI** — memorable and matches the repo, but it
   drops the `frappe`/`erpnext` discoverability of the provisional names. Option:
   keep `cofferdam` and add keywords (done) vs. publish under a `frappe-`-prefixed
   name. *Default: `cofferdam`.*
2. **Minimum Python** — currently **3.10+** (with a `tomli` backport). Dropping to
   3.11+ would let us use stdlib `tomllib` with zero backport. *Default: 3.10+.*
3. **License** — **MIT**. If Datahenge prefers Apache-2.0 (explicit patent grant)
   for a security-adjacent tool, say so. *Default: MIT.*
4. **Repository namespace** — URLs currently point at
   `github.com/datahenge/cofferdam`. Confirm the org/owner.

None of these block progress; they are easy to change now and hard to change
after publishing.

## Implementation sequence (document-driven)

1. ✅ TOML schema + example policy
2. ✅ Config loading + typed policy objects
3. ✅ Schema + semantic validation
4. ✅ Decision engine
5. ✅ Env-var credential resolution + redaction
6. ✅ CLI `validate` / `inspect` / `decide`
7. ⏳ Policy-checked HTTP helper (send path + redirect re-validation)
8. ⏳ Email policy checks
9. ⏳ Frappe helper module (site discovery, caching)
10. ◑ Restore-safety + host-parsing tests (core done; HTTP/email/Frappe pending)
11. ◑ README with ERPNext usage examples (core README done; deepen per milestone)
