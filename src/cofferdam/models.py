"""Typed policy objects, modeled and validated with Pydantic v2 (ADR-0006).

These models define the *schema* of an ``environment_policy.toml`` file and
perform structural validation on load. Cross-cutting *semantic* checks (for
example, an integration referencing an undefined credential) live in
:mod:`cofferdam.validators`; the allow/deny evaluation lives in
:mod:`cofferdam.decisions`.

Models forbid unknown fields (``extra="forbid"``) so that a typo in a policy
file surfaces as a validation error rather than being silently ignored — a
fail-closed posture consistent with ADR-0005 (BR-VALIDATE-003).
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from cofferdam.decisions import Decision


class Environment(str, Enum):
    """The runtime environment a policy describes (BR-MODEL-001)."""

    PRODUCTION = "production"
    STAGING = "staging"
    TEST = "test"
    DEV = "dev"


class SideEffectKind(str, Enum):
    """The category of outbound side effect an integration produces (BR-MODEL-002)."""

    VENDOR_API = "vendor_api"
    EMAIL = "email"
    PAYMENT = "payment"
    WEBHOOK = "webhook"
    REPORT_DELIVERY = "report_delivery"
    FILE_TRANSFER = "file_transfer"


class DefaultDecision(str, Enum):
    """The disposition applied when nothing more specific matches (BR-DECISION-002)."""

    ALLOW = "allow"
    DENY = "deny"


class _Strict(BaseModel):
    """Base model: reject unknown keys and validate on assignment."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_assignment=True)


class Credential(_Strict):
    """A named credential reference (BR-SECRET-001).

    A credential names *where* a secret comes from, never the secret itself by
    default. ``secret_env`` names an environment variable resolved at call time.
    ``secret_value`` (a raw inline secret) is parsed here but rejected by
    default during validation unless raw secrets are explicitly permitted
    (ADR-0007, BR-SECRET-003).
    """

    profile: str = Field(description="Logical profile name, e.g. 'staging' or 'sandbox'.")
    secret_env: str | None = Field(
        default=None, description="Environment variable holding the secret."
    )
    secret_value: str | None = Field(
        default=None,
        description="Raw inline secret. Discouraged; rejected unless explicitly allowed.",
        repr=False,
    )


class Integration(_Strict):
    """A named outbound integration and the operations permitted against it."""

    enabled: bool = False
    kind: SideEffectKind
    credential: str | None = None
    allowed_hosts: list[str] = Field(default_factory=list)
    allowed_methods: list[str] = Field(default_factory=list)
    allowed_operations: list[str] = Field(default_factory=list)

    # Payment-specific gates (see the Stripe example in docs/03-policy-file-format.md).
    allow_authorize: bool = False
    allow_capture: bool = False


class MailPolicy(_Strict):
    """Top-level mail handling for the environment (BR-EMAIL-001)."""

    mode: str = "deny"  # e.g. "deny", "sink", "allow_internal"
    sink: str | None = None
    allow_domains: list[str] = Field(default_factory=list)


class EffectRule(_Strict):
    """An allow/deny rule for a scoped side-effect class, e.g. ``effects.email.customer``."""

    enabled: bool = False
    allow_domains: list[str] = Field(default_factory=list)


class Policy(_Strict):
    """A fully parsed, validated policy for one environment.

    This is the schema-level model. Convenience decision methods
    (:meth:`decide`, :meth:`assert_allowed`, :meth:`resolve_secret`) are attached
    in :mod:`cofferdam.decisions` to keep the schema and the engine separable.
    """

    environment: Environment
    default_decision: DefaultDecision = DefaultDecision.DENY
    mail: MailPolicy | None = None
    credentials: dict[str, Credential] = Field(default_factory=dict)
    integrations: dict[str, Integration] = Field(default_factory=dict)
    # effects.<kind>.<scope> -> EffectRule
    effects: dict[str, dict[str, EffectRule]] = Field(default_factory=dict)

    # -- Convenience API (BR-API-001..004). These delegate to the engine modules;
    #    imports are local to avoid a models <-> engine import cycle. --

    def decide(self, **kwargs: object) -> Decision:
        """Evaluate a side effect and return a :class:`~cofferdam.decisions.Decision`."""
        from cofferdam.decisions import decide

        return decide(self, **kwargs)  # type: ignore[arg-type]

    def assert_allowed(self, **kwargs: object) -> Decision:
        """Evaluate a side effect and raise ``PolicyDeniedError`` if denied."""
        from cofferdam.decisions import assert_allowed

        return assert_allowed(self, **kwargs)

    def resolve_secret(self, name: str, *, allow_raw: bool = False) -> str:
        """Resolve credential ``name`` to its secret material (never logged)."""
        from cofferdam.credentials import resolve_secret

        return resolve_secret(self, name, allow_raw=allow_raw)
