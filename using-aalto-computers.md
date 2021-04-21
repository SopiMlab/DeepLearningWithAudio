# Using Aalto computers

Aalto provides some Linux computers which can be used for training.

# Paniikki

Paniikki is one of Aalto's computer labs for students. The computers can be accessed remotely using SSH. macOS comes with an SSH client preinstalled, but on Linux and Windows you may have to install it yourself:

- [Instructions for Ubuntu](https://ubuntu.com/server/docs/service-openssh)
- [Instructions for Windows 10](https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse)

The hostnames of the Paniikki computers can be found on Aalto's [Linux computer names in IT classrooms](https://www.aalto.fi/en/services/linux-computer-names-in-it-classrooms) page.

In the following examples we will use the username `myusername` and the computer known as `whitespace`. In practice you should substitute your own username and look through the available computers to find one that's not being used (more on that later).

Connect using the `ssh` command and you will be prompted for your password. Type it in (you won't see any output while typing) and press enter to log in.

----

## Connecting from inside Aalto network

If you're on the Aalto network, you can connect directly by running:

```
ssh myusername@whitespace
```

## Connecting from outside Aalto network

If you're not on the Aalto network, you need to "jump" via one of the [shell servers](https://www.aalto.fi/en/services/linux-shell-servers-at-aalto) (`kosh` or `lyta`) that are accessible from outside. For example:

```
ssh -J myusername@kosh.aalto.fi myusername@whitespace
```

You'll have to enter your password twice in this case.

----

After logging in, you will be presented with a Linux shell prompt. If you're new to the Linux command line, you may want to check out a tutorial such as [this one](https://ryanstutorials.net/linuxtutorial/commandline.php).

When you want to log out, run:

```
logout
```

## Check for activity

You probably don't want to run heavy calculations on a computer that others are already using. To check for activity, you can use:

```
htop
```

This shows a live monitoring view of things like CPU load and used memory. If most of the CPU cores are active or most of the memory is used, you should try another system (check the list linked above). Press `q` to exit `htop`.

You can also check live GPU utilization by running:

```
watch -n 1 nvidia-smi
```

This runs the command `nvidia-smi` every second. Press `ctrl-C` to exit `watch`. (In fact `ctrl-C` can be used to exit most interactive processes.)

## Load Anaconda module

To use Conda on Paniikki computers, you first need to load the `anaconda3` module using Lmod, like so:

```
module load anaconda3
```

This applies for the remainder of your login session and you will need to run it again if you log out and later log back in.

See the [Lmod manual](https://lmod.readthedocs.io/en/latest/010_user.html) for more commands.

After this, you should be ready to set up Conda environments as described in our other instructions for Linux, and to run training scripts etc. on the remote system.

## Running things in the background

Training the neural networks covered in the course can take anywhere from a few hours to ~5 days. Normally, whatever processes you're running will be terminated if you log out, get disconnected, etc. To avoid this, you can use the `screen` "terminal multiplexer" utility to leave a process running in the background.

First, start a new screen by running:

```
screen
```

This will show a startup message. Press `space` or `enter` to dismiss it and you'll get a new shell prompt. Anything you run here will persist even if you're not connected to the remote system.

At this point, you would typically load your Conda environment and start whatever script you want to run.

Note: If using screen, you should load the anaconda3 module (see above) **after** starting screen!

To *detach* from the screen, i.e. exit it while leaving it running in the background, press `ctrl-A` followed by `ctrl-D`.

You can list your running screens by running:

```
screen -ls
```

This will output something like:

```
There is a screen on:
	1465521.pts-14.unlambda	(2021-04-06 16:47:34)	(Detached)
1 Socket in /run/screen/S-kastemm1.
```

To *reattach* the screen again, run:

```
screen -r
```

----
### Common issues with `screen`

#### Reattaching fails with "There are several suitable screens on"

If running multiple screens, you have to tell `screen -r` which one to reattach by giving it the screen's ID, e.g.:

```
screen -r 1465521
```

#### Reattaching fails with "There is no screen to be resumed matching ..."

You might have made a typo when specifying the ID, or the screen is already attached in another session. A screen may be left attached if your network suddenly disconnected while working in the screen. You can force it to detach first by using the `-D` flag, e.g.:

```
screen -Dr 1465521
```

----

In summary, to run e.g. a training script on a Paniikki computer:

1. Log in with `ssh`
2. Start a `screen`
3. Load the Anaconda module — `module load anaconda3`
4. Activate your Conda environment — `conda activate ...`
5. Run the script — `python ...`

When doing long runs, it can be easy to forget which computer you chose, so we recommend making a note of this.

## Transferring files

You can transfer files to and from your Aalto home directory using SMB, but you need to be on the Aalto network to do this. When working remotely, you can use the [Aalto VPN](https://www.aalto.fi/en/services/establishing-a-remote-connection-vpn-to-an-aalto-network) to join the network.

Once on the Aalto network, you can connect to the SMB server.

### Using SMB from macOS

In Finder, open the Go menu and select "Connect to Server...". Enter:

```
smb://home.org.aalto.fi
```

Click Connect and log in with your Aalto credentials.

#### Alternative Unix hacker method: SSH tunnel

If you prefer not to set up the Aalto VPN, there is another method on Mac: you can create an SSH tunnel via an outward–facing Aalto shell server like `kosh` or `lyta`. 

Open a separate terminal window and run: (replacing `myusername` with your Aalto username)

```
ssh myusername@kosh.aalto.fi -L 127.0.0.1:10139:home.org.aalto.fi:139
```

In Finder, you can then open the Go menu, select "Connect to Server..." and enter:

```
smb://localhost:10139
```

Click Connect and log in with your Aalto credentials.

The tunnel will be closed when you log out of the ssh connection.

### Using SMB from Windows

Open an Explorer window, and enter in the address bar:

```
\\home.org.aalto.fi
```

Press Enter and log in with your Aalto credentials.