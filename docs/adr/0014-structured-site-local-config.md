# ADR-0014 — Structured site-local configuration is a first-class section, separate from credentials

- **Status:** Accepted
- **Date:** 2026-09-05
- **Issue:** [datahenge/cofferdam#4](https://github.com/Datahenge/cofferdam/issues/4)

## Context

An integration typically needs two different things from its environment:

1. **Secret material** — an API key, an access-key pair. Custody-sensitive,
   never committed, resolved from the process environment
   ([ADR-0007](0007-env-var-credentials.md)).
2. **Environment-specific but non-secret settings** — an S3/R2 endpoint URL, a
   bucket name, a region, key prefixes, an expiry in seconds, a delivery mode.
   These are exactly as environment-dependent as the secret, but they are not
   secret, and they are the kind of thing a support engineer should be able to
   read out of a reviewable file.

Before this ADR, cofferdam had a home for (1) and no home for (2). The observed
workaround (issue #4) was to serialize a JSON bundle into a credential's
`secret_value` and read it back with `allow_raw=True`. That is semantically
wrong on both ends: it labels non-secret data as secret, and — worse — it
requires the caller to habitually pass `allow_raw=True`, which is the precise
opt-in [ADR-0007](0007-env-var-credentials.md) built to be rare and deliberate.
Normalizing that flag erodes the guard.

Cloudflare R2 is the motivating case: `endpoint_url`, `bucket_name`,
`region_name`, and prefixes are non-secret; `access_key_id` and
`secret_access_key` are secret; and the secret half is a *pair*, which the
single-valued `secret_env` field could not express either.

## Decision

1. **Add a top-level `[configs.<name>]` section** holding structured,
   environment-specific, **non-secret** settings: arbitrary TOML scalars,
   arrays, and nested tables. Values are data — cofferdam does not interpret
   them, and no decision depends on them (`BR-CONFIG-004`).

2. **Preserve key casing exactly.** Config keys are application-defined and are
   never case-normalized on either the write or the read path
   (`BR-CONFIG-005`). Compare: `allowed_methods` *is* case-folded, because HTTP
   methods are cofferdam's own vocabulary; config keys are not.

3. **`configs.*` is non-secret by contract, and strict validation enforces it.**
   `cofferdam validate --strict` rejects config keys whose names indicate secret
   material (`password`, `secret`, `token`, `api_key`, `private_key`, and
   related forms) (`BR-CONFIG-006`, `BR-VALIDATE-013`). The policy file is
   reviewable and commit-safe by design (ADR-0007); a section that invites
   free-form values needs a guard against becoming the place secrets get pasted.
   The check is strict-only — it gates CI and deploys, not the request hot path
   — and is a heuristic on key *names*, never on values.

4. **`integrations.<name>` gains a `config` reference** alongside `credential`.
   Both are validated as references: naming an undefined config is a load-time
   error (`BR-VALIDATE-012`), the same fail-closed treatment `credential`
   already receives (`BR-VALIDATE-004`).

5. **Credentials gain an optional `[credentials.<name>.env]` sub-table** mapping
   a logical secret name to the environment variable that holds it, so one
   credential can carry a related set of secrets (`BR-SECRET-004`). Single-valued
   `secret_env` is unchanged and remains the common case. `env` was chosen over
   free-form `<name>_env` keys directly on the credential table because the
   latter would require relaxing `extra="forbid"` to a suffix rule and would
   surrender the typo protection of `BR-VALIDATE-003`.

6. **Three resolution helpers** (`BR-API-005`):
   `policy.resolve_config(name)` returns a config as a plain dict;
   `policy.resolve_credentials(name)` returns the `env` sub-table resolved to
   values; `policy.resolve_json_secret(name)` parses a single resolved secret as
   a JSON object, for secrets that genuinely arrive as one JSON blob.

7. **A JSON parse failure must not leak the secret.** `resolve_json_secret`
   raises `SecretResolutionError` naming only the credential, and suppresses
   exception chaining — `json.JSONDecodeError` carries the entire document on
   its `.doc` attribute, so a chained traceback would print the secret
   (`BR-SECRET-005`, `BR-LOG-002`).

## Consequences

- The conceptual model gains a third noun: policy rules, non-secret config, and
  secret references are now three separate things with three separate sections.
  `02-conceptual-model.md` is updated accordingly.
- `resolve_json_secret` supersedes the `allow_raw=True`-on-a-JSON-bundle
  workaround for the *secret* half. For the non-secret half, `[configs.*]` does.
  Neither requires `allow_raw`, so ADR-0007's opt-in stays rare.
- The strict secret-shaped-key check can produce a false positive on an
  innocuous key name (a config key literally named `token_bucket`, say). The
  escape hatch is to rename the key; there is deliberately no suppression flag,
  because a per-key override would be the first thing reached for when the
  finding is real.
- New sections are additive: every policy valid before this ADR remains valid.
- `configs` is a *known* top-level key, so `[config.foo]` or `[configs]` used as
  a scalar still fails `extra="forbid"` (`BR-VALIDATE-003`). Fail-closed on
  typos is preserved.
