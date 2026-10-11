# Command Completion

MVT utilizes the [Click](https://click.palletsprojects.com/en/stable/) library for creating its command line interface.

Click provides tab completion support for Bash (version 4.4 and up), Zsh, and Fish.

To enable it, you need to register a completion script with your shell, which varies depending on the shell you are using.

`mvt completion` generates one script which covers `mvt`, `mvt-ios` and `mvt-android`. The following describes how to generate that script and add it to your shell configuration.

> **Note: You will need to start a new shell for the changes to take effect.**

### For Bash

```bash
# Generate the bash completion script
mvt completion bash > ~/.mvt-complete.bash
```

Add the following to `~/.bashrc`:
```bash
# source the mvt completion script
[ -f ~/.mvt-complete.bash ] && . ~/.mvt-complete.bash
```

### For Zsh

```bash
# Generate the zsh completion script
mvt completion zsh > ~/.mvt-complete.zsh
```

Add the following to `~/.zshrc`:
```bash
# source the mvt completion script
[ -f ~/.mvt-complete.zsh ] && . ~/.mvt-complete.zsh
```

### For Fish

```bash
# Generate the fish completion script
mkdir -p ~/.config/fish/conf.d
mvt completion fish > ~/.config/fish/conf.d/mvt-completion.fish
```

Fish loads the files in `~/.config/fish/conf.d` automatically.

### Automatic Installation

MVT can write the completion file and update the relevant shell configuration for Bash and Zsh when you pass `--install`:

```bash
mvt completion bash --install
```

Replace `bash` with `zsh` or `fish` as needed. For Fish, `--install` writes the completion file into `~/.config/fish/conf.d` and changes no shell configuration.

!!! note

    Earlier versions generated one script per command, with `mvt-ios completion`
    and `mvt-android completion`. Files written by them keep working. When you
    switch to the single script, remove the old files and the lines which load
    them from your shell configuration.

For more information, visit the official [Click Docs](https://click.palletsprojects.com/en/stable/shell-completion/#enabling-completion).
