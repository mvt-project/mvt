# Command Completion 

MVT utilizes the [Click](https://click.palletsprojects.com/en/stable/) library for creating its command line interface. 

Click provides tab completion support for Bash (version 4.4 and up), Zsh, and Fish.

To enable it, you need to manually register a special function with your shell, which varies depending on the shell you are using.

The following describes how to generate the command completion scripts and add them to your shell configuration. 

> **Note: You will need to start a new shell for the changes to take effect.**

### For Bash

```bash
# Generates bash completion scripts
echo "$(_MVT_IOS_COMPLETE=bash_source mvt-ios)" > ~/.mvt-ios-complete.bash &&
echo "$(_MVT_ANDROID_COMPLETE=bash_source mvt-android)" > ~/.mvt-android-complete.bash
```

Add the following to `~/.bashrc`:
```bash
# source mvt completion scripts
. ~/.mvt-ios-complete.bash && .  ~/.mvt-android-complete.bash
```

### For Zsh

```bash
# Generates zsh completion scripts
echo "$(_MVT_IOS_COMPLETE=zsh_source mvt-ios)" >  ~/.mvt-ios-complete.zsh &&
echo "$(_MVT_ANDROID_COMPLETE=zsh_source mvt-android)" > ~/.mvt-android-complete.zsh
```

Add the following to `~/.zshrc`:
```bash
# source mvt completion scripts
.  ~/.mvt-ios-complete.zsh  && .  ~/.mvt-android-complete.zsh
```

For more information, visit the official [Click Docs](https://click.palletsprojects.com/en/stable/shell-completion/#enabling-completion).


