# Device compatibility

Only results confirmed on physical hardware are listed here. A similar name, UUID, or protocol
hypothesis does not imply compatibility. The BLE address identifies the selected device; its
advertised name is only a hint.

## Verified controller

| Model / kit | Strip type | UUID: service / write / notify | Verified commands | Date | Status |
|---|---|---|---|---|---|
| Smartbuy `SBL-RGBW-KIT-75` (Zengge LEDnetWF) | Analogue RGB, `+ / R / G / B`, one shared colour | `FFFF` / `FF01` / `FF02` | RGB `0B 31`, off `0B 3B 24` | 2026-08-25 | Supported |

Full UUIDs: `0000FFFF-0000-1000-8000-00805F9B34FB`,
`0000FF01-0000-1000-8000-00805F9B34FB`,
`0000FF02-0000-1000-8000-00805F9B34FB`.

`on` and HSV have not been verified and are not supported. Add a new row only after a manual run
records the date, commands, and result. See [protocol notes](protocol-notes.en.md) for GATT and
frame details.

## Adding a result

Save a reproducible manual run in `docs/hardware-tests/`: the model and strip type, commands,
date, observed result, and limitations. Then add a concise row to the table above.
