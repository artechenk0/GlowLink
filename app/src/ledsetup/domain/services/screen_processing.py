"""Average one RGB from a frame: crop letterbox bars, then mean of the rest."""

from __future__ import annotations

from collections.abc import Sequence

from ledsetup.domain.value_objects.rgb import RGB

__all__ = ["LETTERBOX_BLACK_MAX", "average_content_rgb", "crop_letterbox"]

LETTERBOX_BLACK_MAX = 16


def _is_black(pixel: RGB, black_max: int) -> bool:
    return pixel[0] <= black_max and pixel[1] <= black_max and pixel[2] <= black_max


def _row_is_bar(row: Sequence[RGB], black_max: int) -> bool:
    return bool(row) and all(_is_black(pixel, black_max) for pixel in row)


def _col_is_bar(rows: Sequence[Sequence[RGB]], column: int, black_max: int) -> bool:
    return all(_is_black(row[column], black_max) for row in rows)


def crop_letterbox(
    rows: Sequence[Sequence[RGB]],
    *,
    black_max: int = LETTERBOX_BLACK_MAX,
) -> list[list[RGB]]:
    """Drop uniform black bars on the four edges. Interior dark pixels stay."""
    if not rows or not rows[0]:
        return []
    height = len(rows)
    width = len(rows[0])
    top = 0
    while top < height and _row_is_bar(rows[top], black_max):
        top += 1
    bottom = height
    while bottom > top and _row_is_bar(rows[bottom - 1], black_max):
        bottom -= 1
    if top >= bottom:
        return []
    band = rows[top:bottom]
    left = 0
    while left < width and _col_is_bar(band, left, black_max):
        left += 1
    right = width
    while right > left and _col_is_bar(band, right - 1, black_max):
        right -= 1
    if left >= right:
        return []
    return [list(row[left:right]) for row in band]


def average_content_rgb(
    rows: Sequence[Sequence[RGB]],
    *,
    black_max: int = LETTERBOX_BLACK_MAX,
) -> RGB:
    """Letterbox crop, then integer mean. Empty or all-black → (0, 0, 0)."""
    cropped = crop_letterbox(rows, black_max=black_max)
    if not cropped:
        return (0, 0, 0)
    total_r = total_g = total_b = count = 0
    for row in cropped:
        for red, green, blue in row:
            total_r += red
            total_g += green
            total_b += blue
            count += 1
    if count == 0:
        return (0, 0, 0)
    return (total_r // count, total_g // count, total_b // count)


def rows_from_rgb_bytes(
    data: bytes,
    width: int,
    height: int,
    *,
    step: int = 1,
) -> list[list[RGB]]:
    """Row-major RGB bytes → subsampled rows. `step` ≥ 1 keeps every Nth pixel."""
    stride = max(1, step)
    rows: list[list[RGB]] = []
    expected = width * height * 3
    if width <= 0 or height <= 0 or len(data) < expected:
        return []
    for y in range(0, height, stride):
        row: list[RGB] = []
        for x in range(0, width, stride):
            index = (y * width + x) * 3
            row.append((data[index], data[index + 1], data[index + 2]))
        if row:
            rows.append(row)
    return rows
