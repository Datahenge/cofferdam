"""Credential reference resolution (BR-SECRET-*).

A credential names *where* a secret comes from — it is not the secret. In v1 the
only supported source is an environment variable (``secret_env``). Raw inline
secrets (``secret_value``) are rejected unless the caller explicitly opts in
(ADR-0007). No function here logs, prints, or embeds a secret value in an
exception message (BR-LOG-002).
"""

from __future__ import annotations

import os

from cofferdam.errors import CredentialError, SecretResolutionError
from cofferdam.models import Policy


def resolve_secret(policy: Policy, name: str, *, allow_raw: bool = False) -> str:
    """Resolve the secret material for credential ``name``.

    :param name: key into ``policy.credentials``.
    :param allow_raw: when True, a raw ``secret_value`` may be returned. Defaults
        to False so that inline secrets are refused (ADR-0007, BR-SECRET-003).
    :raises CredentialError: the credential is undefined, or defines no usable
        source, or uses a raw secret without opt-in.
    :raises SecretResolutionError: ``secret_env`` names an unset variable.
    """
    cred = policy.credentials.get(name)
    if cred is None:
        raise CredentialError(f"credential {name!r} is not defined in the policy")

    if cred.secret_env:
        try:
            return os.environ[cred.secret_env]
        except KeyError:
            raise SecretResolutionError(
                f"credential {name!r} requires environment variable "
                f"{cred.secret_env!r}, which is not set"
            ) from None

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
