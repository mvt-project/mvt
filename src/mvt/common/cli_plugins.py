# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2026 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

import hashlib
import importlib.metadata
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable

import click

IOS_CLI_PLUGIN_GROUP = "mvt.ios.cli_plugins"
ANDROID_CLI_PLUGIN_GROUP = "mvt.android.cli_plugins"
MVT_IOS_CUSTOM_COMMANDS_ENV = "MVT_IOS_CUSTOM_COMMANDS"
MVT_ANDROID_CUSTOM_COMMANDS_ENV = "MVT_ANDROID_CUSTOM_COMMANDS"

log = logging.getLogger(__name__)


class CustomCommandLoadError(Exception):
    pass


class BrokenPluginCommand(click.Command):
    """A placeholder for an installed or configured command that failed to load."""

    def __init__(self, name: str, source: str, exception: BaseException):
        super().__init__(
            name,
            help=(
                f"Unable to load external command from {source}.\n\n"
                f"{type(exception).__name__}: {exception}"
            ),
            short_help="Warning: external command could not be loaded.",
        )
        self.source = source
        self.exception = exception

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        return args

    def invoke(self, ctx: click.Context) -> None:
        raise click.ClickException(
            f"Unable to load external command '{self.name}' from {self.source}: "
            f"{type(self.exception).__name__}: {self.exception}"
        )


def _module_name_for_path(path: Path) -> str:
    digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
    return f"_mvt_custom_command_{path.stem}_{digest}"


def _iter_command_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix != ".py":
            raise CustomCommandLoadError(
                f"Custom command file is not a Python file: {path}"
            )
        yield path
        return

    if path.is_dir():
        for child in sorted(path.iterdir()):
            if child.name.startswith(".") or child.name == "__init__.py":
                continue
            if child.is_file() and child.suffix == ".py":
                yield child
        return

    raise CustomCommandLoadError(f"Custom command path does not exist: {path}")


def _load_python_file(path: Path) -> ModuleType:
    module_name = _module_name_for_path(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise CustomCommandLoadError(f"Unable to load custom command file: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except (Exception, SystemExit) as exc:
        raise CustomCommandLoadError(
            f"Unable to import custom command {path}: {exc}"
        ) from exc

    return module


def load_cli_command_file(path: Path) -> click.Command:
    module = _load_python_file(path)
    command = getattr(module, "cli", None)
    if not isinstance(command, click.Command):
        raise CustomCommandLoadError(
            f"Custom command {path} must export a Click command or group named 'cli'"
        )
    if command.name is None:
        raise CustomCommandLoadError(f"Custom command {path} has no command name")
    return command


def _register_command(
    group: click.Group,
    command: click.Command,
    *,
    name: str,
    source: str,
    collision_is_error: bool,
) -> bool:
    if name in group.commands:
        registered_sources = getattr(group, "_mvt_external_command_sources", {})
        if registered_sources.get(name) == source:
            return False
        message = (
            f"Unable to register external command '{name}' from {source}: "
            "the command name is already registered"
        )
        if collision_is_error:
            raise CustomCommandLoadError(message)
        log.warning(message)
        return False

    group.add_command(command, name=name)
    registered_sources = getattr(group, "_mvt_external_command_sources", {})
    registered_sources[name] = source
    setattr(group, "_mvt_external_command_sources", registered_sources)
    return True


def register_cli_commands_from_path(
    group: click.Group,
    path: str | Path,
    *,
    collision_is_error: bool = False,
    failures_are_errors: bool = False,
) -> list[str]:
    resolved_path = Path(path).expanduser().resolve()
    registered: list[str] = []

    try:
        command_files = list(_iter_command_files(resolved_path))
    except CustomCommandLoadError as exc:
        if failures_are_errors:
            raise
        name = resolved_path.stem.replace("_", "-") or "custom-command"
        if _register_command(
            group,
            BrokenPluginCommand(name, str(resolved_path), exc),
            name=name,
            source=str(resolved_path),
            collision_is_error=collision_is_error,
        ):
            registered.append(name)
        return registered

    for command_file in command_files:
        try:
            command = load_cli_command_file(command_file)
        except CustomCommandLoadError as exc:
            if failures_are_errors:
                raise
            name = command_file.stem.replace("_", "-")
            command = BrokenPluginCommand(name, str(command_file), exc)

        command_name = command.name
        if command_name is None:
            raise CustomCommandLoadError(
                f"Custom command {command_file} has no command name"
            )
        if _register_command(
            group,
            command,
            name=command_name,
            source=str(command_file),
            collision_is_error=collision_is_error,
        ):
            registered.append(command_name)

    return registered


def _entry_point_source(entry_point: importlib.metadata.EntryPoint) -> str:
    try:
        distribution = getattr(entry_point, "dist", None)
        if distribution is None:
            return f"entry point {entry_point.value}"

        name = distribution.metadata.get("Name", "unknown distribution")
        version = getattr(distribution, "version", None)
        if version:
            return f"{name} {version} ({entry_point.value})"
        return f"{name} ({entry_point.value})"
    except Exception:
        return f"entry point {entry_point.value}"


def register_installed_cli_commands(
    group: click.Group,
    entry_point_group: str,
) -> list[str]:
    try:
        entry_points = importlib.metadata.entry_points(group=entry_point_group)
    except Exception as exc:
        log.warning(
            "Unable to discover external commands in entry-point group %s: %s",
            entry_point_group,
            exc,
        )
        return []
    ordered_entry_points = sorted(
        entry_points,
        key=lambda entry_point: (
            entry_point.name,
            _entry_point_source(entry_point),
            entry_point.value,
        ),
    )
    registered: list[str] = []

    for entry_point in ordered_entry_points:
        source = _entry_point_source(entry_point)
        try:
            command = entry_point.load()
            if not isinstance(command, click.Command):
                raise TypeError(
                    f"entry point must resolve to a Click command or group, "
                    f"not {type(command).__name__}"
                )
        except (Exception, SystemExit) as exc:
            command = BrokenPluginCommand(entry_point.name, source, exc)

        if _register_command(
            group,
            command,
            name=entry_point.name,
            source=source,
            collision_is_error=False,
        ):
            registered.append(entry_point.name)

    return registered


def register_cli_plugins(
    group: click.Group,
    *,
    entry_point_group: str,
    environment_variable: str,
) -> None:
    environment_path = os.environ.get(environment_variable)
    if environment_path:
        register_cli_commands_from_path(group, environment_path)
    register_installed_cli_commands(group, entry_point_group)


def _load_command_option_callback(
    ctx: click.Context,
    param: click.Parameter,
    paths: tuple[str, ...],
) -> tuple[str, ...]:
    if not isinstance(ctx.command, click.Group):
        raise click.ClickException("--load-command requires a Click command group")

    for path in paths:
        try:
            register_cli_commands_from_path(
                ctx.command,
                path,
                collision_is_error=True,
                failures_are_errors=True,
            )
        except CustomCommandLoadError as exc:
            raise click.BadParameter(str(exc), ctx=ctx, param=param) from exc
    return paths


load_cli_commands_option = click.option(
    "--load-command",
    "load_commands",
    type=click.Path(exists=True),
    multiple=True,
    expose_value=False,
    is_eager=True,
    callback=_load_command_option_callback,
    help=(
        "Load a custom CLI command from a Python file or folder "
        "(can be invoked multiple times)"
    ),
)
