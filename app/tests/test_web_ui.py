"""Web UI assets ship with the package."""

from ledsetup.ble import DeviceHit
from ledsetup.gui import (
    APP_TITLE,
    WEB_ICON,
    WEB_INDEX,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    AsyncBridge,
    JsApi,
)
from ledsetup.session import BleSession
from ledsetup.settings import AppSettings


async def _noop_scan(timeout: float = 10.0) -> list[DeviceHit]:
    return []


def test_window_is_wider_than_picker_slice() -> None:
    assert 800 <= WINDOW_WIDTH <= 900
    assert WINDOW_HEIGHT >= 800


def test_web_index_exists() -> None:
    folder = WEB_INDEX.parent
    assert WEB_INDEX.is_file()
    assert WEB_ICON.is_file()
    assert APP_TITLE == "GlowLink"
    assert 'href="glowlink.png"' in WEB_INDEX.read_text(encoding="utf-8")
    assert (folder / "glowlink.png").is_file()
    assert (folder / "app.css").is_file()
    assert (folder / "app.js").is_file()
    assert "diagnostic-template" not in WEB_INDEX.read_text(encoding="utf-8")


def test_sync_controls_only_on_color_view() -> None:
    html = WEB_INDEX.read_text(encoding="utf-8")
    device, _sep, control = html.partition('id="control-view"')
    assert "sync" not in device
    assert 'id="sync"' in control
    assert "monitor-select" in control


def test_web_ui_has_boot_loading_and_state_guards() -> None:
    html = WEB_INDEX.read_text(encoding="utf-8")
    js = (WEB_INDEX.parent / "app.js").read_text(encoding="utf-8")
    css = (WEB_INDEX.parent / "app.css").read_text(encoding="utf-8")

    assert 'id="boot-layer"' in html
    assert 'aria-busy="true"' in html
    assert "setControlsEnabled" in js
    assert "data.selected_id" in js
    assert 'result.kind === "ok"' in js
    assert "Number.isInteger(channel)" in js
    assert "setMonitorEnabled" in js
    assert ".boot-spinner" in css
    assert "@keyframes spin" in css


def test_changing_device_stops_screen_sync() -> None:
    js = (WEB_INDEX.parent / "app.js").read_text(encoding="utf-8")
    assert 'if (syncing) api().stop_sync(); showView("device")' in js


def test_js_api_exposes_only_callables() -> None:
    bridge = AsyncBridge()
    try:
        api = JsApi(
            BleSession(timeout=1.0),
            bridge,
            device_path=None,
            settings_path=None,
            scan_fn=_noop_scan,
            settings=AppSettings(),
        )
        public = [name for name in dir(api) if not name.startswith("_")]
        assert "window" not in public
        for name in public:
            assert callable(getattr(api, name)), name
        api._syncing = True
        assert api.set_color(9, 8, 7) == {"ok": True}
        assert api._pending is None
    finally:
        bridge.stop()
