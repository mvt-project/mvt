# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021-2023 The MVT Authors.
# Use of this software is governed by the MVT License 1.1 that can be found at
#   https://license.mvt.re/1.1/

from pathlib import Path
import shlex

import click
from click.shell_completion import get_completion_class


SUPPORTED_SHELLS = ("bash", "zsh", "fish")


def completion_instructions(program_name: str) -> str:
    return f"""Shell completion for {program_name}

Print a completion script:
  {program_name} completion bash > ~/.{program_name}-complete.bash
  {program_name} completion zsh > ~/.{program_name}-complete.zsh
  mkdir -p ~/.config/fish/completions
  {program_name} completion fish > ~/.config/fish/completions/{program_name}.fish

Load the generated Bash script from ~/.bashrc:
  [ -f ~/.{program_name}-complete.bash ] && . ~/.{program_name}-complete.bash

Load the generated Zsh script from ~/.zshrc:
  [ -f ~/.{program_name}-complete.zsh ] && . ~/.{program_name}-complete.zsh

Fish loads completion files from ~/.config/fish/completions automatically.

To write these files and update Bash/Zsh shell configuration automatically:
  {program_name} completion bash --install
  {program_name} completion zsh --install
  {program_name} completion fish --install
"""


def generate_completion_script(cli: click.Command, program_name: str, shell: str) -> str:
    completion_class = get_completion_class(shell)
    if completion_class is None:
        raise click.ClickException(f"Unsupported shell: {shell}")

    complete_var = f"_{program_name.upper().replace('-', '_')}_COMPLETE"
    return completion_class(cli, {}, program_name, complete_var).source()


def install_completion_script(
    cli: click.Command,
    program_name: str,
    shell: str,
) -> Path:
    script = generate_completion_script(cli, program_name, shell)
    script_path = _completion_script_path(program_name, shell)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")

    if shell in ("bash", "zsh"):
        _install_shell_source_line(program_name, shell, script_path)

    return script_path


def _completion_script_path(program_name: str, shell: str) -> Path:
    home = Path.home()

    if shell == "fish":
        return home / ".config" / "fish" / "completions" / f"{program_name}.fish"

    return home / f".{program_name}-complete.{shell}"


def _install_shell_source_line(program_name: str, shell: str, script_path: Path) -> None:
    shell_config_path = Path.home() / f".{shell}rc"
    source_line = (
        f"[ -f {shlex.quote(str(script_path))} ] && "
        f". {shlex.quote(str(script_path))}"
    )
    block = (
        f"# MVT shell completion for {program_name}\n"
        f"{source_line}\n"
    )

    if shell_config_path.exists():
        shell_config = shell_config_path.read_text(encoding="utf-8")
        if source_line in shell_config:
            return
    else:
        shell_config = ""

    separator = "" if not shell_config or shell_config.endswith("\n") else "\n"
    with shell_config_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{separator}{block}")
