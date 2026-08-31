# Product scope

GlowLink is a Windows application for controlling **one** analogue RGB strip over BLE. The
verified controller type and command status are listed in the
[compatibility matrix](device-compatibility.en.md).

## What is available

- Discovering and selecting a controller by BLE address.
- Connecting, turning the strip off, and setting one solid RGB colour for the whole strip.
- Sending the average colour of one monitor to the whole strip.

## What is outside the product

- Addressable strips, individual LEDs, segments, zones, LED count, chip type, and smear.
- Multiple independently controlled strips.
- Other operating systems or controller types without separate confirmation.
- Ambilight and effects that depend on LED position: synchronisation sends one average colour,
  not a screen map.

## Extending the scope

A new strip or controller type, colour model, multiple devices, operating system, or spatial
effect expands the scope. Before implementation, update this document, make an ADR, and define a
verification method in the compatibility matrix. An unverified command, UUID, or similar device
name does not establish support.
