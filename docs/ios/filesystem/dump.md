# Dumping the filesystem

While iTunes backup provide a lot of very useful databases and diagnostic data, in some cases you might want to jailbreak the device and perform a full filesystem dump. In that case, you should take a look at [checkra1n](https://checkra.in/), which provides an easy way to obtain root on most recent iPhone models.

!!! warning
    Before you checkra1n any device, make sure you take a full backup, and that you are prepared to do a full factory reset before restoring it. Even after using checkra1n's "Restore System", some traces of the jailbreak are still left on the device and [apps with anti-jailbreaks will be able to detect them](https://github.com/checkra1n/BugTracker/issues/279) and stop functioning.

After having jailbroken the device, you should be able to access the phone over ssh. In order to do this you will typically need to use iproxy, which on Debian/Ubuntu systems can be installed with `libusbmuxd-tools`. Run the command:

```bash
iproxy 2222 44
```

Now you will be able to ssh as root to localhost on port 2222 and password `alpine`. Note: if you used a jailbreak other than checkra1n, you might need to specify a different port number instead of 44.

At this point you need to get access to the content of the device from your computer. One way is to run a command like `ssh root@localhost -p 2222 tar czf - /private > dump.tar.gz` which will save a tarball on the host of the */private/* folder from the phone. This will take a while.

Alternatively, you can try run `sftp-server` for iOS and mount the filesystem locally using `sshfs`.


## Use `sshfs` on iOS

If you decide to try to use sshfs, you first have to download locally a compiled copy of sftp-server:

```bash
wget https://github.com/dweinstein/openssh-ios/releases/download/v7.5/sftp-server
```

Then upload the binary to the iPhone:

```bash
scp -P2222 sftp-server root@localhost:.
```

You will need to ssh into the device and set some entitlements in order to allow `sftp-server` to run. This entitlements can be copied from an existing binary:

```bash
chmod +x sftp-server
ldid -e /binpack/bin/sh > /tmp/sh-ents
ldid -S /tmp/sh-ents sftp-server
```

Now you can create a folder on the host and use it as a mount point (**note:** do not create this folder in /tmp/):

```bash
mkdir root_mount
sshfs -p 2222 -o sftp_server=/var/root/sftp-server root@localhost:/ root_mount
```
