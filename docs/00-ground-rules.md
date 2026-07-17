# 00 — Ground Rules

These rules govern *how* `cofferdam` is built. They apply to every contributor,
human or AI.

## Documentation-driven

- **Docs precede code.** A behavior is specified here before it is implemented.
- **Single source of truth.** When design changes, the docs change in the same
  commit as the code. Stale docs are treated as bugs.
- **Traceability.** Every non-trivial rule has a business-rule identifier
  (`BR-<AREA>-<NNN>`). Implementation docstrings and tests cite the identifier
  they satisfy. This lets a reader move from requirement → code → test and back.
- **Record decisions.** Choices with lasting consequences become an
  [ADR](adr/). The [CHANGELOG](../CHANGELOG.md) also carries a "Decided" section.
- **No silent assumptions.** Where a requirement is ambiguous, ask or record the
  assumption explicitly in [15 — Open Questions](15-open-questions.md); do not
  infer behavior from an unstated preference.

## Engineering

- **Fail closed.** When in doubt, deny. See [ADR-0005](adr/0005-fail-closed-by-default.md).
- **Never leak secrets.** No secret value in logs, exceptions, `repr`, CLI
  output, or tracebacks — ever ([05](05-secret-handling.md), `BR-LOG-002`).
- **The core does not import `frappe`.** Frappe-specific behavior is quarantined
  in `cofferdam.frappe`. The library installs and tests as an ordinary Python
  package with no Bench present ([ADR-0002](adr/0002-python-library-not-frappe-app.md)).
- **Small, boring, inspectable.** The policy model is deliberately not a general
  policy language. Readability by a support engineer beats expressiveness.
- **Typed and checked.** `mypy --strict` and `ruff` pass on every commit; the
  package ships `py.typed`.

## Audience separation

- Internal requirement references (`BR-*`, ADR numbers) live in **docstrings and
  comments**.
- User-facing text (`README.md`, CLI `--help`, published docs) is clean and
  professional and does not require the reader to know the internal identifiers.

## Definition of done (per module)

A module is "done" when: its behavior is specified in a doc; it is implemented
with docstrings citing `BR-*`; unit tests cover the specified rules including the
fail-closed paths; `ruff`, `mypy --strict`, and `pytest` are green; and the
CHANGELOG reflects any decision made along the way.
