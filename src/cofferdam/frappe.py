"""Frappe/ERPNext integration helpers (BR-FRAPPE-*).

This is the ONLY module that is Frappe-aware, and even here Frappe is a soft,
runtime-optional dependency: ``import frappe`` is attempted lazily and inside a
guard. The rest of ``cofferdam`` never imports Frappe (ADR-0002, ADR-0010), so
the library installs, imports, and tests as an ordinary Python package with no
Bench present.

Responsibilities (docs/11-frappe-integration.md):
  - locate ``sites/{site_name}/environment_policy.toml``
  - honor an optional ``outbound_policy_path`` override in ``site_config.json``
  - expose ``get_policy()`` with process-lifetime caching and ``reload_policy()``
  - use Frappe logging when available, plain ``logging`` otherwise

    STATUS: scaffolding. Signatures are frozen by the requirements; bodies are
    implemented in the Frappe milestone (implementation sequence step 9).
"""

from __future__ import annotations

from pathlib import Path

from cofferdam.models import Policy

DEFAULT_POLICY_FILENAME = "environment_policy.toml"
SITE_CONFIG_OVERRIDE_KEY = "outbound_policy_path"


def resolve_policy_path(site: str | None = None) -> Path:
    """Return the on-disk path to the active site's policy file (BR-FRAPPE-001).

    Locates the current Frappe site (or ``site`` if given), then returns
    ``sites/{site}/environment_policy.toml`` unless ``site_config.json`` sets
    ``outbound_policy_path``. Never returns a path under ``/files/private``
    (BR-CONFIG-002).
    """
    raise NotImplementedError(
        "cofferdam.frappe.resolve_policy_path is implemented in the Frappe milestone."
    )


def get_policy(site: str | None = None, *, strict: bool = False) -> Policy:
    """Load (and cache for the process lifetime) the active site's policy.

    Suitable for calling from ERPNext server-side code without a custom Frappe
    app. Raises clear cofferdam exceptions on failure (fail-closed).
    """
    raise NotImplementedError(
        "cofferdam.frappe.get_policy is implemented in the Frappe milestone."
    )


def reload_policy(site: str | None = None) -> Policy:
    """Discard any cached policy and reload from disk (BR-FRAPPE-004)."""
    raise NotImplementedError(
        "cofferdam.frappe.reload_policy is implemented in the Frappe milestone."
    )
