"""Sync loop duration and stop — no BLE, no screen."""

import asyncio

from ledsetup.application.services.screen_sync import run_screen_sync
from ledsetup.domain.value_objects.rgb import RGB


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_stopped_loop_does_not_write() -> None:
    writes: list[RGB] = []

    async def send(rgb: RGB) -> None:
        writes.append(rgb)

    last = asyncio.run(
        run_screen_sync(
            sample=lambda: (255, 0, 0),
            send=send,
            should_stop=lambda: True,
        )
    )
    assert last is None
    assert writes == []


def test_seconds_deadline_stops() -> None:
    writes: list[RGB] = []
    ticks: list[RGB] = []
    clock = _Clock()

    async def send(rgb: RGB) -> None:
        writes.append(rgb)

    async def sleep(delay: float) -> None:
        clock.now += delay

    last = asyncio.run(
        run_screen_sync(
            sample=lambda: (10, 20, 30),
            send=send,
            should_stop=lambda: False,
            throttle=None,
            interval=0.1,
            deadline=0.25,
            clock=clock,
            sleep=sleep,
            on_color=ticks.append,
        )
    )
    assert last == (10, 20, 30)
    assert len(ticks) >= 2
    assert clock.now >= 0.2
    assert writes == ticks
