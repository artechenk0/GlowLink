from __future__ import annotations


def normalize_ble_address(value: str) -> str:
    cleaned = value.strip().upper().replace("-", ":")
    if ":" in cleaned:
        parts = [part for part in cleaned.split(":") if part]
        valid = all(len(part) == 2 and all(c in "0123456789ABCDEF" for c in part) for part in parts)
        if len(parts) == 6 and valid:
            return ":".join(parts)
    hex_only = "".join(c for c in cleaned if c in "0123456789ABCDEF")
    if len(hex_only) == 12:
        return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))
    raise ValueError(f"некорректный BLE-адрес: {value!r}")


def ble_addresses_equal(left: str, right: str) -> bool:
    try:
        return normalize_ble_address(left) == normalize_ble_address(right)
    except ValueError:
        return left.strip().upper() == right.strip().upper()
