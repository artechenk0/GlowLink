"""Held BLE session — mock client, no adapter."""

import asyncio

import pytest

from fake_ble import FakeChar, FakeClient, FakeOpener, FakeService, FakeServices
from ledsetup.adapters.ble.session import BleSession, NotConnectedError
from ledsetup.adapters.ble.transport import (
    PROTOCOL_SERVICE_UUID,
    PROTOCOL_WRITE_UUID,
    BluetoothUnavailableError,
    write_on_client,
)
from ledsetup.domain.services.frame_builder import build_rgb_frame


def test_two_writes_one_connect() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)

    async def _run() -> None:
        await session.connect("aa:bb:cc:dd:ee:ff")
        await session.write(build_rgb_frame(255, 0, 0))
        await session.write(build_rgb_frame(0, 255, 0))
        await session.disconnect()

    asyncio.run(_run())
    assert opener.open_calls == 1
    assert session.connect_calls == 1
    assert opener.client.write_calls == 2
    assert opener.client.connect_calls == 1
    red, green = opener.client.written
    assert red[8] == 0x31
    assert red[9:12] == bytes([255, 0, 0])
    assert green[9:12] == bytes([0, 255, 0])
    assert 0xA1 not in red


def test_second_connect_same_address_reuses_client() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)

    async def _run() -> None:
        await session.connect("AA:BB:CC:DD:EE:FF")
        await session.connect("AA:BB:CC:DD:EE:FF")
        await session.disconnect()

    asyncio.run(_run())
    assert opener.open_calls == 1
    assert session.connect_calls == 1


def test_write_without_connect_raises() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close)

    async def _run() -> None:
        try:
            await session.write(build_rgb_frame(1, 2, 3))
        except NotConnectedError:
            return
        raise AssertionError("expected NotConnectedError")

    asyncio.run(_run())
    assert opener.open_calls == 0


def test_write_prefers_without_response_when_both_props() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close, reconnect_pause=0)

    async def _run() -> None:
        await session.connect("AA:BB:CC:DD:EE:FF")
        await session.write(build_rgb_frame(10, 20, 30))
        await session.disconnect()

    asyncio.run(_run())
    assert opener.client.response_flags == [False]


def test_write_with_response_when_only_write_prop() -> None:
    client = FakeClient()
    client.services = FakeServices(
        [
            FakeService(
                PROTOCOL_SERVICE_UUID,
                [FakeChar(PROTOCOL_WRITE_UUID, ("write",), 22)],
            )
        ]
    )

    async def _run() -> None:
        await client.connect()
        await write_on_client(
            client,
            build_rgb_frame(1, 2, 3),
            lambda _msg: None,
            notify_enabled=False,
            settle=0.0,
        )

    asyncio.run(_run())
    assert client.response_flags == [True]


def test_unreachable_write_reconnects_same_address() -> None:
    opener = FakeOpener()
    opener.client.fail_writes = 1
    session = BleSession(opener=opener.open, closer=opener.close, reconnect_pause=0)

    async def _run() -> None:
        await session.connect("AA:BB:CC:DD:EE:FF")
        await session.write(build_rgb_frame(255, 0, 0))
        await session.disconnect()

    asyncio.run(_run())
    assert opener.open_calls == 2
    assert session.connect_calls == 2
    assert opener.client.write_calls == 1
    assert opener.client.written[0][9:12] == bytes([255, 0, 0])


def test_dropped_link_reconnects_on_next_write() -> None:
    opener = FakeOpener()
    session = BleSession(opener=opener.open, closer=opener.close, reconnect_pause=0)

    async def _run() -> None:
        await session.connect("AA:BB:CC:DD:EE:FF")
        opener.client.is_connected = False
        session._on_disconnected()
        await session.write(build_rgb_frame(0, 255, 0))
        await session.disconnect()

    asyncio.run(_run())
    assert opener.open_calls == 2
    assert opener.client.write_calls == 1


def test_unreachable_twice_does_not_loop() -> None:
    opener = FakeOpener()
    opener.client.fail_writes = 99
    session = BleSession(opener=opener.open, closer=opener.close, reconnect_pause=0)

    async def _run() -> None:
        await session.connect("AA:BB:CC:DD:EE:FF")
        with pytest.raises(BluetoothUnavailableError, match="Unreachable"):
            await session.write(build_rgb_frame(1, 2, 3))

    asyncio.run(_run())
    assert opener.open_calls == 2
    assert session.is_connected is False
