# 05 — Secret Handling

Implemented in `cofferdam.credentials`. A credential names *where* a secret comes
from; it is not the secret.

## Sources

- **BR-SECRET-001 — Credential references, not raw secrets.** A `credentials.<name>`
  table declares a `profile` and a secret *source*.
- **BR-SECRET-002 — v1 source is the environment variable** named by `secret_env`,
  resolved at call time via `resolve_secret(policy, name)`.
- **BR-SECRET-003 — Raw `secret_value` is rejected by default**
  ([ADR-0007](adr/0007-env-var-credentials.md)). It parses, but `resolve_secret`
  refuses it unless the caller passes `allow_raw=True`, and strict validation
  rejects it outright. If a project ever enables raw secrets, the policy file
  becomes secret material requiring restrictive permissions and careful backups.
- **Future sources** (not in v1): file references, command references, AWS Secrets
  Manager, HashiCorp Vault, 1Password CLI, Doppler, SOPS.

## Redaction (`BR-LOG-002`)

**The library never logs, prints, `repr`s, or embeds a secret value** in any
output or exception message. Concretely:

- `Credential.secret_value` uses `repr=False`.
- `resolve_secret` returns the secret to the caller but never logs it.
- A `SecretResolutionError` may name the *missing environment variable* (e.g.
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
