#!/usr/bin/env python
# encoding: utf-8
from FlashSession import *
from psychopy.hardware.emulator import launchScan
from psychopy import core
import os
from standard_parameters import *

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass

# Kill Finder during execution (this will be fun)
applescript="\'tell application \"Finder\" to quit\'"
shellCmd = 'osascript -e '+applescript
os.system(shellCmd)

# Set nice to -20: extremely high PID priority
new_nice = -20
sysErr = os.system("sudo renice -n %s %s" % (new_nice, os.getpid()))
if sysErr:
    print('Warning: Failed to renice, probably you arent authorized as superuser')


# Initialize Session
sess = FlashSession(subject_initials='DEBUG', index_number=13, scanner='n', tracker_on=True)

# Launch dummy scanner
sess.scanner = launchScan(win=sess.screen, settings={'TR': 2, 'volumes': 10000, 'sync': 't'}, mode='Test')

if sess.dummy_tracker:  # annoyingly, launchScan sets mouseVisible to False - set it back to True for dummy tracking...
    sess.screen.setMouseVisible(True)

# For recording the frame intervals (debug)
sess.screen.recordFrameIntervals = True

# RUN
sess.run()

# Load and print latest data/events
import cPickle as pickle
from pprint import pprint
from glob import glob
data_file = glob('data/*_outputDict.pickle')[-1]

data = pickle.load(open(data_file, 'r'))
pprint(data)

# Quit PsychoPy processes
core.quit()
