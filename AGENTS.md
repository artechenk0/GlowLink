# Repository Guidelines

## Project Structure & Module Organization

The application lives in `app/` and uses a `src` layout. Production Python code is in
`app/src/ledsetup/`; the CLI entry point is `cli.py`, while `gui.py`, `gui_api.py`, and
`gui_bridge.py` support the desktop interface. BLE protocol and device behavior belong in
`ble.py`, `protocol.py`, and `device.py`; screen-color synchronization is implemented in
`capture.py` and `sync_loop.py`. Web UI assets are in `app/src/ledsetup/web/`.

Tests are in `app/tests/`, with matching `test_<module>.py` names. Shared BLE and screen
test doubles are `fake_ble.py` and `fake_screen.py`. Keep protocol research and technical
notes in `docs/`.

## Build, Test, and Development Commands

Run commands from `app/`:

```powershell
python -m pip install -e ".[test]"  # install app plus test and quality tools
python -m pytest                     # run the complete test suite
python -m ruff check src tests       # lint and check import ordering
python -m mypy src                   # run strict type checking
python -m ledsetup --help            # inspect the installed CLI
```

Use Python 3.11 or newer. Install dependencies into a virtual environment rather than
committing generated environments or build output.

## Coding Style & Naming Conventions

Use four-space indentation, type annotations for all production code, and idiomatic
snake_case for modules, functions, variables, and test names. Classes use PascalCase;
constants use UPPER_SNAKE_CASE. Keep lines at or below 100 characters. Ruff enforces
error, import, modern-Python, bugbear, simplification, and Ruff-specific rules; mypy runs
in strict mode. Prefer focused modules and explicit error handling around BLE and GUI
boundaries.

## Testing Guidelines

Write pytest tests alongside the relevant behavior as `test_<feature>.py`; name test
functions `test_<expected_behavior>()`. Exercise new protocol commands, settings changes,
and synchronization control paths without requiring physical BLE hardware by using the
existing fakes. Run pytest, Ruff, and mypy before submitting changes; this repository has
no separate coverage threshold configured.

## Commit & Pull Request Guidelines

Recent history uses concise imperative subjects, such as `Enhance LEDSetup functionality`
and `Remove project documentation and specs`. Keep each commit narrow and describe the
user-visible change. Pull requests should explain the behavior change, list validation
commands run, link any related issue, and include screenshots for GUI or web-asset changes.
Call out device-specific assumptions and any testing that requires real hardware.
