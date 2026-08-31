"""Structural types limited to the Bleak adapter boundary."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, Protocol


class LogFn(Protocol):
    def __call__(self, message: str, /) -> None: ...


class DisconnectFn(Protocol):
    def __call__(self, client: object = None, /) -> None: ...


class BleClient(Protocol):
    @property
    def address(self) -> str: ...

    @property
    def is_connected(self) -> bool: ...

    @property
    def services(self) -> Any: ...

    async def connect(self) -> object: ...
    async def disconnect(self) -> object: ...

    async def write_gatt_char(
        self,
        char_specifier: object,
        data: bytes | bytearray,
        response: bool | None = ...,
    ) -> object: ...

    async def start_notify(self, char_specifier: object, callback: object) -> object: ...


class ClientOpener(Protocol):
    def __call__(
        self,
        address: str,
        timeout: float,
        on_disconnect: DisconnectFn | None = None,
    ) -> Awaitable[BleClient]: ...


class ClientCloser(Protocol):
    def __call__(self, client: BleClient | None) -> Awaitable[None]: ...
