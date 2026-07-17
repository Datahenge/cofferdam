"""Policy-checked HTTP helper (BR-HTTP-*).

This module wraps ``httpx`` and is only available when the optional dependency is
installed (``pip install "cofferdam[http]"``, ADR-0008). The host parsed from the
request URL is evaluated by the policy engine before any bytes or authorization
headers are sent (BR-HOST-002, BR-HOST-004).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlsplit

from cofferdam.decisions import decide
from cofferdam.errors import CofferdamError

if TYPE_CHECKING:
    import httpx

    from cofferdam.models import Policy

_MAX_REDIRECTS = 10


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

    Uses :func:`urllib.parse.urlsplit` so policy evaluation compares the real
    hostname, never a substring of the raw URL (BR-HOST-001, BR-HOST-002).
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

    Evaluates the policy — including the hostname from ``url`` — before any bytes
    leave (BR-HOST-002, BR-HOST-004). When ``credential`` is supplied its resolved
    secret is injected as ``Authorization: Bearer``. Redirects are not followed by
    default (BR-HTTP-003); when enabled every redirect target is re-validated
    before credentials are forwarded.
    """
    httpx_mod = _require_httpx()

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

    # Resolve and inject credential as Authorization: Bearer (BR-SECRET-001, BR-HOST-004)
    headers: dict[str, str] = {}
    if credential is not None:
        from cofferdam.credentials import resolve_secret

        headers["Authorization"] = f"Bearer {resolve_secret(policy, credential)}"

    # Merge caller-supplied headers; our Authorization takes precedence
    if "headers" in kwargs:
        merged: dict[str, str] = dict(kwargs.pop("headers"))
        merged.update(headers)
        headers = merged

    if not follow_redirects:
        return cast(
            "httpx.Response",
            httpx_mod.request(method, url, headers=headers, follow_redirects=False, **kwargs),
        )

    # Manual redirect loop: re-validate every hop before forwarding credentials (BR-HTTP-003)
    body_keys = {"json", "data", "content", "files"}
    body_kw: dict[str, Any] = {k: v for k, v in kwargs.items() if k in body_keys}
    other_kw: dict[str, Any] = {k: v for k, v in kwargs.items() if k not in body_keys}
    current_url = url
    current_method = method

    for _ in range(_MAX_REDIRECTS + 1):
        response = httpx_mod.request(
            current_method,
            current_url,
            headers=headers,
            follow_redirects=False,
            **body_kw,
            **other_kw,
        )
        if not response.is_redirect:
            return cast("httpx.Response", response)

        redirect_url: str = cast(str, response.headers.get("location", ""))
        redirect_host = host_from_url(redirect_url)
        rd = decide(
            policy,
            integration=integration,
            kind=None,
            operation=operation,
            method=current_method,
            host=redirect_host,
            credential=credential,
        )
        if not rd.allowed:
            raise rd.to_exception()

        current_url = redirect_url
        if response.status_code in (301, 302, 303):
            current_method = "GET"
            body_kw = {}

    raise CofferdamError(f"exceeded {_MAX_REDIRECTS} redirects")
