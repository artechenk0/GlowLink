import asyncio

from fake_ports import ADDRESS, FakeBlePort, FakeConfigRepository, FakeScreenPort
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.models import AppConfig, DeviceInfo
from ledsetup.application.services.config_service import ConfigService
from ledsetup.presentation.cli.menu import parse_menu_choice, parse_rgb_line, run_menu


def make_app() -> tuple[GlowLinkApplication, FakeBlePort, FakeConfigRepository]:
    ble = FakeBlePort()
    store = FakeConfigRepository(AppConfig(selected_device=DeviceInfo(ADDRESS)))
    return GlowLinkApplication(ble, FakeScreenPort(), ConfigService(store)), ble, store


def input_from(values: list[str]):
    iterator = iter(values)
    return lambda _prompt: next(iterator)


def test_menu_parsers() -> None:
    assert parse_menu_choice(" 1 ", {"0", "1"}) == "1"
    assert parse_rgb_line("1 2 3") == (1, 2, 3)


def test_main_menu_exit() -> None:
    app, _ble, _store = make_app()
    output: list[str] = []
    result = asyncio.run(
        run_menu(application=app, input_fn=input_from(["0"]), print_fn=output.append)
    )
    assert result == 0
    assert "выход" in output


def test_preset_color_uses_application_connection() -> None:
    app, ble, store = make_app()
    asyncio.run(
        run_menu(
            application=app,
            input_fn=input_from(["3", "1", "0", "0"]),
            print_fn=lambda _message: None,
        )
    )
    assert ble.connect_calls == 1
    assert len(ble.writes) == 1
    assert store.saved[-1].last_color == (255, 0, 0)


def test_settings_persist_through_facade() -> None:
    app, _ble, store = make_app()
    asyncio.run(
        run_menu(
            application=app,
            input_fn=input_from(["7", "1", "2.5", "0", "0"]),
            print_fn=lambda _message: None,
        )
    )
    assert store.saved[-1].scan_timeout == 2.5
