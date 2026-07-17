# ADR-0007 — Env-var credentials; reject raw secrets by default

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

Integrations need secrets (API keys, tokens). The source requirements permit a
raw `secret_value` in the TOML "allowed but discouraged." Putting secrets in the
policy file, however, turns a reviewable, commit-friendly config into secret
material with all the custody problems that implies. The policy file's whole
purpose is to be the *local, inspectable* execution authority.

## Decision

- The **v1 credential source is the environment variable** named by `secret_env`,
  resolved at call time.
- A raw inline `secret_value` **parses** (so a policy is not rejected outright for
  containing one) but is **refused by default**: `resolve_secret` raises unless
  the caller passes `allow_raw=True`, and `--strict` validation rejects it.
- Secret values are never logged, printed, or placed in an exception; see `BR-LOG-002`.
- Additional sources (files, commands, Vault, AWS Secrets Manager, 1Password,
  Doppler, SOPS) are explicitly future work.

## Consequences

- The policy file stays safe to review and (with care) to store, because it
  contains references, not secrets.
- Teams that truly need an inline secret must opt in explicitly and accept the
  documented custody burden.
- A missing env var fails closed at resolution time with a clear, secret-free
  error naming the variable.
