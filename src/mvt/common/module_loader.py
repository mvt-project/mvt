# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import importlib.metadata
import importlib.util
import inspect
import json
import logging
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Iterable, Optional

from .module import MVTModule
from .version import MVT_VERSION

MVT_CUSTOM_MODULES_ENV = "MVT_CUSTOM_MODULES"
MODULES_ENTRY_POINT_GROUP = "mvt.modules"
EXTERNAL_LOGGER_NAMESPACE = "mvt.ext"
PLUGIN_PACKAGE_PREFIX = "mvt_plugin_"
_ORIGIN_ATTRIBUTE = "_mvt_module_origin"
_PATH_MODULE_PREFIX = "_mvt_custom_module_"
log = logging.getLogger(__name__)


class CustomModuleLoadError(Exception):
    pass


@dataclass(frozen=True)
class ModuleOrigin:
    """Describes where a loaded module came from, for auditability.

    ``kind`` is one of ``builtin`` (shipped with MVT), ``package`` (loaded
    from an installed package) or ``path`` (loaded from a file passed with
    ``--load-module`` or the environment variable).
    """

    kind: str
    name: str
    version: Optional[str] = None
    commit: Optional[str] = None
    file_sha256: Optional[str] = None

    @property
    def label(self) -> str:
        label = self.name
        if self.version:
            label += f"@{self.version}"
        label = f"'{label}'"
        if self.commit:
            label += f" (commit {self.commit})"
        if self.file_sha256:
            label += f" (sha256: {self.file_sha256})"
        return label


def _module_name_for_path(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    return f"{_PATH_MODULE_PREFIX}{path.stem}_{digest}"


def get_module_logger(module_class: type[MVTModule]) -> logging.Logger:
    """Return the logger a module's records should be emitted through.

    Modules loaded from installed packages or file paths live outside the
    "mvt" logger hierarchy, so their records would never reach the handlers
    attached to the "mvt" logger and instead fall through to
    logging.lastResort (which prints bare messages and drops anything below
    WARNING). Their loggers are parented under the "mvt.ext" namespace,
    keeping external module names from colliding with MVT's own logger
    tree. File-path modules are named after their file instead of the
    mangled internal import name, and packages following the recommended
    "mvt_plugin_<name>" naming convention log under "mvt.ext.<name>".
    """
    name = module_class.__module__
    if name == "mvt" or name.startswith("mvt."):
        return logging.getLogger(name)

    if name.startswith(_PATH_MODULE_PREFIX):
        name = Path(get_module_origin(module_class).name).stem
    else:
        top_level, separator, rest = name.partition(".")
        if top_level.startswith(PLUGIN_PACKAGE_PREFIX) and len(top_level) > len(
            PLUGIN_PACKAGE_PREFIX
        ):
            name = top_level[len(PLUGIN_PACKAGE_PREFIX) :] + separator + rest

    return logging.getLogger(f"{EXTERNAL_LOGGER_NAMESPACE}.{name}")


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
        file_sha256 = hashlib.sha256(module_file.read_bytes()).hexdigest()
        loaded_module = _load_python_file(module_file)
        origin = ModuleOrigin(
            kind="path", name=str(module_file), file_sha256=file_sha256
        )
        for module_class in discover_mvt_modules(loaded_module):
            key = (str(module_file), module_class.__qualname__)
            if key in seen:
                continue
            seen.add(key)
            setattr(module_class, _ORIGIN_ATTRIBUTE, origin)
            custom_modules.append(module_class)

    return custom_modules


def _module_key(module_class: type[MVTModule]) -> tuple[str, str]:
    try:
        source = str(Path(inspect.getfile(module_class)).resolve())
    except (OSError, TypeError):
        source = module_class.__module__
    return (source, module_class.__qualname__)


def _distribution_commit(dist: importlib.metadata.Distribution) -> Optional[str]:
    """Return the VCS commit a distribution was installed from, if recorded.

    Packages installed directly from a repository (``pip install git+...``)
    record the commit in ``direct_url.json`` (PEP 610).
    """
    try:
        direct_url_text = dist.read_text("direct_url.json")
        if not direct_url_text:
            return None
        commit = json.loads(direct_url_text).get("vcs_info", {}).get("commit_id")
        return commit if isinstance(commit, str) else None
    except Exception:
        return None


def _entry_point_origin(entry_point: importlib.metadata.EntryPoint) -> ModuleOrigin:
    name = entry_point.name
    version = None
    commit = None
    # Manually constructed entry points have no associated distribution.
    dist = getattr(entry_point, "dist", None)
    if dist is not None:
        try:
            name = dist.name or name
            version = dist.version
        except Exception:
            pass
        commit = _distribution_commit(dist)
    return ModuleOrigin(kind="package", name=name, version=version, commit=commit)


@lru_cache(maxsize=1)
def _packages_distributions() -> dict[str, list[str]]:
    try:
        return dict(importlib.metadata.packages_distributions())
    except Exception:
        return {}


def get_module_origin(module_class: type[MVTModule]) -> ModuleOrigin:
    """Return the origin of a module class for auditing purposes."""
    origin = module_class.__dict__.get(_ORIGIN_ATTRIBUTE)
    if isinstance(origin, ModuleOrigin):
        return origin

    top_level = module_class.__module__.partition(".")[0]
    if top_level == "mvt":
        return ModuleOrigin(kind="builtin", name="mvt", version=MVT_VERSION)

    distributions = _packages_distributions().get(top_level)
    if distributions:
        name = distributions[0]
        version = None
        commit = None
        try:
            dist = importlib.metadata.distribution(name)
            version = dist.version
            commit = _distribution_commit(dist)
        except Exception:
            pass
        return ModuleOrigin(kind="package", name=name, version=version, commit=commit)

    try:
        source = str(Path(inspect.getfile(module_class)).resolve())
    except (OSError, TypeError):
        source = module_class.__module__
    return ModuleOrigin(kind="path", name=source)


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

        origin = _entry_point_origin(entry_point)
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
            setattr(module_class, _ORIGIN_ATTRIBUTE, origin)
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
