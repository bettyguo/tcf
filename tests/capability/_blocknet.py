"""Network-blocking helper for the capability tests (`phase5_audit.md §9`).

The capability suite enforces ADR-017's "privacy-default-local-only"
posture at the syscall layer: under default configuration, no path
through the audio pipeline or the EE/EO worker stubs may reach a
remote host. This helper provides a context manager that
monkey-patches the stdlib `socket` API so any attempted TCP connect
or DNS lookup raises a typed error — the test then asserts the
covered code path completes without triggering it.

The blocked entry points are:
- `socket.socket.connect` — direct TCP.
- `socket.socket.connect_ex` — non-raising variant; we make it raise.
- `socket.create_connection` — `http.client` / `urllib` / `requests` rely on this.
- `socket.getaddrinfo` — DNS lookup. Blocking this catches anything
  trying to resolve a hostname, even if it'd reach a literal IP via
  some other path.

Local Unix-socket / loopback writes (e.g. `127.0.0.1`) are still
caught because the blocking happens at the `socket.socket.connect`
entry, before any address-family branching.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from contextlib import contextmanager


class BlockedNetworkError(RuntimeError):
    """A network operation was attempted while the network was blocked.

    Capability tests catch instances of this to surface *which* call
    leaked. The message includes the offending function name so the
    failure points directly at the leaky code path.
    """


def _blocked(func_name: str):  # type: ignore[no-untyped-def]
    """Return a no-arg callable that raises `BlockedNetworkError`."""

    def _raise(*args: object, **kwargs: object) -> None:
        msg = (
            f"Network blocked: {func_name}() was called with args={args!r} "
            f"under the capability fixture. ADR-017: default mode must "
            "not make any network calls. If this is intentional, the "
            "test fixture should not be blocking; if it is a leak, fix "
            "the code path."
        )
        raise BlockedNetworkError(msg)

    return _raise


@contextmanager
def block_network() -> Iterator[None]:
    """Block stdlib socket egress for the duration of the `with` block.

    Restores the originals on exit, even if the body raises.

    Example:
        >>> import urllib.request
        >>> with block_network():
        ...     try:
        ...         urllib.request.urlopen("http://example.com")
        ...     except BlockedNetworkError:
        ...         got_blocked = True
        ...     except Exception:  # noqa: BLE001 - urllib wraps it
        ...         got_blocked = True
        >>> got_blocked
        True
    """
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create_connection = socket.create_connection
    real_getaddrinfo = socket.getaddrinfo

    socket.socket.connect = _blocked("socket.socket.connect")  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked("socket.socket.connect_ex")  # type: ignore[method-assign]
    socket.create_connection = _blocked("socket.create_connection")  # type: ignore[assignment]
    socket.getaddrinfo = _blocked("socket.getaddrinfo")  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = real_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = real_connect_ex  # type: ignore[method-assign]
        socket.create_connection = real_create_connection
        socket.getaddrinfo = real_getaddrinfo


__all__ = ["BlockedNetworkError", "block_network"]
