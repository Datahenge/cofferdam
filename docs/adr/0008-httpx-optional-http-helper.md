# ADR-0008 — HTTP helper wraps httpx as an optional extra

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

The library offers a *policy-checked* HTTP helper so that credential-bearing
requests cannot reach a non-allowed host. The source left open whether to wrap
`requests`, `httpx`, or both. The core decision engine, however, needs no network
client at all, and forcing one on every install is wrong for a small enforcement
library.

## Decision

- Provide `cofferdam.http.request(...)` wrapping **`httpx`**.
- Ship it behind an **optional extra**: `pip install "cofferdam[http]"`. The core
  package has **no HTTP dependency**; importing `cofferdam.http` without the extra
  raises a clear, actionable `CofferdamError`.
- **Redirects are not followed by default** (`BR-HTTP-003`). If a caller enables
  them, each redirect target must be re-validated against the policy before any
  credential-bearing header is re-sent.
- The host is parsed from the URL with a structured parser and evaluated *before*
  the request is sent ([06 — Host & URL Handling](../06-host-url-handling.md),
  `BR-HOST-004`).

Why `httpx` over `requests`: first-class timeouts, explicit redirect control,
sync + async surface for later, and active maintenance.

## Consequences

- Minimal-footprint default install; network client only when wanted.
- One well-defined choke point where policy is enforced before bytes leave.
- Users who prefer `requests` can still call `decide`/`assert_allowed` directly
  and issue the request with their own client.
