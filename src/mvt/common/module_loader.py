# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import importlib.util
import inspect
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, Optional

from .module import MVTModule

MVT_CUSTOM_MODULES_ENV = "MVT_CUSTOM_MODULES"


class CustomModuleLoadError(Exception):
    pass


def _module_name_for_path(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    return f"_mvt_custom_module_{path.stem}_{digest}"


def _iter_module_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix != ".py":
            raise CustomModuleLoadError(f"Custom module file is not a Python file: {path}")
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
        raise CustomModuleLoadError(f"Unable to import custom module {path}: {exc}") from exc

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


def load_custom_modules(paths: Optional[Iterable[str]] = None) -> list[type[MVTModule]]:
    search_paths: list[str] = []
    env_path = os.environ.get(MVT_CUSTOM_MODULES_ENV)
    if env_path:
        search_paths.append(env_path)
    if paths:
        search_paths.extend(paths)

    custom_modules: list[type[MVTModule]] = []
    seen: set[tuple[str, str]] = set()
    for path in search_paths:
        for module_class in load_custom_modules_from_path(path):
            source = Path(inspect.getfile(module_class)).resolve()
            key = (str(source), module_class.__qualname__)
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
        return True

    return (platform, command) in {tuple(entry) for entry in supported_commands}
