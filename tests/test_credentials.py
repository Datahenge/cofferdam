"""Credential resolution and redaction (BR-SECRET-*, BR-LOG-002)."""

from __future__ import annotations

import pytest

from cofferdam import CredentialError, SecretResolutionError, loads_policy

_POLICY = """
environment = "staging"

[credentials.env_cred]
profile = "staging"
secret_env = "COFFERDAM_TEST_SECRET"

[credentials.raw_cred]
profile = "dev"
secret_value = "inline-secret"
"""


def test_resolve_from_env(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("COFFERDAM_TEST_SECRET", "s3cr3t")
    policy = loads_policy(_POLICY)
    assert policy.resolve_secret("env_cred") == "s3cr3t"


def test_missing_env_var_raises(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("COFFERDAM_TEST_SECRET", raising=False)
    policy = loads_policy(_POLICY)
    with pytest.raises(SecretResolutionError) as excinfo:
        policy.resolve_secret("env_cred")
    # The variable name may appear; the secret value never can (there is none set).
    assert "COFFERDAM_TEST_SECRET" in str(excinfo.value)


def test_raw_secret_rejected_by_default() -> None:
    policy = loads_policy(_POLICY)
    with pytest.raises(CredentialError):
        policy.resolve_secret("raw_cred")


def test_raw_secret_allowed_with_optin() -> None:
    policy = loads_policy(_POLICY)
    assert policy.resolve_secret("raw_cred", allow_raw=True) == "inline-secret"


def test_unknown_credential_raises() -> None:
    policy = loads_policy(_POLICY)
    with pytest.raises(CredentialError):
        policy.resolve_secret("nope")
