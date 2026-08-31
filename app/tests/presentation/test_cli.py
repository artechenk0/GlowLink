import argparse
import asyncio

import pytest

from fake_ports import ADDRESS, FakeBlePort, FakeConfigRepository, FakeScreenPort
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.models import AppConfig, DeviceInfo
from ledsetup.application.services.config_service import ConfigService
from ledsetup.presentation.cli.app_cli import _cmd_scan, build_parser, rgb_byte


def make_app(selected: bool = False) -> tuple[GlowLinkApplication, FakeConfigRepository]:
    config = AppConfig(selected_device=DeviceInfo(ADDRESS)) if selected else AppConfig()
    store = FakeConfigRepository(config)
    app = GlowLinkApplication(FakeBlePort(), FakeScreenPort(), ConfigService(store))
    return app, store


def test_rgb_byte_accepts_edges_and_rejects_range() -> None:
    assert rgb_byte("0") == 0
    assert rgb_byte("255") == 255
    with pytest.raises(argparse.ArgumentTypeError):
        rgb_byte("256")


def test_subcommands_and_defaults_are_stable() -> None:
    parser = build_parser()
    assert parser.parse_args([]).command is None
    assert parser.parse_args(["gui"]).command == "gui"
    assert parser.parse_args(["menu"]).command == "menu"
    assert parser.parse_args(["scan"]).timeout == 10.0
    sync = parser.parse_args(["sync", "--seconds", "1.5", "--monitor", "2"])
    assert sync.seconds == 1.5
    assert sync.monitor == "2"


def test_scan_selects_and_persists_by_index() -> None:
    app, store = make_app()
    result = asyncio.run(_cmd_scan(app, 0.1, index=1))
    assert result == 0
    assert store.saved[-1].selected_device == DeviceInfo(ADDRESS, "Kitchen controller", -40)


def test_scan_non_tty_requires_explicit_choice(capsys) -> None:
    app, _store = make_app()
    result = asyncio.run(_cmd_scan(app, 0.1, stdin_isatty=False))
    assert result == 1
    assert "передайте --index" in capsys.readouterr().out


def test_scan_accepts_known_address_without_advertisement() -> None:
    store = FakeConfigRepository()
    app = GlowLinkApplication(FakeBlePort([]), FakeScreenPort(), ConfigService(store))
    result = asyncio.run(_cmd_scan(app, 0.1, address=ADDRESS))
    assert result == 0
    assert store.saved[-1].selected_device == DeviceInfo(ADDRESS)


def test_invalid_cli_color_and_seconds_exit_with_parser_error(capsys) -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["color", "256", "0", "0"])
    with pytest.raises(SystemExit):
        parser.parse_args(["sync", "--seconds", "0"])
    assert "error" in capsys.readouterr().err
