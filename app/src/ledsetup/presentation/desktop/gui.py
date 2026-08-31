"""Desktop window via WebView2. Two steps: pick the strip, then set color."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

import webview

from ledsetup.application.app import GlowLinkApplication
from ledsetup.bootstrap import build_application
from ledsetup.presentation.desktop.async_bridge import AsyncBridge
from ledsetup.presentation.desktop.gui_api import JsApi

WEB_INDEX = Path(__file__).resolve().parents[2] / "web" / "index.html"
WEB_ICON = WEB_INDEX.parent / "glowlink.ico"
APP_TITLE = "GlowLink"
WINDOW_WIDTH = 820
WINDOW_HEIGHT = 820

__all__ = [
    "APP_TITLE",
    "WEB_ICON",
    "WEB_INDEX",
    "WINDOW_HEIGHT",
    "WINDOW_WIDTH",
    "AsyncBridge",
    "JsApi",
    "run_gui",
]


def run_gui(
    *,
    application: GlowLinkApplication | None = None,
    device_path: Path | None = None,
    settings_path: Path | None = None,
    auto_connect: bool = True,
) -> int:
    app = application or build_application(config_path=settings_path or device_path)
    bridge = AsyncBridge()
    api = JsApi(app, bridge)
    if not WEB_INDEX.is_file():
        print(f"нет UI-файла: {WEB_INDEX}")
        bridge.wait(app.close(), timeout=5)
        bridge.stop()
        return 1

    window = webview.create_window(
        APP_TITLE,
        url=str(WEB_INDEX),
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        background_color="#0b0c10",
        fullscreen=False,
        maximized=False,
        resizable=False,
    )
    if window is None:
        print("не удалось создать окно WebView")
        bridge.wait(app.close(), timeout=5)
        bridge.stop()
        return 1
    api._ui = window

    def _closed() -> None:
        with suppress(Exception):
            api.close()
        bridge.stop()

    window.events.closed += _closed
    _ = auto_connect
    try:
        webview.start(gui="edgechromium", icon=str(WEB_ICON) if WEB_ICON.is_file() else None)
    except Exception:
        # Fallback if WebView2/edgechromium is missing; pywebview picks another backend.
        webview.start(icon=str(WEB_ICON) if WEB_ICON.is_file() else None)
    return 0
