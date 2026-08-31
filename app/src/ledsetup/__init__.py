"""GlowLink: one analog RGB LEDnetWF strip. Advertised name is not a stable ID."""

__version__ = "0.2.0"

# Last seen on this kit (2026-08-25). Name can change; use BLE address.
LAST_SEEN_NAME = "LEDnetWF0200086B1AAC"
LAST_SEEN_ADDRESS = "E4:98:BB:6B:1A:AC"
NAME_PREFIX_HINT = "LEDnetWF"
# Historical mistaken exact name — not a target.
OUTDATED_HYPOTHESIS_NAME = "LEDnetWF0200006B1AAC"


def has_lednetwf_prefix(name: str | None) -> bool:
    """Hint for scan highlighting. Not a unique lock: the user may pick any listed device."""
    n = (name or "").strip()
    return n.startswith(NAME_PREFIX_HINT)
