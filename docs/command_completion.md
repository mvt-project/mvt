# Command Completion

MVT utilizes the [Click](https://click.palletsprojects.com/en/stable/) library for creating its command line interface.

Click provides tab completion support for Bash (version 4.4 and up), Zsh, and Fish.

To enable it, you need to register a completion script with your shell, which varies depending on the shell you are using.

The following describes how to generate the command completion scripts and add them to your shell configuration.

> **Note: You will need to start a new shell for the changes to take effect.**

### For Bash

```bash
# Generate bash completion scripts
mvt-ios completion bash > ~/.mvt-ios-complete.bash
mvt-android completion bash > ~/.mvt-android-complete.bash
```

Add the following to `~/.bashrc`:
```bash
# source mvt completion scripts
[ -f ~/.mvt-ios-complete.bash ] && . ~/.mvt-ios-complete.bash
[ -f ~/.mvt-android-complete.bash ] && . ~/.mvt-android-complete.bash
```

### For Zsh

```bash
# Generate zsh completion scripts
mvt-ios completion zsh > ~/.mvt-ios-complete.zsh
mvt-android completion zsh > ~/.mvt-android-complete.zsh
```

Add the following to `~/.zshrc`:
```bash
# source mvt completion scripts
[ -f ~/.mvt-ios-complete.zsh ] && . ~/.mvt-ios-complete.zsh
[ -f ~/.mvt-android-complete.zsh ] && . ~/.mvt-android-complete.zsh
```

### For Fish

```bash
# Generate fish completion scripts
mkdir -p ~/.config/fish/completions
mvt-ios completion fish > ~/.config/fish/completions/mvt-ios.fish
mvt-android completion fish > ~/.config/fish/completions/mvt-android.fish
```

Fish loads completion files from `~/.config/fish/completions` automatically.

### Automatic Installation

MVT can write the completion file and update the relevant shell configuration for Bash and Zsh when you pass `--install`:

```bash
mvt-ios completion bash --install
mvt-android completion bash --install
```

Replace `bash` with `zsh` or `fish` as needed. For Fish, `--install` writes the completion file into `~/.config/fish/completions`.

For more information, visit the official [Click Docs](https://click.palletsprojects.com/en/stable/shell-completion/#enabling-completion).

