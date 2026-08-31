"""Fake BLE client for tests — no adapter."""

from __future__ import annotations

from collections.abc import Iterator

from bleak.exc import BleakError

from ledsetup.adapters.ble.transport import (
    PROTOCOL_NOTIFY_UUID,
    PROTOCOL_SERVICE_UUID,
    PROTOCOL_WRITE_UUID,
    uuids_equal,
)
from ledsetup.adapters.ble.types import BleClient, DisconnectFn


class FakeChar:
    def __init__(self, uuid: str, properties: tuple[str, ...], handle: int | None = None) -> None:
        self.uuid = uuid
        self.properties = properties
        self.handle = handle


class FakeService:
    def __init__(self, uuid: str, characteristics: list[FakeChar]) -> None:
        self.uuid = uuid
        self.characteristics = characteristics


class FakeServices:
    def __init__(self, services: list[FakeService]) -> None:
        self._services = services

    def __iter__(self) -> Iterator[FakeService]:
        return iter(self._services)

    def get_characteristic(self, uuid: str) -> FakeChar | None:
        for service in self._services:
            for char in service.characteristics:
                if uuids_equal(str(char.uuid), str(uuid)):
                    return char
        return None


class FakeClient:
    def __init__(self, address: str = "AA:BB:CC:DD:EE:FF") -> None:
        self.address = address
        self.is_connected = False
        self.connect_calls = 0
        self.write_calls = 0
        self.notify_calls = 0
        self.fail_writes = 0
        self.written: list[bytes] = []
        self.response_flags: list[bool] = []
        write = FakeChar(PROTOCOL_WRITE_UUID, ("write", "write-without-response"), 22)
        notify = FakeChar(PROTOCOL_NOTIFY_UUID, ("notify", "read"), 19)
        self.services = FakeServices([FakeService(PROTOCOL_SERVICE_UUID, [write, notify])])

    async def connect(self) -> None:
        self.connect_calls += 1
        self.is_connected = True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def write_gatt_char(
        self, char_specifier: object, data: bytes, response: bool = True
    ) -> None:
        self.response_flags.append(response)
        if self.fail_writes > 0:
            self.fail_writes -= 1
            raise BleakError("Could not write value b'...' to characteristic 0016: Unreachable")
        self.write_calls += 1
        self.written.append(bytes(data))

    async def start_notify(self, char_specifier: object, callback: object) -> None:
        self.notify_calls += 1


class FakeOpener:
    def __init__(self, client: FakeClient | None = None) -> None:
        self.client = client or FakeClient()
        self.open_calls = 0
        self.close_calls = 0

    async def open(
        self,
        address: str,
        timeout: float,
        on_disconnect: DisconnectFn | None = None,
    ) -> FakeClient:
        self.open_calls += 1
        self.client.address = address
        await self.client.connect()
        return self.client

    async def close(self, client: BleClient | None) -> None:
        self.close_calls += 1
        if client is not None:
            await client.disconnect()
