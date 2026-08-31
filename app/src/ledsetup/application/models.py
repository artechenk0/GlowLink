"""Data crossing the application boundary."""

from __future__ import annotations

from dataclasses import dataclass, field

from ledsetup.domain.value_objects.ble_address import normalize_ble_address
from ledsetup.domain.value_objects.rgb import RGB, validate_rgb

DEFAULT_SCAN_TIMEOUT = 10.0
DEFAULT_CONNECT_TIMEOUT = 30.0
DEFAULT_SYNC_INTERVAL = 0.1
MAX_TIMEOUT_SEC = 120.0
DEFAULT_COLOR: RGB = (255, 85, 77)


@dataclass(frozen=True)
class DeviceInfo:
    address: str
    name: str = ""
    rssi: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "address", normalize_ble_address(self.address))
        object.__setattr__(self, "name", self.name.strip())


@dataclass(frozen=True)
class MonitorInfo:
    id: str
    index: int
    left: int
    top: int
    width: int
    height: int
    is_primary: bool
    label: str


@dataclass(frozen=True)
class CharInfo:
    uuid: str
    properties: tuple[str, ...]
    handle: int | None = None
    service_uuid: str = ""


@dataclass
class GattSnapshot:
    address: str
    services: list[tuple[str, list[CharInfo]]] = field(default_factory=list)
    service_matched: bool = False
    write_matched: bool = False
    notify_matched: bool = False

    @property
    def all_chars(self) -> list[CharInfo]:
        return [char for _service, chars in self.services for char in chars]

    @property
    def writable(self) -> list[CharInfo]:
        props = {"write", "write-without-response"}
        return [char for char in self.all_chars if props.intersection(char.properties)]


@dataclass(frozen=True)
class WriteResult:
    address: str
    write_uuid: str
    write_method: str
    write_matched: bool
    notify_enabled: bool
    payload_hex: str
    snapshot: GattSnapshot


@dataclass(frozen=True)
class AppConfig:
    scan_timeout: float = DEFAULT_SCAN_TIMEOUT
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    verbose_gatt_after_write: bool = False
    monitor_id: str = ""
    last_color: RGB = DEFAULT_COLOR
    selected_device: DeviceInfo | None = None
    sync_interval: float = DEFAULT_SYNC_INTERVAL

    def __post_init__(self) -> None:
        validate_timeout(self.scan_timeout, "scan_timeout")
        validate_timeout(self.connect_timeout, "connect_timeout")
        validate_timeout(self.sync_interval, "sync_interval")
        if not isinstance(self.verbose_gatt_after_write, bool):
            raise ValueError("verbose_gatt_after_write must be bool")
        if not isinstance(self.monitor_id, str):
            raise ValueError("monitor_id must be str")
        validate_rgb(self.last_color)


def validate_timeout(value: object, field: str = "timeout") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field}: expected a number")
    result = float(value)
    if result <= 0 or result > MAX_TIMEOUT_SEC:
        raise ValueError(f"{field}: must be in range 0 < t <= {MAX_TIMEOUT_SEC:g}")
    return result


def validate_color(value: object) -> RGB:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("last_color must contain three channels")
    channels = tuple(value)
    if any(
        isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel <= 255
        for channel in channels
    ):
        raise ValueError("last_color must contain integer channels 0-255")
    result = (channels[0], channels[1], channels[2])
    validate_rgb(result)
    return result
