from __future__ import division
import pygaze
from psychopy import core, visual, event
from warnings import warn

class FlashTrial(object):

    def __init__(self, window, keyboard, phase_durations=(.5, 1.5, 0.5, 1), n_flashers=2, response_keys=['z', 'm'], radius=3, flasher_size=1, debug=False, exp_handler=None):
        """ Initialize FlashTrial class. Handles everything for stimulus presentation and recording of the Flash Task 
        
        # ToDo: RECORD / LOG everything!
        
        Parameters
        ------------
        window: psychopy.visual.Window
        keyboard: pygaze.libinput.Keyboard
        phase_durations: tuple
            Contains the durations in seconds of every phase of a trial. The phases are fixation cross, stimulus presentation, feedback, and ITI.
            If the second element of the tuple is None, .. #ToDo: finish this
        n_flashers: int
            The number of flashers shown during a trial. Defaults to 2
        radius: int
            The distance of flashers in centimeters from screen center
        flasher_size: int
            Size of a flasher in centimeters
        """
        
        self.window = window
        self.keyboard = keyboard
        self.phase_durations = phase_durations
        self.n_flashers = n_flashers
        self.response_keys = response_keys
        self.debug = debug
        
        if not len(self.response_keys) == self.n_flashers:
            self.window.close()
            raise(IOError('The number of flashers is not the same as the number of key response options.'))

        self.frame_rate = self.window.getActualFrameRate()
        if self.frame_rate is None:
            warn('Could not fetch frame rate! Guessing it is 60Hz...')
            self.frame_rate = 60
            self.frame_duration = 1/60
        else:
            self.frame_rate = np.round(self.frame_rate)
            self.frame_duration = 1/self.frame_rate
        
        # An increment consists of two parts: an 'evidence' part, and a pause. Together, these form an 'increment'.
        # How long does each increment in total take? Enter the duration in frames (Each frame (at 60Hz) takes 16.667ms)
        self.increment_length = 7

        # How long do you want each flash to take? Enter the duration in frames
        self.flash_length = 3

        # How long do you want the time between flashes to be? 
        # By default, this is the total increment length - flash length. You probably shouldn't change this.
        self.pause_length = self.increment_length - self.flash_length

        # Maximum duration of a trial: a trial either quits after a certain time has passed, or if a certain number of increments have been shown.
        # How many increments will totally be available in a trial?
        if self.phase_durations[1] is not None:
            self.n_increments = np.ceil(self.phase_durations[1] / (self.increment_length/self.frame_rate)).astype(int)
        else:
            self.n_increments = 10

        # Here, we calculate how long each trial should maximally take in frames. Leave this untouched.
        self.max_frame = self.n_increments*self.increment_length

        # Next, we set the difficulty of the task. This is determined by the 'chance' of flashing for every flasher.
        # To make things really easy, set the chance of flashing for the correct flasher really high, and the incorrect flasher really low.
        # Proportions: (greater diff = easier; higher values = more flashes)
        self.prop_corr = .7
        self.prop_incorr = .3
        
        # Determine positions to show flashers
        if self.n_flashers == 2:
            t = 0 # modulo: start point on circle in radians. With 2 flashers, starting at t=0 means the flashers are shown horizontally. For vertical, try t=0.5*pi
        else:
            t = 0.5*np.pi # for more than 2 flashers, it's nice to start on the y-axis
        
        # Determine position of flashers in cm
        self.pos_x = radius * np.cos(t + np.arange(1, n_flashers+1) * 2 * np.pi / n_flashers)
        self.pos_y = radius * np.sin(t + np.arange(1, n_flashers+1) * 2 * np.pi / n_flashers)
                
        # prepare mask
        self.mask_idx = np.tile(np.hstack((np.repeat(0, repeats=self.flash_length), np.repeat(1, repeats=self.pause_length))), self.n_increments)
        self.mask_idx = self.mask_idx.astype(bool)
        
    def prepare_trial(self):
        """ Prepares everything for the next trial """
        
        # Define which flashing circle is correct
        correct = np.random.randint(low=0, high=self.n_flashers)
        
        # Define which keys are correct / incorrect
        self.correct_key = self.response_keys[correct]
        self.incorrect_keys = [x for x in self.response_keys if not x == self.correct_key]

        # Initialize 'increment arrays' for correct and incorrect. These are arrays filled with 0s and 1s, determining for each 'increment' whether a piece of evidence is shown or not.
        self.flashers = []
        for i in range(self.n_flashers):
            if i == correct:
                self.flashers.append(np.random.binomial(n=1, p=self.prop_corr, size=self.n_increments))
            else:
                self.flashers.append(np.random.binomial(n=1, p=self.prop_incorr, size=self.n_increments))

        for i in range(self.n_flashers):
            self.flashers[i] = np.repeat(self.flashers[i], self.increment_length)
            self.flashers[i][self.mask_idx] = 0

        # Keep track of actually shown evidence during trial
        self.counter_left = 0
        self.counter_right = 0
        
        # Prepare fixation cross component
        self.fix_cross = visual.TextStim(win=self.window, text='+', font='', pos=(0.0, 0.0), 
                                         depth=0, rgb=None, color=(1.0, 1.0, 1.0), colorSpace='rgb', 
                                         opacity=1.0, contrast=1.0, units='', ori=0.0)
        
        # Prepare actual stimuli components
        self.flasher_stim = []
        for i in range(self.n_flashers):
            self.flasher_stim.append(visual.Polygon(win=self.window, name='flasher_'+str(i), units='cm',
                                                   edges=90, size=[1,1], ori=0, pos=(self.pos_x[i], self.pos_y[i]),
                                                   lineWidth=0, lineColor=[0,0,0], lineColorSpace='rgb',
                                                   fillColor=[1,1,1], fillColorSpace='rgb', opacity=1, depth=-1.0, 
                                                   interpolate=True))

        # Prepare feedback component
        self.feedback_text_component = visual.TextStim(win=self.window, text='If you see this, updating of feedback text went wrong..', color=(100, 255, 100))
        
        # Prepare debug text component
        self.debug_text_component = visual.TextStim(win=self.window, text='', pos=(-4, 4), units='cm', height=0.5)

    def run_trial(self):
        """ Runs a single trial """
        
        # Prepare the trial
        self.prepare_trial()
        
        # Start timing
        trial_clock = core.Clock()
        phase_clock = core.Clock()
        
        # Run trial phases
        # Phase 1: Fixation cross
        max_phase_duration_frames = self.phase_durations[0]*self.frame_rate
        frame_n = -1
        while frame_n < max_phase_duration_frames-1:
            frame_n = frame_n + 1
            
            if self.debug:
                self.debug_text_component.text = 'Phase: stimulus\n' + \
                                                 str(frame_n) + '\n' + \
                                                 str(np.round(trial_clock.getTime(), 3)) + '\n' + \
                                                 str(np.round(phase_clock.getTime(), 3))
                self.debug_text_component.draw()
            
            self.fix_cross.draw()
            self.window.flip()
                        
            # check for quit
            if self.keyboard.get_key()[0] == 'escape':
                self.window.close()
                core.quit()

        # Phase 2: Stimulus
        phase_clock.reset()
        max_phase_duration_frames = self.phase_durations[1]*self.frame_rate
        frame_n = -1
        last_keypress = (None, 0)
        while last_keypress[0] is None and frame_n < max_phase_duration_frames-1:
            frame_n = frame_n + 1

            # Prepare update stimuli for this frame
            for flasher_n in range(self.n_flashers):
                self.flasher_stim[flasher_n].opacity = self.flashers[flasher_n][frame_n]
                self.flasher_stim[flasher_n].draw()

            if self.debug:
                self.debug_text_component.text = 'Phase: stimulus\n' + \
                                                 str(frame_n) + '\n' + \
                                                 str(np.round(trial_clock.getTime(), 3)) + '\n' + \
                                                 str(np.round(phase_clock.getTime(), 3))
                self.debug_text_component.draw()
            
            # Show screen/frame
            self.window.flip()
            
            # Check for key response
            last_keypress = self.keyboard.get_key()
            if last_keypress[0] == 'escape':
                self.window.close()
                core.quit()

        # Phase 3: Feedback
        phase_clock.reset()
        if last_keypress[0] == self.correct_key:
            feedback_text = 'Correct!'
            feedback_col = (100/255, 1, 100/255)
        elif last_keypress[0] in self.incorrect_keys:
            feedback_text = 'Incorrect!'
            feedback_col = (1, 100/255, 100/255)
        else:
            feedback_text = 'Too late!'
            feedback_col = (1, 100/255, 100/255)
        
        self.feedback_text_component.color = feedback_col
        self.feedback_text_component.text = feedback_text

        max_phase_duration_frames = self.phase_durations[2]*self.frame_rate
        frame_n = -1
        while frame_n < max_phase_duration_frames-1:
            frame_n = frame_n + 1

            if self.debug:
                self.debug_text_component.text = 'Phase: fb\n' + \
                                                 str(frame_n) + '\n' + \
                                                 str(np.round(trial_clock.getTime(), 3)) + '\n' + \
                                                 str(np.round(phase_clock.getTime(), 3))
                self.debug_text_component.draw()
            
            self.feedback_text_component.draw()
            self.window.flip()

            if self.keyboard.get_key()[0] == 'escape':
                self.window.close()
                core.quit()

        phase_clock.reset()
        max_phase_duration_frames = self.phase_durations[3]*self.frame_rate
        frame_n = -1
        while frame_n < max_phase_duration_frames-1:
            frame_n = frame_n + 1
            
            if self.debug:
                self.debug_text_component.text = 'Phase: ITI\n' + \
                                                 str(frame_n) + '\n' + \
                                                 str(np.round(trial_clock.getTime(), 3)) + '\n' + \
                                                 str(np.round(phase_clock.getTime(), 3))
                self.debug_text_component.draw()
            self.window.flip()
        
    def run_block(self, n_trials=5):
        for trial in range(n_trials):
            self.run_trial()
        
        self.window.close()
        core.quit()
        
        
if __name__ == '__main__':
    import psychopy
    from psychopy import data, core, gui
    from pygaze import libinput
    from pygaze.defaults import *
    import numpy as np
    from constants import *
    import os
    import sys
    
    # Store info about the experiment session
    expName = 'subcortex'
    expInfo = {u'debug': u'1', u'session': u'001', u'participant': u'1', u'gender': u'', u'age': u''}
#     dlg = gui.DlgFromDict(dictionary=expInfo, title=expName)
#     if dlg.OK == False: core.quit()
    expInfo['date'] = data.getDateStr()
    expInfo['expName'] = expName
    
    _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(sys.getfilesystemencoding())
    os.chdir(_thisDir)

    # Data file name stem = absolute path + name; later add .psyexp, .csv, .log, etc
    filename = _thisDir + os.sep + u'data/%s_%s_%s' %(expInfo['participant'], expName, expInfo['date'])

    # An ExperimentHandler isn't essential but helps with data saving
    thisExp = data.ExperimentHandler(name=expName, version='',
        extraInfo=expInfo, runtimeInfo=None,
        savePickle=True, saveWideText=True,
        dataFileName=filename)

    #save a log file for detail verbose info
    logFile = logging.LogFile(filename+'.log', level=logging.EXP)
    logging.console.setLevel(logging.WARNING)  # this outputs to the screen, not a file

    win = psychopy.visual.Window([1260, 800], monitor='testMonitor')
    kb = libinput.Keyboard(keylist=['z', 'm', 'v', 'escape'])
    FlashTrial(window=win, keyboard=kb, n_flashers=2, debug=False, response_keys=['z', 'm'], exp_handler=thisExp).run_block(n_trials=5)
    