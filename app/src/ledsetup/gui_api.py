"""pywebview JS bridge. Public methods are the JS API; keep other attrs private."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Coroutine
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, TypedDict, TypeVar

from ledsetup.ble import BluetoothUnavailableError, DeviceHit, GattSnapshot, WriteTargetError
from ledsetup.capture import (
    ScreenGrabber,
    grab_average,
    resolve_monitor,
)
from ledsetup.capture import (
    list_monitors as enumerate_monitors,
)
from ledsetup.color import coerce_rgb_byte
from ledsetup.device import (
    SelectedDevice,
    addresses_equal,
    clear_selected,
    load_selected,
    normalize_address,
    save_selected,
    selected_from_hit,
)
from ledsetup.exceptions import CaptureError, SettingsError
from ledsetup.gatt_text import format_gatt_lines
from ledsetup.gui_bridge import AsyncBridge
from ledsetup.protocol import build_off_frame, build_on_frame, build_rgb_frame
from ledsetup.session import BleSession, NotConnectedError
from ledsetup.settings import AppSettings, parse_timeout_input, save_settings
from ledsetup.throttle import ColorThrottle
from ledsetup.types import RGB, ScanFn

T = TypeVar("T")
MsgKind = Literal["info", "ok", "err", "busy"]


class DeviceDict(TypedDict):
    address: str
    name: str


class UiState(TypedDict):
    device: DeviceDict | None
    connected: bool


class UiMessage(TypedDict):
    text: str
    kind: MsgKind
    state: UiState


class GetStateResult(TypedDict):
    device: DeviceDict | None
    connected: bool
    auto_connect: bool


class SettingsDict(TypedDict):
    scan_timeout: float
    connect_timeout: float
    verbose: bool


class ScanHitDict(TypedDict):
    name: str
    address: str
    lednetwf: bool
    rssi: int | None


class ScanEvent(TypedDict):
    text: str
    kind: MsgKind
    state: UiState
    hits: list[ScanHitDict]
    device: DeviceDict | None


class MonitorDict(TypedDict):
    id: str
    index: int
    label: str
    primary: bool


class MonitorListResult(TypedDict):
    monitors: list[MonitorDict]
    selected_id: str
    note: str


class SyncEvent(TypedDict):
    text: str
    kind: MsgKind
    state: UiState
    running: bool
    r: int
    g: int
    b: int


class Ack(TypedDict):
    ok: bool


class JsApi:
    def __init__(
        self,
        session: BleSession,
        bridge: AsyncBridge,
        *,
        device_path: Path | None,
        settings_path: Path | None,
        scan_fn: ScanFn,
        settings: AppSettings,
        grabber: ScreenGrabber | None = None,
    ) -> None:
        # pywebview walks public attrs into JS; keep internals private or the
        # WinForms native window is serialized (recursion + UI-thread errors).
        self._session = session
        self._bridge = bridge
        self._device_path = device_path
        self._settings_path = settings_path
        self._scan_fn = scan_fn
        self._settings = settings
        self._throttle = ColorThrottle()
        self._hits: list[DeviceHit] = []
        self._pending: RGB | None = None
        self._flush_on = False
        self._ui: Any | None = None
        self._io_lock = threading.Lock()
        self._grabber = grabber
        self._syncing = False
        self._sync_stop = threading.Event()
        self._sync_rgb: RGB | None = None

    def _bg(self, fn: Callable[[], None]) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def _wait(self, coro: Coroutine[Any, Any, T], timeout: float = 45.0) -> T:
        return self._bridge.wait(coro, timeout=timeout)

    def _emit(self, name: str, payload: object) -> None:
        if self._ui is None:
            return
        blob = json.dumps(payload, ensure_ascii=False)
        try:
            self._ui.evaluate_js(f"window.__led && window.__led.{name}({blob})")
        except Exception:
            # Native WebView2/WinForms can raise if the window is already tearing down.
            return

    def _device(self) -> SelectedDevice | None:
        return load_selected(self._device_path)

    def _state(self) -> UiState:
        device = self._device()
        return {
            "device": None if device is None else {"address": device.address, "name": device.name},
            "connected": self._session.is_connected,
        }

    def _msg(self, text: str, kind: MsgKind = "info") -> UiMessage:
        return {"text": text, "kind": kind, "state": self._state()}

    def get_state(self) -> GetStateResult:
        payload = self._state()
        return {
            "device": payload["device"],
            "connected": payload["connected"],
            "auto_connect": payload["device"] is not None,
        }

    def get_settings(self) -> SettingsDict:
        return {
            "scan_timeout": self._settings.scan_timeout,
            "connect_timeout": self._settings.connect_timeout,
            "verbose": self._settings.verbose_gatt_after_write,
        }

    def scan(self) -> Ack:
        self._bg(self._scan_bg)
        return {"ok": True}

    def _scan_bg(self) -> None:
        self._halt_sync()

        async def work() -> list[DeviceHit]:
            await self._session.disconnect()
            return await self._scan_fn(timeout=self._settings.scan_timeout)

        with self._io_lock:
            try:
                hits = self._wait(work())
            except BluetoothUnavailableError as exc:
                self._emit("onScan", self._scan_event(str(exc), "err", []))
                return
        self._hits = list(hits)
        if not self._hits:
            self._emit(
                "onScan",
                self._scan_event(
                    "Поблизости никого нет. Bluetooth включён? ZENGGE лучше закрыть.",
                    "err",
                    [],
                ),
            )
            return
        self._emit(
            "onScan",
            self._scan_event(
                "Нажмите карточку — запомним адрес и перейдём к цвету.",
                "ok",
                [
                    {
                        "name": hit.name,
                        "address": hit.address,
                        "lednetwf": hit.lednetwf,
                        "rssi": hit.rssi,
                    }
                    for hit in self._hits
                ],
            ),
        )

    def _scan_event(self, text: str, kind: MsgKind, hits: list[ScanHitDict]) -> ScanEvent:
        msg = self._msg(text, kind)
        return {
            "text": msg["text"],
            "kind": msg["kind"],
            "state": msg["state"],
            "hits": hits,
            "device": msg["state"]["device"],
        }

    def select_device(self, address: str) -> Ack:
        wanted = normalize_address(address)
        hit = next((h for h in self._hits if addresses_equal(h.address, wanted)), None)
        if hit is not None:
            save_selected(selected_from_hit(hit), path=self._device_path)
        else:
            save_selected(SelectedDevice(address=wanted, name=""), path=self._device_path)
        self._bg(lambda: self._emit("onSelected", self._connect_bg()))
        return {"ok": True}

    def connect(self) -> Ack:
        self._bg(lambda: self._emit("onMsg", self._connect_bg()))
        return {"ok": True}

    def _connect_bg(self) -> UiMessage:
        device = self._device()
        if device is None:
            return self._msg("Сначала найдите ленту и нажмите карточку.", "err")
        with self._io_lock:
            try:
                self._wait(self._session.connect(device.address))
            except BluetoothUnavailableError as exc:
                return self._msg(str(exc), "err")
        return self._msg("Подключено. Можно выбирать цвет.", "ok")

    def toggle_connection(self) -> Ack:
        def run() -> None:
            if self._session.is_connected:
                self._halt_sync()
                with self._io_lock:
                    self._wait(self._session.disconnect())
                self._emit("onMsg", self._msg("Отключено.", "info"))
                return
            self._emit("onMsg", self._connect_bg())

        self._bg(run)
        return {"ok": True}

    def set_color(self, red: object, green: object, blue: object) -> Ack:
        if self._syncing:
            return {"ok": True}
        self._pending = (coerce_rgb_byte(red), coerce_rgb_byte(green), coerce_rgb_byte(blue))
        self._arm_flush()
        return {"ok": True}

    def _arm_flush(self) -> None:
        if self._flush_on:
            return
        self._flush_on = True
        delay = max(0.05, self._throttle.delay())
        threading.Timer(delay, self._flush_pending).start()

    def _flush_pending(self) -> None:
        self._flush_on = False
        rgb = self._pending
        if rgb is None:
            return
        if not self._throttle.allow(rgb):
            if self._throttle.delay() > 0:
                self._arm_flush()
            return
        self._throttle.mark(rgb)
        msg = self._write(build_rgb_frame(*rgb), "")
        if msg["text"]:
            self._emit("onMsg", msg)
        if self._pending != rgb:
            self._arm_flush()

    def power_on(self) -> Ack:
        self._bg(lambda: self._emit("onMsg", self._write(build_on_frame(), "Включение (гипотеза)")))
        return {"ok": True}

    def power_off(self) -> Ack:
        self._throttle.clear_last()
        self._bg(lambda: self._emit("onMsg", self._write(build_off_frame(), "Лента выключена")))
        return {"ok": True}

    def gatt(self) -> Ack:
        self._bg(self._gatt_bg)
        return {"ok": True}

    def _gatt_bg(self) -> None:
        async def work() -> GattSnapshot:
            if not self._session.is_connected:
                device = self._device()
                if device is None:
                    raise NotConnectedError()
                await self._session.connect(device.address)
            return await self._session.gatt()

        with self._io_lock:
            try:
                snapshot = self._wait(work())
            except (BluetoothUnavailableError, NotConnectedError) as exc:
                self._emit("onGatt", self._msg(str(exc), "err"))
                return
        self._emit("onGatt", self._msg("\n".join(format_gatt_lines(snapshot)), "ok"))

    def save_settings(self, scan: str, connect: str, verbose: bool) -> UiMessage:
        try:
            scan_t = parse_timeout_input(str(scan), "scan_timeout")
            conn_t = parse_timeout_input(str(connect), "connect_timeout")
        except SettingsError as exc:
            return self._msg(str(exc), "err")
        self._settings = replace(
            self._settings,
            scan_timeout=scan_t,
            connect_timeout=conn_t,
            verbose_gatt_after_write=bool(verbose),
        )
        save_settings(self._settings, path=self._settings_path)
        self._session.timeout = conn_t
        return self._msg("Настройки сохранены.", "ok")

    def forget_device(self) -> Ack:
        self._bg(self._forget_bg)
        return {"ok": True}

    def _forget_bg(self) -> None:
        self._halt_sync()
        # A half-dead BLE link must not block forgetting the saved address.
        with self._io_lock, suppress(Exception):
            self._wait(self._session.disconnect())
        clear_selected(self._device_path)
        self._emit("onForgot", self._msg("Лента забыта. Найдите её заново.", "info"))

    def _write(self, payload: bytes, what: str) -> UiMessage:
        with self._io_lock:
            return self._write_locked(payload, what)

    def _write_locked(self, payload: bytes, what: str) -> UiMessage:
        async def work() -> tuple[str, MsgKind]:
            device = self._device()
            if device is None:
                return ("Сначала найдите ленту.", "err")
            if not self._session.is_connected:
                try:
                    await self._session.connect(device.address)
                except BluetoothUnavailableError as exc:
                    return (str(exc), "err")
            try:
                await self._session.write(payload)
            except (BluetoothUnavailableError, WriteTargetError, NotConnectedError) as exc:
                return (str(exc), "err")
            extra = ""
            if self._settings.verbose_gatt_after_write and self._session.snapshot is not None:
                extra = "\n" + "\n".join(format_gatt_lines(self._session.snapshot))
            text = f"{what}{extra}" if what else extra
            return (text, "ok")

        text, kind = self._wait(work())
        if not text:
            return self._msg("", "ok")
        return self._msg(text, kind)

    def _halt_sync(self) -> None:
        self._sync_stop.set()
        self._syncing = False

    def _sync_event(self, text: str, kind: MsgKind, *, running: bool) -> SyncEvent:
        red, green, blue = self._sync_rgb or (0, 0, 0)
        msg = self._msg(text, kind)
        return {
            "text": msg["text"],
            "kind": msg["kind"],
            "state": msg["state"],
            "running": running,
            "r": red,
            "g": green,
            "b": blue,
        }

    def list_monitors(self) -> MonitorListResult:
        try:
            found = enumerate_monitors(self._grabber)
        except CaptureError as exc:
            return {"monitors": [], "selected_id": "", "note": str(exc)}
        monitor, note = resolve_monitor(found, saved_id=self._settings.monitor_id)
        if note:
            self._settings = replace(self._settings, monitor_id=monitor.id)
            save_settings(self._settings, path=self._settings_path)
        return {
            "monitors": [
                {
                    "id": item.id,
                    "index": item.index,
                    "label": item.label,
                    "primary": item.is_primary,
                }
                for item in found
            ],
            "selected_id": monitor.id,
            "note": note,
        }

    def select_monitor(self, monitor_id: object) -> UiMessage:
        ident = str(monitor_id).strip()
        if not ident:
            return self._msg("Выберите монитор.", "err")
        self._settings = replace(self._settings, monitor_id=ident)
        save_settings(self._settings, path=self._settings_path)
        return self._msg("Монитор сохранён.", "ok")

    def start_sync(self) -> Ack:
        if self._syncing:
            return {"ok": True}
        self._syncing = True
        self._sync_stop.clear()
        self._bg(self._sync_loop)
        return {"ok": True}

    def stop_sync(self) -> Ack:
        was = self._syncing
        self._halt_sync()
        if was:
            self._bg(
                lambda: self._emit(
                    "onSync",
                    self._sync_event(
                        "Захват остановлен. На ленте последний цвет.",
                        "info",
                        running=False,
                    ),
                )
            )
        return {"ok": True}

    def _sync_loop(self) -> None:
        try:
            found = enumerate_monitors(self._grabber)
            _chosen, note = resolve_monitor(found, saved_id=self._settings.monitor_id)
            text = "Идёт захват"
            if note:
                text = note
            self._emit("onSync", self._sync_event(text, "busy", running=True))
            while not self._sync_stop.is_set():
                monitor, _note = resolve_monitor(found, saved_id=self._settings.monitor_id)
                rgb = grab_average(monitor, self._grabber)
                if self._sync_stop.is_set():
                    return
                self._sync_rgb = rgb
                self._emit("onSync", self._sync_event("Идёт захват", "busy", running=True))
                if self._throttle.allow(rgb):
                    self._throttle.mark(rgb)
                    msg = self._write(build_rgb_frame(*rgb), "")
                    if msg["kind"] == "err" and msg["text"]:
                        self._halt_sync()
                        self._emit("onSync", self._sync_event(msg["text"], "err", running=False))
                        return
                self._sync_stop.wait(timeout=0.1)
        except CaptureError as exc:
            self._halt_sync()
            self._emit("onSync", self._sync_event(str(exc), "err", running=False))
        except Exception as exc:
            self._halt_sync()
            self._emit("onSync", self._sync_event(str(exc), "err", running=False))
