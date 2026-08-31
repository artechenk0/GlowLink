import ast
from pathlib import Path

SRC = Path(__file__).parents[1] / "src" / "ledsetup"


def imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def assert_layer_has_no_imports(layer: str, forbidden: tuple[str, ...]) -> None:
    violations: list[str] = []
    for path in (SRC / layer).rglob("*.py"):
        for module in imported_modules(path):
            if module.startswith(forbidden):
                violations.append(f"{path.relative_to(SRC)} -> {module}")
    assert violations == []


def test_domain_is_independent() -> None:
    assert_layer_has_no_imports(
        "domain",
        (
            "ledsetup.application",
            "ledsetup.adapters",
            "ledsetup.presentation",
            "ledsetup.bootstrap",
        ),
    )


def test_application_does_not_depend_on_outer_layers() -> None:
    assert_layer_has_no_imports(
        "application",
        ("ledsetup.adapters", "ledsetup.presentation", "ledsetup.bootstrap"),
    )


def test_presentation_uses_application_not_concrete_adapters() -> None:
    assert_layer_has_no_imports("presentation", ("ledsetup.adapters",))


def test_removed_parallel_architecture_does_not_return() -> None:
    removed_files = [
        SRC / "adapters" / "storage" / "settings_store.py",
        SRC / "adapters" / "storage" / "device_store.py",
    ]
    assert not any(path.exists() for path in removed_files)
    assert not list((SRC / "application" / "use_cases").glob("*.py"))
    assert not list((SRC / "application" / "dto").glob("*.py"))
