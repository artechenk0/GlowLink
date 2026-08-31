"""RGB parsing and normalization helpers."""

from __future__ import annotations

from ledsetup.domain.value_objects.rgb import RGB, validate_rgb


def check_rgb(red: int, green: int, blue: int) -> None:
    validate_rgb((red, green, blue))


def coerce_rgb_byte(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"канал RGB должен быть 0–255, получено {value!r}")
    number = int(value)
    if number < 0 or number > 255:
        raise ValueError(f"канал RGB должен быть 0–255, получено {number}")
    return number


def parse_rgb_channel(value: str) -> int:
    text = value.strip()
    try:
        number = int(text, 10)
    except ValueError as exc:
        raise ValueError(f"ожидалось целое 0–255, получено {value!r}") from exc
    if number < 0 or number > 255:
        raise ValueError(f"канал RGB должен быть 0–255, получено {number}")
    return number


def parse_rgb_triple(raw: str) -> RGB:
    parts = raw.strip().split()
    if len(parts) != 3:
        raise ValueError("ожидалось три числа 0–255, например 255 0 0")
    return (
        parse_rgb_channel(parts[0]),
        parse_rgb_channel(parts[1]),
        parse_rgb_channel(parts[2]),
    )


def rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"
