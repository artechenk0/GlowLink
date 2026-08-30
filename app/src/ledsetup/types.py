"""Shared aliases and Protocols. Keep BLE client structural so tests can fake it."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from ledsetup.ble import DeviceHit

type RGB = tuple[int, int, int]


class LogFn(Protocol):
    def __call__(self, message: str, /) -> None: ...


class InputFn(Protocol):
    def __call__(self, prompt: str, /) -> str: ...


class PrintFn(Protocol):
    def __call__(self, message: str = "", /) -> None: ...


class DisconnectFn(Protocol):
    def __call__(self, client: object = None, /) -> None: ...


class ScanFn(Protocol):
    def __call__(self, timeout: float = ...) -> Awaitable[list[DeviceHit]]: ...


class BleClient(Protocol):
    """Subset of BleakClient used by this app (and by FakeClient in tests).

    Bleak's stubs are stricter/read-only in places this Protocol is not;
    wrap real BleakClient with a cast at the adapter boundary.
    """

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
