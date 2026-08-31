from __future__ import annotations

from ledsetup.domain.value_objects.rgb import RGB, validate_rgb


def boost_max_value(rgb: RGB) -> RGB:
    validate_rgb(rgb)
    maximum = max(rgb)
    if maximum == 0:
        return rgb
    return tuple(round(channel * 255 / maximum) for channel in rgb)  # type: ignore[return-value]
