import numpy as np
import h5py

import os, sys, select, time

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
        self.updateTime = .015
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
    def start_clock(self):
        self.start_time = time.time()
    def end_clock(self):
        self.end_time = time.time()
        if self.end_time - self.start_time < self.updateTime:
            time.sleep(self.updateTime - (self.end_time - self.start_time))
    def MainLoop(self):
            while self.Run:
                self.start_clock()
                self.SortMessages()
                self.end_clock()

class Systems():
    def __init__(self, MsgBusInstance):
        self.MsgQueue = Queue(maxsize=0)
        self.MsgBus = MsgBusInstance
        self.Run = True
        self.updateTime = .015
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
    def start_clock(self):
        self.start_time = time.time()
    def end_clock(self):
        self.end_time = time.time()
        if self.end_time - self.start_time < self.updateTime:
            time.sleep(self.updateTime - (self.end_time - self.start_time))

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

class AppState(Systems):
    def __init__(self, MsgBusInstance, terminal):
        Systems.__init__(self, MsgBusInstance)
        self.terminal = terminal
        self.ActiveBox = None
        self.Boxes = [{}]
        # Possible states: insert, command
        self.State = 'insert'
    def MainLoop(self):
        # We're setting up the first box, as we start the program...
        self.h = self.terminal.height
        self.w = self.terminal.width
        # Let's set this to the 'active' box, which will move our cursor to it.
        self.registerNewBox(boxWindow(size=(int(self.h/2), int(self.w/2)), pos=(int(self.h/4),int(self.w/4)), level=1, name='Main'))
        msg = Msg('active_box', mtype='ACTIVATE_BOX', code=boxWindow(size=(int(self.h/2), int(self.w/2)), pos=(int(self.h/4),int(self.w/4)), level=1, name='Main'))
        self.SendMessage(msg)
        while self.Run:
            self.start_clock()
            self.SortMessages()
            self.end_clock()
    def HandleMessage(self, msg):
        if msg.mtype == 'INPUT':
            if msg.code.code == self.terminal.KEY_ESCAPE:
                self.State = 'command'
            elif self.State == 'command':
                # Move windows, if necessary.  We already know we have an input message...
                if msg.code.code == self.terminal.KEY_LEFT:
                    self.nextBox()
                if msg.code.code == self.terminal.KEY_RIGHT:
                    self.prevBox()

                if msg.code == 'i':
                    self.State = 'insert'
                if msg.code == 'A':
                    msg = Msg('new_box', mtype='NEW_BOX', code=boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=1, name='New'))
                    self.SendMessage(msg)
                    # This usually has to wait, I'm afraid, so we can't pull from the Boxes list yet.  We just send in something with the proper name and level, though.
                    msg = Msg('new_box', mtype='ACTIVATE_BOX', code=boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=1, name='New'))
                    self.SendMessage(msg)
                if msg.code == 'q':
                    self.MsgBus.KillSystems()
                if msg.code == 'P':
                    string = 'Hey!  This is a test message that we are sending when something happens.  Can I write to the correct window?  LET US FIND OUT.'
                    msg = Msg('print_data', mtype='PRINT_DATA', code={ 'box': self.ActiveBox, 'data': string })
                    self.SendMessage(msg)
            elif self.State == 'insert':
                    if msg.code.code == None:
                        # We're just handling raw input, here.
                        msg = Msg('print_data', mtype='PRINT_CHAR', code={ 'box': self.ActiveBox, 'data': msg.code })
                        self.SendMessage(msg)


        elif msg.mtype == 'ACTIVATE_BOX':
            # Stored in the code is the box object information
            self.activateBox(msg.code)
        elif msg.mtype == 'NEW_BOX':
            # Stored in the code is the box object information
            self.registerNewBox(msg.code)

    def nextBox(self):
        stop_next = False
        level = self.ActiveBox.level - 1
        if len(self.Boxes[level]) > 1:
            for box in self.Boxes[level].values():
                if stop_next == True:
                    msg = Msg('activate_box', mtype='ACTIVATE_BOX', code=box)
                    self.SendMessage(msg)
                    stop_next = False
                if self.ActiveBox.name == box.name:
                    stop_next = True

    def prevBox(self):
        stop_now = False
        level = self.ActiveBox.level - 1
        returnBox = None
        if len(self.Boxes[level]) > 1:
            for box in self.Boxes[level].values():
                if self.ActiveBox.name == box.name:
                    stop_now = True
                    if returnBox == None:
                        returnBox = box
                if stop_now == True:
                    msg = Msg('activate_box', mtype='ACTIVATE_BOX', code=returnBox)
                    self.SendMessage(msg)
                    stop_now = False
                returnBox = box


    def activateBox(self, box):
        # We move the cursor to the active box, then set active box to the current one.
        pos = self.Boxes[box.level-1][box.name]
        msg = Msg('move cursor', mtype='MOVE_CURSOR', code=(pos.pos[0]+1, pos.pos[1]+1))
        self.SendMessage(msg)
        self.ActiveBox = box

    def registerNewBox(self, box):
        # Here, we create a new box to draw.  It has a level and a certain position.
        # If we don't have that many levels, we'll enlarge our list of dictionaries until we do.
        while len(self.Boxes) < box.level:
            self.Boxes.append({})
        self.Boxes[box.level-1][box.name] = box
    def getActiveBox(self):
        return self.ActiveBox
    def getState(self):
        return self.State

class TerminalPrinter(Systems):
    def __init__(self, MsgBusInstance, terminal, AppStateInstance):
        # This also handles creating and printing to windows.
        Systems.__init__(self, MsgBusInstance)
        self.terminal = terminal
        self.AppState = AppStateInstance
        self.csr = self.terminal.get_location()
        #self.csr = self.AppState.csr
        self.Boxes = self.AppState.Boxes
        self.ActiveBox = self.AppState.getActiveBox
        self.State = self.AppState.getState

    def HandleMessage(self, msg):
        if msg.mtype == 'INPUT':
            # Let's handle how we do the cursor, yeah?
            if msg.code.code != None:
                # We don't want to move out of the box...
                # ... so this global input keeps us moving around the current, active box.
                if self.State() == 'insert':
                    if msg.code.code == self.terminal.KEY_LEFT:
                        if self.csr[1] - 1 > self.ActiveBox().pos[1]:
                            self.csr = (self.csr[0], self.csr[1] - 1)
                    elif msg.code.code == self.terminal.KEY_RIGHT:
                        if self.csr[1] + 1 < self.ActiveBox().pos[1] + self.ActiveBox().size[1] - 1:
                            self.csr = (self.csr[0], self.csr[1] + 1)
                    elif msg.code.code == self.terminal.KEY_DOWN:
                        if self.csr[0] + 1 < self.ActiveBox().pos[0] + self.ActiveBox().size[0] - 1:
                            self.csr = (self.csr[0] + 1, self.csr[1])
                    elif msg.code.code == self.terminal.KEY_UP:
                        if self.csr[0] - 1 > self.ActiveBox().pos[0]:
                            self.csr = (self.csr[0] - 1, self.csr[1])
        elif msg.mtype == 'MOVE_CURSOR':
            self.csr = msg.code
        elif msg.mtype == 'PRINT_DATA':
            self.printToBox(msg.code['box'], msg.code['data'])
        elif msg.mtype == 'PRINT_CHAR':
            self.printAtChar(msg.code['data'])

    def loopBoxes(self):
        for level in range(0,len(self.Boxes)):
            # First, get the box object, and the position...
            for box in self.Boxes[level].values():
                # ... now draw it.
                if box.drawn == False:
                    self.drawBox(box)
                    box.drawn = True

    def drawBox(self, box):
        for y in range(0, box.size[0]):
            if y == 0 or y == box.size[0] - 1:
                for x in range(0, box.size[1]):
                    print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + '-')
            else:
                for x in [0, box.size[1]]:
                    print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + '|')

    def printAtChar(self, data):
        #print((self.terminal.move(self.csr[0], self.csr[1]) + data))
        print(data)
        self.csr = (self.csr[0], self.csr[1] + 1)

    def printToBox(self, box, data):
        i = 0
        # We just sort through and print.  Probably not that fast, but it'll work for the moment.
        for y in range(1, box.size[0]-1):
            for x in range(1, box.size[1]-1):
                # Top or bottom of the box!
                if i < len(data) - 1:
                    print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + data[i])
                    i += 1
                else:
                    self.csr = (y+box.pos[0],x+box.pos[1]+1)
                    break

    def MainLoop(self):
        # Let's set up the terminal!
        with self.terminal.fullscreen():
            while self.Run:
                self.start_clock()
                # Move the cursor to the current position.
                print((self.terminal.move(self.csr[0], self.csr[1])), end='')
                # Draw all the boxes we want to draw!
                self.loopBoxes()
                self.SortMessages()
                self.end_clock()
                sys.stdout.flush()

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
appstate = AppState(msgbus, terminal)
termprint = TerminalPrinter(msgbus, terminal, appstate)
msgbus.RegisterSystem(appstate)
msgbus.RegisterSystem(termprint)
msgbus.RegisterSystem(inputsys)
msgbus.LaunchSystems()
msgbus.MainLoop()
