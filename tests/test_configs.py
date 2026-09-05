"""Structured site-local configuration (BR-CONFIG-004..006, BR-VALIDATE-012..015)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cofferdam import ConfigError, PolicyValidationError, loads_policy

_POLICY = """
environment = "dev"
default_decision = "deny"

[integrations.cloudflare_r2]
enabled = true
kind = "file_transfer"
credential = "cloudflare_r2_keys"
config = "cloudflare_r2_dev"
allowed_hosts = ["abc123.r2.cloudflarestorage.com"]
allowed_methods = ["GET", "PUT", "DELETE"]
allowed_operations = ["upload", "download", "delete"]

[configs.cloudflare_r2_dev]
account_id = "abc123"
endpoint_url = "https://abc123.r2.cloudflarestorage.com"
bucket_name = "foo-erpnext-dev"
region_name = "auto"
presigned_get_expiry_seconds = 300
delete_from_r2_on_file_delete = false
allowed_extensions = ["pdf", "png"]

[configs.cloudflare_r2_dev.retry]
maxAttempts = 3

[credentials.cloudflare_r2_keys]
profile = "dev"

[credentials.cloudflare_r2_keys.env]
access_key_id = "R2_ACCESS_KEY_ID"
secret_access_key = "R2_SECRET_ACCESS_KEY"
"""


def test_config_values_round_trip_by_type() -> None:
    """A config carries TOML scalars, arrays, and nested tables (BR-CONFIG-004)."""
    config = loads_policy(_POLICY).resolve_config("cloudflare_r2_dev")
    assert config["endpoint_url"] == "https://abc123.r2.cloudflarestorage.com"
    assert config["presigned_get_expiry_seconds"] == 300
    assert config["delete_from_r2_on_file_delete"] is False
    assert config["allowed_extensions"] == ["pdf", "png"]
    assert config["retry"] == {"maxAttempts": 3}


def test_config_keys_keep_exact_casing() -> None:
    """Application config keys are never case-normalized (BR-CONFIG-005)."""
    policy = loads_policy(
        """
environment = "dev"

[configs.app]
MixedCase = 1
UPPER = 2
lower = 3
"""
    )
    assert set(policy.resolve_config("app")) == {"MixedCase", "UPPER", "lower"}


def test_integration_resolves_config_and_credentials_independently(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    """The motivating case: non-secret settings and key material, separately (ADR-0014)."""
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "AKID")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "s3cr3t")
    policy = loads_policy(_POLICY)

    integration = policy.integrations["cloudflare_r2"]
    config = policy.resolve_config(integration.config)
    secrets = policy.resolve_credentials(integration.credential or "")

    assert config["bucket_name"] == "foo-erpnext-dev"
    assert config.get("region_name", "auto") == "auto"
    assert secrets == {"access_key_id": "AKID", "secret_access_key": "s3cr3t"}


def test_unknown_config_fails_closed() -> None:
    """A typo raises rather than yielding an empty mapping (BR-CONFIG-004, ADR-0005)."""
    policy = loads_policy(_POLICY)
    with pytest.raises(ConfigError):
        policy.resolve_config("cloudflare_r2_prod")


def test_config_none_fails_closed() -> None:
    """An integration that declares no config cannot resolve one (BR-CONFIG-004)."""
    policy = loads_policy(_POLICY)
    with pytest.raises(ConfigError):
        policy.resolve_config(None)


def test_resolved_config_is_a_copy() -> None:
    """Mutating a resolved config cannot alter the loaded policy (BR-CONFIG-004)."""
    policy = loads_policy(_POLICY)
    config = policy.resolve_config("cloudflare_r2_dev")
    config["bucket_name"] = "tampered"
    config["retry"]["maxAttempts"] = 99
    assert policy.resolve_config("cloudflare_r2_dev")["bucket_name"] == "foo-erpnext-dev"
    assert policy.resolve_config("cloudflare_r2_dev")["retry"] == {"maxAttempts": 3}


def test_undefined_config_reference_rejected_at_load() -> None:
    """An integration referencing an undefined config fails at load (BR-VALIDATE-012)."""
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(
            """
environment = "dev"

[integrations.r2]
enabled = true
kind = "file_transfer"
config = "nope"
"""
        )
    assert any("BR-VALIDATE-012" in p for p in excinfo.value.problems)


def test_configs_section_typo_still_rejected() -> None:
    """`configs` is a known key; a near-miss still trips extra=forbid (BR-VALIDATE-003)."""
    with pytest.raises(PolicyValidationError):
        loads_policy('environment = "dev"\n\n[config.r2]\nbucket = "x"\n')


@pytest.mark.parametrize(
    "key",
    ["api_key", "password", "SECRET_ACCESS_KEY", "auth-token", "private_key", "passphrase"],
)
def test_strict_rejects_secret_shaped_config_keys(key: str) -> None:
    """Strict mode refuses secret material in a config (BR-CONFIG-006, BR-VALIDATE-013)."""
    text = f'environment = "dev"\n\n[configs.app]\n{key} = "x"\n'
    loads_policy(text)  # permitted on the hot path
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(text, strict=True)
    assert any("BR-VALIDATE-013" in p for p in excinfo.value.problems)


def test_strict_finds_secret_shaped_key_when_nested() -> None:
    """The check descends into nested tables and reports the path (BR-VALIDATE-013)."""
    text = 'environment = "dev"\n\n[configs.app.inner]\nclient_secret = "x"\n'
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(text, strict=True)
    assert any("configs.app.inner.client_secret" in p for p in excinfo.value.problems)


@pytest.mark.parametrize(
    "key",
    ["account_id", "endpoint_url", "bucket_name", "region_name", "access_key_id"],
)
def test_strict_permits_non_secret_config_keys(key: str) -> None:
    """Identifiers and settings are not secrets; access_key_id is exempt by design."""
    loads_policy(f'environment = "dev"\n\n[configs.app]\n{key} = "x"\n', strict=True)


def test_strict_requires_every_env_var_of_a_multipart_credential(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    """A multi-part credential is only usable if every variable is set (BR-VALIDATE-007)."""
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "AKID")
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(_POLICY, strict=True)
    problems = " ".join(excinfo.value.problems)
    assert "R2_SECRET_ACCESS_KEY" in problems
    assert "R2_ACCESS_KEY_ID" not in problems


def test_credential_declaring_both_source_forms_rejected() -> None:
    """A credential names one source form, not two (BR-VALIDATE-015)."""
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(
            """
environment = "dev"

[credentials.mixed]
profile = "dev"
secret_env = "ONE"

[credentials.mixed.env]
other = "TWO"
"""
        )
    assert any("BR-VALIDATE-015" in p for p in excinfo.value.problems)


def test_unknown_key_error_names_the_key_and_the_alternatives() -> None:
    """An extra-key error points at the offending key and what was allowed (BR-VALIDATE-014)."""
    with pytest.raises(PolicyValidationError) as excinfo:
        loads_policy(
            """
environment = "dev"

[credentials.r2]
profile = "dev"
secret_acces_key_env = "R2_SECRET_ACCESS_KEY"
"""
        )
    (problem,) = excinfo.value.problems
    assert "credentials.r2" in problem
    assert "'secret_acces_key_env'" in problem
    assert "permitted:" in problem and "secret_env" in problem


def test_every_shipped_example_validates() -> None:
    """Shipped examples are documentation; a stale one is a broken doc (BR-TEST-001).

    Non-strict: the examples name environment variables that are not set in CI.
    """
    examples = sorted((Path(__file__).resolve().parents[1] / "examples").glob("*.toml"))
    assert examples, "no example policies found"
    for path in examples:
        loads_policy(path.read_text(encoding="utf-8"), source=str(path))
