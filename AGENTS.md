# Repository Guidelines

## Project standards

Shared project recommendations for people and agent environments are in
`docs/standards/README.md`. Before changing code, documentation, workflow, or architecture, read
the applicable standard there. Keep this file for mandatory repository constraints; do not copy
the standards into agent-specific instructions.

Before drafting, reviewing, or revising any repository text, follow
`.agents/documentation-editor/SKILL.md` and `docs/standards/writing.md`. This includes
documentation, skills, UI and CLI copy, messages, comments, and changelog entries.

## Structure

The Python package is `app/src/ledsetup/`; tests are `app/tests/`; desktop assets are
`app/src/ledsetup/web/`; project documentation is `docs/`.

Keep entry points and UI adapters in `cli.py`, `gui.py`, `gui_api.py`, `gui_bridge.py`, and
`web/`. Put shared user actions in an application-scenario module when they serve more than
one UI. Put protocol frames in `protocol.py`, BLE/GATT transport in `ble.py`, held links in
`session.py`, and OS integration in adapters such as `capture.py` and `paths.py`. UI must not
access `BleakClient` or GATT details directly.

## Development

Run from `app/` with the repository virtual environment. Python 3.12 is required by
`app/pyproject.toml`; do not rely on a globally installed `python` command:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[test]"
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m mypy src
.venv\Scripts\python.exe -m ledsetup --help
```

In PowerShell, activate the environment with `.venv\Scripts\Activate.ps1` when convenient;
otherwise use the explicit `.venv\Scripts\python.exe` path above. All Python commands and
tests must run from `app/`.

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
