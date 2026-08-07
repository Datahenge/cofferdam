# ADR-0013 — No secret autoloading; recommend `direnv` in documentation instead

- **Status:** Accepted
- **Date:** 2026-08-07

## Context

Real deployments (e.g. ERPNext + multiple integrations/customizations) can
have many `credentials.<name>` references in a single `environment_policy.toml`.
Each needs its named environment variable set in the process that resolves it —
the ERPNext web server, every worker, and (during development) whatever shell
an engineer or an AI pair-programming agent is running in. Setting a dozen-plus
`SECRET_X=... SECRET_Y=...` prefixes by hand before every command is tedious,
and that tedium creates pressure to add a shortcut into `cofferdam` itself:
either an implicit `.env` lookup adjacent to the policy file, or a
`secret_env_file`-style pointer inside the TOML.

Both shortcuts were considered and rejected:

- An implicit adjacent-`.env` lookup makes `resolve_secret` do filesystem I/O
  and silently widens where a "missing" variable might actually come from,
  which weakens the fail-closed guarantee in
  [ADR-0005](0005-fail-closed-by-default.md) — "missing env var → deny" should
  mean the variable is genuinely absent from the environment, not "absent from
  `os.environ` but perhaps present in a file cofferdam went looking for."
- A TOML-level pointer to a secrets file reintroduces the exact custody
  problem [ADR-0007](0007-env-var-credentials.md) was written to avoid: the
  policy file stops being reviewable/commit-safe on its own and starts naming
  where secret material lives.

The actual problem — populating many env vars for several independent
processes (web server, workers, dev/agent shells) — is a process-bootstrap
problem, not a policy-resolution problem, and has an established solution
outside cofferdam: `direnv`. It hooks the shell itself, so it works uniformly
for interactive developer sessions, AI agents working from a shell, and any
command invoked from within the project directory, without any of them
needing cofferdam-specific wiring.

## Decision

1. `cofferdam` will **not** autoload secrets from any file. `resolve_secret`
   continues to read only `os.environ` (`BR-SECRET-002`); no adjacent-`.env`
   discovery, no `secret_env_file`-style field in the schema.
2. `cofferdam` user documentation **will** explain `direnv` as the recommended
   local-development pattern for provisioning the many env vars a large policy
   file implies: what it is, how to install it, and how to use it (per-directory
   `.envrc`, `direnv allow`) so that developers and AI coding agents working in
   the project directory inherit the right secrets without per-tool setup.
   This is documentation only — it implies no change to `cofferdam`'s runtime
   behavior or schema.

## Consequences

- `resolve_secret` and the policy file schema are unaffected by this decision;
  no code change follows from it.
- Local-dev ergonomics are solved once, at the shell level, and apply equally
  to the web server process (if launched from a `direnv`-managed shell),
  workers, and AI agents — instead of cofferdam reinventing a narrower version
  of the same mechanism.
- Production provisioning is explicitly out of scope here and stays with
  process-manager env injection (systemd `EnvironmentFile=`, supervisor
  `environment=`) or a real secrets manager, per the "future sources" note in
  [05 — Secret Handling](../05-secret-handling.md).
- The `direnv` how-to content lives in the top-level `cofferdam` README under
  "Local development" (see `docs/15-open-questions.md`, Q12).
