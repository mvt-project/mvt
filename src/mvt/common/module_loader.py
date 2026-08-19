# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import importlib.metadata
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, Optional

from .module import MVTModule

MVT_CUSTOM_MODULES_ENV = "MVT_CUSTOM_MODULES"
MODULES_ENTRY_POINT_GROUP = "mvt.modules"
log = logging.getLogger(__name__)


class CustomModuleLoadError(Exception):
    pass


def _module_name_for_path(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    return f"_mvt_custom_module_{path.stem}_{digest}"


def _iter_module_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix != ".py":
            raise CustomModuleLoadError(
                f"Custom module file is not a Python file: {path}"
            )
        yield path
        return

    if path.is_dir():
        for child in sorted(path.iterdir()):
            if child.name.startswith("."):
                continue
            if child.name == "__init__.py":
                continue
            if child.is_file() and child.suffix == ".py":
                yield child
        return

    raise CustomModuleLoadError(f"Custom module path does not exist: {path}")


def _load_python_file(path: Path) -> ModuleType:
    module_name = _module_name_for_path(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CustomModuleLoadError(f"Unable to load custom module file: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise CustomModuleLoadError(
            f"Unable to import custom module {path}: {exc}"
        ) from exc

    return module


def discover_mvt_modules(module: ModuleType) -> list[type[MVTModule]]:
    modules = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if obj is MVTModule:
            continue
        if obj.__module__ != module.__name__:
            continue
        if not issubclass(obj, MVTModule):
            continue
        modules.append(obj)

    return modules


def load_custom_modules_from_path(path: str) -> list[type[MVTModule]]:
    custom_modules: list[type[MVTModule]] = []
    seen: set[tuple[str, str]] = set()
    resolved_path = Path(path).expanduser().resolve()

    for module_file in _iter_module_files(resolved_path):
        loaded_module = _load_python_file(module_file)
        for module_class in discover_mvt_modules(loaded_module):
            key = (str(module_file), module_class.__qualname__)
            if key in seen:
                continue
            seen.add(key)
            custom_modules.append(module_class)

    return custom_modules


def _module_key(module_class: type[MVTModule]) -> tuple[str, str]:
    try:
        source = str(Path(inspect.getfile(module_class)).resolve())
    except (OSError, TypeError):
        source = module_class.__module__
    return (source, module_class.__qualname__)


def load_installed_modules() -> list[type[MVTModule]]:
    """Load MVT modules registered by installed packages.

    Packages register modules in the ``mvt.modules`` entry-point group. Each
    entry point must resolve to an iterable of MVTModule subclasses, or to a
    callable which returns one. A broken entry point is skipped with a
    warning so that a faulty plugin package cannot break MVT.
    """
    try:
        entry_points = importlib.metadata.entry_points(group=MODULES_ENTRY_POINT_GROUP)
    except Exception as exc:
        log.warning(
            "Unable to discover installed module packages in entry-point group %s: %s",
            MODULES_ENTRY_POINT_GROUP,
            exc,
        )
        return []

    installed_modules: list[type[MVTModule]] = []
    ordered_entry_points = sorted(
        entry_points, key=lambda entry_point: (entry_point.name, entry_point.value)
    )
    for entry_point in ordered_entry_points:
        try:
            loaded = entry_point.load()
            if callable(loaded) and not isinstance(loaded, type):
                loaded = loaded()
            module_classes = list(loaded)
        except (Exception, SystemExit) as exc:
            log.warning(
                "Unable to load modules from entry point %s (%s): %s",
                entry_point.name,
                entry_point.value,
                exc,
            )
            continue

        for module_class in module_classes:
            if not (
                isinstance(module_class, type) and issubclass(module_class, MVTModule)
            ):
                log.warning(
                    "Entry point %s (%s) provided %r which is not an "
                    "MVTModule subclass",
                    entry_point.name,
                    entry_point.value,
                    module_class,
                )
                continue
            installed_modules.append(module_class)

    return installed_modules


def load_custom_modules(paths: Optional[Iterable[str]] = None) -> list[type[MVTModule]]:
    search_paths: list[str] = []
    env_path = os.environ.get(MVT_CUSTOM_MODULES_ENV)
    if env_path:
        search_paths.append(env_path)
    if paths:
        search_paths.extend(paths)

    custom_modules: list[type[MVTModule]] = []
    seen: set[tuple[str, str]] = set()

    for module_class in load_installed_modules():
        key = _module_key(module_class)
        if key in seen:
            continue
        seen.add(key)
        custom_modules.append(module_class)

    for path in search_paths:
        for module_class in load_custom_modules_from_path(path):
            key = _module_key(module_class)
            if key in seen:
                continue
            seen.add(key)
            custom_modules.append(module_class)

    return custom_modules


def module_supports_command(
    module_class: type[MVTModule],
    platform: str,
    command: str,
) -> bool:
    supported_commands = getattr(module_class, "supported_commands", None)
    if not supported_commands:
        log.warning(
            "Custom module %s has no supported_commands and will not be run. "
            "Declare the platform/command pairs it supports.",
            module_class.__name__,
        )
        return False

    return (platform, command) in {tuple(entry) for entry in supported_commands}
