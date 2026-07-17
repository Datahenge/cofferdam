"""cofferdam — block outbound side effects from non-production environments.

A plain Python library that makes a local TOML policy file — not the restored
database — the authority over which outbound side effects (vendor API calls,
email, payments, webhooks, report delivery, file transfer) are permitted in the
current environment.

Design rule: *Restored data owns business intent. Local environment config owns
execution authority.* The engine fails closed. See ``docs/`` for the full
requirements specification and ``docs/adr/`` for architecture decisions.

Frappe/ERPNext integration is handled by the companion app ``cofferdam-app``
(ADR-0012). This package has no Frappe dependency at any layer.
"""

from __future__ import annotations

from cofferdam.config import load_policy, loads_policy
from cofferdam.decisions import Decision
from cofferdam.errors import (
    CofferdamError,
    CredentialError,
    PolicyDeniedError,
    PolicyFileNotFoundError,
    PolicyValidationError,
    SecretResolutionError,
)
from cofferdam.models import Environment, Policy, SideEffectKind

__all__ = [
    "CofferdamError",
    "CredentialError",
    "Decision",
    "Environment",
    "Policy",
    "PolicyDeniedError",
    "PolicyFileNotFoundError",
    "PolicyValidationError",
    "SecretResolutionError",
    "SideEffectKind",
    "load_policy",
    "loads_policy",
]

__version__ = "0.1.0"
