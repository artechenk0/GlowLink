"""Limit BLE color writes so dragging a picker does not flood the link."""

from __future__ import annotations

import time
from collections.abc import Callable

from ledsetup.domain.value_objects.rgb import RGB

DEFAULT_MIN_INTERVAL = 0.1


class ColorThrottle:
    def __init__(
        self,
        min_interval: float = DEFAULT_MIN_INTERVAL,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._last_at = 0.0
        self._last_rgb: RGB | None = None

    def delay(self) -> float:
        wait = self.min_interval - (self._clock() - self._last_at)
        return wait if wait > 0 else 0.0

    def allow(self, rgb: RGB) -> bool:
        if rgb == self._last_rgb:
            return False
        return self.delay() <= 0.0

    def mark(self, rgb: RGB) -> None:
        self._last_at = self._clock()
        self._last_rgb = rgb

    def clear_last(self) -> None:
        self._last_rgb = None
