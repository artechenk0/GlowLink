"""Fake monitor grabber for tests — no live screen."""

from __future__ import annotations

from ledsetup.adapters.screen.mss_capture import MonitorInfo
from ledsetup.domain.value_objects.rgb import RGB


class SolidGrabber:
    def __init__(self, rgb: RGB = (255, 0, 0), *, width: int = 8, height: int = 8) -> None:
        self.rgb = rgb
        self.width = width
        self.height = height
        self.calls = 0

    def monitors(self) -> list[MonitorInfo]:
        return [
            MonitorInfo(
                id="0,0,1920x1080",
                index=1,
                left=0,
                top=0,
                width=1920,
                height=1080,
                is_primary=True,
                label="Монитор 1 · 1920×1080 (основной)",
            )
        ]

    def grab_rgb(self, monitor: MonitorInfo) -> tuple[int, int, bytes]:
        self.calls += 1
        red, green, blue = self.rgb
        pixel = bytes((red, green, blue))
        return self.width, self.height, pixel * (self.width * self.height)
