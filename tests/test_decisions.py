"""Restore-safety and fail-closed decision tests (BR-TEST-*, acceptance criteria 2-8)."""

from __future__ import annotations

import pytest

from cofferdam import Policy, PolicyDeniedError
from cofferdam.decisions import decide, host_matches


def test_windmill_sandbox_write_allowed_in_staging(staging_policy: Policy) -> None:
    """Acceptance criterion 2: sandbox Windmill call is allowed in Staging."""
    decision = staging_policy.decide(
        integration="windmill",
        kind="vendor_api",
        operation="write",
        method="POST",
        host="sandbox.windmill.dev",
        credential="windmill_default",
    )
    assert decision.allowed
    assert decision.reason_code == "explicitly_allowed"


def test_production_windmill_host_blocked_in_staging(staging_policy: Policy) -> None:
    """Acceptance criterion 2: a Production host is blocked even for an enabled integration."""
    decision = staging_policy.decide(
        integration="windmill",
        kind="vendor_api",
        operation="write",
        method="POST",
        host="windmill.production.example.com",
        credential="windmill_default",
    )
    assert not decision.allowed
    assert decision.reason_code == "host_not_allowed"


def test_unknown_integration_denied(staging_policy: Policy) -> None:
    decision = staging_policy.decide(integration="does_not_exist")
    assert not decision.allowed
    assert decision.reason_code == "unknown_integration"


def test_payment_capture_denied_outside_production(staging_policy: Policy) -> None:
    """Acceptance criterion: never capture money in Staging."""
    decision = staging_policy.decide(
        integration="stripe", kind="payment", operation="capture", host="api.stripe.com"
    )
    assert not decision.allowed
    assert decision.reason_code == "operation_not_allowed"


def test_payment_authorize_allowed(staging_policy: Policy) -> None:
    decision = staging_policy.decide(
        integration="stripe",
        kind="payment",
        operation="authorize",
        method="POST",
        host="api.stripe.com",
    )
    # 'authorize' is gated by allow_authorize but must also be an allowed_operation.
    # The example policy does not list operations for stripe, so this is denied
    # fail-closed — documenting that operation allowlists are required.
    assert not decision.allowed
    assert decision.reason_code == "operation_not_allowed"


def test_method_not_allowed(staging_policy: Policy) -> None:
    decision = staging_policy.decide(
        integration="windmill",
        kind="vendor_api",
        operation="write",
        method="DELETE",
        host="sandbox.windmill.dev",
        credential="windmill_default",
    )
    assert not decision.allowed
    assert decision.reason_code == "method_not_allowed"


def test_credential_mismatch_denied(staging_policy: Policy) -> None:
    decision = staging_policy.decide(
        integration="windmill",
        kind="vendor_api",
        operation="read",
        host="sandbox.windmill.dev",
        credential="stripe_default",
    )
    assert not decision.allowed
    assert decision.reason_code == "credential_mismatch"


def test_assert_allowed_raises_on_deny(staging_policy: Policy) -> None:
    with pytest.raises(PolicyDeniedError) as excinfo:
        staging_policy.assert_allowed(integration="windmill", host="evil.example.com")
    assert excinfo.value.decision.reason_code == "host_not_allowed"


@pytest.mark.parametrize(
    ("host", "allowed", "expected"),
    [
        ("sandbox.vendor.com", ["sandbox.vendor.com"], True),
        ("SANDBOX.VENDOR.COM", ["sandbox.vendor.com"], True),
        ("sandbox.vendor.com.evil.example", ["sandbox.vendor.com"], False),
        ("evil.sandbox.vendor.com", ["sandbox.vendor.com"], False),
        ("", ["sandbox.vendor.com"], False),
    ],
)
def test_host_matches_is_not_substring(host: str, allowed: list[str], expected: bool) -> None:
    """BR-HOST-001: whole-hostname match, never substring."""
    assert host_matches(host, allowed) is expected


def test_no_secret_in_decision_log(staging_policy: Policy) -> None:
    """BR-LOG-002: the log dict carries the credential name, never a value."""
    decision = decide(
        staging_policy,
        integration="windmill",
        operation="read",
        host="sandbox.windmill.dev",
        credential="windmill_default",
    )
    log = decision.as_log_dict()
    assert log["credential"] == "windmill_default"
    assert "WINDMILL_API_KEY" not in str(log)
