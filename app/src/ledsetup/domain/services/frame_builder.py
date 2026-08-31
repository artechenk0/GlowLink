"""Confirmed power and solid-RGB frame builder for the supported protocol."""

from __future__ import annotations

from ledsetup.domain.value_objects.rgb import validate_rgb

RGB_OFF_VISUALLY_CONFIRMED = True
RGB_OFF_NOTE = (
    "RGB 0B 31 and off 0B 3B 24 visually confirmed on this analog kit "
    "(seq/checksum and extra bytes TBD)"
)
_RGB_TRAILER = bytes.fromhex("00 00 0F")
_POWER_TAIL = bytes.fromhex("00 00 00 00 00 00 00 32 00 00")


def _checksum_after_0b(body_including_0b: bytes) -> int:
    if not body_including_0b or body_including_0b[0] != 0x0B:
        raise ValueError("body must start with 0x0B")
    return sum(body_including_0b[1:]) & 0xFF


def wrap_frame(body_including_0b: bytes, seq: int = 1) -> bytes:
    if not body_including_0b or body_including_0b[0] != 0x0B:
        raise ValueError("payload body must start with 0x0B")
    sequence = seq & 0xFF
    length = len(body_including_0b)
    header = bytes([0x00, sequence, 0x80, 0x00, 0x00, length, length + 1])
    return header + body_including_0b + bytes([_checksum_after_0b(body_including_0b)])


def build_off_frame(seq: int = 1) -> bytes:
    body = bytes([0x0B, 0x3B, 0x24]) + _POWER_TAIL
    return wrap_frame(body, seq=seq)


def build_rgb_frame(red: int, green: int, blue: int, seq: int = 1) -> bytes:
    validate_rgb((red, green, blue))
    body = bytes([0x0B, 0x31, red, green, blue]) + _RGB_TRAILER
    return wrap_frame(body, seq=seq)


def frame_to_hex(frame: bytes) -> str:
    return " ".join(f"{byte:02X}" for byte in frame)
