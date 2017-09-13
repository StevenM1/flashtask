from FlashSession import FlashSession, FlashSessionProbBias
from psychopy.hardware.emulator import launchScan
from psychopy import core
import os

# Kill all background processes (macOS only)
try:
    import appnope
    appnope.nope()
except:
    pass


# Kill Finder during execution (this will be fun)
import os
applescript="\'tell application \"Finder\" to quit\'"
shellCmd = 'osascript -e '+applescript
os.system(shellCmd)


# Set nice to -20: extremely high PID priority
new_nice = -20
sysErr = os.system("sudo renice -n %s %s" % (new_nice, os.getpid()))
if sysErr:
    print('Warning: Failed to renice, probably you arent authorized as superuser')


# ToDo: Trial organization (phases) differently for design optimization? Maybe fixation cross during ITI,
# wait for pulse on first trial.... But how to sync during other trials?

sess = FlashSessionProbBias(subject_initials='SM', index_number=1, scanner='n', tracker_on=True)
sess.scanner = launchScan(win=sess.screen, settings={'TR': 2, 'volumes': 100, 'sync': 't'}, mode='Test')

if sess.dummy_tracker:  # annoyingly, launchScan sets mouseVisible to False - set it back to True for dummy tracking...
    sess.screen.setMouseVisible(True)

sess.screen.recordFrameIntervals = True
sess.run()


import pylab
intervalsMS = pylab.array(sess.screen.frameIntervals) * 1000
m = pylab.mean(intervalsMS)
sd = pylab.std(intervalsMS)

msg = "Mean=%.1fms, s.d.=%.2f, 99%%CI(frame)=%.2f-%.2f"
distString = msg % (m, sd, m - 2.58 * sd, m + 2.58 * sd)
nTotal = len(intervalsMS)
nDropped = sum(intervalsMS > (1.5 * m))
msg = "Dropped/Frames = %i/%i = %.3f%%"
droppedString = msg % (nDropped, nTotal, 100 * nDropped / float(nTotal))

# plot the frameintervals
pylab.figure(figsize=[12, 8])
pylab.subplot(1, 2, 1)
pylab.plot(intervalsMS, '-')
pylab.ylabel('t (ms)')
pylab.xlabel('frame N')
pylab.title(droppedString)

pylab.subplot(1, 2, 2)
pylab.hist(intervalsMS, 50, normed=0, histtype='stepfilled')
pylab.xlabel('t (ms)')
pylab.ylabel('n frames')
pylab.title(distString)
pylab.savefig('/users/steven/Desktop/frames.png')
# se=sd/pylab.sqrt(len(intervalsMS)) # for CI of the mean


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