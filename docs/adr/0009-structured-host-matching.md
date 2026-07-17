# ADR-0009 — Structured whole-hostname matching

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

Host allowlisting is only as safe as its matching logic. A naive substring or
`startswith`/`endswith` check against a raw URL is a classic bypass: an attacker
(or a misconfigured integration) pointing at `sandbox.vendor.com.evil.example`
would match an allowlist entry of `sandbox.vendor.com` under substring matching.

## Decision

- Extract the hostname with a **structured URL parser**
  (`urllib.parse.urlsplit(url).hostname`), never by scanning the raw URL string
  (`BR-HOST-002`).
- Match on the **whole hostname for equality**, case-insensitively, with a single
  trailing DNS-root dot normalized away (`BR-HOST-001`, `BR-HOST-003`). No
  substring, prefix, or suffix matching. Wildcards are not supported in v1.
- **Credential-bearing headers are never sent to a host that has not passed
  policy evaluation** (`BR-HOST-004`); the HTTP helper evaluates before sending.

## Consequences

- `sandbox.vendor.com` authorizes exactly `sandbox.vendor.com`, never
  `sandbox.vendor.com.evil.example` or `evil.sandbox.vendor.com`.
- No subdomain wildcards yet; a future `*.vendor.com` syntax, if added, will be
  specified (with its matching semantics) before implementation.
- The rule is small enough to unit-test exhaustively, and is
  (`test_host_matches_is_not_substring`).
