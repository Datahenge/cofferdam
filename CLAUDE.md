# CLAUDE.md — cofferdam

This project uses **Scribe Coding** (document-driven AI development). These rules
govern how an AI assistant works here. Read them before writing any code.

## The one rule that governs all others

**Docs precede code.** If a behavior is not described in `docs/`, it is not
implemented. If a requirement is ambiguous, check `docs/15-open-questions.md`
— do not infer behavior from unstated preference. If the question is new, add
it to `docs/15-open-questions.md` and ask the user before writing code.

## Before any task (write, debug, review, explain, or answer)

1. Consult the appropriate index to identify which specific doc(s) to load:
   - **Requirement docs:** `docs/README.md` — maps every module and topic to
     its owning document.
   - **ADRs:** `docs/adr/README.md` — index of all architecture decisions.
   - **Tests:** `docs/13-testing.md` owns all testing requirements; consult it
     before writing or modifying any test.
   Then load only the specific doc(s) the index points to. Never load the full
   `docs/` tree or `docs/adr/` directory without first consulting the index.
2. Load only the doc(s) for the concern in scope — do not scan the full source
   tree unless the task explicitly spans multiple modules.

## Coding standards

- **Cite BR-* identifiers.** Every non-trivial function and class docstring cites
  the business-rule identifier(s) it satisfies (e.g. `BR-SECRET-002`). Tests cite
  the identifier they exercise in their docstring or a comment.
- **Fail closed.** When in doubt, deny. Missing policy, missing env var, unknown
  integration → deny. See ADR-0005.
- **Never leak secrets.** No secret value in logs, exceptions, `repr`, CLI output,
  or tracebacks. `BR-LOG-002`.
- **Core does not import frappe.** All Frappe-specific behavior stays in
  `cofferdam.frappe`. See ADR-0002 and ADR-0010.
- **mypy --strict and ruff must pass** after every change.

## Definition of done (per module)

A module is done when:
- its behavior is fully specified in a `docs/NN-*.md` file
- implementation docstrings cite `BR-*` identifiers
- unit tests cover specified behavior including fail-closed paths
- `ruff`, `mypy --strict`, and `pytest` are green
- CHANGELOG records any decision made along the way

## Keeping context small

- Read only the doc for the module in scope, not the full `docs/` tree.
- Load source files one at a time as needed rather than the whole `src/` tree.
- When a task is complete, stop. Do not refactor adjacent code, add unrequested
  features, or clean up code outside the scope of the current task.

## Architecture decisions

Significant choices are recorded in `docs/adr/`. Before proposing an approach
that overrides a prior decision, consult `docs/adr/README.md` to identify the
relevant ADR, then load that ADR. If the decision should change, say so
explicitly and write a new ADR — do not silently deviate.

## What to do when something is ambiguous

1. Check `docs/15-open-questions.md` — the question may already be resolved.
2. If unresolved, add it as a new entry and ask the user.
3. Do not implement speculative behavior while waiting for an answer.

## Implementation status

See `docs/15-open-questions.md` — it is the authoritative source for the
implementation sequence and current status markers. Do not rely on any
status summary here; it would go stale.
