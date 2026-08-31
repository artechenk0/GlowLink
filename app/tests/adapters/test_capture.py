"""MSS adapter behavior without live capture."""

from fake_screen import SolidGrabber
from ledsetup.adapters.screen.mss_capture import MssGrabber, monitors_from_mss_dicts
from ledsetup.application.models import MonitorInfo


def test_mss_dicts_skip_virtual_desktop() -> None:
    raw = [
        {"left": 0, "top": 0, "width": 3200, "height": 1080},
        {"left": 0, "top": 0, "width": 1920, "height": 1080},
        {"left": 1920, "top": 0, "width": 1280, "height": 720},
    ]
    found = monitors_from_mss_dicts(raw)
    assert len(found) == 2
    assert found[0].is_primary is True
    assert found[0].id == "0,0,1920x1080"
    assert found[1].index == 2
    assert "основной" in found[0].label
    assert "основной" not in found[1].label


def test_mss_dicts_use_is_primary_flag() -> None:
    raw = [
        {"left": 0, "top": 0, "width": 3200, "height": 1200},
        {
            "left": 0,
            "top": 0,
            "width": 1920,
            "height": 1200,
            "is_primary": True,
            "name": "BOE PnP Monitor",
        },
    ]
    found = monitors_from_mss_dicts(raw)
    assert found[0].is_primary is True
    assert found[0].width == 1920


class _TestGrabber(MssGrabber):
    def __init__(self, solid: SolidGrabber) -> None:
        super().__init__()
        self.solid = solid

    def grab_rgb(self, monitor: MonitorInfo) -> tuple[int, int, bytes]:
        return self.solid.grab_rgb(monitor)


def test_average_solid_red() -> None:
    solid = SolidGrabber()
    assert _TestGrabber(solid).average(solid.monitors()[0]) == (255, 0, 0)


def test_average_boosts_dim_red() -> None:
    solid = SolidGrabber((40, 0, 0))
    assert _TestGrabber(solid).average(solid.monitors()[0]) == (255, 0, 0)


def test_average_black_stays_off() -> None:
    solid = SolidGrabber((0, 0, 0))
    assert _TestGrabber(solid).average(solid.monitors()[0]) == (0, 0, 0)
