# 14 — Acceptance Criteria

The first usable version (v0.1) is complete when all of the following hold. Each
maps to tests and/or milestones.

| # | Criterion | Status |
|---|-----------|:------:|
| 1 | A TOML policy file can be loaded and validated. | ✅ |
| 2 | A decision allows Windmill sandbox calls in Staging while blocking a Production Windmill host. | ✅ |
| 3 | A decision denies customer email in Staging while allowing internal email or sink routing. | ⏳ email milestone |
| 4 | Credential references resolve from environment variables without logging values. | ✅ |
| 5 | The HTTP helper blocks disallowed hosts before sending credential-bearing requests. | ◑ guard active; send body in HTTP milestone |
| 6 | The CLI can validate, inspect, and simulate a decision. | ✅ |
| 7 | Frappe helper code can locate a site policy without requiring a Frappe app. | ⏳ Frappe milestone |
| 8 | Missing or invalid policy fails closed. | ✅ |
| 9 | Tests cover the core restore-safety scenarios. | ✅ |
| 10 | Documentation includes example TOML, recommended location, and ERPNext refresh guidance. | ✅ |

Legend: ✅ done · ◑ partial (guard implemented, remaining work scoped) · ⏳ planned.

## Current state (initial scaffolding)

The decision engine, config loading/validation, credential resolution,
redaction, and the CLI are implemented and tested (31 passing tests, `ruff` and
`mypy --strict` green). The HTTP send path, email checks, and Frappe discovery
have **frozen signatures and specifications** but deferred bodies, per the
document-driven sequence in [15 — Open Questions](15-open-questions.md).
