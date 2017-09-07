from FlashSession import FlashSession
from psychopy import hardware

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass

scanner = hardware.emulator.launchScan()
sess = FlashSession(subject_initials='SM', index_number=1, scanner='n', tracker_on=False)

sess.run()

# Load and print latest
import cPickle as pickle
import os
from pprint import pprint
data_file = os.listdir('data')[-1]

data = pickle.load(open(os.path.join('data', data_file), 'r'))
pprint(data)
pprint(data['eventArray'])