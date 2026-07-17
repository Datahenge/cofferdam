"""Email policy checks and environment decoration (BR-EMAIL-*, BR-EMAIL-DECORATE-*).

v1 provides *policy checks* that project-specific ERPNext email code can call to
avoid unsafe sends — it does not replace Frappe's email subsystem (ADR-0011).
It also provides pure decoration functions that mutate subject and body so
non-production emails are unmistakably labelled before delivery (BR-EMAIL-006).
"""

from __future__ import annotations

from dataclasses import dataclass

from cofferdam.models import Environment, Policy

# ---------------------------------------------------------------------------
# HTML banner template (BR-EMAIL-DECORATE-005)
# ---------------------------------------------------------------------------

_HTML_BANNER = (
    '<div style="background:#f59e0b;color:#000;padding:8px 12px;'
    "font-family:sans-serif;font-weight:bold;margin-bottom:8px;\">"
    "⚠ This email was sent from the {env} environment — not Production."
    "</div>"
)

# Plain-text notice template (BR-EMAIL-DECORATE-006)
_PLAIN_NOTICE = (
    "[{env}] This email was sent from the {env_lower} environment"
    " — not Production.\n\n"
)


# ---------------------------------------------------------------------------
# Recipient decision (BR-EMAIL-002)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MailDecision:
    """Outcome of an email policy check (BR-EMAIL-002)."""

    allowed: bool
    reason_code: str
    redirect_to: str | None = None
    subject_prefix: str | None = None  # informational; use decorate_* for mutation


def _extract_domain(recipient: str) -> str:
    """Extract lowercase domain from an email address or 'Name <addr>' string."""
    if "<" in recipient and ">" in recipient:
        start = recipient.index("<") + 1
        end = recipient.index(">", start)
        recipient = recipient[start:end].strip()
    if "@" in recipient:
        return recipient.split("@", 1)[1].lower()
    return ""


def _domain_matches(domain: str, allowed: list[str]) -> bool:
    lower = domain.lower()
    return any(lower == d.lower() for d in allowed)


def check_recipient(
    policy: Policy, *, recipient: str, recipient_class: str = "unknown"
) -> MailDecision:
    """Decide whether mail may be sent to ``recipient`` (BR-EMAIL-002).

    Evaluates ``policy.mail`` and ``effects.email.*`` rules. Fails closed when
    no rule permits the recipient (BR-EMAIL-003).
    """
    if policy.mail is None:
        return MailDecision(allowed=False, reason_code="no_mail_policy")

    mode = policy.mail.mode

    # Deny mode: reject all outbound mail (BR-EMAIL-003)
    if mode == "deny":
        return MailDecision(allowed=False, reason_code="mail_mode_deny")

    # Sink mode: redirect every recipient to the sink address (BR-EMAIL-005)
    if mode == "sink":
        return MailDecision(
            allowed=True,
            reason_code="sink_redirect",
            redirect_to=policy.mail.sink,
        )

    # allow_internal (and any future modes): evaluate recipient domain
    domain = _extract_domain(recipient)

    # Scoped effect rule: class-level block takes priority over allow_domains (BR-EMAIL-007)
    effect_rule = policy.effects.get("email", {}).get(recipient_class)
    if effect_rule is not None and not effect_rule.enabled:
        return MailDecision(allowed=False, reason_code="recipient_class_disabled")

    # Top-level allow_domains (BR-EMAIL-004)
    if domain and _domain_matches(domain, policy.mail.allow_domains):
        return MailDecision(allowed=True, reason_code="domain_allowed")

    # Scoped effect allow_domains fallback
    if effect_rule is not None and domain and _domain_matches(domain, effect_rule.allow_domains):
        return MailDecision(allowed=True, reason_code="domain_allowed")

    return MailDecision(allowed=False, reason_code="no_matching_rule")


# ---------------------------------------------------------------------------
# Email decoration (BR-EMAIL-DECORATE-*)
# ---------------------------------------------------------------------------


def should_decorate(policy: Policy) -> bool:
    """Return True when subject/body decoration is active for this policy.

    Production never decorates (BR-EMAIL-DECORATE-001). For non-production,
    decoration is on by default and disabled only by ``decorate = false`` in
    ``[mail]`` (BR-EMAIL-DECORATE-002).
    """
    if policy.environment is Environment.PRODUCTION:
        return False
    if policy.mail is None:
        return True
    return policy.mail.decorate


def _is_html(body: str) -> bool:
    """BR-EMAIL-DECORATE-004: HTML detection by substring, no parser."""
    lower = body.lower()
    return "<html" in lower or "<body" in lower


def decorate_subject(subject: str, *, environment: str) -> str:
    """Prepend the uppercased environment name to ``subject`` (BR-EMAIL-DECORATE-003).

    Example: ``decorate_subject("Weekly Report", environment="staging")``
    returns ``"STAGING - Weekly Report"``.
    """
    return f"{environment.upper()} - {subject}"


def decorate_body(body: str, *, environment: str) -> str:
    """Decorate ``body`` with an environment notice (BR-EMAIL-DECORATE-004..006).

    HTML bodies receive a styled banner ``<div>`` injected after the first
    ``<body`` tag (or prepended when absent). Plain-text bodies receive a
    notice line prepended.
    """
    env_upper = environment.upper()

    if _is_html(body):
        banner = _HTML_BANNER.format(env=env_upper)
        lower = body.lower()
        start = lower.find("<body")
        if start != -1:
            close = body.find(">", start)
            if close != -1:
                pos = close + 1
                return body[:pos] + "\n" + banner + "\n" + body[pos:]
        return banner + "\n" + body

    notice = _PLAIN_NOTICE.format(env=env_upper, env_lower=environment.lower())
    return notice + body


def decorate_email(
    subject: str, body: str, *, policy: Policy
) -> tuple[str, str]:
    """Convenience wrapper: decorate subject and body when ``should_decorate`` is True.

    Returns the original strings unchanged when decoration is inactive
    (production environment or ``decorate = false`` in ``[mail]``).
    """
    if not should_decorate(policy):
        return subject, body
    env = policy.environment.value
    return decorate_subject(subject, environment=env), decorate_body(body, environment=env)
