"""CLI smoke tests (BR-CLI-*)."""

from __future__ import annotations

from pathlib import Path

from cofferdam.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "environment_policy.staging.toml"


def test_validate_ok(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["validate", str(EXAMPLE)]) == 0
    assert "OK" in capsys.readouterr().out


def test_validate_missing_file_nonzero() -> None:
    assert main(["validate", "/no/such/policy.toml"]) == 2


def test_inspect_redacts_secrets(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["inspect", str(EXAMPLE)]) == 0
    out = capsys.readouterr().out
    assert "windmill" in out
    assert "env:WINDMILL_API_KEY" in out  # source name shown, value never resolved


def test_decide_allow(capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(
        [
            "decide",
            str(EXAMPLE),
            "--integration",
            "windmill",
            "--kind",
            "vendor_api",
            "--operation",
            "write",
            "--method",
            "POST",
            "--url",
            "https://sandbox.windmill.dev/api/jobs/run",
            "--credential",
            "windmill_default",
        ]
    )
    assert code == 0
    assert "ALLOW" in capsys.readouterr().out


def test_decide_deny_production_host(capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(
        [
            "decide",
            str(EXAMPLE),
            "--integration",
            "windmill",
            "--operation",
            "write",
            "--method",
            "POST",
            "--url",
            "https://windmill.prod.example.com/api/jobs/run",
            "--credential",
            "windmill_default",
        ]
    )
    assert code == 1
    assert "DENY" in capsys.readouterr().out
