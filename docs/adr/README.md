# Architecture Decision Records

Each ADR records one decision: its context, the decision itself, and the
consequences. ADRs are immutable — to change a decision, add a new ADR that
supersedes the old one. Format after Michael Nygard's ADR template.

| ADR | Title | Status |
|-----|-------|--------|
| [0002](0002-python-library-not-frappe-app.md) | Ship a Python library, not a Frappe app | Accepted |
| [0003](0003-package-and-cli-name-cofferdam.md) | Name the package, import, and CLI `cofferdam` | Accepted |
| [0004](0004-toml-policy-format.md) | Use TOML for the policy file | Accepted |
| [0005](0005-fail-closed-by-default.md) | Fail closed by default | Accepted |
| [0006](0006-pydantic-v2-schema-validation.md) | Validate the schema with Pydantic v2 | Accepted |
| [0007](0007-env-var-credentials.md) | Env-var credentials; reject raw secrets by default | Accepted |
| [0008](0008-httpx-optional-http-helper.md) | HTTP helper wraps httpx as an optional extra | Accepted |
| [0010](0010-frappe-isolation.md) | Isolate Frappe behind one guarded module | Superseded by ADR-0012 |
| [0011](0011-frappe-app-first-release.md) | Ship a Frappe app (`cofferdam-app`) in the first release | Accepted |
| [0012](0012-remove-cofferdam-frappe-module.md) | Remove `cofferdam.frappe` from the core library | Accepted |

*ADR-0001 and ADR-0009 were deleted: neither recorded an architectural decision. 0001 was template boilerplate already covered by the ground rules; 0009 was a security requirement already fully specified in [06 — Host & URL Handling](../06-host-url-handling.md).*
