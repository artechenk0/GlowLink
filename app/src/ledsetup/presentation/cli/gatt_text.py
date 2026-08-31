"""Human-readable GATT dump shared by CLI, terminal menu, and the desktop window."""

from __future__ import annotations

from ledsetup.application.models import GattSnapshot


def format_gatt_lines(snapshot: GattSnapshot, *, include_expected: bool = False) -> list[str]:
    lines = [f"GATT {snapshot.address} (UUID FFFF/FF01/FF02 сверены на этом ките):"]
    for svc_uuid, chars in snapshot.services:
        lines.append(f"  service {svc_uuid}")
        for char in chars:
            props = ",".join(char.properties) or "-"
            handle = f" handle={char.handle}" if char.handle is not None else ""
            lines.append(f"    char {char.uuid} props={props}{handle}")
    lines.append(
        "совпадение UUID: "
        f"service={'да' if snapshot.service_matched else 'нет'}, "
        f"write={'да' if snapshot.write_matched else 'нет'}, "
        f"notify={'да' if snapshot.notify_matched else 'нет'}"
    )
    if include_expected:
        lines.append("ожидаемые роли: service FFFF; write FF01; notify FF02")
    return lines
