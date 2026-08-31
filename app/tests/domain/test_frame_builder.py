"""Protocol frame shape — no BLE adapter."""

from ledsetup.domain.services.frame_builder import (
    build_off_frame,
    build_rgb_frame,
    frame_to_hex,
    wrap_frame,
)

# Captured reverse examples (seq/checksum often ignored by devices).
OFF_EXAMPLE = bytes.fromhex("00 5b 80 00 00 0d 0e 0b 3b 24 00 00 00 00 00 00 00 32 00 00 91")
RGB_RED_EXAMPLE = bytes.fromhex("00 23 80 00 00 08 09 0B 31 FF 00 00 00 00 0F 3F")


def test_off_frame_matches_reverse_example() -> None:
    frame = build_off_frame(seq=0x5B)
    assert frame == OFF_EXAMPLE
    assert frame[9] == 0x24


def test_rgb_red_matches_reverse_example() -> None:
    frame = build_rgb_frame(255, 0, 0, seq=0x23)
    assert frame == RGB_RED_EXAMPLE
    assert len(frame) == 16
    assert frame[7:10] == bytes.fromhex("0B 31 FF")
    assert frame[10:12] == bytes.fromhex("00 00")


def test_rgb_channels_placed_after_0b31() -> None:
    frame = build_rgb_frame(1, 2, 3, seq=1)
    assert frame[8] == 0x31
    assert frame[9:12] == bytes([1, 2, 3])
    assert "FF" not in frame_to_hex(frame).split()[9:12]


def test_wrap_rejects_non_0b_body() -> None:
    try:
        wrap_frame(b"\x0a\x00", seq=1)
    except ValueError as exc:
        assert "0x0B" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_rgb_out_of_range() -> None:
    for bad in ((-1, 0, 0), (0, 256, 0), (0, 0, 1.5)):
        try:
            build_rgb_frame(*bad)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"expected error for {bad}")
