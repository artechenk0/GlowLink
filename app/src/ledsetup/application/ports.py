"""The three external capabilities used by the application."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from ledsetup.application.models import (
    AppConfig,
    DeviceInfo,
    GattSnapshot,
    MonitorInfo,
    WriteResult,
)
from ledsetup.domain.value_objects.rgb import RGB


class BlePort(Protocol):
    @property
    def address(self) -> str | None: ...

    @property
    def is_connected(self) -> bool: ...

    @property
    def snapshot(self) -> GattSnapshot | None: ...

    async def scan(self, timeout: float) -> Sequence[DeviceInfo]: ...
    async def connect(self, address: str, timeout: float) -> GattSnapshot: ...
    async def disconnect(self) -> None: ...
    async def write(self, payload: bytes) -> WriteResult: ...
    async def gatt(self) -> GattSnapshot: ...


class ScreenPort(Protocol):
    def monitors(self) -> Sequence[MonitorInfo]: ...
    def average(self, monitor: MonitorInfo) -> RGB: ...


class ConfigRepository(Protocol):
    def load(self) -> AppConfig: ...
    def save(self, config: AppConfig) -> None: ...


LogFn = Callable[[str], None]
