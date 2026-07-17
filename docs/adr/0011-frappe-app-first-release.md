# ADR-0011 — Ship a Frappe app (`cofferdam-app`) in the first release

- **Status:** Accepted
- **Date:** 2026-07-17
- **Related:** [ADR-0002](0002-python-library-not-frappe-app.md), [ADR-0010](0010-frappe-isolation.md)

## Context

ADR-0002 deferred a Frappe app to a possible future layer, on the grounds that
the core policy engine required none of Frappe's machinery. That reasoning is
correct for the *library*, but it understated the reach problem.

As a plain Python library, `cofferdam` only guards code that explicitly calls it.
Every call site must be written cofferdam-aware by a developer who knows the
library exists. This leaves Frappe's native outbound paths — `frappe.sendmail`,
webhook delivery, and similar — entirely unguarded, regardless of whether
`cofferdam` is installed. Those native paths are the primary source of
production side-effects when a database backup is restored to a non-production
environment.

A Frappe app that intercepts those paths via `hooks.py` and targeted
monkey-patching provides immediate, zero-code-change protection for the full
Frappe surface area. It also resolves the Frappe Cloud distribution problem:
Frappe Cloud subscribers cannot `pip install` arbitrary packages, but they can
install a Frappe app from GitHub, and that app's `requirements.txt` pulls in
the `cofferdam` PyPI package automatically.

## Naming

The app is named **`cofferdam-app`** (GitHub repo: `datahenge/cofferdam-app`;
Frappe bench app package: `cofferdam_app`).

The alternative `cofferdam-frappe` was rejected. Using a framework or company
name as a prefix implies official association or endorsement — a problem the
Rust community encountered and resolved by adopting the `-rs` suffix convention
rather than a `rust-` prefix. Frappe Technologies has not published an explicit
third-party naming policy, but the same risk applies: `cofferdam-frappe` could
be read as a Frappe Technologies product. `cofferdam-app` is unambiguous: it is
the app distribution of cofferdam, owned and maintained by Datahenge.

## Decision

- A Frappe app ships as part of the **first release**, not as a deferred
  optional layer.
- The app repository is `datahenge/cofferdam-app`; the bench package name is
  `cofferdam_app`.
- The app declares `cofferdam` (the PyPI package) as a pip dependency so that
  bench installation pulls in the policy engine automatically.
- The app's `hooks.py` and app init intercept Frappe's native outbound
  functions (at minimum `frappe.sendmail` and webhook delivery) and route them
  through `cofferdam`'s policy engine before allowing dispatch.
- The `cofferdam` library itself remains Frappe-agnostic (ADR-0002 still
  holds). The Frappe app is a consumer of the library, not the reverse.

## Consequences

- Frappe Cloud subscribers can install `cofferdam-app` from GitHub and receive
  full policy enforcement without any SSH or pip access to the host.
- Existing ERPNext installations gain outbound protection immediately on app
  installation, with no changes to custom code.
- The library and the app are versioned and released independently; the app
  pins a minimum `cofferdam` version in its requirements.
- The interception layer (hooks + monkey-patching) is Frappe-version-sensitive.
  This is the primary maintenance burden introduced by this decision.
- Desk UI, fixtures, and Bench commands remain out of scope for v1 of the app.
