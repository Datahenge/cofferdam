# 06 — Host & URL Handling

Host checks are security-critical: a substring match is a bypass. Implemented in
`cofferdam.decisions.host_matches` and `cofferdam.http.host_from_url`.

## Rules

- **BR-HOST-001 — Whole-hostname match, never substring.** `allowed_hosts =
  ["sandbox.vendor.com"]` must **not** authorize `sandbox.vendor.com.evil.example`
  or `evil.sandbox.vendor.com`. Matching compares the full hostname for equality.
- **BR-HOST-002 — Structured parsing.** The HTTP helper extracts the hostname with
  `urllib.parse.urlsplit(url).hostname`, never by scanning the raw URL string.
- **BR-HOST-003 — Case-insensitive.** `SANDBOX.VENDOR.COM` matches
  `sandbox.vendor.com`. A single trailing dot (the DNS root) is normalized away.
- **BR-HOST-004 — Credential-bearing headers must not be sent to a host that has
  not passed policy evaluation.** The `http.request` helper evaluates the policy —
  including the host — *before* sending anything.

## Redirects (`BR-HTTP-003`)

Redirects are **not** followed by default
([ADR-0008](adr/0008-httpx-optional-http-helper.md)). When a caller opts into
following redirects, each redirect target must be re-validated against the policy
before any credential-bearing header is re-sent. A redirect to a non-allowed host
is a denial, not a silent follow.

## Ports

Port handling is explicit where port checks are added. v1 matches on hostname
only; a future `allowed_hosts` entry format may include a port, at which point the
default-port semantics will be specified here before implementation.

## Examples

| `allowed_hosts` | candidate | verdict |
|-----------------|-----------|---------|
| `sandbox.vendor.com` | `sandbox.vendor.com` | allow |
| `sandbox.vendor.com` | `SANDBOX.VENDOR.COM` | allow |
| `sandbox.vendor.com` | `sandbox.vendor.com.evil.example` | **deny** |
| `sandbox.vendor.com` | `evil.sandbox.vendor.com` | **deny** |
| `sandbox.vendor.com` | *(empty host)* | **deny** |
