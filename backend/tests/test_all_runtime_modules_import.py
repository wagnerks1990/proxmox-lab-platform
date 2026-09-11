import importlib
from pathlib import Path


def test_every_runtime_module_imports():
    """Catch dormant modules whose imports have drifted out of the test graph."""
    app_root = Path(__file__).resolve().parents[1] / "app"
    failures: list[str] = []

    for path in sorted(app_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        relative = path.with_suffix("").relative_to(app_root.parent)
        module_name = ".".join(relative.parts)
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover - assertion reports exact import
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")

    assert failures == [], "Runtime module import failures:\n" + "\n".join(failures)
