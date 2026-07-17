"""Policy-checked HTTP helper (BR-HTTP-*).

This module wraps ``httpx`` and is only importable when the optional dependency
is installed (``pip install "cofferdam[http]"``, ADR-0008). It guarantees that a
credential-bearing request is evaluated by the policy engine — including a
structured hostname check — *before* any bytes or authorization headers are sent
(BR-HOST-002).

    STATUS: scaffolding. The signature and guarantees below are frozen by the
    requirements; the body is implemented in the HTTP milestone (docs/09,
    implementation sequence step 7).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from cofferdam.decisions import decide
from cofferdam.errors import CofferdamError

if TYPE_CHECKING:
    import httpx

    from cofferdam.models import Policy


def _require_httpx() -> Any:
    try:
        import httpx
    except ModuleNotFoundError as exc:  # pragma: no cover - trivial guard
        raise CofferdamError(
            "cofferdam.http requires the optional 'http' extra: "
            'pip install "cofferdam[http]"'
        ) from exc
    return httpx


def host_from_url(url: str) -> str:
    """Extract the lowercase hostname from ``url`` using a structured parser.

    Uses :func:`urllib.parse.urlsplit` so that policy evaluation compares the
    real hostname, never a substring of the raw URL (BR-HOST-001).
    """
    host = urlsplit(url).hostname
    if not host:
        raise CofferdamError(f"could not parse a hostname from URL: {url!r}")
    return host.lower()


def request(
    *,
    policy: Policy,
    integration: str,
    operation: str,
    method: str,
    url: str,
    credential: str | None = None,
    follow_redirects: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    """Issue a policy-checked HTTP request.

    The request is evaluated with :func:`cofferdam.decisions.decide` — including
    the hostname parsed from ``url`` — and is only sent if allowed. Redirects are
    **not** followed by default (BR-HTTP-003); when enabled, each redirect target
    must be re-validated before credential-bearing headers are re-sent.
    """
    _require_httpx()  # fail early if the optional 'http' extra is not installed

    host = host_from_url(url)
    decision = decide(
        policy,
        integration=integration,
        kind=None,
        operation=operation,
        method=method,
        host=host,
        credential=credential,
    )
    if not decision.allowed:
        raise decision.to_exception()

    # NOTE: credential injection (attaching resolved secrets as headers) and
    # redirect re-validation are implemented in the HTTP milestone. Until then
    # this helper enforces the guard and performs the plain request.
    raise NotImplementedError(
        "cofferdam.http.request body is implemented in the HTTP milestone; "
        "the policy guard above is active."
    )
