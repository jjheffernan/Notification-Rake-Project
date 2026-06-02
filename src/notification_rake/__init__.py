"""Notification Rake — vehicle listing ingestion and alerts."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

try:
    from importlib.metadata import version as _pkg_version
except ImportError:  # pragma: no cover
    from importlib_metadata import version as _pkg_version  # type: ignore[no-redef]

from notification_rake.config import settings

__version__ = _pkg_version("notification-rake")

ScriptFn = Callable[[], int]


def scripts_dir() -> Path:
    """Directory of function-based container scripts (see scripts/)."""
    return settings.scripts_dir


def _load_module(name: str) -> ModuleType:
    root = scripts_dir()
    path = root / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"script not found: {path}")
    spec = importlib.util.spec_from_file_location(f"rake_scripts.{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def script_names() -> list[str]:
    root = scripts_dir()
    if not root.is_dir():
        return []
    return sorted(p.stem for p in root.glob("*.py") if p.name != "__init__.py")


def run_script(name: str) -> int:
    """Run a function-based script from scripts/{name}.py."""
    module = _load_module(name)
    fn = getattr(module, "run", None)
    if not callable(fn):
        raise TypeError(f"scripts/{name}.py must define run() -> int")
    return int(fn())


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        names = ", ".join(script_names()) or "(none)"
        print(f"notification-rake {__version__}")
        print("usage: python -m notification_rake <command>")
        print(f"commands: {names}")
        return 0
    if args[0] in {"-V", "--version", "version"}:
        print(__version__)
        return 0
    try:
        return run_script(args[0])
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        print(f"available: {', '.join(script_names())}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
