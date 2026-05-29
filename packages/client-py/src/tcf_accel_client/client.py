"""Minimal Phase 2 client.

A thin `httpx` wrapper that handles auth, base URL, and error-envelope
decoding. The fully-typed surface arrives once Phase 3 implementations
land and the generator runs against a stable spec.
"""

from __future__ import annotations

from typing import Any

import httpx

from tcf_accel.errors import TCFAccelError


class Client:
    """Phase 2 minimal HTTP client.

    Example:
        >>> c = Client('http://localhost:8000')
        >>> # c.get('/healthz')  # would hit the live API
    """

    def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 10.0) -> None:
        """Build a client.

        Args:
            base_url: e.g. ``http://localhost:8000``.
            token: Optional bearer token (`Authorization: Bearer …`).
            timeout: Per-request timeout in seconds.
        """
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def get(self, path: str, **params: Any) -> Any:  # noqa: ANN401
        """Issue a GET; raise on non-2xx with envelope decoding."""
        return self._request("GET", path, params=params)

    def post(self, path: str, *, json: Any = None) -> Any:  # noqa: ANN401
        """Issue a POST; raise on non-2xx with envelope decoding."""
        return self._request("POST", path, json=json)

    def close(self) -> None:
        """Close the underlying httpx session."""
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kw: Any) -> Any:  # noqa: ANN401
        response = self._http.request(method, path, **kw)
        if response.is_success:
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return response.content
        # Try to decode the envelope; fall back to a generic error.
        try:
            detail = response.json().get("detail", {})
            code = detail.get("code", "E_BASE_000")
            msg = detail.get("message") or response.text
        except ValueError:
            code = "E_BASE_000"
            msg = response.text
        err = TCFAccelError()
        err.context = {"code": code, "http_status": response.status_code, "response_message": msg}
        raise err


__all__ = ["Client"]
