"""Screen → one RGB → strip. Stops without sending off (last color stays)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from ledsetup.application.services.throttle import ColorThrottle
from ledsetup.domain.value_objects.rgb import RGB

__all__ = ["DEFAULT_SYNC_INTERVAL", "run_screen_sync"]

DEFAULT_SYNC_INTERVAL = 0.1

SampleFn = Callable[[], RGB]
SendFn = Callable[[RGB], Awaitable[None]]
StopFn = Callable[[], bool]
TickFn = Callable[[RGB], None]


async def run_screen_sync(
    *,
    sample: SampleFn,
    send: SendFn,
    should_stop: StopFn,
    throttle: ColorThrottle | None = None,
    interval: float = DEFAULT_SYNC_INTERVAL,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    on_color: TickFn | None = None,
) -> RGB | None:
    """Loop until stop/deadline. Returns last RGB that was sampled. No off frame."""
    last: RGB | None = None
    while True:
        if should_stop() or (deadline is not None and clock() >= deadline):
            return last
        rgb = sample()
        last = rgb
        if on_color is not None:
            on_color(rgb)
        if throttle is None or throttle.allow(rgb):
            if throttle is not None:
                throttle.mark(rgb)
            await send(rgb)
        if should_stop() or (deadline is not None and clock() >= deadline):
            return last
        await sleep(interval)
