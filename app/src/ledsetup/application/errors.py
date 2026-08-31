"""Recoverable errors shown by presentation adapters."""

from __future__ import annotations

from ledsetup.application.models import GattSnapshot


class LedSetupError(Exception):
    """Base class for expected application failures."""


class BluetoothUnavailableError(LedSetupError):
    pass


class WriteTargetError(LedSetupError):
    def __init__(self, message: str, snapshot: GattSnapshot | None = None) -> None:
        super().__init__(message)
        self.snapshot = snapshot


class DeviceNotSelectedError(LedSetupError):
    def __init__(self) -> None:
        super().__init__(
            "устройство не выбрано. Запустите `ledsetup scan` и укажите номер, "
            "либо передайте --address."
        )


class SelectionError(LedSetupError):
    pass


class SettingsError(LedSetupError, ValueError):
    pass


class NotConnectedError(LedSetupError):
    def __init__(self) -> None:
        super().__init__("нет BLE-соединения. Подключитесь из меню или выберите устройство.")


class CaptureError(LedSetupError):
    pass
