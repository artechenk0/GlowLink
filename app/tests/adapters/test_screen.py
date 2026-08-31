"""Letterbox crop and mean RGB — no screen, no BLE."""

from ledsetup.domain.services.screen_processing import (
    average_content_rgb,
    crop_letterbox,
    rows_from_rgb_bytes,
)


def _solid(width: int, height: int, rgb: tuple[int, int, int]) -> list[list[tuple[int, int, int]]]:
    return [[rgb] * width for _ in range(height)]


def test_black_frame_is_zero() -> None:
    assert average_content_rgb(_solid(4, 4, (0, 0, 0))) == (0, 0, 0)


def test_solid_red() -> None:
    assert average_content_rgb(_solid(3, 3, (255, 0, 0))) == (255, 0, 0)


def test_letterbox_red_not_gray() -> None:
    black = (0, 0, 0)
    red = (255, 0, 0)
    rows = [
        [black, black, black, black],
        [black, black, black, black],
        [red, red, red, red],
        [red, red, red, red],
        [black, black, black, black],
        [black, black, black, black],
    ]
    cropped = crop_letterbox(rows)
    assert cropped == [[red, red, red, red], [red, red, red, red]]
    assert average_content_rgb(rows) == (255, 0, 0)


def test_pillarbox_blue() -> None:
    black = (0, 0, 0)
    blue = (0, 0, 255)
    rows = [
        [black, blue, blue, black],
        [black, blue, blue, black],
    ]
    assert average_content_rgb(rows) == (0, 0, 255)


def test_interior_dark_pixels_still_count() -> None:
    red = (255, 0, 0)
    dark = (0, 0, 0)
    rows = [
        [red, red, red, red],
        [red, dark, dark, red],
        [red, red, red, red],
    ]
    averaged = average_content_rgb(rows)
    assert averaged[0] < 255
    assert averaged[0] > 150
    assert averaged[1] == 0
    assert averaged[2] == 0


def test_rows_from_rgb_bytes_step() -> None:
    data = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 255])
    rows = rows_from_rgb_bytes(data, 2, 2, step=2)
    assert rows == [[(255, 0, 0)]]
