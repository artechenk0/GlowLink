"""Interactive numbered menus in the terminal. No GUI, one analog RGB strip."""

from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import replace
from enum import Enum
from pathlib import Path
from typing import cast

from ledsetup import NAME_PREFIX_HINT, __version__
from ledsetup.ble import BluetoothUnavailableError, WriteTargetError, scan_devices
from ledsetup.capture import (
    MonitorInfo,
    ScreenGrabber,
    grab_average,
    list_monitors,
    resolve_monitor,
)
from ledsetup.color import parse_rgb_triple
from ledsetup.device import (
    SelectedDevice,
    SelectionError,
    clear_selected,
    format_scan_line,
    load_selected,
    parse_choice_index,
    save_selected,
    selected_from_hit,
)
from ledsetup.exceptions import CaptureError, SettingsError
from ledsetup.gatt_text import format_gatt_lines
from ledsetup.protocol import (
    HYPOTHESIS_NOTE,
    RGB_OFF_NOTE,
    build_off_frame,
    build_on_frame,
    build_rgb_frame,
    frame_to_hex,
)
from ledsetup.session import BleSession, NotConnectedError
from ledsetup.settings import (
    AppSettings,
    load_settings,
    parse_timeout_input,
    save_settings,
)
from ledsetup.sync_loop import run_screen_sync
from ledsetup.throttle import ColorThrottle
from ledsetup.types import RGB, InputFn, PrintFn, ScanFn

NON_TTY_MESSAGE = (
    "терминальное меню нужно запускать в PowerShell / Windows Terminal: `ledsetup menu`. "
    "Или откройте окно: `ledsetup`. "
    "Подкоманды: scan, gatt, on, off, color, sync. Справка: ledsetup --help"
)

COLOR_PRESETS: dict[str, tuple[str, int, int, int]] = {
    "1": ("Красный", 255, 0, 0),
    "2": ("Зелёный", 0, 255, 0),
    "3": ("Синий", 0, 0, 255),
    "4": ("Белый", 255, 255, 255),
}

MAIN_CHOICES = frozenset("012345678")
COLOR_CHOICES = frozenset("012345")
SETTINGS_CHOICES = frozenset("01234")


class Screen(Enum):
    MAIN = "main"
    COLOR = "color"
    SETTINGS = "settings"


def parse_menu_choice(raw: str, valid: Sequence[str] | frozenset[str]) -> str:
    text = raw.strip()
    if text not in valid:
        raise SelectionError(f"нет пункта {raw!r}. Введите номер из меню.")
    return text


def parse_rgb_line(raw: str) -> RGB:
    try:
        return parse_rgb_triple(raw)
    except ValueError as exc:
        raise SelectionError(str(exc)) from exc


def format_header(selected: SelectedDevice | None, connected: bool) -> list[str]:
    lines = [f"GlowLink {__version__}"]
    if selected is None:
        lines.append("устройство: не выбрано")
        return lines
    name = selected.name or "(нет)"
    link = "подключено" if connected else "не подключено"
    lines.append(f"устройство: {selected.address}  имя (справочно, не ID): {name}  связь: {link}")
    return lines


def _yes_no(flag: bool) -> str:
    return "да" if flag else "нет"


def _as_print_fn(print_fn: PrintFn | None) -> PrintFn:
    if print_fn is not None:
        return print_fn

    def _print(message: str = "") -> None:
        print(message)

    return _print


class MenuApp:
    def __init__(
        self,
        *,
        input_fn: InputFn,
        print_fn: PrintFn,
        device_path: Path | None,
        settings_path: Path | None,
        session: BleSession,
        scan_fn: ScanFn,
        settings: AppSettings,
        grabber: ScreenGrabber | None = None,
    ) -> None:
        self._input = input_fn
        self._print = print_fn
        self._device_path = device_path
        self._settings_path = settings_path
        self.session = session
        self._scan_fn = scan_fn
        self.settings = settings
        self.screen = Screen.MAIN
        self._grabber = grabber
        self._ask_lock = threading.Lock()

    def emit(self, msg: str = "") -> None:
        self._print(msg)

    def ask(self, prompt: str) -> str:
        with self._ask_lock:
            return self._input(prompt)

    def selected(self) -> SelectedDevice | None:
        return load_selected(self._device_path)

    def _banner(self) -> None:
        self.emit("========")
        for line in format_header(self.selected(), self.session.is_connected):
            self.emit(line)
        self.emit("")

    def persist_settings(self) -> None:
        save_settings(self.settings, path=self._settings_path)
        self.session.timeout = self.settings.connect_timeout

    async def ensure_connected(self) -> bool:
        device = self.selected()
        if device is None:
            self.emit("устройство не выбрано. Сначала пункт 1 — сканировать и выбрать.")
            return False
        if self.session.is_connected:
            return True
        try:
            await self.session.connect(device.address)
        except BluetoothUnavailableError as exc:
            self.emit(str(exc))
            return False
        self.emit(f"подключено: {device.address}")
        return True

    async def _write(self, payload: bytes, what: str, note: str) -> None:
        if not await self.ensure_connected():
            return
        self.emit(f"{what}: {note}")
        self.emit(f"кадр ({len(payload)} байт): {frame_to_hex(payload)}")
        try:
            result = await self.session.write(payload)
        except (BluetoothUnavailableError, WriteTargetError, NotConnectedError) as exc:
            snapshot = getattr(exc, "snapshot", None)
            if snapshot is not None and self.settings.verbose_gatt_after_write:
                for line in format_gatt_lines(snapshot):
                    self.emit(line)
            self.emit(str(exc))
            return
        self.emit(
            "write "
            + ("UUID FF01 совпал" if result.write_matched else "UUID write не совпал с FF01")
            + f" → {result.write_uuid} method={result.write_method}"
        )
        if self.settings.verbose_gatt_after_write:
            for line in format_gatt_lines(result.snapshot):
                self.emit(line)

    async def handle_main(self, choice: str) -> bool:
        """Return False to quit the app."""
        if choice == "0":
            await self.session.disconnect()
            self.emit("выход")
            return False
        if choice == "1":
            await self._scan_and_select()
            return True
        if choice == "2":
            await self._toggle_connection()
            return True
        if choice == "3":
            self.screen = Screen.COLOR
            return True
        if choice == "4":
            await self._write(build_on_frame(), "on", HYPOTHESIS_NOTE)
            return True
        if choice == "5":
            await self._write(build_off_frame(), "off", RGB_OFF_NOTE)
            return True
        if choice == "6":
            await self._show_gatt()
            return True
        if choice == "7":
            self.screen = Screen.SETTINGS
            return True
        if choice == "8":
            await self._run_sync()
            return True
        return True

    async def handle_color(self, choice: str) -> None:
        if choice == "0":
            self.screen = Screen.MAIN
            return
        if choice == "5":
            try:
                raw = self.ask("RGB (три числа 0–255): ")
                red, green, blue = parse_rgb_line(raw)
            except (SelectionError, EOFError) as exc:
                if isinstance(exc, EOFError):
                    self.emit("ввод прерван")
                else:
                    self.emit(str(exc))
                return
            await self._write(
                build_rgb_frame(red, green, blue),
                f"color {red},{green},{blue} kind=rgb",
                RGB_OFF_NOTE,
            )
            return
        label, red, green, blue = COLOR_PRESETS[choice]
        await self._write(
            build_rgb_frame(red, green, blue),
            f"color {red},{green},{blue} kind=rgb ({label})",
            RGB_OFF_NOTE,
        )

    async def handle_settings(self, choice: str) -> None:
        if choice == "0":
            self.screen = Screen.MAIN
            return
        if choice == "1":
            try:
                raw = self.ask("таймаут scan, секунды: ")
                value = parse_timeout_input(raw, "scan_timeout")
            except (SettingsError, EOFError) as exc:
                self.emit("ввод прерван" if isinstance(exc, EOFError) else str(exc))
                return
            self.settings = replace(self.settings, scan_timeout=value)
            self.persist_settings()
            self.emit(f"scan timeout = {value:g} с")
            return
        if choice == "2":
            try:
                raw = self.ask("таймаут connect, секунды: ")
                value = parse_timeout_input(raw, "connect_timeout")
            except (SettingsError, EOFError) as exc:
                self.emit("ввод прерван" if isinstance(exc, EOFError) else str(exc))
                return
            self.settings = replace(self.settings, connect_timeout=value)
            self.persist_settings()
            self.emit(f"connect timeout = {value:g} с")
            return
        if choice == "3":
            self.settings = replace(
                self.settings,
                verbose_gatt_after_write=not self.settings.verbose_gatt_after_write,
            )
            self.persist_settings()
            self.emit(
                "подробный GATT после write: " + _yes_no(self.settings.verbose_gatt_after_write)
            )
            return
        if choice == "4":
            await self.session.disconnect()
            clear_selected(self._device_path)
            self.emit("выбранное устройство сброшено")

    async def _scan_and_select(self) -> None:
        await self.session.disconnect()
        self.emit(f"сканирование {self.settings.scan_timeout:g} с…")
        try:
            hits = await self._scan_fn(timeout=self.settings.scan_timeout)
        except BluetoothUnavailableError as exc:
            self.emit(str(exc))
            return
        if not hits:
            self.emit(
                f"поблизости нет BLE-рекламы (таймаут {self.settings.scan_timeout:g} с). "
                "Bluetooth включён?"
            )
            return
        self.emit(f"* — префикс {NAME_PREFIX_HINT} (подсказка; имя не ID, цель — адрес)")
        for i, hit in enumerate(hits, start=1):
            self.emit(format_scan_line(i, hit))
        try:
            raw = self.ask("номер устройства (0 — отмена): ")
            if raw.strip() == "0":
                self.emit("выбор не изменён")
                return
            index = parse_choice_index(raw, len(hits))
        except (SelectionError, EOFError) as exc:
            self.emit("выбор не получен" if isinstance(exc, EOFError) else str(exc))
            return
        hit = hits[index]
        path = save_selected(selected_from_hit(hit), path=self._device_path)
        self.emit(f"выбрано: {hit.address}  имя (справочно, не ID): {hit.name or '(нет)'}")
        self.emit(f"сохранено: {path}")

    async def _toggle_connection(self) -> None:
        if self.session.is_connected:
            await self.session.disconnect()
            self.emit("отключено")
            return
        device = self.selected()
        if device is None:
            self.emit("устройство не выбрано. Сначала пункт 1 — сканировать и выбрать.")
            return
        try:
            await self.session.connect(device.address)
        except BluetoothUnavailableError as exc:
            self.emit(str(exc))
            return
        self.emit(f"подключено: {device.address}")

    async def _show_gatt(self) -> None:
        if not await self.ensure_connected():
            return
        try:
            snapshot = await self.session.gatt()
        except (BluetoothUnavailableError, NotConnectedError) as exc:
            self.emit(str(exc))
            return
        for line in format_gatt_lines(snapshot):
            self.emit(line)

    def _pick_monitor(self, monitors: list[MonitorInfo]) -> MonitorInfo | None:
        for item in monitors:
            self.emit(f"{item.index}. {item.label}")
        try:
            raw = self.ask("номер монитора (Enter — сохранённый / основной): ")
        except EOFError:
            self.emit("ввод прерван")
            return None
        text = raw.strip()
        if not text:
            monitor, note = resolve_monitor(monitors, saved_id=self.settings.monitor_id)
            if note:
                self.emit(note)
            return monitor
        try:
            monitor, _note = resolve_monitor(monitors, flag=text)
        except CaptureError as exc:
            self.emit(str(exc))
            return None
        self.settings = replace(self.settings, monitor_id=monitor.id)
        self.persist_settings()
        return monitor

    async def _run_sync(self) -> None:
        if not await self.ensure_connected():
            return
        try:
            monitors = list_monitors(self._grabber)
        except CaptureError as exc:
            self.emit(str(exc))
            return
        monitor = self._pick_monitor(monitors)
        if monitor is None:
            return
        self.emit(f"захват: {monitor.label}")
        self.emit("Enter — остановить. Лента останется на последнем цвете.")
        stop = threading.Event()

        def wait_enter() -> None:
            with suppress(EOFError):
                self.ask("")
            stop.set()

        waiter = threading.Thread(target=wait_enter, daemon=True)
        waiter.start()
        last: RGB | None = None

        async def send(rgb: RGB) -> None:
            await self.session.write(build_rgb_frame(*rgb))

        def sample() -> RGB:
            return grab_average(monitor, self._grabber)

        try:
            last = await run_screen_sync(
                sample=sample,
                send=send,
                should_stop=stop.is_set,
                throttle=ColorThrottle(),
            )
        except (
            CaptureError,
            BluetoothUnavailableError,
            WriteTargetError,
            NotConnectedError,
        ) as exc:
            self.emit(str(exc))
            return
        if last is None:
            self.emit("sync остановлен")
            return
        self.emit(f"sync остановлен, последний цвет {last[0]} {last[1]} {last[2]}")

    def _print_main_menu(self) -> None:
        link = "Отключить" if self.session.is_connected else "Подключить"
        self.emit("1. Сканировать и выбрать устройство")
        self.emit(f"2. {link}")
        self.emit("3. Цвет…")
        self.emit("4. Включить (on, гипотеза)")
        self.emit("5. Выключить (off)")
        self.emit("6. GATT")
        self.emit("7. Настройки…")
        self.emit("8. Экран → лента (sync)")
        self.emit("0. Выход")

    def _print_color_menu(self) -> None:
        self.emit("Цвет всей ленты (один RGB)")
        for key, (label, red, green, blue) in COLOR_PRESETS.items():
            self.emit(f"{key}. {label}  {red} {green} {blue}")
        self.emit("5. Свой RGB")
        self.emit("0. Назад")

    def _print_settings_menu(self) -> None:
        self.emit("Настройки")
        self.emit(f"1. Таймаут scan (сейчас {self.settings.scan_timeout:g} с)")
        self.emit(f"2. Таймаут connect (сейчас {self.settings.connect_timeout:g} с)")
        self.emit(
            "3. Подробный GATT после write: " + _yes_no(self.settings.verbose_gatt_after_write)
        )
        self.emit("4. Сбросить выбранное устройство")
        self.emit("0. Назад")

    async def loop(self) -> int:
        while True:
            self._banner()
            if self.screen is Screen.MAIN:
                self._print_main_menu()
                valid = MAIN_CHOICES
            elif self.screen is Screen.COLOR:
                self._print_color_menu()
                valid = COLOR_CHOICES
            else:
                self._print_settings_menu()
                valid = SETTINGS_CHOICES
            try:
                choice = parse_menu_choice(self.ask("пункт: "), valid)
            except EOFError:
                await self.session.disconnect()
                self.emit("выход")
                return 0
            except SelectionError as exc:
                self.emit(str(exc))
                continue
            if self.screen is Screen.MAIN:
                if not await self.handle_main(choice):
                    return 0
            elif self.screen is Screen.COLOR:
                await self.handle_color(choice)
            else:
                await self.handle_settings(choice)


async def run_menu(
    *,
    input_fn: InputFn | None = None,
    print_fn: PrintFn | None = None,
    device_path: Path | None = None,
    settings_path: Path | None = None,
    session: BleSession | None = None,
    scan_fn: ScanFn | None = None,
    grabber: ScreenGrabber | None = None,
) -> int:
    settings = load_settings(settings_path)
    printer = _as_print_fn(print_fn)
    held = session or BleSession(timeout=settings.connect_timeout, log=printer)
    held.timeout = settings.connect_timeout
    prompt = input_fn if input_fn is not None else cast(InputFn, input)
    app = MenuApp(
        input_fn=prompt,
        print_fn=printer,
        device_path=device_path,
        settings_path=settings_path,
        session=held,
        scan_fn=scan_fn or scan_devices,
        settings=settings,
        grabber=grabber,
    )
    try:
        return await app.loop()
    finally:
        await held.disconnect()


def run_interactive(
    *,
    argv_tty: bool | None = None,
    input_fn: InputFn | None = None,
    print_fn: PrintFn | None = None,
    device_path: Path | None = None,
    settings_path: Path | None = None,
    session: BleSession | None = None,
    scan_fn: ScanFn | None = None,
    grabber: ScreenGrabber | None = None,
) -> int:
    interactive = sys.stdin.isatty() if argv_tty is None else argv_tty
    out = _as_print_fn(print_fn)
    if not interactive:
        out(NON_TTY_MESSAGE)
        return 1
    try:
        return asyncio.run(
            run_menu(
                input_fn=input_fn,
                print_fn=print_fn,
                device_path=device_path,
                settings_path=settings_path,
                session=session,
                scan_fn=scan_fn,
                grabber=grabber,
            )
        )
    except KeyboardInterrupt:
        out("прервано")
        return 130
