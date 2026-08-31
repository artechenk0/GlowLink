"""Command-line presentation for GlowLink."""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from collections.abc import Callable, Sequence

from ledsetup import __version__
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.errors import (
    BluetoothUnavailableError,
    LedSetupError,
    SelectionError,
    WriteTargetError,
)
from ledsetup.application.models import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_SCAN_TIMEOUT,
    DeviceInfo,
    GattSnapshot,
    WriteResult,
)
from ledsetup.bootstrap import build_application
from ledsetup.domain.services.color_values import parse_rgb_channel
from ledsetup.domain.services.frame_builder import RGB_OFF_NOTE
from ledsetup.domain.value_objects.ble_address import ble_addresses_equal, normalize_ble_address
from ledsetup.presentation.cli.gatt_text import format_gatt_lines

InputFn = Callable[[str], str]
CONNECT_TIMEOUT = DEFAULT_CONNECT_TIMEOUT


def rgb_byte(value: str) -> int:
    try:
        return parse_rgb_channel(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def ble_address(value: str) -> str:
    try:
        return normalize_ble_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _add_timeout(parser: argparse.ArgumentParser, default: float, help_text: str) -> None:
    parser.add_argument("--timeout", type=float, default=default, help=help_text)


def _add_address_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--address",
        type=ble_address,
        help="BLE-адрес (стабильный ID). Иначе берётся устройство, выбранное в scan",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ledsetup",
        description=(
            "Управление одной аналоговой RGB-лентой по BLE. Без подкоманды — окно. "
            "Имя в рекламе нестабильно — цель задаётся адресом. Вся полоса — один цвет. "
            "sync — средний цвет выбранного монитора."
        ),
    )
    parser.add_argument("--version", action="version", version=f"ledsetup {__version__}")
    sub = parser.add_subparsers(dest="command", required=False)
    sub.add_parser("gui", help="окно управления (то же, что без подкоманды)")
    sub.add_parser("menu", help="терминальное меню")

    scan = sub.add_parser("scan", help="список BLE-устройств рядом и выбор цели")
    _add_timeout(scan, DEFAULT_SCAN_TIMEOUT, "секунды сканирования")
    select = scan.add_mutually_exclusive_group()
    select.add_argument("--index", type=int, metavar="N")
    select.add_argument("--address", type=ble_address)
    select.add_argument("--name")

    gatt = sub.add_parser("gatt", help="подключиться и перечислить GATT")
    _add_timeout(gatt, CONNECT_TIMEOUT, "таймаут connect")
    _add_address_flag(gatt)
    off = sub.add_parser("off", help="кадр питания off")
    _add_timeout(off, CONNECT_TIMEOUT, "таймаут connect")
    _add_address_flag(off)
    color = sub.add_parser("color", help="сплошной RGB-подсветки")
    color.add_argument("r", type=rgb_byte)
    color.add_argument("g", type=rgb_byte)
    color.add_argument("b", type=rgb_byte)
    _add_timeout(color, CONNECT_TIMEOUT, "таймаут connect")
    _add_address_flag(color)
    sync = sub.add_parser("sync", help="средний цвет монитора → RGB-подсветка")
    sync.add_argument("--seconds", type=_positive_seconds, default=None, metavar="N")
    sync.add_argument("--monitor", default=None)
    _add_timeout(sync, CONNECT_TIMEOUT, "таймаут connect")
    _add_address_flag(sync)
    return parser


def _positive_seconds(value: str) -> float:
    try:
        number = float(value.replace(",", "."))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ожидалось число секунд") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("--seconds должен быть > 0")
    return number


def _print(message: str = "") -> None:
    print(message)


def _print_gatt(snapshot: GattSnapshot) -> None:
    for line in format_gatt_lines(snapshot, include_expected=True):
        _print(line)


def format_scan_line(index: int, device: DeviceInfo) -> str:
    label = device.name or "(без имени)"
    rssi = f"  RSSI={device.rssi}" if device.rssi is not None else ""
    return f"{index:2d}  {label}  {device.address}{rssi}"


def _print_scan_hits(devices: Sequence[DeviceInfo]) -> None:
    for index, device in enumerate(devices, start=1):
        _print(format_scan_line(index, device))


def _select_device(
    devices: Sequence[DeviceInfo],
    *,
    index: int | None,
    address: str | None,
    name: str | None,
) -> DeviceInfo:
    if sum(value is not None for value in (index, address, name)) != 1:
        raise SelectionError("укажите ровно один способ: --index, --address или --name")
    if index is not None:
        if not 1 <= index <= len(devices):
            raise SelectionError(f"номер {index} вне диапазона 1–{len(devices)}")
        return devices[index - 1]
    if address is not None:
        wanted = normalize_ble_address(address)
        return next(
            (device for device in devices if ble_addresses_equal(device.address, wanted)),
            DeviceInfo(address=wanted),
        )
    wanted_name = (name or "").strip().casefold()
    matches = [device for device in devices if device.name.casefold() == wanted_name]
    if len(matches) != 1:
        raise SelectionError(f"имя {name!r} не идентифицирует ровно одно устройство")
    return matches[0]


async def _cmd_scan(
    app: GlowLinkApplication,
    timeout: float,
    *,
    index: int | None = None,
    address: str | None = None,
    name: str | None = None,
    input_fn: InputFn | None = None,
    stdin_isatty: bool | None = None,
) -> int:
    devices = await app.scan(timeout)
    if devices:
        _print_scan_hits(devices)
    else:
        _print(f"поблизости нет BLE-рекламы (таймаут {timeout:g} с). Bluetooth включён?")
    if any(value is not None for value in (index, address, name)):
        try:
            selected = _select_device(devices, index=index, address=address, name=name)
        except (SelectionError, ValueError) as exc:
            _print(str(exc))
            return 1
    elif not devices:
        return 1
    else:
        interactive = sys.stdin.isatty() if stdin_isatty is None else stdin_isatty
        if not interactive:
            _print("scan без выбора: передайте --index / --address / --name")
            return 1
        try:
            raw = (input_fn or input)("номер устройства: ")
            selected = _select_device(devices, index=int(raw.strip()), address=None, name=None)
        except (EOFError, ValueError, SelectionError) as exc:
            _print("выбор не получен" if isinstance(exc, EOFError) else str(exc))
            return 1
    await app.select_device(selected)
    _print(f"выбрано: {selected.address}  имя (справочно, не ID): {selected.name or '(нет)'}")
    return 0


def _print_write(result: WriteResult, what: str) -> None:
    _print(f"{what}: {RGB_OFF_NOTE}")
    _print(f"кадр ({len(bytes.fromhex(result.payload_hex))} байт): {result.payload_hex}")
    _print_gatt(result.snapshot)
    _print(
        f"write {'UUID FF01 совпал' if result.write_matched else 'UUID write не совпал с FF01'} "
        f"→ {result.write_uuid} method={result.write_method} "
        f"notify/CCCD={'да' if result.notify_enabled else 'нет'}"
    )


async def run_cli_sync(
    app: GlowLinkApplication,
    *,
    seconds: float | None,
    monitor_flag: str | None,
    address: str | None = None,
) -> int:
    monitors = app.list_monitors()
    for monitor in monitors:
        _print(f"{monitor.index}. {monitor.label}  id={monitor.id}")
    chosen, note = app.resolve_monitor(monitors, flag=monitor_flag)
    if note:
        _print(note)
    _print(f"захват: {chosen.label}")
    deadline = None if seconds is None else time.monotonic() + seconds
    last = await app.run_screen_sync(
        should_stop=lambda: False,
        address=address,
        monitor_flag=chosen.id,
        deadline=deadline,
    )
    if last is None:
        _print("sync остановлен")
    else:
        _print(f"sync остановлен, последний цвет {last[0]} {last[1]} {last[2]}")
    return 0


async def _run(args: argparse.Namespace, app: GlowLinkApplication) -> int:
    if args.command == "scan":
        return await _cmd_scan(
            app,
            args.timeout,
            index=args.index,
            address=args.address,
            name=args.name,
        )
    if args.command == "gatt":
        _print_gatt(await app.inspect_gatt(args.address))
        return 0
    if args.command == "off":
        _print_write(await app.power_off(args.address), "off")
        return 0
    if args.command == "color":
        what = f"color {args.r},{args.g},{args.b}"
        _print_write(await app.set_color((args.r, args.g, args.b), args.address), what)
        return 0
    if args.command == "sync":
        return await run_cli_sync(
            app,
            seconds=args.seconds,
            monitor_flag=args.monitor,
            address=args.address,
        )
    _print(f"неизвестная команда: {args.command}")
    return 2


async def _run_and_close(args: argparse.Namespace) -> int:
    app = build_application(timeout=getattr(args, "timeout", None), log=_print)
    try:
        return await _run(args, app)
    finally:
        await app.close()


def main(argv: Sequence[str] | None = None, *, stdin_isatty: bool | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command is None or args.command == "gui":
        from ledsetup.presentation.desktop.gui import run_gui

        return run_gui()
    if args.command == "menu":
        from ledsetup.presentation.cli.menu import run_interactive

        return run_interactive(argv_tty=stdin_isatty)
    try:
        return asyncio.run(_run_and_close(args))
    except WriteTargetError as exc:
        if exc.snapshot is not None:
            _print_gatt(exc.snapshot)
        _print(str(exc))
        return 2
    except (BluetoothUnavailableError, LedSetupError) as exc:
        _print(str(exc))
        return 1
    except KeyboardInterrupt:
        _print("прервано")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
