"""Interactive menu — scripted input, no BLE adapter."""

import asyncio
from pathlib import Path

from fake_ble import FakeOpener
from ledsetup.ble import DeviceHit
from ledsetup.cli import build_parser, main
from ledsetup.device import load_selected, save_selected, selected_from_hit
from ledsetup.menu import (
    MAIN_CHOICES,
    NON_TTY_MESSAGE,
    parse_menu_choice,
    parse_rgb_line,
    run_interactive,
    run_menu,
)
from ledsetup.session import BleSession
from ledsetup.settings import load_settings


def test_parse_menu_choice() -> None:
    assert parse_menu_choice(" 3 ", "01234567") == "3"
    assert parse_menu_choice("8", MAIN_CHOICES) == "8"
    try:
        parse_menu_choice("9", "01234567")
    except Exception as exc:
        assert "нет пункта" in str(exc)
    else:
        raise AssertionError("expected error")


def test_parse_rgb_line() -> None:
    assert parse_rgb_line("255 0 128") == (255, 0, 128)
    try:
        parse_rgb_line("255 0")
    except Exception as exc:
        assert "три числа" in str(exc)
    else:
        raise AssertionError("expected error")
    try:
        parse_rgb_line("256 0 0")
    except Exception as exc:
        assert "0–255" in str(exc)
    else:
        raise AssertionError("expected error")


def test_parser_allows_no_command() -> None:
    args = build_parser().parse_args([])
    assert args.command is None


def test_gui_and_menu_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["gui"]).command == "gui"
    assert parser.parse_args(["menu"]).command == "menu"


def test_non_tty_does_not_enter_menu(capsys) -> None:
    code = main(["menu"], stdin_isatty=False)
    assert code == 1
    assert "терминал" in capsys.readouterr().out or "menu" in NON_TTY_MESSAGE
    assert "scan" in NON_TTY_MESSAGE


def _script(lines: list[str]):
    leftover = list(lines)

    def _input(_prompt: str) -> str:
        if not leftover:
            raise EOFError
        return leftover.pop(0)

    return _input


def test_main_menu_and_exit(tmp_path: Path) -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)
    lines: list[str] = []

    def capture(msg: str) -> None:
        lines.append(msg)

    code = asyncio.run(
        run_menu(
            input_fn=_script(["0"]),
            print_fn=capture,
            device_path=tmp_path / "dev.json",
            settings_path=tmp_path / "settings.json",
            session=session,
        )
    )
    assert code == 0
    text = "\n".join(lines)
    assert "GlowLink" in text
    assert "устройство: не выбрано" in text
    assert "1. Сканировать и выбрать устройство" in text
    assert "7. Настройки" in text
    assert "8. Экран → лента" in text
    assert opener.open_calls == 0


def test_two_colors_one_connect(tmp_path: Path) -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)
    save_selected(
        selected_from_hit(DeviceHit("LEDnetWFX", "E4:98:BB:6B:1A:AC", -40, True)),
        path=tmp_path / "dev.json",
    )
    code = asyncio.run(
        run_menu(
            input_fn=_script(["3", "1", "2", "0", "0"]),
            print_fn=lambda _msg: None,
            device_path=tmp_path / "dev.json",
            settings_path=tmp_path / "settings.json",
            session=session,
        )
    )
    assert code == 0
    assert opener.open_calls == 1
    assert opener.client.write_calls == 2
    red, green = opener.client.written
    assert red[8] == 0x31
    assert red[9:12] == bytes([255, 0, 0])
    assert green[9:12] == bytes([0, 255, 0])
    assert green[8] != 0xA1


def test_custom_rgb(tmp_path: Path) -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)
    save_selected(
        selected_from_hit(DeviceHit("X", "AA:BB:CC:DD:EE:FF", None, False)),
        path=tmp_path / "dev.json",
    )
    asyncio.run(
        run_menu(
            input_fn=_script(["3", "5", "10 20 30", "0", "0"]),
            print_fn=lambda _msg: None,
            device_path=tmp_path / "dev.json",
            settings_path=tmp_path / "settings.json",
            session=session,
        )
    )
    assert opener.client.written[0][9:12] == bytes([10, 20, 30])
    assert opener.client.written[0][8] == 0x31


def test_settings_persist(tmp_path: Path) -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)
    settings_path = tmp_path / "settings.json"
    asyncio.run(
        run_menu(
            input_fn=_script(["7", "1", "12", "2", "25", "3", "0", "0"]),
            print_fn=lambda _msg: None,
            device_path=tmp_path / "dev.json",
            settings_path=settings_path,
            session=session,
        )
    )
    loaded = load_settings(settings_path)
    assert loaded.scan_timeout == 12.0
    assert loaded.connect_timeout == 25.0
    assert loaded.verbose_gatt_after_write is True


def test_clear_selected_device(tmp_path: Path) -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)
    store = tmp_path / "dev.json"
    save_selected(
        selected_from_hit(DeviceHit("X", "E4:98:BB:6B:1A:AC", None, True)),
        path=store,
    )
    asyncio.run(
        run_menu(
            input_fn=_script(["7", "4", "0", "0"]),
            print_fn=lambda _msg: None,
            device_path=store,
            settings_path=tmp_path / "settings.json",
            session=session,
        )
    )
    assert load_selected(store) is None


def test_scan_selects_and_disconnects_first(tmp_path: Path) -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)
    store = tmp_path / "dev.json"
    save_selected(
        selected_from_hit(DeviceHit("Old", "11:22:33:44:55:66", None, False)),
        path=store,
    )

    async def fake_scan(timeout: float = 10.0):
        return [
            DeviceHit("LEDnetWFX", "E4:98:BB:6B:1A:AC", -40, True),
            DeviceHit("Kitchen", "AA:BB:CC:DD:EE:FF", -70, False),
        ]

    asyncio.run(
        run_menu(
            input_fn=_script(["2", "1", "1", "0"]),
            print_fn=lambda _msg: None,
            device_path=store,
            settings_path=tmp_path / "settings.json",
            session=session,
            scan_fn=fake_scan,
        )
    )
    selected = load_selected(store)
    assert selected is not None
    assert selected.address == "E4:98:BB:6B:1A:AC"
    # connect (2) then scan disconnects before listing
    assert opener.open_calls == 1


def test_run_interactive_non_tty() -> None:
    seen: list[str] = []
    code = run_interactive(argv_tty=False, print_fn=seen.append)
    assert code == 1
    assert any("терминал" in line for line in seen)
