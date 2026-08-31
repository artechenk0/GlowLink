"""Synchronous pywebview API backed by one application and asyncio loop."""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any, Literal, TypeVar

from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.errors import LedSetupError
from ledsetup.application.models import DeviceInfo, GattSnapshot, MonitorInfo
from ledsetup.application.services.throttle import ColorThrottle
from ledsetup.domain.services.color_values import coerce_rgb_byte
from ledsetup.domain.value_objects.ble_address import ble_addresses_equal, normalize_ble_address
from ledsetup.domain.value_objects.rgb import RGB
from ledsetup.presentation.cli.gatt_text import format_gatt_lines
from ledsetup.presentation.desktop.async_bridge import AsyncBridge

T = TypeVar("T")
MsgKind = Literal["info", "ok", "err", "busy"]
Ack = dict[str, bool]
UiState = dict[str, object]
UiMessage = dict[str, object]


class JsApi:
    def __init__(self, app: GlowLinkApplication, bridge: AsyncBridge) -> None:
        self._app = app
        self._bridge = bridge
        self._ui: Any | None = None
        self._hits: list[DeviceInfo] = []
        self._color_lock = threading.Lock()
        self._pending_color: RGB | None = None
        self._color_future: Future[None] | None = None
        self._throttle = ColorThrottle()
        self._sync_lock = threading.Lock()
        self._sync_stop: threading.Event | None = None
        self._sync_future: Future[None] | None = None
        self._sync_rgb: RGB | None = None

    def _submit(self, coro: Coroutine[Any, Any, T], done: Any | None = None) -> Future[T]:
        future = self._bridge.submit(coro)
        if done is not None:
            future.add_done_callback(done)
        return future

    def _emit(self, name: str, payload: object) -> None:
        if self._ui is None:
            return
        blob = json.dumps(payload, ensure_ascii=False)
        try:
            self._ui.evaluate_js(f"window.__led && window.__led.{name}({blob})")
        except Exception:
            return

    def _state(self) -> UiState:
        device = self._app.config.selected_device
        return {
            "device": None if device is None else {"address": device.address, "name": device.name},
            "connected": self._app.is_connected,
        }

    def _msg(self, text: str, kind: MsgKind = "info") -> UiMessage:
        return {"text": text, "kind": kind, "state": self._state()}

    def _error(self, future: Future[Any]) -> str | None:
        try:
            future.result()
        except LedSetupError as exc:
            return str(exc)
        except Exception as exc:
            return str(exc)
        return None

    def get_state(self) -> dict[str, object]:
        state = self._state()
        return {
            **state,
            "auto_connect": state["device"] is not None,
            "color": list(self._app.config.last_color),
        }

    def get_settings(self) -> dict[str, object]:
        config = self._app.config
        return {
            "scan_timeout": config.scan_timeout,
            "connect_timeout": config.connect_timeout,
            "verbose": config.verbose_gatt_after_write,
        }

    def scan(self) -> Ack:
        async def work() -> list[DeviceInfo]:
            return await self._app.scan()

        def done(future: Future[list[DeviceInfo]]) -> None:
            error = self._error(future)
            if error is not None:
                self._emit("onScan", self._scan_event(error, "err", []))
                return
            self._hits = list(future.result())
            text = (
                "Нажмите карточку — запомним адрес и перейдём к цвету."
                if self._hits
                else "Поблизости никого нет. Bluetooth включён?"
            )
            self._emit("onScan", self._scan_event(text, "ok" if self._hits else "err", self._hits))

        self._submit(work(), done)
        return {"ok": True}

    def _scan_event(self, text: str, kind: MsgKind, devices: list[DeviceInfo]) -> dict[str, object]:
        return {
            "text": text,
            "kind": kind,
            "state": self._state(),
            "device": self._state()["device"],
            "hits": [
                {
                    "name": device.name,
                    "address": device.address,
                    "rssi": device.rssi,
                }
                for device in devices
            ],
        }

    def select_device(self, address: str) -> Ack:
        wanted = normalize_ble_address(address)
        device = next(
            (item for item in self._hits if ble_addresses_equal(item.address, wanted)),
            DeviceInfo(address=wanted),
        )

        async def work() -> None:
            self._stop_sync()
            await self._app.select_device(device)
            await self._app.connect()

        def done(future: Future[None]) -> None:
            error = self._error(future)
            self._emit(
                "onSelected",
                self._msg(error or "Подключено. Можно выбирать цвет.", "err" if error else "ok"),
            )

        self._submit(work(), done)
        return {"ok": True}

    def connect(self) -> Ack:
        def done(future: Future[GattSnapshot]) -> None:
            error = self._error(future)
            self._emit(
                "onMsg",
                self._msg(error or "Подключено. Можно выбирать цвет.", "err" if error else "ok"),
            )

        self._submit(self._app.connect(), done)
        return {"ok": True}

    def toggle_connection(self) -> Ack:
        if self._app.is_connected:
            self._stop_sync()

            def done(future: Future[None]) -> None:
                error = self._error(future)
                self._emit("onMsg", self._msg(error or "Отключено.", "err" if error else "info"))

            self._submit(self._app.disconnect(), done)
        else:
            self.connect()
        return {"ok": True}

    def set_color(self, red: object, green: object, blue: object) -> Ack:
        with self._sync_lock:
            if self._sync_future is not None and not self._sync_future.done():
                return {"ok": True}
        color = (coerce_rgb_byte(red), coerce_rgb_byte(green), coerce_rgb_byte(blue))
        with self._color_lock:
            self._pending_color = color
            if self._color_future is None:
                self._color_future = self._submit(self._drain_colors())
        return {"ok": True}

    async def _drain_colors(self) -> None:
        while True:
            await asyncio.sleep(max(0.01, self._throttle.delay()))
            with self._color_lock:
                color = self._pending_color
                self._pending_color = None
                if color is None:
                    self._color_future = None
                    return
            try:
                await self._app.set_color(color)
                self._throttle.mark(color)
            except LedSetupError as exc:
                self._emit("onMsg", self._msg(str(exc), "err"))
                with self._color_lock:
                    self._color_future = None
                return

    def power_off(self) -> Ack:
        self._throttle.clear_last()

        def done(future: Future[Any]) -> None:
            error = self._error(future)
            self._emit(
                "onMsg",
                self._msg(error or "RGB-подсветка выключена", "err" if error else "ok"),
            )

        self._submit(self._app.power_off(), done)
        return {"ok": True}

    def gatt(self) -> Ack:
        def done(future: Future[GattSnapshot]) -> None:
            error = self._error(future)
            text = error or "\n".join(format_gatt_lines(future.result()))
            self._emit("onGatt", self._msg(text, "err" if error else "ok"))

        self._submit(self._app.inspect_gatt(), done)
        return {"ok": True}

    def save_settings(self, scan: str, connect: str, verbose: bool) -> UiMessage:
        try:
            self._app.update_settings(
                scan_timeout=float(str(scan).replace(",", ".")),
                connect_timeout=float(str(connect).replace(",", ".")),
                verbose=bool(verbose),
            )
        except ValueError as exc:
            return self._msg(str(exc), "err")
        return self._msg("Настройки сохранены.", "ok")

    def forget_device(self) -> Ack:
        self._stop_sync()

        def done(future: Future[None]) -> None:
            error = self._error(future)
            self._emit(
                "onForgot",
                self._msg(
                    error or "Устройство забыто. Найдите его заново.",
                    "err" if error else "info",
                ),
            )

        self._submit(self._app.forget_device(), done)
        return {"ok": True}

    def list_monitors(self) -> dict[str, object]:
        try:
            monitors = self._app.list_monitors()
            selected, note = self._app.resolve_monitor(monitors)
            if note:
                self._app.select_monitor(selected.id)
        except LedSetupError as exc:
            return {"monitors": [], "selected_id": "", "note": str(exc)}
        return {
            "monitors": [self._monitor_dict(monitor) for monitor in monitors],
            "selected_id": selected.id,
            "note": note,
        }

    @staticmethod
    def _monitor_dict(monitor: MonitorInfo) -> dict[str, object]:
        return {
            "id": monitor.id,
            "index": monitor.index,
            "label": monitor.label,
            "primary": monitor.is_primary,
        }

    def select_monitor(self, monitor_id: object) -> UiMessage:
        try:
            self._app.select_monitor(str(monitor_id))
        except ValueError as exc:
            return self._msg(str(exc), "err")
        return self._msg("Монитор сохранён.", "ok")

    def start_sync(self) -> Ack:
        with self._sync_lock:
            if self._sync_future is not None and not self._sync_future.done():
                return {"ok": True}
            stop = threading.Event()
            future = self._submit(self._sync_worker(stop))
            self._sync_stop = stop
            self._sync_future = future
            future.add_done_callback(lambda done: self._sync_done(done, stop))
        return {"ok": True}

    def stop_sync(self) -> Ack:
        self._stop_sync()
        return {"ok": True}

    def _stop_sync(self) -> None:
        with self._sync_lock:
            if self._sync_stop is not None:
                self._sync_stop.set()

    async def _sync_worker(self, stop: threading.Event) -> None:
        self._emit("onSync", self._sync_event("Идёт захват", "busy", running=True))

        def on_color(rgb: RGB) -> None:
            self._sync_rgb = rgb
            self._emit("onSync", self._sync_event("Идёт захват", "busy", running=True))

        await self._app.run_screen_sync(should_stop=stop.is_set, on_color=on_color)

    def _sync_done(self, future: Future[None], stop: threading.Event) -> None:
        error = self._error(future)
        with self._sync_lock:
            if self._sync_stop is stop:
                self._sync_stop = None
                self._sync_future = None
        self._emit(
            "onSync",
            self._sync_event(
                error or "Захват остановлен. На RGB-подсветке остался последний цвет.",
                "err" if error else "info",
                running=False,
            ),
        )

    def _sync_event(self, text: str, kind: MsgKind, *, running: bool) -> dict[str, object]:
        red, green, blue = self._sync_rgb or (0, 0, 0)
        return {
            "text": text,
            "kind": kind,
            "state": self._state(),
            "running": running,
            "r": red,
            "g": green,
            "b": blue,
        }

    def close(self) -> None:
        self._stop_sync()
        with self._color_lock:
            self._pending_color = None
            color_future = self._color_future
        if color_future is not None:
            color_future.cancel()
        self._bridge.wait(self._app.close(), timeout=5.0)
