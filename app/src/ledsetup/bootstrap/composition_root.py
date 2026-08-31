"""Composition root for all user interfaces."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ledsetup.adapters.ble.session import BleSession
from ledsetup.adapters.screen.mss_capture import MssGrabber
from ledsetup.adapters.storage.config_store import ConfigStore
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.ports import BlePort, LogFn, ScreenPort
from ledsetup.application.services.config_service import ConfigService


def build_application(
    *,
    config_path: Path | None = None,
    timeout: float | None = None,
    log: LogFn | None = None,
    ble: BlePort | None = None,
    screen: ScreenPort | None = None,
) -> GlowLinkApplication:
    store = ConfigStore(config_path)
    config = store.load()
    if timeout is not None:
        config = replace(config, connect_timeout=timeout)
    service = ConfigService(store, config)
    return GlowLinkApplication(
        ble=ble or BleSession(timeout=config.connect_timeout, log=log),
        screen=screen or MssGrabber(),
        config=service,
    )
