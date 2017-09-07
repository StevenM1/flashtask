from __future__ import division
import pygaze
from pygaze import libscreen
import psychopy
from psychopy import core, visual, event, monitors
from warnings import warn
from pprint import pprint
from copy import deepcopy

class Session(object):
    
    def __init__(self, scanner=None, eyetracker=None, monitor='u2715h', debug=False):
        
        if monitor not in monitors.getAllMonitors():
            raise(IOError('Monitor %s not found in settings...' % monitor))
        
        self.scanner = scanner
        self.eyetracker = eyetracker
        self.clock = core.Clock()
        self.stopped = False
        self.debug = debug
        self.t_start = None
        self.phase_start = None
        self.setup_screen(monitor=monitor)
        
        if self.eyetracker is not None:
            self.setup_eyetracker
    
        if self.scanner is not None:
            from psychopy.hardware.emulator import launchScan
            self.scanner = launchScan(win=self.window, settings={'TR': 2.0, 'volumes': 100, 'sound': False, 'sync': 't'}, globalClock=self.clock)
    
    def setup_screen(self, monitor):
        self.display = libscreen.Display(disptype='psychopy', screennr=0)
        self.window = pygaze.expdisplay
        self.window.monitor = monitors.Monitor(monitor)  # this is necessary because the physical size is specified here

        self.frame_rate = self.window.getActualFrameRate()
        if self.frame_rate is None:
            warn('Could not fetch frame rate! Guessing it is 60Hz...')
            self.frame_rate = 60
            self.frame_duration = 1/60
        else:
            self.frame_rate = np.round(self.frame_rate)
            self.frame_duration = 1/self.frame_rate

    def setup_eyetracker(self):
        self.eyetracker.calibrate()
    
    def run(self, n_trials=5):
        fltr = FlashTrial(window=self.window, session=self, debug=self.debug)
        
        for trial_n in range(n_trials):
            fltr.reset()
            fltr.run()
            
            # After every trial, check for stop signal
            if self.stopped:
                pprint(fltr.events)
                self.stop()

        # Currently, at the end of the block, stop
        pprint(fltr.events)
        self.stop()

    def stop(self):
        
        # Print events and close window, exit python
        self.window.close()
        core.quit()


class Trial(object):
    
    def __init__(self, session, window, phase_durations, experiment_handler):
        self.session = session
        self.window = window
        self.phase_durations = phase_durations
        self.experiment_handler = experiment_handler
        self.phase = 0
        self.stopped = False
        self.events = []
        self.trial_answer = None
        
    def event(self):
        pass

    def draw(self):
        self.window.flip()
    
    def phase_forward(self):
        self.phase += 1
        self.phase_start = self.session.clock.getTime()

class FlashTrial(Trial):

    def __init__(self, window, session, parameters={'flash_length': 3, 'increment_length': 7, 'n_increments': 10, 'frame_rate':60, 'prop_correct': .7, 'prop_incorrect': .4}, 
                 phase_durations=(0.5, 1.5, 0.5, 1), n_flashers=2, response_keys=['z', 'm'], radius=3, flasher_size=1, debug=False, 
                 experiment_handler=None):
    
        """ Initialize FlashTrial class. Handles everything for stimulus presentation and recording of the Flash Task 
        
        # ToDo: RECORD / LOG everything! -> superclass? session?
        """
        
        super(FlashTrial, self).__init__(session, window, phase_durations, experiment_handler)

        self.n_flashers = n_flashers
        self.response_keys = response_keys
        self.debug = debug
        
        if not len(self.response_keys) == self.n_flashers:
            self.window.close()
            raise(IOError('The number of flashers is not the same as the number of key response options.'))        

        # An increment consists of two parts: an 'evidence' part, and a pause. Together, these form an 'increment'.
        # How long does each increment in total take? Enter the duration in frames (Each frame (at 60Hz) takes 16.667ms)
        self.increment_length = parameters['increment_length']

        # How long do you want each flash to take? Enter the duration in frames
        self.flash_length = parameters['flash_length']

        # How long do you want the time between flashes to be? 
        # By default, this is the total increment length - flash length. You probably shouldn't change this.
        self.pause_length = self.increment_length - self.flash_length

        # Maximum duration of a trial: a trial either quits after a certain time has passed, or if a certain number of increments have been shown.
        # How many increments will totally be available in a trial?
        if self.phase_durations[1] is not None:
            self.n_increments = np.ceil(self.phase_durations[1] / (self.increment_length/self.session.frame_rate)).astype(int)
        else:
            self.n_increments = parameters['n_increments']

        # Here, we calculate how long each trial should maximally take in frames. Leave this untouched.
        self.max_frame = self.n_increments*self.increment_length

        # Next, we set the difficulty of the task. This is determined by the 'chance' of flashing for every flasher.
        # To make things really easy, set the chance of flashing for the correct flasher really high, and the incorrect flasher really low.
        # Proportions: (greater diff = easier; higher values = more flashes)
        self.prop_corr = parameters['prop_correct']
        self.prop_incorr = parameters['prop_incorrect']
        
        # Determine positions to show flashers
        if self.n_flashers == 2:
            t = 0 # modulo: start point on circle in radians. With 2 flashers, starting at t=0 means the flashers are shown horizontally. For vertical, try t=0.5*pi
        else:
            t = 0.5*np.pi # for more than 2 flashers, it's nice to start on the y-axis
        
        # Determine position of flashers in cm
        self.pos_x = radius * np.cos(t + np.arange(1, n_flashers+1) * 2 * np.pi / n_flashers)
        self.pos_y = radius * np.sin(t + np.arange(1, n_flashers+1) * 2 * np.pi / n_flashers)
        
        # Prepare mask
        self.mask_idx = np.tile(np.hstack((np.repeat(0, repeats=self.flash_length), 
                                           np.repeat(1, repeats=self.pause_length))), 
                                self.n_increments)
        self.mask_idx = self.mask_idx.astype(bool)
        
    def prepare_trial(self):
        """ Prepares everything for the next trial """
        
        # Define which flashing circle is correct
        self.correct = np.random.randint(low=0, high=self.n_flashers)
        
        # Define which keys are correct / incorrect
        self.correct_key = self.response_keys[self.correct]
        self.incorrect_keys = [x for x in self.response_keys if not x == self.correct_key]

        # Initialize 'increment arrays' for correct and incorrect. These are arrays filled with 0s and 1s, determining for each 'increment' whether a piece of evidence is shown or not.
        self.flashers = []
        for i in range(self.n_flashers):
            if i == self.correct:
                self.flashers.append(np.random.binomial(n=1, p=self.prop_corr, size=self.n_increments))
            else:
                self.flashers.append(np.random.binomial(n=1, p=self.prop_incorr, size=self.n_increments))

        self.full_increment_streams = deepcopy(self.flashers)
        
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
        
    def event(self):
        """ Get and process all events (keypresses) during the current frame """

        for i, ev in enumerate(event.getKeys()):
            if len(ev) > 0:
                if ev in ['esc', 'escape']:
                    self.stopped = True
                    self.session.stopped = True
                    self.phase = 0
                    self.events.append([-99, self.session.clock.getTime(), 'escape: user killed session'])
                    print('Session stopped!')
                
                elif ev in self.response_keys:
                    if self.phase == 0:
                        self.events.append([ev, self.session.clock.getTime(), 'early keypress'])
                        
                    if self.phase == 1:
                        self.trial_answer = ev

                        if i == 0:  # First keypress
                            if ev == self.correct_key:
                                self.events.append([ev, self.session.clock.getTime(), 'first keypress', 'correct', self.session.clock.getTime() - self.phase_start])
                            else:
                                self.events.append([ev, self.session.clock.getTime(), 'first keypress', 'incorrect', self.session.clock.getTime() - self.phase_start])
                        else:
                            self.events.append([ev, self.session.clock.getTime(), 'late keypress (during stimulus)'])

                    if self.phase == 2:
                        self.events.append([ev, self.session.clock.getTime(), 'late keypress (during feedback)'])

                    if self.phase == 3:
                        self.events.append([ev, self.session.clock.getTime(), 'late keypress (during ITI)'])

                elif ev == 't':  # Scanner pulse
                    self.events.append([99, self.session.clock.getTime(), 'pulse'])                    
    
    def draw(self, frame_n):
        """ Draws components in current phase """

        if self.debug:
            self.debug_text_component.text = 'Phase: ' + str(self.phase) + '\n' + \
                                             str(frame_n) + '\n' + \
                                             str(np.round(self.session.clock.getTime() - self.t_start, 3)) + '\n' + \
                                             str(np.round(self.session.clock.getTime() - self.phase_start, 3)) + '\n' + self.correct_key
            self.debug_text_component.draw()

        if self.phase == 0:
            self.fix_cross.draw()
        
        elif self.phase == 1:
            for flasher_n in range(self.n_flashers):
                self.flasher_stim[flasher_n].opacity = self.flashers[flasher_n][frame_n]
                self.flasher_stim[flasher_n].draw()
        
        elif self.phase == 2:
            self.feedback_text_component.draw()

        super(FlashTrial, self).draw()  # Super-class handles the window-flipping
        
    def run(self):
        """ Runs a single trial. In the current set-up, trial timing is handled by counting frames.
        If frames are dropped, timing is NOT accurate!!
        """
        
        # Prepare the trial
        self.prepare_trial()
        
        # Start timing
        self.t_start = self.session.clock.getTime()
        self.phase_start = self.session.clock.getTime()

        # Log start time and additional info about this trial
        start_log_msg = [1, self.t_start, 'trial start', self.correct, self.correct_key]
#         for i in range(self.n_flashers):
#             start_log_msg.append(self.full_increment_streams[i])
        
        self.events.append(start_log_msg)
        self.events.append([2, self.phase_start, 'fixation cross start'])
        
        frame_n = -1
        while not self.stopped:
            cur_time = self.session.clock.getTime()
            frame_n = frame_n + 1

            # Run trial phases
            if self.phase == 0:  # Fixation cross                
                if cur_time - self.phase_start >= self.phase_durations[self.phase]:
                    self.events.append([3, cur_time, 'stimulus start'])
                    self.phase_forward()
                    frame_n = 0

            if self.phase == 1:  # Stimulus
                if cur_time - self.phase_start >= self.phase_durations[self.phase]:
                    self.events.append([4, cur_time, 'trial timeout'])
                    self.phase_forward()
                    frame_n = 0

                elif self.trial_answer is not None:  # key was pressed
                    self.phase_forward()
                    frame_n = 0

            if self.phase == 2:  # Feedback
                if frame_n == 0:
                    if self.trial_answer is None:
                        self.feedback_text_component.color = (1, 100/255, 100/255)
                        self.feedback_text_component.text = 'Too late!'
                    elif self.trial_answer[0] == self.correct_key:
                        self.feedback_text_component.color = (100/255, 1, 100/255)
                        self.feedback_text_component.text = 'Correct!'
                    elif self.trial_answer[0] in self.incorrect_keys:
                        self.feedback_text_component.color = (1, 100/255, 100/255)
                        self.feedback_text_component.text = 'Wrong!'
                
                if cur_time - self.phase_start >= self.phase_durations[self.phase]:
                    self.phase_forward()
                    frame_n = 0

            if self.phase == 3:  # ITI
                if cur_time - self.phase_start >= self.phase_durations[self.phase]:
                    self.events.append([5, cur_time, 'trial end', cur_time - self.t_start])
                    self.stopped = True
            
            # Show screen/frame
            self.event()
            self.draw(frame_n)
            
    def reset(self):
        self.stopped = False
        self.phase = 0
        self.trial_answer = None
    
    def run_block(self, n_trials=5):
        for trial in range(n_trials):
            self.reset()
            self.run()



if __name__ == '__main__':
    import psychopy
    from psychopy import data, core
    from pygaze import libinput
    from pygaze.defaults import *
    import numpy as np
    from constants import *
    import os
    import sys
    
    ses = Session(monitor='laptop', scanner=True, debug=True).run()
