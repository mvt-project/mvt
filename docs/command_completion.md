# Command Completion 

MVT utilizes the [Click](https://click.palletsprojects.com/en/stable/) library for creating its command line interface. 

Click provides tab completion support for Bash (version 4.4 and up), Zsh, and Fish.

To enable it, you need to register a special function with your shell, which varies depending on the shell you are using.

`You need to start a new shell in order for the changes to be loaded.`

### For Bash

```bash
# Get the completion scripts 
curl --tlsv1.3 -O https://github.com/mvt-project/mvt/tree/main/src/mvt/shell_completion/.mvt-{ios,android}-complete.bash

# Source the file in ~/.bashrc.
. .mvt-android-complete.bash && . .mvt-ios-complete.bash
```

### For Zsh

```bash
# Get the completion scripts 
curl --tlsv1.3 -O https://github.com/mvt-project/mvt/tree/main/src/mvt/shell_completion/.mvt-{ios,android}-complete.zsh

# Source the file in ~/.zshrc.
. .mvt-android-complete.zsh && . .mvt-ios-complete.zsh
```

## Generate Scripts locally 

In case you prefer not to download the command completion scripts from the MVT Project, you can generate your own scripts locally.

### For Bash

```bash
echo "$(_MVT_IOS_COMPLETE=bash_source mvt-ios)" > ~/.mvt-ios-complete.bash &&
echo "$(_MVT_ANDROID_COMPLETE=bash_source mvt-android)" > ~/.mvt-android-complete.bash
```

### For Zsh
```bash
echo "$(_MVT_IOS_COMPLETE=zsh_source mvt-ios)" >  ~/.mvt-ios-complete.zsh &&
echo "$(_MVT_ANDROID_COMPLETE=zsh_source mvt-android)" > ~/.mvt-android-complete.zsh
```

You will then need to source the files in your shell configuration file and restart it for the changes to be loaded.


For more information, visit the official [Click Docs](https://click.palletsprojects.com/en/stable/shell-completion/#enabling-completion).


