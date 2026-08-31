"""Windows screen grab via mss. One monitor → RGB bytes for averaging."""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from typing import Any

from ledsetup.application.errors import CaptureError
from ledsetup.application.models import MonitorInfo
from ledsetup.domain.services.color_normalizer import boost_max_value
from ledsetup.domain.services.screen_processing import average_content_rgb, rows_from_rgb_bytes
from ledsetup.domain.value_objects.rgb import RGB

__all__ = [
    "DOWNSAMPLE_MAX_SIDE",
    "MonitorInfo",
]

DOWNSAMPLE_MAX_SIDE = 160


def monitor_id(left: int, top: int, width: int, height: int) -> str:
    return f"{left},{top},{width}x{height}"


def _label(index: int, width: int, height: int, *, primary: bool) -> str:
    extra = " (основной)" if primary else ""
    return f"Монитор {index} · {width}×{height}{extra}"


def _capture_fail(prefix: str, exc: BaseException) -> str:
    detail = str(exc).strip() or type(exc).__name__
    return f"{prefix}: {detail}"


def monitors_from_mss_dicts(raw: Sequence[Mapping[str, Any]]) -> list[MonitorInfo]:
    """`raw[0]` is the virtual desktop; the rest are physical displays."""
    physical = list(raw[1:]) if len(raw) > 1 else []
    if not physical:
        raise CaptureError("не видно ни одного монитора")
    found: list[MonitorInfo] = []
    primary_assigned = False
    for i, item in enumerate(physical, start=1):
        left = int(item["left"])
        top = int(item["top"])
        width = int(item["width"])
        height = int(item["height"])
        if "is_primary" in item:
            is_primary = bool(item["is_primary"]) and not primary_assigned
        else:
            is_primary = left == 0 and top == 0 and not primary_assigned
        if is_primary:
            primary_assigned = True
        found.append(
            MonitorInfo(
                id=monitor_id(left, top, width, height),
                index=i,
                left=left,
                top=top,
                width=width,
                height=height,
                is_primary=is_primary,
                label=_label(i, width, height, primary=is_primary),
            )
        )
    if not any(item.is_primary for item in found):
        first = found[0]
        found[0] = MonitorInfo(
            id=first.id,
            index=first.index,
            left=first.left,
            top=first.top,
            width=first.width,
            height=first.height,
            is_primary=True,
            label=_label(first.index, first.width, first.height, primary=True),
        )
    return found


def _box_for_monitor(raw: Sequence[Mapping[str, Any]], monitor: MonitorInfo) -> dict[str, int]:
    physical = list(raw[1:]) if len(raw) > 1 else []
    if 1 <= monitor.index <= len(physical):
        live = physical[monitor.index - 1]
        return {
            "left": int(live["left"]),
            "top": int(live["top"]),
            "width": int(live["width"]),
            "height": int(live["height"]),
        }
    return {
        "left": monitor.left,
        "top": monitor.top,
        "width": monitor.width,
        "height": monitor.height,
    }


class MssGrabber:
    """GDI handles from mss are per-thread. The GUI lists monitors on the UI
    thread; sync grabs on a worker. Sharing one MSS instance fails the grab.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    def _mss(self) -> Any:
        sct = getattr(self._local, "sct", None)
        if sct is not None:
            return sct
        try:
            from mss import MSS
        except ImportError as exc:
            raise CaptureError(
                "нет библиотеки захвата экрана (mss). Установите зависимости приложения."
            ) from exc
        try:
            self._local.sct = MSS()
        except Exception as exc:
            raise CaptureError(_capture_fail("не удалось открыть захват экрана", exc)) from exc
        return self._local.sct

    def monitors(self) -> list[MonitorInfo]:
        try:
            raw = list(self._mss().monitors)
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError(_capture_fail("не удалось получить список мониторов", exc)) from exc
        return monitors_from_mss_dicts(raw)

    def grab_rgb(self, monitor: MonitorInfo) -> tuple[int, int, bytes]:
        sct = self._mss()
        try:
            raw = list(sct.monitors)
        except Exception as exc:
            raise CaptureError(_capture_fail("не удалось получить список мониторов", exc)) from exc
        box = _box_for_monitor(raw, monitor)
        try:
            shot = sct.grab(box)
        except Exception as exc:
            raise CaptureError(_capture_fail("захват экрана не удался", exc)) from exc
        width = int(shot.width)
        height = int(shot.height)
        rgb = bytes(shot.rgb)
        if width <= 0 or height <= 0 or len(rgb) < width * height * 3:
            raise CaptureError("захват экрана вернул пустой кадр")
        return width, height, rgb[: width * height * 3]

    def average(self, monitor: MonitorInfo) -> RGB:
        width, height, data = self.grab_rgb(monitor)
        step = max(1, max(width, height) // DOWNSAMPLE_MAX_SIDE)
        rows = rows_from_rgb_bytes(data, width, height, step=step)
        if not rows:
            raise CaptureError("захват экрана вернул пустой кадр")
        return boost_max_value(average_content_rgb(rows))
