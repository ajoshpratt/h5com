#! /usr/bin/env python2.7

from __future__ import print_function, division; __metaclass__ = type

import numpy as np
import h5py
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
import os, sys, select, time

from threading import Thread

import blessed
from blessed import Terminal
# This is Python3.  Python2 has Queue.
#from queue import Queue
from Queue import Queue
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
        self.Run = False
        for i in range(0, len(self.Systems)):
            self.Systems[i].Run = False
        #    self.SystemThreads[i].join()
        #sys.exit(0)
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
                #if keypress.code == 'q':
                #    # shut it down.
                #    self.Run = False

class AppState(Systems):
    def __init__(self, MsgBusInstance, terminal, h5file):
        Systems.__init__(self, MsgBusInstance)
        self.terminal = terminal
        self.ActiveBox = None
        self.ActiveKeys = None
        self.Boxes = [{}]
        self.h5file = h5file
        # Possible states: insert, command
        self.State = 'command'
        self.h = self.terminal.height
        self.w = self.terminal.width
        self.storedCommand = '/'
        self.potentialCommand = ''
        self.potentialCommandId = -1
    def MainLoop(self):
        # We're setting up the first box, as we start the program...
        #self.h = self.terminal.height
        #self.w = self.terminal.width
        # Let's set this to the 'active' box, which will move our cursor to it.
        #self.registerNewBox(boxWindow(size=(int(self.h/2), int(self.w/2)), pos=(int(self.h/4),int(self.w/4)), level=1, name='Main'))
        #msg = Msg('active_box', mtype='ACTIVATE_BOX', code=boxWindow(size=(int(self.h/2), int(self.w/2)), pos=(int(self.h/4),int(self.w/4)), level=1, name='Main'))
        #self.SendMessage(msg)
        self.modeWindow(self.State)
        while self.Run:
            self.start_clock()
            self.SortMessages()
            self.end_clock()
    def HandleMessage(self, msg):
        if msg.mtype == 'RETURN_CURRENT_KEYS':
            self.ActiveKeys = msg.code
        if msg.mtype == 'INPUT':
            if msg.code.code == self.terminal.KEY_ESCAPE:
                self.State = 'command'
                self.modeWindow(self.State)
            elif self.State == '/':
                # We're going into 'terminal' mode.
                # If we're not using tab...
                if msg.code.code == 512:
                    if self.potentialCommandId >= len(self.ActiveKeys)-1:
                        self.potentialCommandId = -1
                    for ii,i in enumerate(self.ActiveKeys):
                        if self.storedCommand[1:] in i and self.potentialCommandId < ii:
                            self.potentialCommand = '/' + str(i)
                            self.potentialCommandId = ii
                            self.modeWindow(self.potentialCommand)
                            break
                if msg.code.code == self.terminal.KEY_BACKSPACE:
                    self.potentialCommand = ''
                    self.potentialCommandId = -1
                    self.storeInput(msg.code)
                    self.modeWindow(self.storedCommand)
                if msg.code.code == self.terminal.KEY_ENTER:
                    self.storedCommand = self.potentialCommand
                    self.potentialCommand = ''
                    self.potentialCommandId = -1
                    self.storeInput(msg.code)
                    self.modeWindow(self.storedCommand)
                else:
                    self.storeInput(msg.code)
                    if self.potentialCommandId == -1:
                        self.modeWindow(self.storedCommand)
            elif self.State == 'move':
                if msg.code.code == self.terminal.KEY_LEFT:
                    self.nextBox()
                if msg.code.code == self.terminal.KEY_RIGHT:
                    self.prevBox()
            elif self.State == 'command':
                # Move windows, if necessary.  We already know we have an input message...

                #if msg.code == 'l':
                #    msg = Msg('new_box', mtype='H5_LOAD', code=None)
                #    self.SendMessage(msg)
                if msg.code == 'i':
                    self.State = 'insert'
                    self.modeWindow(self.State)
                if msg.code == 'm':
                    self.State = 'move'
                    self.modeWindow(self.State)
                if msg.code == '/':
                    self.State = '/'
                    self.modeWindow(self.State)
                    # Let's get the current active keys!
                    newmsg = Msg('input!', mtype='H5_RETURN_CURRENT_KEYS', code={})
                    self.SendMessage(newmsg)
                if msg.code == 'e':
                    for i in range(0, 8):
                        msg = Msg('input!', mtype='INPUT', code=Msg('', mtype='', code=self.terminal.KEY_RIGHT))
                        self.SendMessage(msg)
                #if msg.code == 'A':
                #    msg = Msg('new_box', mtype='NEW_BOX', code=boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=1, name='New'))
                #    self.SendMessage(msg)
                    # This usually has to wait, I'm afraid, so we can't pull from the Boxes list yet.  We just send in something with the proper name and level, though.
                #    msg = Msg('new_box', mtype='ACTIVATE_BOX', code=boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=1, name='New'))
                #    self.SendMessage(msg)
                if msg.code == 'q':
                    self.MsgBus.KillSystems()
                #if msg.code == 'P':
                #    string = 'Hey!  This is a test message that we are sending when something happens.  Can I write to the correct window?  LET US FIND OUT.'
                #    msg = Msg('print_data', mtype='PRINT_DATA', code={ 'box': self.ActiveBox, 'data': string })
                #    self.SendMessage(msg)
                if msg.code != None:
                    if msg.code.code == self.terminal.KEY_BACKSPACE or msg.code.code == self.terminal.KEY_DELETE:
                        # Now we'll try and load up a dataset, and print it to another window... or just modify the current, maybe?  We'll see.
                        msg = Msg('load_item', mtype='H5_PREV_GROUP', code=None)
                        self.SendMessage(msg)
                    elif msg.code.code == self.terminal.KEY_ENTER:
                        # Now we'll try and load up a dataset, and print it to another window... or just modify the current, maybe?  We'll see.
                        msg = Msg('load_item', mtype='H5_LOAD', code=None)
                        self.SendMessage(msg)
            elif self.State == 'insert':
                    if msg.code.code == None:
                        # We're just handling raw input, here.
                        msg = Msg('print_data', mtype='PRINT_CHAR', code={ 'box': self.ActiveBox, 'data': msg.code })
                        self.SendMessage(msg)


        elif msg.mtype == 'ACTIVATE_BOX':
            # Stored in the code is the box object information
            self.activateBox(msg.code)
            self.State = 'command'
        elif msg.mtype == 'NEW_BOX':
            # Stored in the code is the box object information
            self.registerNewBox(msg.code)
            #self.State = 'command'
        elif msg.mtype == 'PRINT_COMMAND':
            self.modeWindow(msg.code)

    def modeWindow(self, dataset):
        box = boxWindow(size=(3, int(self.w)), pos=(int(self.h-4),int(1)), level=3, name='Mode', data=[dataset])
        box.decorate = False
        box.damaged = True
        msg = Msg('new_box', mtype='NEW_BOX', code=box)
        self.SendMessage(msg)

    def tabWindow(self, dataset):
        box = boxWindow(size=(3, int(self.w)), pos=(int(self.h-3),int(1)), level=3, name='tab', data=[dataset])
        box.decorate = False
        box.damaged = True
        msg = Msg('new_box', mtype='NEW_BOX', code=box)
        self.SendMessage(msg)

    def storeInput(self, char):
        if char.code == self.terminal.KEY_ENTER:
            msg = Msg('handle_input', mtype='H5_USER_LOAD', code=self.storedCommand[1:])
            self.SendMessage(msg)
            self.storedCommand = '/'
            self.State = 'command'
            self.modeWindow(self.State)
        elif char.code == 330:
            self.storedCommand = self.storedCommand[:-1]
        elif char.code == 512:
            pass
        else:
            self.storedCommand += char

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

class H5DataLoader(Systems):
    def __init__(self, MsgBusInstance, AppStateInstance, TerminalInstance, terminal):
        Systems.__init__(self, MsgBusInstance)
        self.h5 = h5py.File(AppStateInstance.h5file)
        # We've initialized and the loaded the file.  Now what do we need?  We need to load and print the datasets...
        self.AppState = AppStateInstance
        #self.csr = self.AppState.csr
        self.ActiveBox = self.AppState.getActiveBox
        self.currentGroup = '/'
        self.ActiveKeys = []
        self.Terminal = TerminalInstance
        self.csr = self.Terminal.returnBoxCsr
        self.terminal = terminal
        self.h = self.terminal.height
        self.w = self.terminal.width
    def HandleMessage(self, msg):
        # We need to set a current dataset/group...
        # When we print a message to the terminal, we want what dataset we get to... well, we'll just see.
        if msg.mtype == 'H5_RETURN_CURRENT_KEYS':
            msg = Msg('print_data', mtype='RETURN_CURRENT_KEYS', code=self.returnGroupKeys(self.currentGroup))
            self.SendMessage(msg)
        if msg.mtype == 'H5_PRINT_CURRENT':
            self.printGroupKeys(self.currentGroup, self.ActiveBox())
        if msg.mtype == 'H5_GET_DATASET':
            msg = Msg('print_data', mtype='PRINT_DATA', code={ 'box': self.ActiveBox(), 'data': str(self.h5[msg.code]) })
            self.SendMessage(msg)
        if msg.mtype == 'H5_SWITCH_GROUP':
            self.currentGroup = msg.code
        if msg.mtype == 'H5_PREV_GROUP':
            self.prevGroup()
            self.returnGroupKeys(self.currentGroup)
            box = boxWindow(size=(int(self.h-5), int(self.w/4)), pos=(int(1),int(1)), level=1, name='Main', data=self.ActiveKeys)
            #box = boxWindow(size=(int(self.h/4), int(self.w/4)), pos=(0,0), level=1, name='New', data=self.ActiveKeys)
            msg = Msg('new_box', mtype='NEW_BOX', code=box)
            self.SendMessage(msg)
            # This usually has to wait, I'm afraid, so we can't pull from the Boxes list yet.  We just send in something with the proper name and level, though.
            msg = Msg('new_box', mtype='ACTIVATE_BOX', code=box)
            self.SendMessage(msg)
        if msg.mtype == 'H5_RETURN_CURRENT_GROUP':
            msg = Msg('print_data', mtype='H5_GROUP', code=self.currentGroup)
            self.SendMessage(msg)
        if msg.mtype == 'H5_LOAD':
            try:
                self.changeGroup(self.ActiveKeys[self.csr(self.ActiveBox())[0] + self.ActiveBox().y_coord[0]])
            except:
                # This happens when we load up the dataset for the first time.
                pass
            # We'll just check to see if it's a group.  Otherwise, it's a dataset.
            try:
                # This shouldn't really be happening unless we ACTUALLY change groups.  But hey...
                self.returnGroupKeys(self.currentGroup)
                box = boxWindow(size=(int(self.h-5), int(self.w/4)), pos=(int(1),int(1)), level=1, name='Main', data=self.ActiveKeys)
            except:
                self.returnDataset(self.currentGroup)
                box = boxWindow(size=(int(self.h-5), int(self.w/4*3)-5), pos=(int(1),int(self.w/4)+5), level=2, name='Data', data=self.data)
                box.isGrid = True
            msg = Msg('new_box', mtype='NEW_BOX', code=box)
            self.SendMessage(msg)
            msg = Msg('new_box', mtype='ACTIVATE_BOX', code=box)
            try:
                self.ActiveBox().damaged = False
            except:
                pass
            self.SendMessage(msg)
            self.statusWindow(self.currentGroup)
        if msg.mtype == 'H5_USER_LOAD':
            group = str(self.currentGroup)
            try:
                self.changeGroup(msg.code)
                try:
                    # This shouldn't really be happening unless we ACTUALLY change groups.  But hey...
                    self.returnGroupKeys(self.currentGroup)
                    box = boxWindow(size=(int(self.h-5), int(self.w/4)), pos=(int(1),int(1)), level=1, name='Main', data=self.ActiveKeys)
                except:
                    self.returnDataset(self.currentGroup)
                    box = boxWindow(size=(int(self.h-5), int(self.w/4*3)-5), pos=(int(1),int(self.w/4)+5), level=2, name='Data', data=self.data)
                    box.isGrid = True
                msg = Msg('new_box', mtype='NEW_BOX', code=box)
                self.SendMessage(msg)
                msg = Msg('new_box', mtype='ACTIVATE_BOX', code=box)
                try:
                    self.ActiveBox().damaged = False
                except:
                    pass
                self.SendMessage(msg)
                self.statusWindow(self.currentGroup)
            except:
                self.currentGroup = group
                self.statusWindow(self.currentGroup)
                msg = Msg('print_data', mtype='H5_GROUP', code=self.currentGroup)
                self.SendMessage(msg)
            # We'll just check to see if it's a group.  Otherwise, it's a dataset.

    def statusWindow(self, dataset):
        box = boxWindow(size=(3, int(self.w)), pos=(int(self.h-3),int(1)), level=1, name='Status', data=[dataset])
        box.decorate = False
        msg = Msg('new_box', mtype='NEW_BOX', code=box)
        self.SendMessage(msg)

    def changeGroup(self, newGroup):
        self.currentGroup += newGroup + '/'
        self.statusWindow(self.currentGroup)

    def prevGroup(self):
        currentGroup = '/' + str.join('/', list(filter(None, self.currentGroup.split('/')))[0:-1]) + '/'
        if currentGroup[1] == '/':
            currentGroup = currentGroup[1:]
        self.currentGroup = currentGroup
        self.statusWindow(self.currentGroup)

    def returnGroupKeys(self, group):
        self.ActiveKeys = []
        for key, value in self.h5[group].items():
            # Should we do it here, or have the other sort it out?
            self.ActiveKeys.append(key)
        return self.ActiveKeys

    def returnDataset(self, group):
        #self.data = []
        #for item in range(0, self.h5[group].shape[0]):
            # Should we do it here, or have the other sort it out?
        #    self.data.append(self.h5[group][item,:])
        self.data = self.h5[group][:]

    def MainLoop(self):
            while self.Run:
                self.start_clock()
                self.SortMessages()
                self.end_clock()


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
                if self.State() == 'insert' or self.State() == 'command':
                    if msg.code.code == self.terminal.KEY_LEFT:
                        if self.ActiveBox().isGrid == False:
                            if self.csr[1] - 1 > self.ActiveBox().pos[1]:
                                self.csr = (self.csr[0], self.csr[1] - 1)
                            else:
                                self.ActiveBox().move_left()
                        else:
                            self.ActiveBox().move_left()
                    elif msg.code.code == self.terminal.KEY_RIGHT:
                        # Check if the active box is a grid.
                        if self.ActiveBox().isGrid == False:
                            if self.csr[1] + 1 < self.ActiveBox().pos[1] + self.ActiveBox().size[1] - 1:
                                self.csr = (self.csr[0], self.csr[1] + 1)
                            else:
                                # Useful for debugging.
                                newmsg = Msg('print_data', mtype='PRINT_COMMAND', code=(self.ActiveBox().x_coord, self.ActiveBox().data.shape[1]))
                                #msg.mtype = mtype='PRINT_COMMAND'
                                #msg.code.code = (self.ActiveBox().x_coord, self.ActiveBox().data.shape[0])
                                #self.SendMessage(newmsg)
                                self.ActiveBox().move_right()
                        else:
                            self.ActiveBox().move_right()
                    elif msg.code.code == self.terminal.KEY_DOWN:
                        if self.ActiveBox().isGrid == False:
                            if self.csr[0] + 1 < self.ActiveBox().pos[0] + self.ActiveBox().size[0] - 1:
                                if self.csr[0] + 1 - self.ActiveBox().pos[0] <= self.ActiveBox().y_items:
                                    self.csr = (self.csr[0] + 1, self.csr[1])
                                    self.ActiveBox().damaged = True
                            else:
                                self.ActiveBox().move_down()
                                self.ActiveBox().damaged = True
                        else:
                            self.ActiveBox().move_down()
                            self.ActiveBox().damaged = True
                    elif msg.code.code == self.terminal.KEY_UP:
                        if self.ActiveBox().isGrid == False:
                            if self.csr[0] - 1 > self.ActiveBox().pos[0]:
                                if self.csr[0] - 1 - self.ActiveBox().pos[0] >= 0:
                                    self.csr = (self.csr[0] - 1, self.csr[1])
                                    self.ActiveBox().damaged = True

                            else:
                                self.ActiveBox().move_up()
                                self.ActiveBox().damaged = True
                        else:
                            self.ActiveBox().move_up()
                            self.ActiveBox().damaged = True
                    # Temp standin for page down
                    elif msg.code.code == 338:
                        # What is the height?
                        if self.ActiveBox().isGrid == False:
                            if self.csr[0] + 10 < self.ActiveBox().pos[0] + self.ActiveBox().size[0] - 10:
                                if self.csr[0] + 10 - self.ActiveBox().pos[0] <= self.ActiveBox().y_items:
                                    self.csr = (self.csr[0] + 10, self.csr[1])
                                    self.ActiveBox().damaged = True
                            else:
                                self.ActiveBox().move_down(10)
                                self.ActiveBox().damaged = True
                        else:
                            self.ActiveBox().move_down(10)
                            self.ActiveBox().damaged = True
                    if msg.code.code == 339:
                        # What is the height?
                        if self.ActiveBox().isGrid == False:
                            if self.csr[0] - 10 > self.ActiveBox().pos[0]:
                                if self.csr[0] - 10 - self.ActiveBox().pos[0] >= 0:
                                    self.csr = (self.csr[0] - 10, self.csr[1])
                                    self.ActiveBox().damaged = True
                            else:
                                self.ActiveBox().move_up(10)
                                self.ActiveBox().damaged = True
                        else:
                            self.ActiveBox().move_up(10)
                            self.ActiveBox().damaged = True
            if self.State() == 'command':
                if msg.code == '+':
                    # What is the height?
                    #print(msg.code)
                    self.ActiveBox().move_layer_up()
                if msg.code == '-':
                    # What is the height?
                    self.ActiveBox().move_layer_down()
        elif msg.mtype == 'MOVE_CURSOR':
            self.csr = msg.code
            self.ActiveBox().damaged = True
        elif msg.mtype == 'PRINT_DATA':
            self.printToBox(msg.code['box'], msg.code['data'])
        elif msg.mtype == 'PRINT_CHAR':
            self.printAtChar(msg.code['data'])

    def loopBoxes(self):
        for level in range(0,len(self.Boxes)):
            # First, get the box object, and the position...
            for box in self.Boxes[level].values():
                # ... now draw it.
                if box.damaged == True:
                    self.clearBoxFast(box)
                    #self.clearBox(box)
                    # THIS FUNCTION IS SUPER SLOW.
                    if box.decorate == True:
                        self.drawBox(box)
                    if box.isGrid == False:
                        self.printListBox(box, box.draw_data)
                    else:
                        self.printGridBox(box, box.draw_data)
                    box.damaged = False

    def clearBox(self, box):
        # but not the frame!
        for y in range(1, box.size[0]-1):
            for x in range(1, box.size[1]-1):
                # FILL CODE
                print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + ' ')

    def clearBoxFast(self, box):
        for y in range(1, box.size[0]-1):
            #clearstring = str('|'*(box.size[1]-2) + '\n')*(box.size[0]-2)
            clearstring = str(' '*(box.size[1]-1))
            print(self.terminal.move(box.pos[0]+y,box.pos[1]) + clearstring)
        #clearstring = str((box.size))

    def drawBox(self, box):
        x_offset = 0
        for y in range(0, box.size[0]+1):
            if y == 0:
                for x in range(0, box.size[1]+1-len(box.name)-3):
                    # This is the top!
                    if x == 0:
                        print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + u'\u250c')
                    elif x == box.size[1]-len(box.name)-3:
                        print(self.terminal.move(y+box.pos[0],x+x_offset+box.pos[1]) + u'\u2510')
                    elif x == int(box.size[1]/2)-int((len(box.name)+4)/2):
                        print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + u'\u2524 ' + box.name + ' ' + u'\u251c')
                        x_offset = len(box.name)+3
                    else:
                        print(self.terminal.move(y+box.pos[0],x+x_offset+box.pos[1]) + u'\u2500')
            elif y == box.size[0]:
                for x in range(0, box.size[1]+1):
                    # This is the top!
                    if x == 0:
                        print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + u'\u2514')
                    elif x == box.size[1]:
                        print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + u'\u2518')
                    else:
                        print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + u'\u2500')

            else:
                for x in [0, box.size[1]]:
                    print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + u'\u2502')

    def printAtChar(self, data):
        #print((self.terminal.move(self.csr[0], self.csr[1]) + data))
        print(data)
        self.csr = (self.csr[0], self.csr[1] + 1)

    def printListBox(self, box, data):
        i = 0
        y = 1
        x = 1
        underline = False
        # Here, we assume the data is a list.
        for item in data:
            # We want to know if the current item is highlighted...
            if self.csr[0] == y + 1:
                underline = True
            if len(item) < box.size[1]:
                if underline == True:
                    print(self.terminal.underline + self.terminal.move(y+box.pos[0],x+box.pos[1]) + str(item) + self.terminal.normal)
                else:
                    print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + str(item))
            else:
                if underline == True:
                    print(self.terminal.underline + self.terminal.move(y+box.pos[0],x+box.pos[1]) + str(item[0:box.size[1]]) + self.terminal.normal)
                else:
                    print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + str(item[0:box.size[1]]))
            underline = False
            y += 1
            if y == box.size[0]-1:
                break

    def printGridBox(self, box, data):
        i = 0
        y = 1
        x = 1
        # Data is a numpy array.  We can't sort through it the normal way; instead, we want to print it item by item.
        stringToPrint = ''
        for iline, line in enumerate(data):
            if iline == 0:
                if data.dtype.names == None:
                    # We're printing headers, here!  But what if we're not a blah blah blah?
                    #padding = int(np.ceil(np.log10(data.shape[0]))) + 1
                    padding = int(np.ceil(np.log10(data.shape[0]))) + 1
                    padding = int(np.ceil(np.log10(box.y_items))) + 1
                    #padding = 8
                    stringToPrint += ' '*padding + ' '
                    for iitem in range(box.x_coord[0], box.x_coord[1]):
                        padding = 8
                        item = str(iitem).zfill(padding)
                        stringToPrint += ' ' + item + ' '
                        x += 1
                        if x == box.cells - 1:
                            x = 1
                            break
                else:
                    padding = int(np.ceil(np.log10(data.shape[0]))) + 1
                    #padding = 8
                    padding = int(np.ceil(np.log10(box.y_items))) + 1
                    stringToPrint += ' '*padding + ' '
                    for item in data.dtype.names:
                        new_padding = 8
                        if len(str(item)) > new_padding:
                            item = str(item)[0:new_padding]
                        else:
                            item = str(item) + (' '*(new_padding-len(str(item))))
                        stringToPrint += ' ' + item + ' '
                        x += 1
                        if x == box.cells - 1:
                            x = 1
                            break

                print(self.terminal.move(y+box.pos[0]+1,box.pos[1]+1) + str(stringToPrint))
                y += 1
                stringToPrint = ''
            try:
                for iitem, item in enumerate(line):
                    # Our box should ultimately have a 'cell', and we just jump to cell coordinates.  Eventually.
                    #for x in range(0, box.cells):
                    new_padding = int(np.ceil(np.log10(data.shape[0]))) + 1
                    new_padding = 8
                    new_padding = box.n_digits + 4
                    # Spacing, you know?
                    if iitem == 0:
                        #padding = int(np.ceil(np.log10(data.shape[0]))) + 1
                        padding = int(np.ceil(np.log10(box.y_items))) + 1
                        stringToPrint += str(iline+box.y_coord[0]).zfill(padding) + (' ')
                    if type(item) is np.float32 or type(item) is np.double:
                        item = '%.2e' % float(item)
                    else:
                        if len(str(item)) > new_padding:
                            item = str(item)[0:new_padding]
                        else:
                            item = str(item) + (' '*(new_padding-len(str(item))))
                    stringToPrint += ' ' + item + ' '
                    x += 1
                    if x == box.cells - 1:
                        x = 1
                        break
            except:
                # We should really just try and sort the dataset.  But this is 'single value' sets which are sooort of escaping
                # the logic used to sort the data shape.
                    padding = int(np.ceil(np.log10(data.shape[0]))) + 1
                    stringToPrint += str(iline+box.y_coord[0]).zfill(padding) + '   '
                    if type(line) is float:
                        item = '%.2e' % float(line)
                    else:
                        item = str(line)
                    stringToPrint += ' ' + item + ' '
            print(self.terminal.move(y+box.pos[0]+1,box.pos[1]+1) + str(stringToPrint))
            stringToPrint = ''
            y += 1
            if y == box.size[0]-2:
                break

    def printToBox(self, box, data):
        i = 0
        y = 1
        x = 1
        # We just sort through and print.  Probably not that fast, but it'll work for the moment.
        while i < len(data) - 1:
            #while y < box.size[0]-1:
            #    while x < box.size[1]-1:
                # So, this is the character position of the box.  We're temporarily looping through, but...
                # .. what we really want to do is work like a typewriter.
            try:
                if data[i:i+1] == '\n':
                    y += 1
                    x  = 0
            except:
                pass

            if x == box.size[1]-1:
                x  = 0
                y += 1
            if y == box.size[0]-1:
                if x == box.size[1]-1:
                    break
            print(self.terminal.move(y+box.pos[0],x+box.pos[1]) + data[i])
            i += 1
            x += 1
            #x = 0
            #y += 1
        #self.csr = (y+box.pos[0],x+box.pos[1])
    def returnBoxCsr(self, box):
        return (self.csr[0] - box.pos[0]-1, self.csr[1] - box.pos[1]-1)


    def MainLoop(self):
        # Let's set up the terminal!
        with self.terminal.hidden_cursor():
            with self.terminal.fullscreen():
                while self.Run:
                    self.start_clock()
                    # Move the cursor to the current position.
                    # Draw all the boxes we want to draw!
                    #with self.terminal.hidden_cursor():
                    self.loopBoxes()
                    # Can we highlight the entire box line?
                    #with self.terminal.hidden_cursor():
                    #print(self.terminal.move(self.csr[0], self.csr[1]), end='')

                    #print(self.terminal.normal)
                    #print(self.terminal.color(5))
                    #try:
                    #    with self.terminal.location(self.ActiveBox().pos[0], self.csr[1]):
                    #except:
                    #    pass
                    self.SortMessages()
                    self.end_clock()
                    sys.stdout.flush()

class boxWindow():
    def __init__(self, size, pos, level, name, data=None):
        self.size = size
        self.pos = pos
        self.name = name
        self.level = level
        self.drawn = False
        self.new = True
        # These are values about the window on the dataset, here...
        self.y_coord = (0, self.size[0] - 1)
        # This coord is a little more difficult.  Just using the box size isn't good enough,
        # as we need to also limit the number of elements we show.  Ergo, let's start with... 3
        #self.x_coord = (0, self.size[1] - 1)
        # Let's say we always want to show... oh, 4 digits.
        # How many cells do we have?  Well, we need space, so that's 6 for each...
        self.n_digits = 4
        try:
            self.cells = min((int(np.floor(self.size[1]/(self.n_digits+5)))) - 1, data.shape[1]-1)
        except:
            self.cells = 1
        self.x_coord = (0, self.cells)
        self.data = data
        self.damaged = True
        self.decorate = True
        self.isGrid = False
        self.y_items = 0
        # Let's set it to layer 0, here...
        if self.data != None:
            self.sort_data()
        self.activeLayer = 0
        self.updateDrawData()
    def sort_data(self):
        # It works by drawing lines.
        # Let's assume the data is brought in as a list or numpy array.  It's not hard, whatever.
        # First, figure out the number of dimensions...
        try:
            self.dim = len(self.data.shape)
        except:
            # we're a list, then!
            # We shouldn't really assume 1 dimension, but it's fine for now.
            self.dim = 1
            self.y_items = len(self.data)
        # If it's two dimensions, our number of layers are 1.  Otherwise, we set
        # it to the third value.
        if self.dim == 2:
            self.y_items = self.data.shape[0]
        elif self.dim == 1:
            self.y_items = len(self.data)
        else:
            self.layers = self.data.shape[2]
            self.y_items = self.data.shape[0]
    def updateDrawData(self):
        if self.dim == 3:
            self.draw_data = self.data[self.y_coord[0]:self.y_coord[1],self.x_coord[0]:self.x_coord[1],self.activeLayer]
        elif self.dim == 2:
            self.draw_data = self.data[self.y_coord[0]:self.y_coord[1],self.x_coord[0]:self.x_coord[1]]
        else:
            self.draw_data = self.data[self.y_coord[0]:self.y_coord[1]]
    def move_down(self, items=1):
        if self.y_coord[1] < self.data.shape[0]:
            self.y_coord = (self.y_coord[0]+items, self.y_coord[1]+items)
            self.updateDrawData()
            self.damaged = True
    def move_up(self, items=1):
        if self.y_coord[0] > 0:
            self.y_coord = (self.y_coord[0]-items, self.y_coord[1]-items)
            self.updateDrawData()
            self.damaged = True
    def move_left(self):
        if self.x_coord[0] > 0:
            self.x_coord = (self.x_coord[0]-1, self.x_coord[1]-1)
            self.updateDrawData()
            self.damaged = True
    def move_right(self):
        # If this doesn't work, then eh.
        # If we have a complex datatype with N values, we'll need to figure that out.
        if len(self.data.shape) > 1:
            comparison = self.data.shape[1]
        else:
            comparison = len(self.data.dtype)
        if self.x_coord[1] <= comparison:
            self.x_coord = (self.x_coord[0]+1, self.x_coord[1]+1)
            self.updateDrawData()
            self.damaged = True
    def move_layer_up(self):
        if self.dim == 3:
            if self.activeLayer < self.data.shape[2]-1:
                self.activeLayer += 1
                self.updateDrawData()
                self.damaged = True
    def move_layer_down(self):
        if self.dim == 3:
            if self.activeLayer > 0:
                self.activeLayer -= 1
                self.updateDrawData()
                self.damaged = True

    # There's no real limit on how big a box can be, internally.
    # We just have a window into it, and that's the 'size'.
    # We should be able to shift the viewport...
    # ... so we should be able to store and sort through lines of data.

msgbus = MsgBus()
terminal = Terminal()
inputsys = Input(msgbus, terminal)
import sys
appstate = AppState(msgbus, terminal, sys.argv[1])
termprint = TerminalPrinter(msgbus, terminal, appstate)
dataloader = H5DataLoader(msgbus, appstate, termprint, terminal)
msgbus.RegisterSystem(appstate)
msgbus.RegisterSystem(termprint)
msgbus.RegisterSystem(inputsys)
msgbus.RegisterSystem(dataloader)
msgbus.LaunchSystems()
# Let's create a message and load up the file!
msg = Msg('new_box', mtype='H5_LOAD', code=None)
appstate.SendMessage(msg)
msgbus.MainLoop()
