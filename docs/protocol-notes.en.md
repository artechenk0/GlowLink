# Low-level protocol notes

User-facing device status and UUIDs are in the [compatibility matrix](device-compatibility.en.md).
This document contains LEDnetWF research observations only; it is not a specification. To control
a strip, start with the [main README](../README.en.md), not this document.

## GATT and transport

On the verified kit, FF01 supports `write` and `write-without-response`; the application chooses
the latter. Writing with response during synchronisation at about 10 Hz produced WinRT
`characteristic 0016: Unreachable`. Notify was enabled on FF02 before writing; whether CCCD is
required is unknown.

Services `1800`, `1801`, and vendor service `FE00` with `FF22` (handle 13) and `FF11` (handle
16) were also found. The application does not write to them.

## Frames

The single-fragment format is `[flags] [seq] 80 00 00 [len] [len+1] [0B …] [checksum?]`.
Sequence, checksum, and padding are not yet confirmed.

| Operation | Body | Status |
|---|---|---|
| RGB | `0B 31 R G B 00 00 0F` | visually verified |
| off | `0B 3B 24` + trailer `00 00 00 00 00 00 00 32 00 00` | visually verified |
| on | `0B 3B 23` + same trailer | hypothesis |
| HSV | `0B 3B A1 …` | hypothesis |

After blue RGB, FF02 sent the JSON notification
`{"code":0,"payload":"810823612301008E70000300F022"}`; its meaning is unknown. Do not send chip
type, LED count, or smear values copied from reverse engineering of addressable firmware.

Sources: [zengge_lednetwf](https://github.com/8none1/zengge_lednetwf),
[lednetwf_ble](https://github.com/8none1/lednetwf_ble). Testing was performed on 2026-08-25.
