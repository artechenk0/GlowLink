"""In-memory configuration with explicit, deterministic persistence."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import replace

from ledsetup.application.models import (
    AppConfig,
    DeviceInfo,
    validate_color,
    validate_timeout,
)
from ledsetup.application.ports import ConfigRepository


class ConfigService:
    def __init__(self, store: ConfigRepository, config: AppConfig | None = None) -> None:
        self.store = store
        self._config = config if config is not None else store.load()
        self._dirty = False
        self._lock = threading.RLock()

    @property
    def config(self) -> AppConfig:
        with self._lock:
            return self._config

    def _change(
        self, update: Callable[[AppConfig], AppConfig], *, persist: bool = False
    ) -> AppConfig:
        with self._lock:
            self._config = update(self._config)
            self._dirty = True
            if persist:
                self.flush()
            return self._config

    def update_settings(
        self, *, scan_timeout: object, connect_timeout: object, verbose: bool
    ) -> AppConfig:
        scan = validate_timeout(scan_timeout, "scan_timeout")
        connect = validate_timeout(connect_timeout, "connect_timeout")
        if not isinstance(verbose, bool):
            raise ValueError("verbose must be bool")
        return self._change(
            lambda c: replace(
                c,
                scan_timeout=scan,
                connect_timeout=connect,
                verbose_gatt_after_write=verbose,
            ),
            persist=True,
        )

    def set_color(self, color: object) -> AppConfig:
        return self._change(lambda c: replace(c, last_color=validate_color(color)))

    def select_monitor(self, monitor_id: str) -> AppConfig:
        ident = monitor_id.strip()
        if not ident:
            raise ValueError("monitor_id must not be empty")
        return self._change(lambda c: replace(c, monitor_id=ident), persist=True)

    def select_device(self, device: DeviceInfo | str, name: str = "") -> AppConfig:
        if isinstance(device, str):
            device = DeviceInfo(device, name)
        return self._change(lambda c: replace(c, selected_device=device), persist=True)

    def forget_device(self) -> AppConfig:
        return self._change(lambda c: replace(c, selected_device=None), persist=True)

    def flush(self) -> None:
        with self._lock:
            if self._dirty:
                self.store.save(self._config)
                self._dirty = False
