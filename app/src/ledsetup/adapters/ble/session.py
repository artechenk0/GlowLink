"""Held BLE connection for the interactive apps. One analog strip."""

from __future__ import annotations

import asyncio

from ledsetup.adapters.ble.transport import (
    GattSnapshot,
    WriteResult,
    close_bleak_client,
    enable_protocol_notify,
    open_bleak_client,
    scan_devices,
    snapshot_from_client,
    write_on_client,
)
from ledsetup.adapters.ble.types import BleClient, ClientCloser, ClientOpener, LogFn
from ledsetup.application.errors import BluetoothUnavailableError, NotConnectedError
from ledsetup.application.models import DeviceInfo
from ledsetup.domain.value_objects.ble_address import ble_addresses_equal as addresses_equal
from ledsetup.domain.value_objects.ble_address import normalize_ble_address as normalize_address

__all__ = ["BleSession", "NotConnectedError"]

RECONNECT_PAUSE = 0.5


def _discard_log(_msg: str) -> None:
    return


class BleSession:
    """One live BleakClient. Connect once, write many times, until disconnect."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        log: LogFn | None = None,
        opener: ClientOpener | None = None,
        closer: ClientCloser | None = None,
        reconnect_pause: float = RECONNECT_PAUSE,
    ) -> None:
        self.timeout = timeout
        self._log: LogFn = log if log is not None else _discard_log
        self._opener: ClientOpener = opener or open_bleak_client
        self._closer: ClientCloser = closer or close_bleak_client
        self._reconnect_pause = reconnect_pause
        self._client: BleClient | None = None
        self._address: str | None = None
        self._snapshot: GattSnapshot | None = None
        self._notify_enabled = False
        self._dropped = False
        self.connect_calls = 0

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def snapshot(self) -> GattSnapshot | None:
        return self._snapshot

    @property
    def is_connected(self) -> bool:
        if self._dropped or self._client is None:
            return False
        return bool(self._client.is_connected)

    def _on_disconnected(self, _client: object = None) -> None:
        self._dropped = True

    async def scan(self, timeout: float) -> list[DeviceInfo]:
        return await scan_devices(timeout)

    async def connect(self, address: str, timeout: float | None = None) -> GattSnapshot:
        if timeout is not None:
            self.timeout = timeout
        wanted = normalize_address(address)
        if self.is_connected and self._address and addresses_equal(self._address, wanted):
            if self._snapshot is None:
                raise BluetoothUnavailableError("соединение есть, но GATT-снимок потерян")
            return self._snapshot
        await self.disconnect()
        self._dropped = False
        self.connect_calls += 1
        client = await self._opener(wanted, self.timeout, self._on_disconnected)
        self._client = client
        self._address = wanted
        self._snapshot = snapshot_from_client(client)
        self._notify_enabled = await enable_protocol_notify(client, self._snapshot, self._log)
        return self._snapshot

    async def disconnect(self) -> None:
        client = self._client
        self._client = None
        self._address = None
        self._snapshot = None
        self._notify_enabled = False
        self._dropped = False
        await self._closer(client)

    async def gatt(self) -> GattSnapshot:
        if not self.is_connected or self._client is None:
            raise NotConnectedError()
        self._snapshot = snapshot_from_client(self._client)
        return self._snapshot

    async def _ensure_connected(self) -> None:
        if self.is_connected and self._client is not None:
            return
        address = self._address
        if address is None:
            await self.disconnect()
            raise NotConnectedError()
        await self.connect(address)

    async def _write_live(self, payload: bytes) -> WriteResult:
        if not self.is_connected or self._client is None:
            await self.disconnect()
            raise NotConnectedError()
        return await write_on_client(
            self._client,
            payload,
            self._log,
            notify_enabled=self._notify_enabled,
            settle=0.0,
        )

    async def write(self, payload: bytes) -> WriteResult:
        """Write, reconnecting once to the same address if the link went stale."""
        await self._ensure_connected()
        try:
            return await self._write_live(payload)
        except BluetoothUnavailableError:
            address = self._address
            await self.disconnect()
            if address is None:
                raise
            self._log(f"линк отвалился, повторное подключение к {address}")
            if self._reconnect_pause > 0:
                await asyncio.sleep(self._reconnect_pause)
            await self.connect(address)
            try:
                return await self._write_live(payload)
            except BluetoothUnavailableError:
                await self.disconnect()
                raise
