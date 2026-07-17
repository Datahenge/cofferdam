# Architecture Decision Records

Each ADR records one decision: its context, the decision itself, and the
consequences. ADRs are immutable — to change a decision, add a new ADR that
supersedes the old one. Format after Michael Nygard's ADR template.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-python-library-not-frappe-app.md) | Ship a Python library, not a Frappe app | Accepted |
| [0003](0003-package-and-cli-name-cofferdam.md) | Name the package, import, and CLI `cofferdam` | Accepted |
| [0004](0004-toml-policy-format.md) | Use TOML for the policy file | Accepted |
| [0005](0005-fail-closed-by-default.md) | Fail closed by default | Accepted |
| [0006](0006-pydantic-v2-schema-validation.md) | Validate the schema with Pydantic v2 | Accepted |
| [0007](0007-env-var-credentials.md) | Env-var credentials; reject raw secrets by default | Accepted |
| [0008](0008-httpx-optional-http-helper.md) | HTTP helper wraps httpx as an optional extra | Accepted |
| [0009](0009-structured-host-matching.md) | Structured whole-hostname matching | Accepted |
| [0010](0010-frappe-isolation.md) | Isolate Frappe behind one guarded module | Accepted |
