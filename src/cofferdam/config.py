"""Load and parse TOML policy files (BR-CONFIG-*).

Uses the standard-library ``tomllib`` on Python 3.11+ and the ``tomli`` backport
on 3.10. Parsing produces a validated :class:`~cofferdam.models.Policy`; semantic
checks that span multiple sections are applied by :mod:`cofferdam.validators`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on 3.10 only
    import tomli as tomllib

from pydantic import ValidationError

from cofferdam.errors import PolicyFileNotFoundError, PolicyValidationError
from cofferdam.models import Policy


def _build_policy(data: dict[str, Any], *, source: str, strict: bool) -> Policy:
    try:
        policy = Policy.model_validate(data)
    except ValidationError as exc:
        problems = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        ]
        raise PolicyValidationError(
            f"invalid policy schema in {source}", problems=problems
        ) from exc

    from cofferdam.validators import validate_policy

    validate_policy(policy, strict=strict, source=source)
    return policy


def loads_policy(text: str, *, source: str = "<string>", strict: bool = False) -> Policy:
    """Parse and validate a policy from a TOML string."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PolicyValidationError(f"malformed TOML in {source}: {exc}") from exc
    return _build_policy(data, source=source, strict=strict)


def load_policy(path: str | Path, *, strict: bool = False) -> Policy:
    """Load, parse, and validate a policy from a filesystem path.

    :param strict: when True, apply stricter semantic checks (for example,
        verifying that every ``secret_env`` variable is set). Intended for the
        ``cofferdam validate`` CLI and CI, not the hot path.
    :raises PolicyFileNotFoundError: the file does not exist (fail-closed;
        BR-DECISION-001).
    :raises PolicyValidationError: the file is malformed or invalid.
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PolicyFileNotFoundError(f"policy file not found: {p}") from exc
    return loads_policy(text, source=str(p), strict=strict)
