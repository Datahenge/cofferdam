"""The allow/deny decision engine (BR-DECISION-*).

The engine is **fail-closed** (ADR-0005): a side effect is allowed only when the
policy *explicitly* permits every dimension the caller supplies. Any missing,
disabled, mismatched, or empty-allowlist condition denies. Each decision carries
a stable ``reason_code`` and a redacted, log-safe context (BR-LOG-001) that never
includes a secret value (BR-LOG-002).
"""

from __future__ import annotations

from dataclasses import dataclass

from cofferdam.errors import PolicyDeniedError
from cofferdam.models import Policy, SideEffectKind


def host_matches(host: str, allowed_hosts: list[str]) -> bool:
    """Return True iff ``host`` exactly matches an allowed hostname.

    Comparison is case-insensitive and matches whole hostnames only, never
    substrings, so ``sandbox.vendor.com`` never authorizes
    ``sandbox.vendor.com.evil.example`` (BR-HOST-001). Extraction of a hostname
    from a full URL is the caller's responsibility (see :mod:`cofferdam.http`).
    """
    needle = host.strip().rstrip(".").lower()
    if not needle:
        return False
    return any(needle == allowed.strip().rstrip(".").lower() for allowed in allowed_hosts)


@dataclass(frozen=True)
class Decision:
    """The structured outcome of a policy evaluation.

    ``allowed`` is the verdict; ``reason_code`` is a stable machine-readable
    token (e.g. ``"host_not_allowed"``). The remaining fields are log-safe
    context. ``credential`` is the credential *reference name*, never its value.
    """

    allowed: bool
    reason_code: str
    environment: str | None = None
    integration: str | None = None
    kind: str | None = None
    operation: str | None = None
    method: str | None = None
    host: str | None = None
    credential: str | None = None
    detail: str = ""

    def as_log_dict(self) -> dict[str, object]:
        """Return a redacted mapping suitable for structured logging (BR-LOG-001)."""
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "environment": self.environment,
            "integration": self.integration,
            "kind": self.kind,
            "operation": self.operation,
            "method": self.method,
            "host": self.host,
            "credential": self.credential,  # reference name only, never the secret
            "detail": self.detail,
        }

    def message(self) -> str:
        verb = "allowed" if self.allowed else "denied"
        return (
            f"outbound side effect {verb} "
            f"[env={self.environment} integration={self.integration} "
            f"kind={self.kind} operation={self.operation}] reason={self.reason_code}"
            + (f": {self.detail}" if self.detail else "")
        )

    def to_exception(self) -> PolicyDeniedError:
        """Build (but do not raise) a :class:`PolicyDeniedError` from this decision."""
        return PolicyDeniedError(self)


@dataclass(frozen=True)
class _Ctx:
    """Common evaluation context threaded into each Decision."""

    environment: str
    integration: str | None = None
    kind: str | None = None
    operation: str | None = None
    method: str | None = None
    host: str | None = None
    credential: str | None = None

    def deny(self, reason_code: str, detail: str = "") -> Decision:
        return Decision(allowed=False, reason_code=reason_code, detail=detail, **vars(self))

    def allow(self, reason_code: str = "explicitly_allowed", detail: str = "") -> Decision:
        return Decision(allowed=True, reason_code=reason_code, detail=detail, **vars(self))


def decide(
    policy: Policy,
    *,
    integration: str,
    kind: str | None = None,
    operation: str | None = None,
    method: str | None = None,
    host: str | None = None,
    credential: str | None = None,
) -> Decision:
    """Evaluate whether a single outbound side effect is permitted (BR-DECISION-001..010).

    Only the dimensions the caller supplies are enforced, and each supplied
    dimension must appear in the integration's explicit allowlist. An empty
    allowlist denies (fail-closed). See ``docs/04-decision-engine.md``.
    """
    ctx = _Ctx(
        environment=policy.environment.value,
        integration=integration,
        kind=kind,
        operation=operation,
        method=method,
        host=host,
        credential=credential,
    )

    integ = policy.integrations.get(integration)
    if integ is None:
        return ctx.deny("unknown_integration")
    if not integ.enabled:
        return ctx.deny("integration_disabled")

    if kind is not None and integ.kind.value != kind:
        return ctx.deny("kind_mismatch", f"policy declares kind={integ.kind.value}")

    # Credential reference must exist and, if the integration pins one, must match.
    if credential is not None:
        if credential not in policy.credentials:
            return ctx.deny("missing_credential")
        if integ.credential is not None and integ.credential != credential:
            return ctx.deny("credential_mismatch", f"integration requires {integ.credential!r}")

    # Operation must be explicitly allowed when supplied (empty list denies).
    if operation is not None and operation not in integ.allowed_operations:
        return ctx.deny("operation_not_allowed")

    # Payment-specific gates.
    if integ.kind is SideEffectKind.PAYMENT:
        if operation == "authorize" and not integ.allow_authorize:
            return ctx.deny("payment_authorize_not_allowed")
        if operation == "capture" and not integ.allow_capture:
            return ctx.deny("payment_capture_not_allowed")

    # HTTP method must be explicitly allowed when supplied (empty list denies).
    if method is not None:
        allowed_methods = {m.upper() for m in integ.allowed_methods}
        if method.upper() not in allowed_methods:
            return ctx.deny("method_not_allowed")

    # Host must be explicitly allowed when supplied (empty list denies).
    if host is not None and not host_matches(host, integ.allowed_hosts):
        return ctx.deny("host_not_allowed")

    return ctx.allow()


def assert_allowed(policy: Policy, **kwargs: object) -> Decision:
    """Evaluate a side effect and raise :class:`PolicyDeniedError` if denied.

    Returns the allowing :class:`Decision` so callers may log it.
    """
    decision = decide(policy, **kwargs)  # type: ignore[arg-type]
    if not decision.allowed:
        raise decision.to_exception()
    return decision
