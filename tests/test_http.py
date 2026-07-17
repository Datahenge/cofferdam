"""Tests for cofferdam.http — policy-checked HTTP helper (BR-HTTP-*, BR-HOST-*).

Covers: host_from_url structured parsing, policy enforcement before send,
credential injection, caller-header merging, redirect re-validation, and the
too-many-redirects guard.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from cofferdam.errors import CofferdamError, PolicyDeniedError
from cofferdam.http import host_from_url, request

# ---------------------------------------------------------------------------
# host_from_url (BR-HOST-001, BR-HOST-002, BR-HOST-003)
# ---------------------------------------------------------------------------


def test_host_from_url_standard() -> None:
    """BR-HOST-002: structured parser extracts clean hostname."""
    assert host_from_url("https://sandbox.windmill.dev/api/jobs") == "sandbox.windmill.dev"


def test_host_from_url_case_normalized() -> None:
    """BR-HOST-003: hostname is lowercased."""
    assert host_from_url("HTTPS://SANDBOX.WINDMILL.DEV/") == "sandbox.windmill.dev"


def test_host_from_url_strips_port() -> None:
    """BR-HOST-002: port is not included in the returned hostname."""
    assert host_from_url("https://sandbox.windmill.dev:8080/api") == "sandbox.windmill.dev"


def test_host_from_url_relative_raises() -> None:
    """BR-HOST-002: URL with no host raises CofferdamError (fail-closed)."""
    with pytest.raises(CofferdamError, match="could not parse"):
        host_from_url("/api/relative")


def test_host_from_url_empty_raises() -> None:
    """BR-HOST-002: empty string raises CofferdamError."""
    with pytest.raises(CofferdamError):
        host_from_url("")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(status_code: int = 200, location: str | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_redirect = status_code in (301, 302, 303, 307, 308)
    resp.headers = {"location": location} if location else {}
    return resp


# ---------------------------------------------------------------------------
# Policy enforcement before send (BR-HOST-004, BR-DECISION-*)
# ---------------------------------------------------------------------------


def test_request_denied_does_not_send(staging_policy: Any) -> None:
    """BR-HOST-004: policy denial raises PolicyDeniedError without sending the request."""
    with patch("httpx.request") as mock_req:
        with pytest.raises(PolicyDeniedError):
            request(
                policy=staging_policy,
                integration="windmill",
                operation="write",
                method="POST",
                url="https://production.windmill.dev/api/jobs",  # not in allowed_hosts
                credential="windmill_default",
            )
        mock_req.assert_not_called()


def test_request_unknown_integration_denied_before_send(staging_policy: Any) -> None:
    """BR-DECISION-001: unknown integration denies without sending."""
    with patch("httpx.request") as mock_req:
        with pytest.raises(PolicyDeniedError):
            request(
                policy=staging_policy,
                integration="nonexistent",
                operation="read",
                method="GET",
                url="https://sandbox.windmill.dev/api/status",
            )
        mock_req.assert_not_called()


# ---------------------------------------------------------------------------
# Credential injection (BR-SECRET-001, BR-HOST-004)
# ---------------------------------------------------------------------------


def test_request_credential_injected_as_bearer(staging_policy: Any, monkeypatch: Any) -> None:
    """BR-HOST-004: resolved credential is sent as Authorization: Bearer."""
    monkeypatch.setenv("WINDMILL_API_KEY", "test-secret-key")
    mock_resp = _mock_response(200)

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        response = request(
            policy=staging_policy,
            integration="windmill",
            operation="write",
            method="POST",
            url="https://sandbox.windmill.dev/api/jobs",
            credential="windmill_default",
            json={"task": "test"},
        )

    assert response is mock_resp
    _, kwargs = mock_req.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-secret-key"


def test_request_no_credential_no_auth_header(staging_policy: Any) -> None:
    """No credential supplied → no Authorization header injected."""
    mock_resp = _mock_response(200)

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        request(
            policy=staging_policy,
            integration="windmill",
            operation="read",
            method="GET",
            url="https://sandbox.windmill.dev/api/status",
        )

    _, kwargs = mock_req.call_args
    assert "Authorization" not in kwargs["headers"]


def test_request_caller_headers_preserved_authorization_wins(
    staging_policy: Any, monkeypatch: Any
) -> None:
    """Caller headers are merged; our Authorization: Bearer takes precedence (BR-HOST-004)."""
    monkeypatch.setenv("WINDMILL_API_KEY", "real-secret")
    mock_resp = _mock_response(200)

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        request(
            policy=staging_policy,
            integration="windmill",
            operation="read",
            method="GET",
            url="https://sandbox.windmill.dev/api/status",
            credential="windmill_default",
            headers={"X-Custom": "value", "Authorization": "Bearer stale"},
        )

    _, kwargs = mock_req.call_args
    assert kwargs["headers"]["X-Custom"] == "value"
    assert kwargs["headers"]["Authorization"] == "Bearer real-secret"


# ---------------------------------------------------------------------------
# Redirect default (BR-HTTP-003)
# ---------------------------------------------------------------------------


def test_request_no_redirects_by_default(staging_policy: Any) -> None:
    """BR-HTTP-003: follow_redirects defaults to False; passed to httpx."""
    mock_resp = _mock_response(200)

    with patch("httpx.request", return_value=mock_resp) as mock_req:
        request(
            policy=staging_policy,
            integration="windmill",
            operation="read",
            method="GET",
            url="https://sandbox.windmill.dev/api/status",
        )

    _, kwargs = mock_req.call_args
    assert kwargs["follow_redirects"] is False


# ---------------------------------------------------------------------------
# Redirect re-validation (BR-HTTP-003)
# ---------------------------------------------------------------------------


def test_redirect_302_to_allowed_host_followed(staging_policy: Any, monkeypatch: Any) -> None:
    """BR-HTTP-003: 302 redirect to an allowed host is followed with GET."""
    monkeypatch.setenv("WINDMILL_API_KEY", "secret")
    redirect_resp = _mock_response(302, location="https://sandbox.windmill.dev/api/v2/jobs")
    final_resp = _mock_response(200)

    with patch("httpx.request", side_effect=[redirect_resp, final_resp]) as mock_req:
        response = request(
            policy=staging_policy,
            integration="windmill",
            operation="write",
            method="POST",
            url="https://sandbox.windmill.dev/api/jobs",
            credential="windmill_default",
            follow_redirects=True,
        )

    assert response is final_resp
    assert mock_req.call_count == 2
    second = mock_req.call_args_list[1]
    assert second.args[0] == "GET"  # 302 switches to GET
    assert "json" not in second.kwargs  # body dropped on 302


def test_redirect_307_preserves_method_and_body(staging_policy: Any, monkeypatch: Any) -> None:
    """BR-HTTP-003: 307 redirect preserves method and request body."""
    monkeypatch.setenv("WINDMILL_API_KEY", "secret")
    redirect_resp = _mock_response(307, location="https://sandbox.windmill.dev/api/v2/jobs")
    final_resp = _mock_response(200)

    with patch("httpx.request", side_effect=[redirect_resp, final_resp]) as mock_req:
        request(
            policy=staging_policy,
            integration="windmill",
            operation="write",
            method="POST",
            url="https://sandbox.windmill.dev/api/jobs",
            credential="windmill_default",
            follow_redirects=True,
            json={"task": "test"},
        )

    second = mock_req.call_args_list[1]
    assert second.args[0] == "POST"  # method preserved
    assert second.kwargs.get("json") == {"task": "test"}  # body preserved


def test_redirect_to_denied_host_raises(staging_policy: Any, monkeypatch: Any) -> None:
    """BR-HTTP-003: redirect to a non-allowed host raises PolicyDeniedError."""
    monkeypatch.setenv("WINDMILL_API_KEY", "secret")
    redirect_resp = _mock_response(302, location="https://production.windmill.dev/api/jobs")

    with patch("httpx.request", return_value=redirect_resp):
        with pytest.raises(PolicyDeniedError):
            request(
                policy=staging_policy,
                integration="windmill",
                operation="write",
                method="POST",
                url="https://sandbox.windmill.dev/api/jobs",
                credential="windmill_default",
                follow_redirects=True,
            )


def test_too_many_redirects_raises(staging_policy: Any) -> None:
    """BR-HTTP-003: exceeding _MAX_REDIRECTS raises CofferdamError."""
    loop_resp = _mock_response(302, location="https://sandbox.windmill.dev/api/loop")

    with patch("httpx.request", return_value=loop_resp):
        with pytest.raises(CofferdamError, match="exceeded"):
            request(
                policy=staging_policy,
                integration="windmill",
                operation="read",
                method="GET",
                url="https://sandbox.windmill.dev/api/start",
                follow_redirects=True,
            )
