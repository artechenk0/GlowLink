"""Background asyncio loop used by the synchronous pywebview boundary."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncBridge:
    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self._stopped = False
        self._thread.start()

    def submit(self, coro: Coroutine[Any, Any, T]) -> Future[T]:
        if self._stopped:
            coro.close()
            raise RuntimeError("async bridge is stopped")
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    def wait(self, coro: Coroutine[Any, Any, T], timeout: float = 45.0) -> T:
        return self.submit(coro).result(timeout=timeout)

    def stop(self, timeout: float = 5.0) -> None:
        if self._stopped:
            return
        self._stopped = True

        async def cancel_pending() -> None:
            current = asyncio.current_task()
            pending = [task for task in asyncio.all_tasks() if task is not current]
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        future = asyncio.run_coroutine_threadsafe(cancel_pending(), self.loop)
        try:
            future.result(timeout=timeout)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self._thread.join(timeout=timeout)
            if not self._thread.is_alive():
                self.loop.close()
