"""Email policy checks (BR-EMAIL-*).

v1 provides *policy checks* that project-specific ERPNext email code can call to
avoid unsafe sends — it does not replace Frappe's email subsystem (ADR-0007
scope note; docs/07-email-policy.md). Supported dispositions include: deny all
external mail in non-Production, allow listed internal domains, redirect to a
sink address, and block customer/supplier recipient classes.

    STATUS: scaffolding. Signatures are frozen by the requirements; bodies are
    implemented in the email milestone (implementation sequence step 8).
"""

from __future__ import annotations

from dataclasses import dataclass

from cofferdam.models import Policy


@dataclass(frozen=True)
class MailDecision:
    """Outcome of an email policy check."""

    allowed: bool
    reason_code: str
    redirect_to: str | None = None
    subject_prefix: str | None = None


def check_recipient(
    policy: Policy, *, recipient: str, recipient_class: str = "unknown"
) -> MailDecision:
    """Decide whether mail may be sent to ``recipient`` (BR-EMAIL-002).

    Evaluates the recipient domain against ``policy.mail`` and the relevant
    ``effects.email.*`` rules, honoring sink-redirect and internal-domain
    allowances. Fails closed when no rule permits the recipient.
    """
    raise NotImplementedError(
        "cofferdam.mail.check_recipient is implemented in the email milestone."
    )
