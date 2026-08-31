"""Write-target selection without a BLE adapter."""

import pytest

from ledsetup.adapters.ble.transport import (
    PROTOCOL_WRITE_UUID,
    CharInfo,
    DeviceInfo,
    WriteTargetError,
    _scan_sort_key,
    normalize_uuid,
    select_write_characteristic,
    uuids_equal,
)


def test_normalize_short_uuid() -> None:
    assert normalize_uuid("FF01") == PROTOCOL_WRITE_UUID
    assert uuids_equal("ff01", PROTOCOL_WRITE_UUID)
    assert uuids_equal("0000FF01-0000-1000-8000-00805F9B34FB", PROTOCOL_WRITE_UUID)


def test_prefers_protocol_write_uuid() -> None:
    other = CharInfo("0000aaaa-0000-1000-8000-00805f9b34fb", ("write",))
    protocol = CharInfo(PROTOCOL_WRITE_UUID, ("write-without-response",))
    chosen = select_write_characteristic([other, protocol])
    assert chosen.uuid == PROTOCOL_WRITE_UUID


def test_short_uuid_counts_as_protocol_write() -> None:
    chosen = select_write_characteristic([CharInfo("ff01", ("write",))])
    assert uuids_equal(chosen.uuid, PROTOCOL_WRITE_UUID)


def test_single_unmatched_writable_is_used() -> None:
    only = CharInfo("00001111-0000-1000-8000-00805f9b34fb", ("write",))
    chosen = select_write_characteristic([only])
    assert chosen is only


def test_refuses_first_of_many_unmatched() -> None:
    a = CharInfo("00001111-0000-1000-8000-00805f9b34fb", ("write",))
    b = CharInfo("00002222-0000-1000-8000-00805f9b34fb", ("write-without-response",))
    with pytest.raises(WriteTargetError, match="несколько"):
        select_write_characteristic([a, b])


def test_refuses_when_none_writable() -> None:
    with pytest.raises(WriteTargetError, match="нет characteristic"):
        select_write_characteristic([])


def test_scan_sorting_places_named_devices_before_unnamed() -> None:
    devices = [
        DeviceInfo("AA:BB:CC:DD:EE:03", ""),
        DeviceInfo("AA:BB:CC:DD:EE:02", "beta"),
        DeviceInfo("AA:BB:CC:DD:EE:01", "Alpha"),
    ]

    assert sorted(devices, key=_scan_sort_key) == [devices[2], devices[1], devices[0]]
