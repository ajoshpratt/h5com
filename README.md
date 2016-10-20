# h5com
A sort of vaguely-working h5 file browser, ala midnight commander.

Massive work in progress.

Requires numpy, h5py, and blessed.

This is less of a program to fulfill a need (although I suppose it does that), and more of a way to play around with message passing interfaces in the context of an end-user program in Python.  In addition, it's multithreaded (not that it needs to be).  Uses a modal motif, ala vim.

Can still crash if you hit the wrong key.

The h5 file is hardcoded (for the moment) as west.h5.  Simply have a west.h5 in your directory, and

```python h5.py```

From there, hit l to load up the file.  You should now be able to use the arrow keys to browse.  To open a group/dataset, hit enter.  To go back (either to the main pane, or just up in the hierarchy), hit del/backspace.

Tested on Arch Linux.

```
sudo pacman -S python-pip
sudo pip install numpy h5py blessed
```

Assume no license as of yet.
