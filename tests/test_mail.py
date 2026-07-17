"""Tests for cofferdam.mail — recipient checks and email decoration.

BR-EMAIL-001..008, BR-EMAIL-DECORATE-001..006.
"""

from __future__ import annotations

from typing import Any

from cofferdam import loads_policy
from cofferdam.mail import (
    check_recipient,
    decorate_body,
    decorate_email,
    decorate_subject,
    should_decorate,
)

# ---------------------------------------------------------------------------
# Policy fixtures (inline TOML to cover modes not in the staging example)
# ---------------------------------------------------------------------------

_DENY_POLICY = """
environment = "staging"
[mail]
mode = "deny"
"""

_SINK_POLICY = """
environment = "staging"
[mail]
mode = "sink"
sink = "dev@internal.test"
"""

_ALLOW_INTERNAL_POLICY = """
environment = "staging"
[mail]
mode = "allow_internal"
allow_domains = ["internal.example.com"]

[effects.email.customer]
enabled = false

[effects.email.internal]
enabled = true
allow_domains = ["internal.example.com"]
"""

_NO_MAIL_POLICY = """
environment = "staging"
"""

_PRODUCTION_POLICY = """
environment = "production"
[mail]
mode = "sink"
sink = "dev@internal.test"
"""

_DECORATE_OFF_POLICY = """
environment = "staging"
[mail]
mode = "sink"
sink = "dev@internal.test"
decorate = false
"""


def _load(toml: str) -> Any:
    return loads_policy(toml)


# ---------------------------------------------------------------------------
# check_recipient — mode = "deny" (BR-EMAIL-003)
# ---------------------------------------------------------------------------


def test_deny_mode_rejects_all() -> None:
    """BR-EMAIL-003: deny mode rejects every recipient."""
    policy = _load(_DENY_POLICY)
    result = check_recipient(policy, recipient="user@example.com")
    assert not result.allowed
    assert result.reason_code == "mail_mode_deny"


def test_no_mail_policy_fails_closed() -> None:
    """BR-EMAIL-002: absent [mail] section fails closed."""
    policy = _load(_NO_MAIL_POLICY)
    result = check_recipient(policy, recipient="user@example.com")
    assert not result.allowed
    assert result.reason_code == "no_mail_policy"


# ---------------------------------------------------------------------------
# check_recipient — mode = "sink" (BR-EMAIL-005)
# ---------------------------------------------------------------------------


def test_sink_mode_allows_with_redirect() -> None:
    """BR-EMAIL-005: sink mode allows all recipients and provides redirect_to."""
    policy = _load(_SINK_POLICY)
    result = check_recipient(policy, recipient="customer@external.com")
    assert result.allowed
    assert result.reason_code == "sink_redirect"
    assert result.redirect_to == "dev@internal.test"


def test_sink_mode_redirects_internal_too() -> None:
    """BR-EMAIL-005: sink redirects apply even to internal addresses."""
    policy = _load(_SINK_POLICY)
    result = check_recipient(policy, recipient="staff@internal.example.com")
    assert result.allowed
    assert result.reason_code == "sink_redirect"


# ---------------------------------------------------------------------------
# check_recipient — allow_internal mode (BR-EMAIL-004, BR-EMAIL-007)
# ---------------------------------------------------------------------------


def test_internal_domain_allowed(staging_policy: Any) -> None:
    """BR-EMAIL-004: recipient in allow_domains is permitted."""
    policy = _load(_ALLOW_INTERNAL_POLICY)
    result = check_recipient(policy, recipient="staff@internal.example.com")
    assert result.allowed
    assert result.reason_code == "domain_allowed"


def test_external_domain_denied() -> None:
    """BR-EMAIL-003: external recipient denied when no rule permits."""
    policy = _load(_ALLOW_INTERNAL_POLICY)
    result = check_recipient(policy, recipient="customer@external.com")
    assert not result.allowed
    assert result.reason_code == "no_matching_rule"


def test_customer_class_disabled() -> None:
    """BR-EMAIL-007: effects.email.customer disabled blocks that recipient class."""
    policy = _load(_ALLOW_INTERNAL_POLICY)
    result = check_recipient(
        policy,
        recipient="buyer@internal.example.com",
        recipient_class="customer",
    )
    assert not result.allowed
    assert result.reason_code == "recipient_class_disabled"


def test_internal_class_allowed_by_effect() -> None:
    """BR-EMAIL-007: effects.email.internal enabled allows matching domain."""
    policy = _load(_ALLOW_INTERNAL_POLICY)
    result = check_recipient(
        policy,
        recipient="staff@internal.example.com",
        recipient_class="internal",
    )
    assert result.allowed
    assert result.reason_code == "domain_allowed"


def test_name_bracket_address_parsed() -> None:
    """BR-EMAIL-002: 'Display Name <user@domain>' format is parsed correctly."""
    policy = _load(_ALLOW_INTERNAL_POLICY)
    result = check_recipient(
        policy, recipient="Alice Smith <alice@internal.example.com>"
    )
    assert result.allowed


# ---------------------------------------------------------------------------
# should_decorate (BR-EMAIL-DECORATE-001, BR-EMAIL-DECORATE-002)
# ---------------------------------------------------------------------------


def test_should_decorate_staging() -> None:
    """BR-EMAIL-DECORATE-001: staging environment decorates by default."""
    assert should_decorate(_load(_SINK_POLICY))


def test_should_decorate_production_never() -> None:
    """BR-EMAIL-DECORATE-001: production never decorates."""
    assert not should_decorate(_load(_PRODUCTION_POLICY))


def test_should_decorate_opt_out() -> None:
    """BR-EMAIL-DECORATE-002: decorate=false suppresses decoration."""
    assert not should_decorate(_load(_DECORATE_OFF_POLICY))


def test_should_decorate_no_mail_section() -> None:
    """BR-EMAIL-DECORATE-002: absent [mail] section defaults to decorating."""
    assert should_decorate(_load(_NO_MAIL_POLICY))


# ---------------------------------------------------------------------------
# decorate_subject (BR-EMAIL-DECORATE-003)
# ---------------------------------------------------------------------------


def test_decorate_subject_staging() -> None:
    """BR-EMAIL-DECORATE-003: environment name uppercased and prepended."""
    assert decorate_subject("Weekly Sales Report", environment="staging") == (
        "STAGING - Weekly Sales Report"
    )


def test_decorate_subject_test_env() -> None:
    assert decorate_subject("Invoice #1042 Ready", environment="test") == (
        "TEST - Invoice #1042 Ready"
    )


def test_decorate_subject_dev() -> None:
    assert decorate_subject("Password Reset", environment="dev") == (
        "DEV - Password Reset"
    )


# ---------------------------------------------------------------------------
# decorate_body — plain text (BR-EMAIL-DECORATE-004, BR-EMAIL-DECORATE-006)
# ---------------------------------------------------------------------------


def test_decorate_body_plain_text_prepends_notice() -> None:
    """BR-EMAIL-DECORATE-006: plain-text body gets notice + blank line prepended."""
    result = decorate_body("Hello, world.", environment="staging")
    assert result.startswith("[STAGING]")
    assert "staging environment" in result
    assert "not Production" in result
    assert result.endswith("Hello, world.")


def test_decorate_body_plain_text_blank_line_separator() -> None:
    """BR-EMAIL-DECORATE-006: blank line separates notice from original body."""
    result = decorate_body("Body text.", environment="staging")
    assert "\n\nBody text." in result


# ---------------------------------------------------------------------------
# decorate_body — HTML (BR-EMAIL-DECORATE-004, BR-EMAIL-DECORATE-005)
# ---------------------------------------------------------------------------


def test_decorate_body_html_detection_body_tag() -> None:
    """BR-EMAIL-DECORATE-004: body containing <body is treated as HTML."""
    html = "<html><body><p>Hello</p></body></html>"
    result = decorate_body(html, environment="staging")
    assert "<div" in result
    assert "STAGING" in result


def test_decorate_body_html_detection_html_tag() -> None:
    """BR-EMAIL-DECORATE-004: body containing <html (no <body) is treated as HTML."""
    html = "<html><p>Hello</p></html>"
    result = decorate_body(html, environment="staging")
    assert "<div" in result


def test_decorate_body_html_banner_after_body_tag() -> None:
    """BR-EMAIL-DECORATE-005: banner injected immediately after <body> tag."""
    html = "<html><body><p>Content</p></body></html>"
    result = decorate_body(html, environment="staging")
    body_pos = result.lower().index("<body>")
    div_pos = result.index("<div", body_pos)
    p_pos = result.index("<p>Content</p>", div_pos)
    assert body_pos < div_pos < p_pos


def test_decorate_body_html_banner_after_body_with_attrs() -> None:
    """BR-EMAIL-DECORATE-005: banner works when <body> has attributes."""
    html = '<html><body class="main"><p>Content</p></body></html>'
    result = decorate_body(html, environment="staging")
    assert '<body class="main">' in result
    assert "<div" in result
    # banner appears after the opening body tag
    assert result.index("<div") > result.index('<body class="main">')


def test_decorate_body_html_no_body_tag_prepends() -> None:
    """BR-EMAIL-DECORATE-005: when no <body tag, banner is prepended."""
    html = "<html><p>Hello</p></html>"
    result = decorate_body(html, environment="staging")
    assert result.startswith("<div")


def test_decorate_body_html_banner_case_insensitive_detection() -> None:
    """BR-EMAIL-DECORATE-004: detection is case-insensitive."""
    html = "<HTML><BODY><p>Hello</p></BODY></HTML>"
    result = decorate_body(html, environment="staging")
    assert "<div" in result


def test_decorate_body_html_banner_contains_env_name() -> None:
    """BR-EMAIL-DECORATE-005: banner text contains the environment name."""
    html = "<html><body><p>Hi</p></body></html>"
    result = decorate_body(html, environment="test")
    assert "TEST" in result
    assert "not Production" in result


def test_decorate_body_html_banner_style() -> None:
    """BR-EMAIL-DECORATE-005: banner carries the expected warning style."""
    html = "<html><body><p>Hi</p></body></html>"
    result = decorate_body(html, environment="staging")
    assert "background:#f59e0b" in result


# ---------------------------------------------------------------------------
# decorate_email convenience wrapper (BR-EMAIL-DECORATE-001, BR-EMAIL-DECORATE-002)
# ---------------------------------------------------------------------------


def test_decorate_email_decorates_non_production() -> None:
    """decorate_email applies both subject and body decoration for non-production."""
    policy = _load(_SINK_POLICY)
    s, b = decorate_email("Report", "Hello.", policy=policy)
    assert s == "STAGING - Report"
    assert "[STAGING]" in b


def test_decorate_email_passthrough_production() -> None:
    """BR-EMAIL-DECORATE-001: decorate_email is a no-op for production."""
    policy = _load(_PRODUCTION_POLICY)
    s, b = decorate_email("Report", "Hello.", policy=policy)
    assert s == "Report"
    assert b == "Hello."


def test_decorate_email_passthrough_when_opt_out() -> None:
    """BR-EMAIL-DECORATE-002: decorate_email is a no-op when decorate=false."""
    policy = _load(_DECORATE_OFF_POLICY)
    s, b = decorate_email("Report", "Hello.", policy=policy)
    assert s == "Report"
    assert b == "Hello."
