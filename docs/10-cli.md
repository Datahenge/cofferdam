# 10 — CLI

The `cofferdam` console script (`cofferdam.cli:main`) wraps the library over a
local policy file. It uses stdlib `argparse` to keep the core dependency-free.

## Commands

### `validate` (`BR-CLI-001`)

```console
$ cofferdam validate path/to/environment_policy.toml
$ cofferdam validate path/to/environment_policy.toml --strict
```

Loads and validates the policy. **Exits non-zero on an invalid policy**
(exit code `2`), printing each problem. `--strict` additionally requires every
`secret_env` variable to be set, rejects raw secrets, and rejects secret-shaped
key names under `configs.*` (`BR-VALIDATE-013`).

### `inspect` (`BR-CLI-002`)

```console
$ cofferdam inspect path/to/environment_policy.toml
```

Prints a **redacted** summary: environment, default decision, mail mode,
integrations (kind/state/hosts), credentials (profile and *source name* only —
never a value, `BR-CLI-004`), and configs (name and *key names* only). Config
values are non-secret by contract, but `inspect` still prints only key names, so
that a value mistakenly stored there is not echoed to a terminal or a CI log.

### `decide` (`BR-CLI-003`)

```console
$ cofferdam decide path/to/environment_policy.toml \
      --integration windmill --kind vendor_api --operation write \
      --method POST --url https://sandbox.windmill.dev/api/jobs/run \
      --credential windmill_default
```

Simulates a decision and prints `ALLOW`/`DENY` plus the `reason_code`, never a
secret. Accepts `--url` (hostname parsed structurally) or `--host`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | success / `ALLOW` |
| `1` | `decide` returned `DENY` |
| `2` | invalid or missing policy |
| `3` | usage error (reserved) |

The `decide` deny exit code (`1`) lets shell scripts and CI gate on a simulated
decision.
