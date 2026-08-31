"""Single application facade shared by CLI, menu and desktop UI."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence

from ledsetup.application.errors import CaptureError, DeviceNotSelectedError
from ledsetup.application.models import (
    AppConfig,
    DeviceInfo,
    GattSnapshot,
    MonitorInfo,
    WriteResult,
)
from ledsetup.application.ports import BlePort, ScreenPort
from ledsetup.application.services.config_service import ConfigService
from ledsetup.application.services.screen_sync import run_screen_sync
from ledsetup.application.services.throttle import ColorThrottle
from ledsetup.domain.services.frame_builder import build_off_frame, build_rgb_frame
from ledsetup.domain.value_objects.ble_address import ble_addresses_equal
from ledsetup.domain.value_objects.rgb import RGB, validate_rgb


class GlowLinkApplication:
    def __init__(self, ble: BlePort, screen: ScreenPort, config: ConfigService) -> None:
        self._ble = ble
        self._screen = screen
        self._config = config
        self._io_lock = asyncio.Lock()

    @property
    def config(self) -> AppConfig:
        return self._config.config

    @property
    def is_connected(self) -> bool:
        return self._ble.is_connected

    @property
    def address(self) -> str | None:
        return self._ble.address

    async def scan(self, timeout: float | None = None) -> list[DeviceInfo]:
        async with self._io_lock:
            await self._ble.disconnect()
            found = await self._ble.scan(timeout or self.config.scan_timeout)
        return list(found)

    async def select_device(self, device: DeviceInfo) -> DeviceInfo:
        current = self.config.selected_device
        changed = current is None or not ble_addresses_equal(current.address, device.address)
        if changed:
            async with self._io_lock:
                await self._ble.disconnect()
        self._config.select_device(device)
        return device

    async def forget_device(self) -> None:
        async with self._io_lock:
            await self._ble.disconnect()
        self._config.forget_device()

    async def connect(self, address: str | None = None) -> GattSnapshot:
        target = self._target_address(address)
        async with self._io_lock:
            return await self._connect_locked(target)

    async def disconnect(self) -> None:
        async with self._io_lock:
            await self._ble.disconnect()

    async def set_color(self, rgb: RGB, address: str | None = None) -> WriteResult:
        validate_rgb(rgb)
        result = await self._write(build_rgb_frame(*rgb), address)
        self._config.set_color(rgb)
        return result

    async def power_off(self, address: str | None = None) -> WriteResult:
        return await self._write(build_off_frame(), address)

    async def inspect_gatt(self, address: str | None = None) -> GattSnapshot:
        target = self._target_address(address)
        async with self._io_lock:
            await self._connect_locked(target)
            return await self._ble.gatt()

    def list_monitors(self) -> list[MonitorInfo]:
        return list(self._screen.monitors())

    def resolve_monitor(
        self, monitors: Sequence[MonitorInfo], *, flag: str | None = None
    ) -> tuple[MonitorInfo, str]:
        if not monitors:
            raise CaptureError("не видно ни одного монитора")
        primary = next((item for item in monitors if item.is_primary), monitors[0])
        if flag is not None and flag.strip():
            text = flag.strip()
            if text.isdigit():
                index = int(text)
                if not 1 <= index <= len(monitors):
                    raise CaptureError(f"нет монитора {index}. В списке {len(monitors)}.")
                return monitors[index - 1], ""
            found = next((item for item in monitors if item.id == text), None)
            if found is None:
                raise CaptureError(f"монитор {text} не найден")
            return found, ""
        if self.config.monitor_id:
            found = next((item for item in monitors if item.id == self.config.monitor_id), None)
            if found is not None:
                return found, ""
            return primary, "сохранённый монитор больше не в системе — беру основной Windows."
        return primary, ""

    def select_monitor(self, monitor_id: str) -> AppConfig:
        return self._config.select_monitor(monitor_id)

    def update_settings(
        self, *, scan_timeout: object, connect_timeout: object, verbose: bool
    ) -> AppConfig:
        return self._config.update_settings(
            scan_timeout=scan_timeout,
            connect_timeout=connect_timeout,
            verbose=verbose,
        )

    async def run_screen_sync(
        self,
        *,
        should_stop: Callable[[], bool],
        address: str | None = None,
        monitor_flag: str | None = None,
        deadline: float | None = None,
        on_color: Callable[[RGB], None] | None = None,
        throttle: ColorThrottle | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> RGB | None:
        monitors = self.list_monitors()
        monitor, _note = self.resolve_monitor(monitors, flag=monitor_flag)
        await self.connect(address)

        async def send(rgb: RGB) -> None:
            await self._write(build_rgb_frame(*rgb), address)
            self._config.set_color(rgb)

        return await run_screen_sync(
            sample=lambda: self._screen.average(monitor),
            send=send,
            should_stop=should_stop,
            throttle=throttle or ColorThrottle(clock=clock),
            interval=self.config.sync_interval,
            deadline=deadline,
            clock=clock,
            sleep=sleep,
            on_color=on_color,
        )

    async def close(self) -> None:
        try:
            await self.disconnect()
        finally:
            self._config.flush()

    async def _write(self, payload: bytes, address: str | None = None) -> WriteResult:
        target = self._target_address(address)
        async with self._io_lock:
            await self._connect_locked(target)
            return await self._ble.write(payload)

    async def _connect_locked(self, address: str) -> GattSnapshot:
        if self._ble.is_connected and self._ble.address is not None:
            if ble_addresses_equal(self._ble.address, address):
                snapshot = self._ble.snapshot
                return snapshot if snapshot is not None else await self._ble.gatt()
            await self._ble.disconnect()
        return await self._ble.connect(address, self.config.connect_timeout)

    def _target_address(self, address: str | None) -> str:
        if address is not None:
            return address
        selected = self.config.selected_device
        if selected is None:
            raise DeviceNotSelectedError()
        return selected.address
