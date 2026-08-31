import asyncio

import pytest

from fake_ports import ADDRESS, FakeBlePort, FakeConfigRepository, FakeScreenPort
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.errors import DeviceNotSelectedError
from ledsetup.application.models import AppConfig, DeviceInfo, MonitorInfo
from ledsetup.application.services.config_service import ConfigService


def make_app(
    *, config: AppConfig | None = None
) -> tuple[GlowLinkApplication, FakeBlePort, FakeScreenPort, FakeConfigRepository]:
    ble = FakeBlePort()
    screen = FakeScreenPort()
    store = FakeConfigRepository(config)
    return GlowLinkApplication(ble, screen, ConfigService(store)), ble, screen, store


def test_scan_disconnects_first_and_returns_boundary_models() -> None:
    app, ble, _screen, _store = make_app()
    devices = asyncio.run(app.scan(0.1))
    assert devices == ble.devices
    assert ble.disconnect_calls == 1
    assert ble.scan_calls == 1


def test_select_different_device_disconnects_and_persists() -> None:
    app, ble, _screen, store = make_app(
        config=AppConfig(selected_device=DeviceInfo("11:22:33:44:55:66"))
    )
    asyncio.run(app.select_device(DeviceInfo(ADDRESS, "strip")))
    assert ble.disconnect_calls == 1
    assert store.saved[-1].selected_device == DeviceInfo(ADDRESS, "strip")


def test_color_auto_connects_reuses_link_and_flushes_last_color() -> None:
    app, ble, _screen, store = make_app(config=AppConfig(selected_device=DeviceInfo(ADDRESS)))

    async def run() -> None:
        await app.set_color((1, 2, 3))
        await app.set_color((4, 5, 6))
        await app.close()

    asyncio.run(run())
    assert ble.connect_calls == 1
    assert len(ble.writes) == 2
    assert store.saved[-1].last_color == (4, 5, 6)


def test_parallel_actions_are_serialized() -> None:
    app, ble, _screen, _store = make_app(config=AppConfig(selected_device=DeviceInfo(ADDRESS)))

    async def run() -> None:
        await asyncio.gather(
            app.set_color((1, 2, 3)),
            app.set_color((4, 5, 6)),
            app.power_off(),
        )

    asyncio.run(run())
    assert ble.max_active_writes == 1
    assert ble.connect_calls == 1


def test_sync_uses_selected_monitor_and_held_connection() -> None:
    app, ble, screen, _store = make_app(
        config=AppConfig(selected_device=DeviceInfo(ADDRESS), sync_interval=0.1)
    )
    now = 0.0

    def clock() -> float:
        return now

    async def sleep(delay: float) -> None:
        nonlocal now
        now += delay

    last = asyncio.run(
        app.run_screen_sync(
            should_stop=lambda: False,
            deadline=0.25,
            clock=clock,
            sleep=sleep,
        )
    )
    assert last == screen.rgb
    assert screen.calls >= 2
    assert ble.connect_calls == 1
    assert len(ble.writes) == 1  # unchanged colors are throttled


def test_action_without_selection_fails_cleanly() -> None:
    app, _ble, _screen, _store = make_app()
    with pytest.raises(DeviceNotSelectedError):
        asyncio.run(app.power_off())


def test_monitor_resolution_handles_flag_saved_id_and_fallback() -> None:
    app, _ble, screen, _store = make_app(config=AppConfig(monitor_id="1920,0,1280x720"))
    second = MonitorInfo(
        id="1920,0,1280x720",
        index=2,
        left=1920,
        top=0,
        width=1280,
        height=720,
        is_primary=False,
        label="Monitor 2",
    )
    monitors = [screen.monitor, second]
    assert app.resolve_monitor(monitors)[0] == second
    assert app.resolve_monitor(monitors, flag="1")[0] == screen.monitor

    fallback, note = make_app(config=AppConfig(monitor_id="missing"))[0].resolve_monitor(monitors)
    assert fallback == screen.monitor
    assert "основной" in note
