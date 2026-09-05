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


_MULTIPART = """
environment = "staging"

[credentials.r2_keys]
profile = "staging"

[credentials.r2_keys.env]
access_key_id = "COFFERDAM_TEST_AKID"
secret_access_key = "COFFERDAM_TEST_SAK"

[credentials.json_cred]
profile = "staging"
secret_env = "COFFERDAM_TEST_JSON"
"""


def test_resolve_credentials_returns_every_secret(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A multi-part credential resolves as a mapping (BR-SECRET-004)."""
    monkeypatch.setenv("COFFERDAM_TEST_AKID", "AKID")
    monkeypatch.setenv("COFFERDAM_TEST_SAK", "s3cr3t")
    policy = loads_policy(_MULTIPART)
    assert policy.resolve_credentials("r2_keys") == {
        "access_key_id": "AKID",
        "secret_access_key": "s3cr3t",
    }


def test_resolve_credentials_missing_var_fails_closed(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """One unset variable denies the whole credential (BR-SECRET-004, BR-LOG-002)."""
    monkeypatch.setenv("COFFERDAM_TEST_AKID", "AKID")
    monkeypatch.delenv("COFFERDAM_TEST_SAK", raising=False)
    policy = loads_policy(_MULTIPART)
    with pytest.raises(SecretResolutionError) as excinfo:
        policy.resolve_credentials("r2_keys")
    assert "COFFERDAM_TEST_SAK" in str(excinfo.value)
    assert "AKID" not in str(excinfo.value)  # no resolved value in the message


def test_resolve_secret_on_multipart_credential_redirects(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The single-value API refuses a multi-part credential rather than guessing."""
    policy = loads_policy(_MULTIPART)
    with pytest.raises(CredentialError) as excinfo:
        policy.resolve_secret("r2_keys")
    assert "resolve_credentials" in str(excinfo.value)


def test_resolve_credentials_on_single_valued_credential_redirects() -> None:
    """And the reverse: no `env` table means no mapping to resolve (BR-SECRET-004)."""
    policy = loads_policy(_MULTIPART)
    with pytest.raises(CredentialError) as excinfo:
        policy.resolve_credentials("json_cred")
    assert "resolve_secret" in str(excinfo.value)


def test_resolve_json_secret_parses_object(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A secret that is itself a JSON object parses in one step (BR-SECRET-005)."""
    monkeypatch.setenv("COFFERDAM_TEST_JSON", '{"client_id": "abc", "key": "s3cr3t"}')
    policy = loads_policy(_MULTIPART)
    assert policy.resolve_json_secret("json_cred") == {"client_id": "abc", "key": "s3cr3t"}


def test_resolve_json_secret_never_echoes_the_value(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A parse failure must not leak the secret through the chained exception.

    ``json.JSONDecodeError`` carries the whole document on ``.doc``. Suppressing
    the chain for display is not enough — the object must not be reachable at
    all, so neither ``__cause__`` nor ``__context__`` may hold it
    (BR-SECRET-005, BR-LOG-002).
    """
    monkeypatch.setenv("COFFERDAM_TEST_JSON", "s3cr3t-not-json")
    policy = loads_policy(_MULTIPART)
    with pytest.raises(SecretResolutionError) as excinfo:
        policy.resolve_json_secret("json_cred")
    assert "s3cr3t" not in str(excinfo.value)
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None


def test_resolve_json_secret_rejects_non_object(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Valid JSON that is not an object is refused, without echoing it (BR-SECRET-005)."""
    monkeypatch.setenv("COFFERDAM_TEST_JSON", '"s3cr3t"')
    policy = loads_policy(_MULTIPART)
    with pytest.raises(SecretResolutionError) as excinfo:
        policy.resolve_json_secret("json_cred")
    assert "s3cr3t" not in str(excinfo.value)
    assert "expected an object" in str(excinfo.value)
