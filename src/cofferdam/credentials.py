"""Credential reference resolution (BR-SECRET-*).

A credential names *where* a secret comes from — it is not the secret. The
supported sources are an environment variable (``secret_env``) or, for a
credential carrying several related secrets, an ``env`` table of them
(BR-SECRET-004, ADR-0014). Raw inline secrets (``secret_value``) are rejected
unless the caller explicitly opts in (ADR-0007). No function here logs, prints,
or embeds a secret value in an exception message (BR-LOG-002).
"""

from __future__ import annotations

import json
import os
from typing import Any

from cofferdam.errors import CredentialError, SecretResolutionError
from cofferdam.models import Credential, Policy

_UNPARSED = object()  # sentinel: keeps a failed json.loads off the exception chain


def _require(policy: Policy, name: str) -> Credential:
    """Return credential ``name`` or fail closed (BR-SECRET-001)."""
    cred = policy.credentials.get(name)
    if cred is None:
        raise CredentialError(f"credential {name!r} is not defined in the policy")
    return cred


def _from_env(var: str, *, credential: str) -> str:
    """Read ``var`` from the process environment, naming only the variable on failure."""
    try:
        return os.environ[var]
    except KeyError:
        raise SecretResolutionError(
            f"credential {credential!r} requires environment variable "
            f"{var!r}, which is not set"
        ) from None


def resolve_secret(policy: Policy, name: str, *, allow_raw: bool = False) -> str:
    """Resolve the secret material for credential ``name``.

    :param name: key into ``policy.credentials``.
    :param allow_raw: when True, a raw ``secret_value`` may be returned. Defaults
        to False so that inline secrets are refused (ADR-0007, BR-SECRET-003).
    :raises CredentialError: the credential is undefined, or defines no usable
        source, or uses a raw secret without opt-in.
    :raises SecretResolutionError: ``secret_env`` names an unset variable.
    """
    cred = _require(policy, name)

    if cred.secret_env:
        return _from_env(cred.secret_env, credential=name)

    if cred.env:
        raise CredentialError(
            f"credential {name!r} declares a multi-part 'env' table; use "
            f"resolve_credentials({name!r}) to resolve it (BR-SECRET-004)"
        )

    if cred.secret_value is not None:
        if not allow_raw:
            raise CredentialError(
                f"credential {name!r} uses a raw inline secret_value, which is "
                f"rejected by default; pass allow_raw=True to permit it"
            )
        return cred.secret_value

    raise CredentialError(
        f"credential {name!r} defines no secret source (expected secret_env)"
    )


def resolve_credentials(policy: Policy, name: str) -> dict[str, str]:
    """Resolve every secret in a multi-part credential (BR-SECRET-004).

    A credential declaring an ``[credentials.<name>.env]`` table carries a set of
    related secrets — an access-key pair, for example. Each logical key maps to
    the environment variable holding that secret; keys keep their exact casing.

    :returns: ``{logical_key: secret}``, resolved at call time.
    :raises CredentialError: the credential is undefined, or declares no ``env``
        table (use :func:`resolve_secret` for a single-valued credential).
    :raises SecretResolutionError: a named variable is unset — fail-closed, and
        the message names the variable, never a value (BR-LOG-002).
    """
    cred = _require(policy, name)
    if not cred.env:
        raise CredentialError(
            f"credential {name!r} declares no 'env' table; use "
            f"resolve_secret({name!r}) for a single-valued credential"
        )
    return {key: _from_env(var, credential=name) for key, var in cred.env.items()}


def resolve_json_secret(
    policy: Policy, name: str, *, allow_raw: bool = False
) -> dict[str, Any]:
    """Resolve credential ``name`` and parse its value as a JSON object (BR-SECRET-005).

    For secret material that genuinely arrives as one JSON document (a service
    account key, for example). Non-secret settings do not belong here — they
    belong in ``[configs.<name>]`` (BR-CONFIG-004, ADR-0014).

    The failure path is the sensitive one: ``json.JSONDecodeError`` carries the
    entire document on its ``.doc`` attribute, so any exception chained to it
    would carry the secret with it. The error raised here is therefore fully
    detached from the parse failure and names only the credential (BR-LOG-002).

    :raises SecretResolutionError: the value is not valid JSON, or is valid JSON
        but not an object.
    """
    raw = resolve_secret(policy, name, allow_raw=allow_raw)
    parsed: Any = _UNPARSED
    try:
        parsed = json.loads(raw)
    except ValueError:
        pass
    if parsed is _UNPARSED:
        # Raised *outside* the except block on purpose. `raise ... from None`
        # would still leave the JSONDecodeError on __context__, and that object
        # carries the entire secret document on its `.doc` attribute — reachable
        # by any error reporter that walks the chain (BR-SECRET-005, BR-LOG-002).
        raise SecretResolutionError(f"credential {name!r} does not contain valid JSON")
    if not isinstance(parsed, dict):
        raise SecretResolutionError(
            f"credential {name!r} contains JSON of type {type(parsed).__name__}, "
            f"expected an object"
        )
    result: dict[str, Any] = parsed
    return result
