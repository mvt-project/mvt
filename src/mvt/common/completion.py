# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from pathlib import Path
import shlex

import click
from click.shell_completion import get_completion_class

from .help import HELP_MSG_COMPLETION


SUPPORTED_SHELLS = ("bash", "zsh", "fish")
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

COMPLETION_INSTRUCTIONS = """Shell completion for mvt, mvt-ios and mvt-android

Print one completion script covering the three commands:
  mvt completion bash > ~/.mvt-complete.bash
  mvt completion zsh > ~/.mvt-complete.zsh
  mkdir -p ~/.config/fish/conf.d
  mvt completion fish > ~/.config/fish/conf.d/mvt-completion.fish

Load the generated Bash script from ~/.bashrc:
  [ -f ~/.mvt-complete.bash ] && . ~/.mvt-complete.bash

Load the generated Zsh script from ~/.zshrc:
  [ -f ~/.mvt-complete.zsh ] && . ~/.mvt-complete.zsh

Fish loads the files in ~/.config/fish/conf.d automatically.

To write these files and update the Bash/Zsh shell configuration automatically:
  mvt completion bash --install
  mvt completion zsh --install
  mvt completion fish --install
"""


def _mvt_programs() -> list[tuple[str, click.Command]]:
    """Return the console script name and CLI group of every MVT program.

    The three CLIs are imported here rather than at module level: mvt.cli
    imports this module while it is being defined, and generating a completion
    script should not make the start-up of `mvt` import the platform CLIs.
    """
    from mvt.android.cli import cli as android_cli
    from mvt.cli import cli as mvt_cli
    from mvt.ios.cli import cli as ios_cli

    return [("mvt", mvt_cli), ("mvt-ios", ios_cli), ("mvt-android", android_cli)]


@click.command(
    "completion",
    context_settings=CONTEXT_SETTINGS,
    help=HELP_MSG_COMPLETION,
    short_help="Generate or install shell completion",
)
@click.argument("shell", required=False, type=click.Choice(SUPPORTED_SHELLS))
@click.option(
    "--install",
    is_flag=True,
    help="Write completion files and update shell configuration.",
)
def completion(shell, install):
    if shell is None:
        if install:
            raise click.UsageError("A shell is required when using --install.")
        click.echo(COMPLETION_INSTRUCTIONS)
        return

    if install:
        script_path = install_completion_script(shell)
        click.echo(
            f"Installed {shell} completion for mvt, mvt-ios and mvt-android "
            f"to {script_path}"
        )
        if shell in ("bash", "zsh"):
            click.echo(f"Updated ~/.{shell}rc")
        else:
            click.echo("Fish loads the files in ~/.config/fish/conf.d automatically.")
        return

    click.echo(generate_mvt_completion_script(shell))


def generate_completion_script(cli: click.Command, program_name: str, shell: str) -> str:
    completion_class = get_completion_class(shell)
    if completion_class is None:
        raise click.ClickException(f"Unsupported shell: {shell}")

    complete_var = f"_{program_name.upper().replace('-', '_')}_COMPLETE"
    return completion_class(cli, {}, program_name, complete_var).source()


def generate_mvt_completion_script(shell: str) -> str:
    """Return one script completing every MVT command.

    Click names the completion function of each program after the program, so
    the scripts of the three commands can simply be concatenated.
    """
    scripts = [
        generate_completion_script(cli, program_name, shell).strip("\n")
        for program_name, cli in _mvt_programs()
    ]
    return "\n\n".join(scripts)


def install_completion_script(shell: str) -> Path:
    script = generate_mvt_completion_script(shell)
    script_path = _completion_script_path(shell)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(f"{script}\n", encoding="utf-8")

    if shell in ("bash", "zsh"):
        _install_shell_source_line(shell, script_path)

    return script_path


def _completion_script_path(shell: str) -> Path:
    home = Path.home()

    if shell == "fish":
        # conf.d is sourced when the shell starts, unlike the completions
        # folder, whose files fish loads on demand by command name.
        return home / ".config" / "fish" / "conf.d" / "mvt-completion.fish"

    return home / f".mvt-complete.{shell}"


def _install_shell_source_line(shell: str, script_path: Path) -> None:
    shell_config_path = Path.home() / f".{shell}rc"
    source_line = (
        f"[ -f {shlex.quote(str(script_path))} ] && "
        f". {shlex.quote(str(script_path))}"
    )
    block = f"# MVT shell completion\n{source_line}\n"

    if shell_config_path.exists():
        shell_config = shell_config_path.read_text(encoding="utf-8")
        if source_line in shell_config:
            return
    else:
        shell_config = ""

    separator = "" if not shell_config or shell_config.endswith("\n") else "\n"
    with shell_config_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{separator}{block}")
