# h5com - 'thief'
A sort of vaguely-working h5 file browser, ala midnight commander/ranger (hence 'thief').

Massive work in progress.

Requires numpy, h5py, and blessed, which can be installed through pip.  Works with Python2 (slight modifications can make it work with 3).  Has okay dataset visibility, and handles 3D numpy datasets relatively well.  Still some issues surrounding printing to the terminal, but much more robust.

This is less of a program to fulfill a need (although I suppose it does that), and more of a way to play around with a message bus in the context of an end-user program in Python.  In addition, it's multithreaded (not that it needs to be).  Uses a modal motif, ala vim.

```thief filename```

You should now be able to use the arrow keys to browse.  To open a group/dataset, hit enter.  To go back (either to the main pane, or just up in the hierarchy), hit del/backspace.  For N-D datasets, use plus or minus to change dimensions.

Tested on Arch Linux.

```
sudo pacman -S python-pip
sudo pip install numpy h5py blessed
```

Also works on macOS.

Let's go with 'do whatever you would like' as a license.
