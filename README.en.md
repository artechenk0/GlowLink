# GlowLink

**English** | [Русский](README.md)

GlowLink is a Windows app for controlling **one analogue RGB LED strip** with a Zengge LEDnetWF
BLE controller. You can select a controller, turn the strip on or off, set one colour, and send
the average colour of one monitor to it.

> Addressable strips, zones, independently controlled devices, and perimeter Ambilight are not
> supported. See the complete boundaries in the [product scope](docs/product-scope.md).

## Get started

### Packaged app

Download `GlowLink.exe` from [Releases](../../releases) and run it. Python is not required. The
interface needs Microsoft Edge WebView2 Runtime, which is usually installed on Windows 10 and 11.

1. Turn on Bluetooth in Windows and power the controller.
2. Open GlowLink and select **Find strip**.
3. Select a discovered device and connect.
4. Choose a colour, turn the strip off, or start screen synchronisation.

GlowLink saves the **BLE address**, not the name: advertised names can change. If connecting
fails, close the ZENGGE app and disconnect the controller in Windows Settings—it may be in use by
another app.

### Run from source

You need Windows with Bluetooth LE, Python 3.12+, and a compatible controller with an analogue
RGB strip.

```powershell
cd app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
ledsetup
```

## Command line

First discover and save the controller. The commands below then use the saved address.

```powershell
ledsetup scan
ledsetup color 255 40 40
ledsetup off
ledsetup sync --monitor 1
```

For a one-off command, pass the address explicitly:

```powershell
ledsetup color 255 40 40 --address E4:98:BB:6B:1A:AC
```

| Command | Purpose |
| --- | --- |
| `ledsetup` or `ledsetup gui` | Open the control window. |
| `ledsetup scan` | Discover nearby BLE devices and choose a controller. |
| `ledsetup color R G B` | Set one colour for the entire strip. |
| `ledsetup off` | Turn the strip off. |
| `ledsetup sync --monitor 1` | Send the chosen monitor's average colour; stop with `Ctrl+C`. |
| `ledsetup gatt` | Show GATT services for diagnostics. |

`sync` does not create a perimeter lighting effect: the whole strip receives one average colour.
The `on` and `color --hsv` commands are experimental and should not be relied on for control.

## Compatibility and help

RGB and `off` have only been visually verified on Smartbuy `SBL-RGBW-KIT-75` (Zengge LEDnetWF).
See the verified status and limitations in the [compatibility matrix](docs/device-compatibility.md).
Technical GATT and frame observations are in the [protocol notes](docs/protocol-notes.md).

The rest of the documentation is listed in the [documentation index](docs/README.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks, branches, and pull requests. The project
is licensed under the [MIT License](LICENSE).
