# Repository Guidelines

## Structure

The Python package is `app/src/ledsetup/`; tests are `app/tests/`; desktop assets are
`app/src/ledsetup/web/`; project documentation is `docs/`.

Keep entry points and UI adapters in `cli.py`, `gui.py`, `gui_api.py`, `gui_bridge.py`, and
`web/`. Put shared user actions in an application-scenario module when they serve more than
one UI. Put LEDnetWF frames in `protocol.py`, BLE/GATT transport in `ble.py`, held links in
`session.py`, and OS integration in adapters such as `capture.py` and `paths.py`. UI must not
access `BleakClient` or GATT details directly.

## Development

Run from `app/` with Python 3.11+:

```powershell
python -m pip install -e ".[test]"
python -m pytest
python -m ruff check src tests
python -m mypy src
python -m ledsetup --help
```

Use four spaces, annotations in production code, snake_case names, PascalCase classes,
UPPER_SNAKE_CASE constants, and lines up to 100 characters.

## Tests and documentation

Add unit tests as `app/tests/test_<module>.py`; use `fake_ble.py` and `fake_screen.py` so they
need no hardware. Integration tests cover scenario-to-adapter boundaries with fakes. Record
manual device runs under `docs/hardware-tests/` and summarize verified outcomes in
`docs/device-compatibility.md`.

Update documentation whenever CLI, protocol, compatibility, or UX changes. An experimental
command remains experimental until it is reproducibly checked on hardware and the protocol
notes and compatibility matrix are updated.

## Contributions

Use branches named `codex/<short-task>`. Keep one task per logical PR and do not mix a
refactor with a feature change. PRs state the behaviour, validation commands, relevant issue,
and any required hardware test or UI screenshot.
