"""App settings persistence — no BLE adapter."""

from pathlib import Path

import pytest

from ledsetup.settings import (
    AppSettings,
    SettingsError,
    load_settings,
    parse_timeout_input,
    save_settings,
)


def test_defaults_when_missing(tmp_path: Path) -> None:
    loaded = load_settings(tmp_path / "missing.json")
    assert loaded == AppSettings()
    assert loaded.verbose_gatt_after_write is False


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = AppSettings(
        scan_timeout=12.5,
        connect_timeout=20.0,
        verbose_gatt_after_write=True,
        monitor_id="0,0,1920x1080",
        last_color=(12, 34, 56),
    )
    save_settings(original, path)
    assert load_settings(path) == original


def test_invalid_saved_color_uses_default(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"last_color": [300, 1, 2]}', encoding="utf-8")
    assert load_settings(path).last_color == (255, 85, 77)


def test_corrupt_file_falls_back(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_settings(path) == AppSettings()


def test_parse_timeout_input() -> None:
    assert parse_timeout_input("10") == 10.0
    assert parse_timeout_input(" 8,5 ") == 8.5
    with pytest.raises(SettingsError):
        parse_timeout_input("0")
    with pytest.raises(SettingsError):
        parse_timeout_input("121")
    with pytest.raises(SettingsError):
        parse_timeout_input("abc")
