"""Shared pytest fixtures for the cofferdam test suite.

Tests must run without a Frappe Bench (BR-TEST-004).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cofferdam import Policy, loads_policy

_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_POLICY = _ROOT / "examples" / "environment_policy.staging.toml"


@pytest.fixture
def staging_policy() -> Policy:
    """The canonical staging example policy, parsed."""
    return loads_policy(EXAMPLE_POLICY.read_text(encoding="utf-8"), source=str(EXAMPLE_POLICY))
