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

# Key-name fragments that indicate secret material. `configs.*` is non-secret by
# contract (BR-CONFIG-006, ADR-0014); this catches a secret pasted into the
# reviewable, commit-safe policy file. Names only — never values (BR-VALIDATE-013).
_SECRET_SHAPED = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "privatekey",
    "access_key",
    "accesskey",
    "credential",
)


def _check_credential_references(policy: Policy, problems: list[str]) -> None:
    for name, integ in policy.integrations.items():
        if integ.credential is not None and integ.credential not in policy.credentials:
            problems.append(
                f"integration.{name}: references undefined credential "
                f"{integ.credential!r} (BR-VALIDATE-004)"
            )


def _check_config_references(policy: Policy, problems: list[str]) -> None:
    # An integration's config reference is validated exactly as its credential
    # reference is: a typo must fail at load (BR-VALIDATE-012, ADR-0014).
    for name, integ in policy.integrations.items():
        if integ.config is not None and integ.config not in policy.configs:
            problems.append(
                f"integration.{name}: references undefined config "
                f"{integ.config!r} (BR-VALIDATE-012)"
            )


def _check_credential_sources(policy: Policy, problems: list[str]) -> None:
    # A credential declares one form of source. Both would leave which one wins
    # to implementation order rather than to the author (BR-VALIDATE-015).
    for name, cred in policy.credentials.items():
        if cred.env and cred.secret_env:
            problems.append(
                f"credential.{name}: declares both 'secret_env' and an 'env' table; "
                f"use one or the other (BR-VALIDATE-015)"
            )
        if cred.env and cred.secret_value is not None:
            problems.append(
                f"credential.{name}: declares both 'secret_value' and an 'env' table; "
                f"use one or the other (BR-VALIDATE-015)"
            )


def _is_secret_shaped(key: str) -> bool:
    """Whether a config key name indicates secret material (BR-VALIDATE-013).

    ``access_key_id`` is exempt: an access-key *identifier* is the public half of
    a key pair, the way a username is, and it is a common legitimate config key.
    The secret half (``secret_access_key``) still matches on ``secret``.
    """
    normalized = key.lower().replace("-", "_")
    if normalized.endswith("_id") and "secret" not in normalized:
        return False
    return any(fragment in normalized for fragment in _SECRET_SHAPED)


def _check_config_keys_not_secret_shaped(policy: Policy, problems: list[str]) -> None:
    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_str = str(key)
                child = f"{path}.{key_str}"
                if _is_secret_shaped(key_str):
                    problems.append(
                        f"{child}: key name indicates secret material; configs are "
                        f"non-secret — move it to credentials.<name> "
                        f"(BR-CONFIG-006, BR-VALIDATE-013)"
                    )
                walk(value, child)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    for name, table in policy.configs.items():
        walk(table, f"configs.{name}")


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
        # Both source forms are checked: a multi-part credential is only usable
        # if every variable it names is set (BR-SECRET-004, BR-VALIDATE-007).
        named = [cred.secret_env] if cred.secret_env else list(cred.env.values())
        for var in named:
            if var not in os.environ:
                problems.append(
                    f"credential.{name}: environment variable {var!r} is "
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

    :param strict: additionally require that every named environment variable is
        set, reject any raw ``secret_value``, and reject secret-shaped key names
        under ``configs.*``. Intended for ``cofferdam validate`` and CI, not the
        request hot path.
    """
    problems: list[str] = []

    _check_credential_references(policy, problems)
    _check_config_references(policy, problems)
    _check_credential_sources(policy, problems)
    _check_methods(policy, problems)
    _check_hosts(policy, problems)
    _check_production_not_blanket(policy, problems)

    if strict:
        _check_no_raw_secrets(policy, problems)
        _check_env_vars_present(policy, problems)
        _check_config_keys_not_secret_shaped(policy, problems)

    if problems:
        raise PolicyValidationError(
            f"policy failed semantic validation ({source}): {len(problems)} problem(s)",
            problems=problems,
        )
