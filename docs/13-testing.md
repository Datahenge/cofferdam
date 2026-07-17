# 13 — Testing

## Principle (`BR-TEST-004`)

The whole suite runs **without a Frappe Bench**. Frappe-specific tests are
isolated and mock Frappe where practical. Tests cite the `BR-*` identifier(s)
they exercise.

## Required coverage (`BR-TEST-001..003`)

| Scenario | Where | Status |
|----------|-------|:------:|
| Production SQL restore hazard (Production host blocked in Staging) | `test_decisions.py` | ✅ |
| Non-Production deny-by-default | `test_decisions.py`, `test_config.py` | ✅ |
| Explicit sandbox allow | `test_decisions.py` | ✅ |
| Production credential reference blocked in Staging | `test_decisions.py` (`credential_mismatch`) | ✅ |
| Missing policy file fails closed | `test_config.py` | ✅ |
| Malformed TOML | `test_config.py` | ✅ |
| Missing env-var secret | `test_credentials.py` | ✅ |
| Raw secret redaction / rejection | `test_credentials.py` | ✅ |
| URL host parsing edge cases (no substring match) | `test_decisions.py` | ✅ |
| Undefined credential reference rejected | `test_config.py` | ✅ |
| Production blanket allow-all rejected | `test_config.py` | ✅ |
| CLI validate / inspect / decide | `test_cli.py` | ✅ |
| Redirect handling policy | `test_http.py` | ✅ |
| Email recipient domain allow/block | *email milestone* | ⏳ |
| Subject decorated with env name in non-production | *email milestone* | ⏳ |
| Subject unchanged in production | *email milestone* | ⏳ |
| Body: plain-text notice prepended | *email milestone* | ⏳ |
| Body: HTML banner injected after `<body>` tag | *email milestone* | ⏳ |
| Body: HTML banner prepended when no `<body>` tag | *email milestone* | ⏳ |
| HTML body detected via `<html`/`<body` substring | *email milestone* | ⏳ |
| `decorate = false` in `[mail]` suppresses decoration | *email milestone* | ⏳ |
| Production never decorates regardless of `decorate` setting | *email milestone* | ⏳ |
| `decorate_email` passthrough when decoration disabled | *email milestone* | ⏳ |

## Running

```console
$ pip install -e ".[dev]"
$ pytest                 # unit tests
$ ruff check .           # lint
$ mypy                   # type check (strict)
```

## Conventions

- The canonical fixture is
  [`examples/environment_policy.staging.toml`](../examples/environment_policy.staging.toml),
  loaded by the `staging_policy` fixture in `conftest.py`. Using the shipped
  example as the test fixture keeps documentation and tests honest.
- Secret env vars in tests are set via `monkeypatch`, never committed.
- Every fail-closed branch has an explicit test; a denial reaching `allow` by
  omission is the failure mode we most guard against.
