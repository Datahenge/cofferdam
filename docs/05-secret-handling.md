# 05 — Secret Handling

Implemented in `cofferdam.credentials`. A credential names *where* a secret comes
from; it is not the secret.

## Sources

- **BR-SECRET-001 — Credential references, not raw secrets.** A `credentials.<name>`
  table declares a `profile` and a secret *source*.
- **BR-SECRET-002 — v1 source is the environment variable** named by `secret_env`,
  resolved at call time via `resolve_secret(policy, name)`.
- **BR-SECRET-004 — A credential may carry several related secrets** through an
  `[credentials.<name>.env]` sub-table mapping a logical key to the environment
  variable holding it (an access-key pair, for example). `resolve_credentials(
  policy, name)` resolves the whole table and returns
  `dict[logical_key, secret]`. Every named variable must be set; the first
  missing one raises `SecretResolutionError` naming that variable. Logical keys
  keep their exact casing. A credential declares the `env` table **or** a
  single-valued source (`secret_env` / `secret_value`), never both
  ([ADR-0014](adr/0014-structured-site-local-config.md), `BR-VALIDATE-015`).
- **BR-SECRET-005 — A secret that is itself a JSON document** may be resolved
  and parsed in one step with `resolve_json_secret(policy, name)`, which returns
  the parsed JSON **object** as a dict. The parse failure path is the sensitive
  one: `json.JSONDecodeError` carries the entire document on its `.doc`
  attribute, so a chained traceback would print the secret. `resolve_json_secret`
  therefore raises `SecretResolutionError` naming only the *credential*, and
  suppresses exception chaining (`raise ... from None`) (`BR-LOG-002`). A JSON
  value that is not an object (a bare string, a list) is likewise refused
  without echoing it.
- **BR-SECRET-003 — Raw `secret_value` is rejected by default**
  ([ADR-0007](adr/0007-env-var-credentials.md)). It parses, but `resolve_secret`
  refuses it unless the caller passes `allow_raw=True`, and strict validation
  rejects it outright. If a project ever enables raw secrets, the policy file
  becomes secret material requiring restrictive permissions and careful backups.
- **Future sources** (not in v1): file references, command references, AWS Secrets
  Manager, HashiCorp Vault, 1Password CLI, Doppler, SOPS.
- **No implicit file autoloading.** `resolve_secret` reads `os.environ` only —
  never an adjacent `.env` or a file path named in the policy. Populating many
  env vars for local development (web server, workers, AI pair-programming
  agents) is a shell/process-bootstrap concern, not cofferdam's; see
  [ADR-0013](adr/0013-no-secret-autoloading-direnv-docs.md), which also commits
  to documenting `direnv` for that purpose.

## What is *not* a secret

Environment-specific but non-secret settings — endpoints, bucket names, regions,
prefixes — belong in `[configs.<name>]` ([03](03-policy-file-format.md),
[ADR-0014](adr/0014-structured-site-local-config.md)), not in a credential.
Serializing a mixed bundle into `secret_value` and reading it back with
`allow_raw=True` is not the intended pattern: it mislabels non-secret data and,
more importantly, it makes `allow_raw=True` a habit, when
[ADR-0007](adr/0007-env-var-credentials.md) deliberately made it rare. Split the
two — `configs.*` for the settings, `credentials.*` for the key material.

## Redaction (`BR-LOG-002`)

Secret values are never logged, printed, or embedded in exceptions — see
[08 — Logging & Observability](08-logging-observability.md). Within this module:

- `Credential.secret_value` uses `repr=False`.
- `resolve_secret` returns the secret to the caller but never logs it.
- A `SecretResolutionError` names the *missing environment variable* (e.g.
  `WINDMILL_API_KEY`) — never a value.
- `Decision.as_log_dict()` and CLI `inspect` emit the credential *reference name*
  and its *source name*, never the value.

## Failure modes

| Condition | Exception | Reason |
|-----------|-----------|--------|
| credential name not in policy | `CredentialError` | undefined reference |
| `secret_env` variable unset | `SecretResolutionError` | fail-closed |
| `secret_value` used without `allow_raw` | `CredentialError` | raw secrets rejected |
| credential defines no source | `CredentialError` | nothing to resolve |
| `env` sub-table names an unset variable | `SecretResolutionError` | fail-closed |
| `resolve_credentials` on a single-valued credential | `CredentialError` | no `env` table to resolve |
| `resolve_json_secret` value is not valid JSON | `SecretResolutionError` | unchained; value never echoed |
| `resolve_json_secret` value is valid JSON but not an object | `SecretResolutionError` | value never echoed |
