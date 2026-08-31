import asyncio

from fake_ports import ADDRESS, FakeBlePort, FakeConfigRepository, FakeScreenPort
from ledsetup.application.app import GlowLinkApplication
from ledsetup.application.models import AppConfig, DeviceInfo
from ledsetup.application.services.config_service import ConfigService
from ledsetup.presentation.desktop.gui import (
    APP_TITLE,
    WEB_ICON,
    WEB_INDEX,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    AsyncBridge,
    JsApi,
)


def make_api() -> tuple[JsApi, AsyncBridge, FakeBlePort, FakeScreenPort]:
    ble = FakeBlePort()
    screen = FakeScreenPort()
    config = AppConfig(selected_device=DeviceInfo(ADDRESS))
    app = GlowLinkApplication(ble, screen, ConfigService(FakeConfigRepository(config)))
    bridge = AsyncBridge()
    return JsApi(app, bridge), bridge, ble, screen


def test_window_assets_and_size() -> None:
    assert 800 <= WINDOW_WIDTH <= 900
    assert WINDOW_HEIGHT >= 800
    assert WEB_INDEX.is_file()
    assert WEB_ICON.is_file()
    assert APP_TITLE == "GlowLink"
    assert (WEB_INDEX.parent / "glowlink.png").is_file()
    assert (WEB_INDEX.parent / "app.css").is_file()
    assert (WEB_INDEX.parent / "app.js").is_file()


def test_web_contract_keeps_loading_sync_and_monitor_guards() -> None:
    html = WEB_INDEX.read_text(encoding="utf-8")
    js = (WEB_INDEX.parent / "app.js").read_text(encoding="utf-8")
    css = (WEB_INDEX.parent / "app.css").read_text(encoding="utf-8")
    assert 'id="boot-layer"' in html
    assert 'id="sync"' in html.partition('id="control-view"')[2]
    assert "data.selected_id" in js
    assert 'if (syncing) api().stop_sync(); showView("device")' in js
    assert "setControlsEnabled" in js
    assert ".boot-spinner" in css


def test_js_api_exposes_only_callables() -> None:
    api, bridge, _ble, _screen = make_api()
    try:
        public = [name for name in dir(api) if not name.startswith("_")]
        for name in public:
            assert callable(getattr(api, name)), name
    finally:
        api.close()
        bridge.stop()


def test_rapid_colors_coalesce_to_latest_value() -> None:
    api, bridge, ble, _screen = make_api()
    try:
        api.set_color(1, 2, 3)
        api.set_color(4, 5, 6)
        api.set_color(7, 8, 9)
        with api._color_lock:
            future = api._color_future
        assert future is not None
        future.result(timeout=2)
        assert ble.writes[-1][9:12] == bytes((7, 8, 9))
        assert len(ble.writes) <= 2
    finally:
        api.close()
        bridge.stop()


def test_sync_start_is_idempotent_and_restart_uses_new_token() -> None:
    api, bridge, _ble, _screen = make_api()
    try:
        api.start_sync()
        first = api._sync_future
        api.start_sync()
        assert api._sync_future is first
        bridge.wait(asyncio.sleep(0.03))
        api.stop_sync()
        assert first is not None
        first.result(timeout=2)
        api.start_sync()
        second = api._sync_future
        assert second is not None and second is not first
        api.stop_sync()
        second.result(timeout=2)
    finally:
        api.close()
        bridge.stop()
