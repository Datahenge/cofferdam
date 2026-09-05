"""Load and parse TOML policy files, and read `configs.*` sections (BR-CONFIG-*).

Uses the standard-library ``tomllib`` on Python 3.11+ and the ``tomli`` backport
on 3.10. Parsing produces a validated :class:`~cofferdam.models.Policy`; semantic
checks that span multiple sections are applied by :mod:`cofferdam.validators`.

``resolve_config`` lives here rather than in a separate module so that
``cofferdam.config`` (policy configuration) has no near-identical sibling name.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - exercised on 3.10 only
    import tomli as tomllib

from pydantic import ValidationError

from cofferdam.errors import ConfigError, PolicyFileNotFoundError, PolicyValidationError
from cofferdam.models import Credential, EffectRule, Integration, MailPolicy, Policy

# The model owning each policy section, used to name the permitted keys when a
# typo trips extra="forbid" (BR-VALIDATE-014).
_SECTION_MODELS: dict[str, type[Policy] | type[Credential] | type[Integration]
                      | type[MailPolicy] | type[EffectRule]] = {
    "credentials": Credential,
    "integrations": Integration,
    "effects": EffectRule,
    "mail": MailPolicy,
}


def _describe_error(err: dict[str, Any]) -> str:
    """Render one Pydantic error, naming permitted keys for a typo (BR-VALIDATE-014).

    Pydantic reports *where* an unknown key is but not what was expected there.
    The mistake this check exists to catch is nearly always a near-miss on a real
    key name, so the alternatives are worth printing.
    """
    loc = tuple(str(p) for p in err["loc"])
    where = ".".join(loc)
    if err["type"] != "extra_forbidden" or not loc:
        return f"{where}: {err['msg']}"

    owner = Policy if len(loc) == 1 else _SECTION_MODELS.get(loc[0])
    section = ".".join(loc[:-1]) or "<top level>"
    if owner is None:
        return f"{section}: unknown key {loc[-1]!r}"
    permitted = ", ".join(sorted(owner.model_fields))
    return f"{section}: unknown key {loc[-1]!r} (permitted: {permitted})"


def resolve_config(policy: Policy, name: str | None) -> dict[str, Any]:
    """Return a copy of the non-secret ``configs.<name>`` table (BR-CONFIG-004).

    Config values are structured, environment-specific and **not secret** — an
    endpoint, a bucket, a region, a prefix (ADR-0014). Keys are returned with
    their exact casing as written in the policy file (BR-CONFIG-005).

    A deep copy is returned so that a caller mutating the result cannot alter the
    loaded policy, which is otherwise immutable.

    :raises ConfigError: ``name`` is None (the integration declares no config) or
        names a config the policy does not define. Fail-closed: a typo raises
        rather than yielding an empty mapping (ADR-0005).
    """
    if name is None:
        raise ConfigError("no config name given (the integration declares no config)")
    try:
        table = policy.configs[name]
    except KeyError:
        raise ConfigError(f"config {name!r} is not defined in the policy") from None
    return deepcopy(table)


def _build_policy(data: dict[str, Any], *, source: str, strict: bool) -> Policy:
    try:
        policy = Policy.model_validate(data)
    except ValidationError as exc:
        problems = [_describe_error(dict(err)) for err in exc.errors()]
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
