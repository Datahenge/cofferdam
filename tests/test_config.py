"""Config loading, validation, and fail-closed file handling (BR-CONFIG-*, BR-VALIDATE-*)."""

from __future__ import annotations

import pytest

from cofferdam import (
    Environment,
    PolicyFileNotFoundError,
    PolicyValidationError,
    load_policy,
    loads_policy,
)


def test_example_policy_parses(staging_policy) -> None:  # type: ignore[no-untyped-def]
    assert staging_policy.environment is Environment.STAGING
    assert "windmill" in staging_policy.integrations
    assert staging_policy.integrations["stripe"].allow_capture is False


def test_missing_file_fails_closed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(PolicyFileNotFoundError):
        load_policy(tmp_path / "nope.toml")


def test_malformed_toml_rejected() -> None:
    with pytest.raises(PolicyValidationError):
        loads_policy("environment = 'staging' this is not toml")


def test_unknown_field_rejected() -> None:
    with pytest.raises(PolicyValidationError):
        loads_policy('environment = "staging"\nbogus_key = 1\n')


def test_undefined_credential_reference_rejected() -> None:
    text = """
    environment = "staging"

    [integrations.windmill]
    enabled = true
    kind = "vendor_api"
    credential = "not_defined"
    """
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(text)
    assert any("undefined credential" in p for p in excinfo.value.problems)


def test_strict_rejects_raw_secret() -> None:
    text = """
    environment = "dev"

    [credentials.raw]
    profile = "dev"
    secret_value = "should-not-be-here"
    """
    # Non-strict parse succeeds; strict validation rejects the raw secret.
    loads_policy(text)
    with pytest.raises(PolicyValidationError):
        loads_policy(text, strict=True)


def test_production_blanket_allow_rejected() -> None:
    text = """
    environment = "production"
    default_decision = "allow"
    """
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(text)
    assert any("blanket allow-all" in p for p in excinfo.value.problems)
