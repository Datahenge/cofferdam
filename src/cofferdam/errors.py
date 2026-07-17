"""Explicit exception types for cofferdam.

Implements the requirement that unsafe calls *fail closed with clear errors*
(docs/01-overview.md, docs/04-decision-engine.md). Every exception carries
enough structured context for server-side logging while guaranteeing that no
secret value is ever placed in an exception message (BR-LOG-002).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cofferdam.decisions import Decision


class CofferdamError(Exception):
    """Base class for every error raised by cofferdam."""


class PolicyFileNotFoundError(CofferdamError):
    """A policy file was expected on the local filesystem but not found.

    Per BR-DECISION-001 this is a fail-closed condition: a missing policy file
    denies all side effects unless the caller explicitly opted into a fallback.
    """


class PolicyValidationError(CofferdamError):
    """A policy file is syntactically or semantically invalid.

    Aggregates one or more human-readable problems. Distinguishes syntax errors
    (malformed TOML) from semantic policy errors (BR-VALIDATE-011).
    """

    def __init__(self, message: str, *, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems: list[str] = problems or []


class PolicyDeniedError(CofferdamError):
    """Raised by ``assert_allowed`` when a side effect is not permitted.

    Carries the originating :class:`~cofferdam.decisions.Decision` so callers and
    logs can see the environment, integration, operation, and reason code — but
    never a secret value.
    """

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        super().__init__(decision.message())


class CredentialError(CofferdamError):
    """A credential reference is missing, malformed, or mismatched.

    Examples: an integration names a credential that the policy does not define,
    or the credential's ``profile`` does not match what the integration requires.
    """


class SecretResolutionError(CredentialError):
    """A credential is defined but its secret material could not be resolved.

    Example: ``secret_env`` names an environment variable that is unset. The
    missing variable name may appear in the message; the secret value never can.
    """
