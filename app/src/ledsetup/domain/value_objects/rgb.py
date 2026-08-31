from __future__ import annotations

type RGB = tuple[int, int, int]


def validate_rgb(value: RGB) -> RGB:
    invalid = any(
        isinstance(channel, bool) or not isinstance(channel, int) or not 0 <= channel <= 255
        for channel in value
    )
    if len(value) != 3 or invalid:
        raise ValueError(f"RGB must contain three integer channels 0-255: {value!r}")
    return value
