"""Shared bounded HTTP transport for provider connectors: one origin, no redirects, capped reads."""

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock
from time import monotonic

import httpx

MAX_RESPONSE_BYTES = 1_000_000


class BoundedClient:
    """Serialized reads with an explicit budget; provider bodies never reach error messages."""

    error: type[Exception]

    def __init__(
        self, origin: str, label: str, timeout_seconds: float, transport: httpx.BaseTransport | None
    ):
        self._label = label
        self._timeout = timeout_seconds
        self._lock = Lock()
        self._client = httpx.Client(
            base_url=origin,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "ECON-Hub/0.2"},
        )

    def close(self) -> None:
        self._client.close()

    @contextmanager
    def _exclusive(self, budget: float, error: type[Exception] | None = None) -> Iterator[float]:
        """One budget covers both the lock wait and the serialized provider operation."""
        deadline = monotonic() + budget
        if not self._lock.acquire(timeout=budget):
            raise (error or self.error)(
                f"Ya hay una operación de {self._label} en curso; intente más tarde."
            )
        try:
            yield deadline
        finally:
            self._lock.release()

    def _bounded(
        self, method: str, path: str, deadline: float, error: type[Exception] | None = None, **kw
    ) -> tuple[int, bytes]:
        error = error or self.error
        timeout = error("La lectura superó el tiempo permitido.")
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise timeout
        try:
            with self._client.stream(
                method, path, timeout=min(remaining, self._timeout), **kw
            ) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    if monotonic() > deadline:
                        raise timeout
                    if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                        raise error("La respuesta excedió el tamaño de lectura permitido.")
                    body.extend(chunk)
                if monotonic() > deadline:
                    raise timeout
                return response.status_code, bytes(body)
        except httpx.HTTPError:
            raise error(
                f"No fue posible consultar {self._label} dentro del tiempo permitido."
            ) from None
