# Contributing to GlowLink

**English** | [Русский](CONTRIBUTING.md)

Thank you for contributing. One pull request should address one clear task and must not combine a
feature with an unrelated refactor.

## Quick start

Python 3.12+ is required. Run every command below from the `app/` directory.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest
python -m ruff format --check src tests
python -m ruff check src tests
python -m mypy src
```

For a coverage report, also run:

```powershell
python -m pytest --cov=ledsetup --cov-report=term-missing
```

Install local checks once from the repository root:

```powershell
python -m pre_commit install
```

Run all hooks manually with `python -m pre_commit run --all-files`. They shorten feedback, but
CI in the pull request is still required.

## Workflow

1. Create a short-lived branch from current `main`. In Codex, use the `codex/` prefix; see
   [Gitflow](docs/standards/gitflow.md) for other branch conventions.
2. Make the change and add tests. Use the fakes in `app/tests/` for BLE and screen capture, so
   tests do not need hardware.
3. Run the relevant checks above.
4. Open a pull request to `main`. Describe the behaviour, related issue (if any), checks, and
   known limitations.

Include a screenshot for GUI changes. For BLE, state the device model, commands, and manual test
result. Do not claim a new device is supported merely because its name or UUID looks similar, or
because a fake-based test passes.

## When a specification is required

Create one record in `docs/specs/<slug>/` when user behaviour, CLI, GUI, protocol,
compatibility, or architecture boundaries change. The full process is in the
[SDD guide](docs/standards/sdd.md). Small text corrections and mechanical changes that do not
change behaviour do not require a specification.

## Documentation and decisions

Update documentation with the change:

| Change | Where to record it |
| --- | --- |
| User workflow or CLI | `README.md` and, where needed, `docs/README.md` |
| Product boundary | `docs/product-scope.md` |
| Verified protocol or device | `docs/protocol-notes.md` and `docs/device-compatibility.md` |
| Material architecture decision | A new ADR in `docs/decisions/` |

Record a new hardware result in `docs/hardware-tests/`, then summarise it in the compatibility
matrix. The complete shared rules are in the [project standards](docs/standards/README.md); the
mandatory minimum for agents is in [AGENTS.md](AGENTS.md).
