"""Persisted app settings. Timeouts, verbose GATT dump, last monitor for sync."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from ledsetup.ble import DEFAULT_SCAN_TIMEOUT
from ledsetup.exceptions import SettingsError
from ledsetup.paths import default_app_dir

__all__ = [
    "DEFAULT_CONNECT_TIMEOUT",
    "MAX_TIMEOUT_SEC",
    "AppSettings",
    "SettingsError",
    "default_settings_path",
    "load_settings",
    "parse_timeout_input",
    "save_settings",
]

DEFAULT_CONNECT_TIMEOUT = 30.0
MAX_TIMEOUT_SEC = 120.0


@dataclass(frozen=True)
class AppSettings:
    scan_timeout: float = DEFAULT_SCAN_TIMEOUT
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    verbose_gatt_after_write: bool = False
    monitor_id: str = ""
    last_color: tuple[int, int, int] = (255, 85, 77)


def default_settings_path() -> Path:
    override = os.environ.get("LEDSETUP_SETTINGS_FILE")
    if override:
        return Path(override)
    return default_app_dir() / "settings.json"


def _as_timeout(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SettingsError(f"{field}: ожидалось число секунд")
    number = float(value)
    if number <= 0 or number > MAX_TIMEOUT_SEC:
        raise SettingsError(f"{field}: таймаут должен быть в диапазоне 0 < t ≤ {MAX_TIMEOUT_SEC:g}")
    return number


def _as_color(value: object) -> tuple[int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return (255, 85, 77)
    if any(isinstance(channel, bool) or not isinstance(channel, int) for channel in value):
        return (255, 85, 77)
    if any(channel < 0 or channel > 255 for channel in value):
        return (255, 85, 77)
    return (value[0], value[1], value[2])


def parse_timeout_input(raw: str, field: str = "таймаут") -> float:
    text = raw.strip().replace(",", ".")
    if not text:
        raise SettingsError(f"{field}: ничего не введено")
    try:
        number = float(text)
    except ValueError as exc:
        raise SettingsError(f"{field}: ожидалось число секунд, получено {raw!r}") from exc
    return _as_timeout(number, field)


def load_settings(path: Path | None = None) -> AppSettings:
    store = path or default_settings_path()
    try:
        raw = json.loads(store.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return AppSettings()
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return AppSettings()
    if not isinstance(raw, dict):
        return AppSettings()
    try:
        scan = (
            _as_timeout(raw["scan_timeout"], "scan_timeout")
            if "scan_timeout" in raw
            else DEFAULT_SCAN_TIMEOUT
        )
        connect = (
            _as_timeout(raw["connect_timeout"], "connect_timeout")
            if "connect_timeout" in raw
            else DEFAULT_CONNECT_TIMEOUT
        )
    except SettingsError:
        return AppSettings()
    verbose = raw.get("verbose_gatt_after_write", False)
    if not isinstance(verbose, bool):
        verbose = bool(verbose)
    monitor_id = raw.get("monitor_id", "")
    if not isinstance(monitor_id, str):
        monitor_id = ""
    return AppSettings(
        scan_timeout=scan,
        connect_timeout=connect,
        verbose_gatt_after_write=verbose,
        monitor_id=monitor_id.strip(),
        last_color=_as_color(raw.get("last_color", (255, 85, 77))),
    )


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    store = path or default_settings_path()
    store.parent.mkdir(parents=True, exist_ok=True)
    tmp = store.with_name(store.name + ".tmp")
    tmp.write_text(
        json.dumps(asdict(settings), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(store)
    return store
