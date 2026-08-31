"""Atomic persistence for the single application configuration file."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from ledsetup.application.models import (
    AppConfig,
    DeviceInfo,
    validate_color,
    validate_timeout,
)

_WRITE_LOCK = threading.Lock()
SCHEMA_VERSION = 1


def default_config_path() -> Path:
    override = os.environ.get("LEDSETUP_CONFIG_FILE")
    if override:
        return Path(override)
    root = os.environ.get("LOCALAPPDATA")
    base = Path(root) / "ledsetup" if root else Path.home() / ".ledsetup"
    return base / "config.json"


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()

    def load(self) -> AppConfig:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return AppConfig()
            defaults = AppConfig()
            selected = _selected_device(raw.get("selected_device"))
            return AppConfig(
                scan_timeout=_timeout(
                    raw.get("scan_timeout"), defaults.scan_timeout, "scan_timeout"
                ),
                connect_timeout=_timeout(
                    raw.get("connect_timeout"), defaults.connect_timeout, "connect_timeout"
                ),
                verbose_gatt_after_write=_bool(
                    raw.get("verbose_gatt_after_write"), defaults.verbose_gatt_after_write
                ),
                monitor_id=_text(raw.get("monitor_id"), defaults.monitor_id),
                last_color=_color(raw.get("last_color"), defaults.last_color),
                selected_device=selected,
                sync_interval=_timeout(
                    raw.get("sync_interval"), defaults.sync_interval, "sync_interval"
                ),
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        selected = config.selected_device
        data = {
            "schema_version": SCHEMA_VERSION,
            "scan_timeout": config.scan_timeout,
            "connect_timeout": config.connect_timeout,
            "verbose_gatt_after_write": config.verbose_gatt_after_write,
            "monitor_id": config.monitor_id,
            "last_color": list(config.last_color),
            "selected_device": (
                None if selected is None else {"address": selected.address, "name": selected.name}
            ),
            "sync_interval": config.sync_interval,
        }
        payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        with _WRITE_LOCK:
            fd, name = tempfile.mkstemp(
                prefix=f"{self.path.name}.", suffix=".tmp", dir=self.path.parent
            )
            temp = Path(name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as stream:
                    stream.write(payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, self.path)
            except BaseException:
                temp.unlink(missing_ok=True)
                raise


def _timeout(value: object, default: float, field: str) -> float:
    try:
        return validate_timeout(value, field)
    except ValueError:
        return default


def _bool(value: object, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _text(value: object, default: str) -> str:
    return value.strip() if isinstance(value, str) else default


def _color(value: object, default: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        return validate_color(value)
    except ValueError:
        return default


def _selected_device(value: object) -> DeviceInfo | None:
    if not isinstance(value, dict):
        return None
    address = value.get("address")
    name = value.get("name", "")
    if not isinstance(address, str) or not isinstance(name, str):
        return None
    try:
        return DeviceInfo(address=address, name=name)
    except ValueError:
        return None
