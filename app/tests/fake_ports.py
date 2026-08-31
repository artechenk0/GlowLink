from __future__ import annotations

import asyncio

from ledsetup.application.models import (
    AppConfig,
    CharInfo,
    DeviceInfo,
    GattSnapshot,
    MonitorInfo,
    WriteResult,
)
from ledsetup.domain.value_objects.rgb import RGB

ADDRESS = "AA:BB:CC:DD:EE:FF"


class FakeConfigRepository:
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self.saved: list[AppConfig] = []

    def load(self) -> AppConfig:
        return self.config

    def save(self, config: AppConfig) -> None:
        self.config = config
        self.saved.append(config)


class FakeBlePort:
    def __init__(self, devices: list[DeviceInfo] | None = None) -> None:
        self.devices = (
            [DeviceInfo(ADDRESS, "Kitchen controller", -40)] if devices is None else devices
        )
        self._address: str | None = None
        self._connected = False
        self._snapshot: GattSnapshot | None = None
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.scan_calls = 0
        self.writes: list[bytes] = []
        self.active_writes = 0
        self.max_active_writes = 0

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def snapshot(self) -> GattSnapshot | None:
        return self._snapshot

    async def scan(self, timeout: float) -> list[DeviceInfo]:
        self.scan_calls += 1
        return list(self.devices)

    async def connect(self, address: str, timeout: float) -> GattSnapshot:
        self.connect_calls += 1
        self._address = address
        self._connected = True
        self._snapshot = GattSnapshot(
            address,
            services=[("ffff", [CharInfo("ff01", ("write",))])],
            service_matched=True,
            write_matched=True,
        )
        return self._snapshot

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._address = None
        self._connected = False
        self._snapshot = None

    async def write(self, payload: bytes) -> WriteResult:
        self.active_writes += 1
        self.max_active_writes = max(self.max_active_writes, self.active_writes)
        await asyncio.sleep(0)
        self.writes.append(payload)
        self.active_writes -= 1
        assert self._snapshot is not None
        return WriteResult(
            address=self._address or "",
            write_uuid="ff01",
            write_method="write-without-response",
            write_matched=True,
            notify_enabled=True,
            payload_hex=" ".join(f"{byte:02X}" for byte in payload),
            snapshot=self._snapshot,
        )

    async def gatt(self) -> GattSnapshot:
        assert self._snapshot is not None
        return self._snapshot


class FakeScreenPort:
    def __init__(self, rgb: RGB = (10, 20, 30)) -> None:
        self.rgb = rgb
        self.calls = 0
        self.monitor = MonitorInfo(
            id="0,0,1920x1080",
            index=1,
            left=0,
            top=0,
            width=1920,
            height=1080,
            is_primary=True,
            label="Монитор 1 · 1920×1080 (основной)",
        )

    def monitors(self) -> list[MonitorInfo]:
        return [self.monitor]

    def average(self, monitor: MonitorInfo) -> RGB:
        self.calls += 1
        return self.rgb
