import numpy as np
import h5py

import os, sys, getch, select

from threading import Thread

import blessed
from blessed import Terminal
# This is Python3.  Python2 has Queue.
from queue import Queue
#import curses
#stdscr = curses.initscr()


class MsgBus():
    def __init__(self):
        self.Systems       = []
        self.SystemThreads = []
        self.MsgQueue      = Queue(maxsize=0)
        self.Run = True
    def RegisterSystem(self, system):
        self.Systems.append(system)
    def LaunchSystems(self):
        for i in range(0, len(self.Systems)):
            self.SystemThreads.append(Thread(target=self.Systems[i].MainLoop))
        for i in range(0, len(self.Systems)):
            self.SystemThreads[i].start()
    def KillSystems(self):
        # This doesn't work, but whatever.
        # We'll have to poll for a signal command.
        # works well enough, at least.
        for i in range(0, len(self.Systems)):
            self.Systems[i].Run = False
        #    self.SystemThreads[i].join()
        self.Run = False
        sys.exit(0)
    def ReceiveMessage(self, msg):
        self.MsgQueue.put(msg)
    def SendMessages(self, msg):
        for i in range(0, len(self.Systems)):
            self.Systems[i].ReceiveMessage(msg)
    def SortMessages(self):
        if not self.MsgQueue.empty():
            while not self.MsgQueue.empty():
                self.SendMessages(self.MsgQueue.get())
        else:
            return 0
    def MainLoop(self):
            while self.Run:
                self.SortMessages()

class Systems():
    def __init__(self, MsgBusInstance):
        self.MsgQueue = Queue(maxsize=0)
        self.MsgBus = MsgBusInstance
        self.Run = True
    def ReceiveMessage(self, msg):
        self.MsgQueue.put(msg)
    def SendMessage(self, msg):
        self.MsgBus.ReceiveMessage(msg)
    def HandleMessage(self, msg):
        # Put in some code here for the various proper systems.
        return 0
    def MainLoop(self):
        return 0
    def SortMessages(self):
        # Just loops through and handles the messsages.
        if not self.MsgQueue.empty():
            while not self.MsgQueue.empty():
                self.HandleMessage(self.MsgQueue.get())
        else:
            return 0

class Msg():
    def __init__(self, name, mtype, code=0):
        # Very basic.  Name, message type, and a particular thing to actually send.  Can be anything.
        self.name = name
        self.mtype = mtype
        self.code = code

class Input(Systems):
    def __init__(self, MsgBusInstance, terminal):
        Systems.__init__(self, MsgBusInstance)
        self.terminal = terminal
    def MainLoop(self):
        while self.Run:
            with self.terminal.cbreak():
                keypress = self.terminal.inkey()
                msg = Msg('input!', mtype='INPUT', code=keypress)
                self.SendMessage(msg)
                self.SortMessages()
                if keypress.code == 'q':
                    # shut it down.
                    self.Run = False

class TerminalPrinter(Systems):
    def __init__(self, MsgBusInstance, terminal):
        Systems.__init__(self, MsgBusInstance)
        self.terminal = terminal
        # Keep track of the cursor position.
        self.csr = self.terminal.get_location()
        self.Boxes = []

    def HandleMessage(self, msg):
        if msg.mtype == 'INPUT':
            # Let's handle how we do the cursor, yeah?
            if msg.code.code != None:
                # We don't want to move out of the box...
                # ... so this global input keeps us moving around the current, active box.
                if msg.code.code == self.terminal.KEY_LEFT:
                    if self.csr[1] - 1 > self.ActiveBox.pos[1]:
                        self.csr = (self.csr[0], self.csr[1] - 1)
                elif msg.code.code == self.terminal.KEY_RIGHT:
                    if self.csr[1] + 1 < self.ActiveBox.pos[1] + self.ActiveBox.size[1] - 1:
                        self.csr = (self.csr[0], self.csr[1] + 1)
                elif msg.code.code == self.terminal.KEY_DOWN:
                    if self.csr[0] + 1 < self.ActiveBox.pos[0] + self.ActiveBox.size[0] - 1:
                        self.csr = (self.csr[0] + 1, self.csr[1])
                elif msg.code.code == self.terminal.KEY_UP:
                    if self.csr[0] - 1 > self.ActiveBox.pos[0]:
                        self.csr = (self.csr[0] - 1, self.csr[1])
            elif msg.code == 'A':
                msg = Msg('new_box', mtype='NEW_BOX', code=boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=2, name='New'))
                self.SendMessage(msg)
                # This usually has to wait, I'm afraid, so we can't pull from the Boxes list yet.  We just send in something with the proper name and level, though.
                msg = Msg('new_box', mtype='ACTIVATE_BOX', code=boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=2, name='New'))
                self.SendMessage(msg)
            elif msg.code == 'q':
                # for the moment, kill everything.
                self.MsgBus.KillSystems()
                #msg = Msg('quit', mtype='QUIT', code='quit'))
            else:
                # This is just in case we want to print something at this position.  Not a big problem...
                print((self.terminal.move(self.csr[0], self.csr[1]) + msg.code), end='')
                self.csr = (self.csr[0], self.csr[1] + 1)
                sys.stdout.flush()
        elif msg.mtype == 'NEW_BOX':
            # Stored in the code is the box object information
            self.registerNewBox(msg.code)
        elif msg.mtype == 'ACTIVATE_BOX':
            # Stored in the code is the box object information
            self.activateBox(msg.code)
    def registerNewBox(self, box):
        # Here, we create a new box to draw.  It has a level and a certain position.
        # If we don't have that many levels, we'll enlarge our list of dictionaries until we do.
        while len(self.Boxes) < box.level:
            self.Boxes.append({})
        self.Boxes[box.level-1][box.name] = box
    def loopBoxes(self):
        for level in range(0,len(self.Boxes)):
            # First, get the box object, and the position...
            for box in self.Boxes[level].values():
                # ... now draw it.
                if box.drawn == False:
                    self.drawBox(box)
                    box.drawn = True
    def activateBox(self, box):
        # We move the cursor to the active box, then set active box to the current one.
        pos = self.Boxes[box.level-1][box.name]
        self.csr = (pos.pos[0]+1, pos.pos[1]+1)
        self.ActiveBox = box

    def drawBox(self, box):
        for y in range(0, box.size[1]):
            if y == 0 or y == box.size[1] - 1:
                for x in range(0, box.size[0]):
                    # Top or bottom of the box!
                    print(self.terminal.move(x+box.pos[0],y+box.pos[1]) + '-')
            else:
                if y == 0 or y == box.size[1] - 1:
                    for x in [0, box.size[0]]:
                        print(self.terminal.move(x+box.pos[0],y+box.pos[1]) + '|')
                else:
                        print(self.terminal.move(x+box.pos[0],y+box.pos[1]) + '|')

    def MainLoop(self):
        # Let's set up the terminal!
        with self.terminal.fullscreen():
            # Let's draw one box which is the size of the everything.
            self.h = self.terminal.height
            self.w = self.terminal.width
            #msg = Msg('new_box', mtype='NEW_BOX', code=boxWindow(size=(int(self.h*.9), int(self.w*.9)), pos=(0,0), level=1, name='Main'))
            self.registerNewBox(boxWindow(size=(int(self.h/2), int(self.w/2)), pos=(int(self.h/4),int(self.w/4)), level=1, name='Main'))
            # Let's set this to the 'active' box, which will move our cursor to it.
            msg = Msg('active_box', mtype='ACTIVATE_BOX', code=self.Boxes[0]['Main'])
            self.SendMessage(msg)
            while self.Run:
                # Move the cursor to the current position.
                print((self.terminal.move(self.csr[0], self.csr[1])), end='')
                # Draw all the boxes we want to draw!
                self.loopBoxes()
                self.SortMessages()
                #print("hooray")

class boxWindow():
    def __init__(self, size, pos, level, name):
        self.size = size
        self.pos = pos
        self.name = name
        self.level = level
        self.drawn = False

msgbus = MsgBus()
terminal = Terminal()
inputsys = Input(msgbus, terminal)
termprint = TerminalPrinter(msgbus, terminal)
msgbus.RegisterSystem(termprint)
msgbus.RegisterSystem(inputsys)
msgbus.LaunchSystems()
msgbus.MainLoop()
