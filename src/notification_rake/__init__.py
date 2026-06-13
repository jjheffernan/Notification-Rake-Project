"""Function-based container scripts for notification-rake.

Layout mirrors ``src/notification_rake/ingestion/``:

- ``ingest/`` — per-source and per-route ingest wrappers (+ ``_common.py``)
- ``catalog/`` — seed, normalize, upsert helpers
- ``ops/`` — health checks, Hasura, scheduled jobs

Each script defines ``run() -> int``. Optional ``ALIASES`` keeps legacy CLI names
(e.g. ``ingest_all`` → ``ingest.all``).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

try:
    from importlib.metadata import version as _pkg_version
except ImportError:  # pragma: no cover
    from importlib_metadata import version as _pkg_version  # type: no-redef

from notification_rake.config import settings

__version__ = _pkg_version("notification-rake")

ScriptFn = Callable[[], int]

_script_registry: dict[str, Path] | None = None


def scripts_dir() -> Path:
    """Directory of function-based container scripts."""
    return settings.scripts_dir


def _ensure_scripts_import_path() -> None:
    root = str(scripts_dir().resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


def _load_module_from_path(module_name: str, path: Path) -> ModuleType:
    _ensure_scripts_import_path()
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _script_paths() -> list[Path]:
    root = scripts_dir()
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "__init__.py" or path.name.startswith("_"):
            continue
        paths.append(path)
    return paths


def _canonical_name(path: Path) -> str:
    return ".".join(path.relative_to(scripts_dir()).with_suffix("").parts)


def _aliases_for_module(module: ModuleType) -> list[str]:
    aliases = getattr(module, "ALIASES", ())
    if isinstance(aliases, str):
        return [aliases]
    return [str(name) for name in aliases]


def _build_registry() -> dict[str, Path]:
    registry: dict[str, Path] = {}
    for path in _script_paths():
        canonical = _canonical_name(path)
        module_name = f"rake_scripts.{canonical.replace('.', '_')}"
        module = _load_module_from_path(module_name, path)
        registry[canonical] = path
        for alias in _aliases_for_module(module):
            registry[alias] = path
    return registry


def script_registry() -> dict[str, Path]:
    global _script_registry
    if _script_registry is None:
        _script_registry = _build_registry()
    return _script_registry


def script_names() -> list[str]:
    return sorted(script_registry())


def run_script(name: str) -> int:
    """Run a script by canonical or alias name."""
    registry = script_registry()
    path = registry.get(name)
    if path is None:
        raise FileNotFoundError(f"script not found: {name}")
    canonical = _canonical_name(path)
    module = _load_module_from_path(f"rake_scripts.{canonical.replace('.', '_')}", path)
    fn = getattr(module, "run", None)
    if not callable(fn):
        raise TypeError(f"{path} must define run() -> int")
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
