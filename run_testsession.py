from FlashSession import FlashSession
from psychopy.hardware.emulator import launchScan
from psychopy import core

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass

sess = FlashSession(subject_initials='SM', index_number=1, scanner='n', tracker_on=True)
sess.scanner = launchScan(win=sess.screen, settings={'TR': 2, 'volumes': 100, 'sync': 't'}, mode='Test')

if sess.dummy_tracker:  # annoyingly, launchScan removes the mouse visibility - get it back for dummy tracking...
    sess.screen.setMouseVisible(True)

sess.run()

# Load and print latest
import cPickle as pickle
import os
from pprint import pprint
data_file = os.listdir('data')[-1]

data = pickle.load(open(os.path.join('data', data_file), 'r'))
pprint(data)
pprint(data['eventArray'])


# Quit PsychoPy processes
core.quit()
