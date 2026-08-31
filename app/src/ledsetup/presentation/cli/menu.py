"""Interactive terminal presentation."""

from __future__ import annotations

import asyncio
import sys
import threading
from collections.abc import Callable, Sequence
from contextlib import suppress
from enum import Enum
from pathlib import Path

from ledsetup import __version__
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.errors import LedSetupError, SelectionError
from ledsetup.application.models import AppConfig, DeviceInfo, MonitorInfo
from ledsetup.bootstrap import build_application
from ledsetup.domain.services.color_values import parse_rgb_triple
from ledsetup.domain.value_objects.rgb import RGB
from ledsetup.presentation.cli.app_cli import format_scan_line
from ledsetup.presentation.cli.gatt_text import format_gatt_lines

InputFn = Callable[[str], str]
PrintFn = Callable[[str], None]
NON_TTY_MESSAGE = (
    "терминальное меню нужно запускать в PowerShell / Windows Terminal: `ledsetup menu`. "
    "Или откройте окно: `ledsetup`."
)
COLOR_PRESETS: dict[str, tuple[str, int, int, int]] = {
    "1": ("Красный", 255, 0, 0),
    "2": ("Зелёный", 0, 255, 0),
    "3": ("Синий", 0, 0, 255),
    "4": ("Тёплый", 255, 85, 77),
}


class Screen(Enum):
    MAIN = "main"
    COLOR = "color"
    SETTINGS = "settings"


def parse_menu_choice(raw: str, valid: Sequence[str] | frozenset[str]) -> str:
    choice = raw.strip()
    if choice not in valid:
        raise SelectionError(f"ожидался один из пунктов: {', '.join(valid)}")
    return choice


def parse_rgb_line(raw: str) -> RGB:
    return parse_rgb_triple(raw)


def format_header(selected: DeviceInfo | None, connected: bool) -> list[str]:
    device = "не выбрана" if selected is None else f"{selected.address} {selected.name}".strip()
    link = "подключено" if connected else "отключено"
    return [f"GlowLink {__version__}", f"Устройство: {device}", f"BLE: {link}"]


class MenuApp:
    def __init__(
        self,
        app: GlowLinkApplication,
        *,
        input_fn: InputFn,
        print_fn: PrintFn,
    ) -> None:
        self.app = app
        self._input = input_fn
        self._print = print_fn
        self.screen = Screen.MAIN
        self._ask_lock = threading.Lock()

    @property
    def settings(self) -> AppConfig:
        return self.app.config

    def emit(self, message: str = "") -> None:
        self._print(message)

    def ask(self, prompt: str) -> str:
        with self._ask_lock:
            return self._input(prompt)

    def _banner(self) -> None:
        self.emit("========")
        for line in format_header(self.settings.selected_device, self.app.is_connected):
            self.emit(line)
        self.emit()

    async def ensure_connected(self) -> bool:
        if self.settings.selected_device is None:
            self.emit("устройство не выбрано. Сначала пункт 1 — сканировать и выбрать.")
            return False
        try:
            await self.app.connect()
        except LedSetupError as exc:
            self.emit(str(exc))
            return False
        return True

    async def _main_choice(self, choice: str) -> bool:
        if choice == "0":
            self.emit("выход")
            return False
        if choice == "1":
            await self._scan_and_select()
        elif choice == "2":
            if self.app.is_connected:
                await self.app.disconnect()
                self.emit("отключено")
            elif await self.ensure_connected():
                self.emit(f"подключено: {self.app.address}")
        elif choice == "3":
            self.screen = Screen.COLOR
        elif choice == "5":
            if await self.ensure_connected():
                await self.app.power_off()
                self.emit("RGB-подсветка выключена")
        elif choice == "6":
            if await self.ensure_connected():
                for line in format_gatt_lines(await self.app.inspect_gatt()):
                    self.emit(line)
        elif choice == "7":
            self.screen = Screen.SETTINGS
        elif choice == "8":
            await self._run_sync()
        return True

    async def _color_choice(self, choice: str) -> None:
        if choice == "0":
            self.screen = Screen.MAIN
            return
        if choice == "5":
            try:
                rgb = parse_rgb_line(self.ask("RGB через пробел: "))
            except (EOFError, ValueError) as exc:
                self.emit("ввод прерван" if isinstance(exc, EOFError) else str(exc))
                return
        else:
            _label, red, green, blue = COLOR_PRESETS[choice]
            rgb = (red, green, blue)
        if await self.ensure_connected():
            await self.app.set_color(rgb)
            self.emit(f"цвет: {rgb[0]} {rgb[1]} {rgb[2]}")

    async def _settings_choice(self, choice: str) -> None:
        if choice == "0":
            self.screen = Screen.MAIN
            return
        if choice in {"1", "2"}:
            label = "scan" if choice == "1" else "connect"
            try:
                value = float(self.ask(f"таймаут {label}, секунды: ").replace(",", "."))
                self.app.update_settings(
                    scan_timeout=value if choice == "1" else self.settings.scan_timeout,
                    connect_timeout=value if choice == "2" else self.settings.connect_timeout,
                    verbose=self.settings.verbose_gatt_after_write,
                )
            except (EOFError, ValueError) as exc:
                self.emit("ввод прерван" if isinstance(exc, EOFError) else str(exc))
                return
            self.emit(f"{label} timeout = {value:g} с")
        elif choice == "3":
            self.app.update_settings(
                scan_timeout=self.settings.scan_timeout,
                connect_timeout=self.settings.connect_timeout,
                verbose=not self.settings.verbose_gatt_after_write,
            )
            self.emit(
                "подробный GATT после write: "
                + ("да" if self.settings.verbose_gatt_after_write else "нет")
            )
        elif choice == "4":
            await self.app.forget_device()
            self.emit("выбранное устройство сброшено")

    async def _scan_and_select(self) -> None:
        self.emit(f"сканирование {self.settings.scan_timeout:g} с…")
        try:
            devices = await self.app.scan()
        except LedSetupError as exc:
            self.emit(str(exc))
            return
        if not devices:
            self.emit("поблизости нет BLE-рекламы. Bluetooth включён?")
            return
        for index, device in enumerate(devices, start=1):
            self.emit(format_scan_line(index, device))
        try:
            raw = self.ask("номер устройства (0 — отмена): ").strip()
            if raw == "0":
                return
            index = int(raw)
            if not 1 <= index <= len(devices):
                raise SelectionError(f"номер {index} вне диапазона 1–{len(devices)}")
        except (EOFError, ValueError, SelectionError) as exc:
            self.emit("выбор не получен" if isinstance(exc, EOFError) else str(exc))
            return
        selected = await self.app.select_device(devices[index - 1])
        self.emit(f"выбрано: {selected.address}  имя: {selected.name or '(нет)'}")

    def _pick_monitor(self, monitors: list[MonitorInfo]) -> MonitorInfo | None:
        for monitor in monitors:
            self.emit(f"{monitor.index}. {monitor.label}")
        try:
            flag = self.ask("номер монитора (Enter — сохранённый / основной): ")
            monitor, note = self.app.resolve_monitor(monitors, flag=flag)
        except (EOFError, LedSetupError) as exc:
            self.emit("ввод прерван" if isinstance(exc, EOFError) else str(exc))
            return None
        if note:
            self.emit(note)
        self.app.select_monitor(monitor.id)
        return monitor

    async def _run_sync(self) -> None:
        if not await self.ensure_connected():
            return
        try:
            monitor = self._pick_monitor(self.app.list_monitors())
        except LedSetupError as exc:
            self.emit(str(exc))
            return
        if monitor is None:
            return
        self.emit(f"захват: {monitor.label}")
        self.emit("Enter — остановить. RGB-подсветка останется на последнем цвете.")
        stop = threading.Event()

        def wait_enter() -> None:
            with suppress(EOFError):
                self.ask("")
            stop.set()

        threading.Thread(target=wait_enter, daemon=True).start()
        try:
            last = await self.app.run_screen_sync(
                should_stop=stop.is_set,
                monitor_flag=monitor.id,
            )
        except LedSetupError as exc:
            self.emit(str(exc))
            return
        if last is None:
            self.emit("sync остановлен")
        else:
            self.emit(f"sync остановлен, последний цвет {last[0]} {last[1]} {last[2]}")

    def _render(self) -> frozenset[str]:
        self._banner()
        if self.screen is Screen.MAIN:
            self.emit("1. Сканировать и выбрать устройство")
            self.emit("2. Подключить / отключить")
            self.emit("3. Цвет…")
            self.emit("5. Выключить (off)")
            self.emit("6. GATT")
            self.emit("7. Настройки…")
            self.emit("8. Экран → RGB-подсветка (sync)")
            self.emit("0. Выход")
            return frozenset({"0", "1", "2", "3", "5", "6", "7", "8"})
        if self.screen is Screen.COLOR:
            self.emit("Цвет RGB-подсветки (один RGB)")
            for key, (label, red, green, blue) in COLOR_PRESETS.items():
                self.emit(f"{key}. {label}  {red} {green} {blue}")
            self.emit("5. Свой RGB")
            self.emit("0. Назад")
            return frozenset({"0", "1", "2", "3", "4", "5"})
        self.emit("Настройки")
        self.emit(f"1. Таймаут scan (сейчас {self.settings.scan_timeout:g} с)")
        self.emit(f"2. Таймаут connect (сейчас {self.settings.connect_timeout:g} с)")
        self.emit("3. Подробный GATT после write")
        self.emit("4. Сбросить выбранное устройство")
        self.emit("0. Назад")
        return frozenset({"0", "1", "2", "3", "4"})

    async def loop(self) -> int:
        running = True
        while running:
            valid = self._render()
            try:
                choice = parse_menu_choice(self.ask("> "), valid)
                if self.screen is Screen.MAIN:
                    running = await self._main_choice(choice)
                elif self.screen is Screen.COLOR:
                    await self._color_choice(choice)
                else:
                    await self._settings_choice(choice)
            except EOFError:
                self.emit("выход")
                return 0
            except LedSetupError as exc:
                self.emit(str(exc))
        return 0


async def run_menu(
    *,
    input_fn: InputFn | None = None,
    print_fn: PrintFn | None = None,
    device_path: Path | None = None,
    settings_path: Path | None = None,
    application: GlowLinkApplication | None = None,
) -> int:
    printer = print_fn or print
    prompt = input_fn or input
    app = application or build_application(
        config_path=settings_path or device_path,
        log=printer,
    )
    try:
        return await MenuApp(app, input_fn=prompt, print_fn=printer).loop()
    finally:
        await app.close()


def run_interactive(
    *,
    argv_tty: bool | None = None,
    input_fn: InputFn | None = None,
    print_fn: PrintFn | None = None,
    device_path: Path | None = None,
    settings_path: Path | None = None,
    application: GlowLinkApplication | None = None,
) -> int:
    interactive = sys.stdin.isatty() if argv_tty is None else argv_tty
    out = print_fn or print
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
                application=application,
            )
        )
    except KeyboardInterrupt:
        out("прервано")
        return 130
