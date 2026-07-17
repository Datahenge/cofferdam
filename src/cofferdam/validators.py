"""Semantic (cross-section) policy validation (BR-VALIDATE-*).

Schema-shape validation happens in :mod:`cofferdam.models` via Pydantic. This
module adds checks that span multiple sections of a policy — the kind of mistake
that is individually well-formed but collectively unsafe. Validation distinguishes
syntax errors (raised earlier, in :mod:`cofferdam.config`) from these semantic
policy errors (BR-VALIDATE-011).
"""

from __future__ import annotations

import os

from cofferdam.errors import PolicyValidationError
from cofferdam.models import Environment, Policy

_KNOWN_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _check_credential_references(policy: Policy, problems: list[str]) -> None:
    for name, integ in policy.integrations.items():
        if integ.credential is not None and integ.credential not in policy.credentials:
            problems.append(
                f"integration.{name}: references undefined credential "
                f"{integ.credential!r} (BR-VALIDATE-004)"
            )


def _check_methods(policy: Policy, problems: list[str]) -> None:
    for name, integ in policy.integrations.items():
        for method in integ.allowed_methods:
            if method.upper() not in _KNOWN_METHODS:
                problems.append(
                    f"integration.{name}: unsupported HTTP method {method!r} "
                    f"(BR-VALIDATE-006)"
                )


def _check_hosts(policy: Policy, problems: list[str]) -> None:
    for name, integ in policy.integrations.items():
        for host in integ.allowed_hosts:
            if not host or "/" in host or " " in host or host != host.strip():
                problems.append(
                    f"integration.{name}: invalid hostname {host!r} — expected a "
                    f"bare hostname, not a URL (BR-VALIDATE-005)"
                )


def _check_no_raw_secrets(policy: Policy, problems: list[str]) -> None:
    # In strict mode, raw inline secrets are a hard error (ADR-0007, BR-VALIDATE-010).
    for name, cred in policy.credentials.items():
        if cred.secret_value is not None:
            problems.append(
                f"credential.{name}: raw secret_value is not permitted "
                f"(use secret_env) (BR-VALIDATE-010)"
            )


def _check_env_vars_present(policy: Policy, problems: list[str]) -> None:
    for name, cred in policy.credentials.items():
        if cred.secret_env and cred.secret_env not in os.environ:
            problems.append(
                f"credential.{name}: environment variable {cred.secret_env!r} is "
                f"not set (BR-VALIDATE-007)"
            )


def _check_production_not_blanket(policy: Policy, problems: list[str]) -> None:
    # Production must be explicit, not an accidental allow-all (BR-DECISION-011).
    if policy.environment is Environment.PRODUCTION and policy.default_decision.value == "allow":
        problems.append(
            "environment 'production' with default_decision='allow' is an unsafe "
            "blanket allow-all; permit side effects explicitly instead "
            "(BR-VALIDATE-009)"
        )


def validate_policy(policy: Policy, *, strict: bool = False, source: str = "<policy>") -> None:
    """Run semantic validation, raising :class:`PolicyValidationError` on any problem.

    :param strict: additionally require that every ``secret_env`` variable is set
        and reject any raw ``secret_value``. Intended for ``cofferdam validate``
        and CI, not the request hot path.
    """
    problems: list[str] = []

    _check_credential_references(policy, problems)
    _check_methods(policy, problems)
    _check_hosts(policy, problems)
    _check_production_not_blanket(policy, problems)

    if strict:
        _check_no_raw_secrets(policy, problems)
        _check_env_vars_present(policy, problems)

    if problems:
        raise PolicyValidationError(
            f"policy failed semantic validation ({source}): {len(problems)} problem(s)",
            problems=problems,
        )
